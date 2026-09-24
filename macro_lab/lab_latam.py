"""El laboratorio sobre LATAM. `uv run python -m macro_lab.lab_latam`

Un pais no distingue un hallazgo de una casualidad. La pregunta que este modulo responde
es si el patron encontrado en Colombia -flexibles en calma, simples en la ruptura- se
repite cuando se corre el mismo protocolo, sin tocar nada, sobre las demas economias.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import backtest, combinacion, datos, latam
from .modelos import Modelo, _deriva, _naive, _red, _sarimax, _supervisado

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"
RUPTURA = [2020, 2021]


def catalogo_latam() -> list[Modelo]:
    """Catalogo recortado: un representante fuerte por familia, mas las combinaciones.

    Correr los 19 modelos en 20 paises multiplica el costo sin cambiar la conclusion:
    lo que se contrasta es el comportamiento de las familias, no el orden interno de cada
    una, que ya quedo medido en la corrida de Colombia.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge

    M = [
        Modelo("Ingenuo", "referencia", _naive),
        Modelo("Deriva", "referencia", _deriva),
        Modelo("AR(1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 0, 0), trend="c")),
        Modelo("ARMA(2,2)", "Box-Jenkins", _sarimax, params=dict(order=(2, 0, 2), trend="c")),
        Modelo("ARIMA(1,1,1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 1, 1))),
        Modelo("Ridge sobre rezagos", "regularizado", _supervisado,
               params=dict(estimador=Ridge(alpha=1.0), n_lags=8)),
        Modelo("Random Forest", "aprendizaje", _supervisado,
               params=dict(estimador=RandomForestRegressor(n_estimators=300, random_state=7),
                           n_lags=8)),
        Modelo("LSTM(16)", "red neuronal", _red,
               params=dict(arquitectura="lstm", ventana=8, unidades=16)),
    ]
    return M + combinacion.catalogo_combinaciones()


def corrida_pais(y: pd.Series, etiqueta: str, min_entrenamiento: int) -> pd.DataFrame:
    if len(y) < min_entrenamiento + 8:
        print(f"  {etiqueta:18s} serie corta ({len(y)}), se omite")
        return pd.DataFrame()
    det = backtest.origen_movil(y, catalogo_latam(), h=1,
                                min_entrenamiento=min_entrenamiento, verbose=False)
    det["iso3"] = etiqueta
    n_or = det.origen.nunique()
    mejor = backtest.resumen(det).iloc[0]
    print(f"  {etiqueta:18s} {n_or:3d} origenes | mejor: {mejor.modelo:22s} "
          f"MAE {mejor.mae:.3f}")
    return det


def tabla_por_regimen(detalle: pd.DataFrame, titulo: str) -> pd.DataFrame:
    """Por pais y por regimen (del periodo pronosticado): que familia gana."""
    detalle = detalle.copy()
    detalle["regimen"] = backtest.regimen(detalle, RUPTURA)

    filas = []
    for (iso3, reg), g in detalle.groupby(["iso3", "regimen"]):
        r = backtest.resumen(g)
        r = r[r.rankeable]  # un modelo que no entrego pronostico no puede ganar
        if r.empty or r.mae.isna().all():
            continue
        top = r.iloc[0]
        ing = r[r.modelo == "Ingenuo"]
        filas.append(dict(
            iso3=iso3, regimen=reg, mejor=top.modelo, familia=top.familia,
            mae=top.mae, mae_ingenuo=float(ing.mae.iloc[0]) if len(ing) else None,
            ganancia_pct=top.ganancia_pct, p=top.dm_p, p_holm=top.dm_p_holm,
            n=int(top.n),
        ))
    tabla = pd.DataFrame(filas)

    print(f"\n{'=' * 106}\n{titulo}\n{'=' * 106}")
    print(f"{'pais':6s} {'regimen':9s} {'mejor modelo':24s} {'familia':14s} "
          f"{'MAE':>7s} {'ingenuo':>8s} {'gana':>7s} {'p':>7s} {'p Holm':>7s}")
    print("-" * 106)
    for _, r in tabla.sort_values(["iso3", "regimen"]).iterrows():
        gan = f"{r.ganancia_pct:+6.1f}%" if pd.notna(r.ganancia_pct) else "     -"
        p = f"{r.p:7.3f}" if pd.notna(r.p) else "      -"
        ph = f"{r.p_holm:7.3f}" if pd.notna(r.p_holm) else "      -"
        ing = f"{r.mae_ingenuo:8.3f}" if pd.notna(r.mae_ingenuo) else "       -"
        print(f"{r.iso3:6s} {r.regimen:9s} {r.mejor[:24]:24s} {r.familia[:14]:14s} "
              f"{r.mae:7.3f} {ing} {gan} {p} {ph}")
    print("-" * 106)

    print("\n--- Cuantas veces gana cada familia ---")
    conteo = (tabla.groupby(["regimen", "familia"]).size()
              .unstack(fill_value=0))
    print(conteo.to_string())
    return tabla


def _wilcoxon(v: pd.Series) -> float:
    """Wilcoxon de rangos con signo sobre log(MAE relativo) contra cero."""
    v = np.log(v.dropna().astype(float))
    v = v[v != 0]
    return float(stats.wilcoxon(v).pvalue) if len(v) >= 6 else np.nan


def relativo_por_pais(detalle: pd.DataFrame) -> pd.DataFrame:
    """Por pais, regimen y modelo: MAE relativo al ingenuo y si la mejora es significativa.

    Solo entran modelos con cobertura suficiente: sin ella el MAE saldria de los origenes
    faciles (R-07).
    """
    detalle = detalle.copy()
    detalle["regimen"] = backtest.regimen(detalle, RUPTURA)

    filas = []
    for (iso3, reg), g in detalle.groupby(["iso3", "regimen"]):
        r = backtest.resumen(g).set_index("modelo")
        if "Ingenuo" not in r.index:
            continue
        base = r.loc["Ingenuo", "mae"]
        if not pd.notna(base) or base == 0:
            continue
        for modelo, fila in r.iterrows():
            if not fila.rankeable:
                continue
            gana_sig = bool(pd.notna(fila.dm_p) and fila.dm_p < 0.05
                            and fila.ganancia_pct > 0)
            filas.append(dict(iso3=iso3, regimen=reg, modelo=modelo,
                              mae_rel=fila.mae / base, dm_p=fila.dm_p, gana_sig=gana_sig))
    return pd.DataFrame(filas)


def ranking_agregado(rel: pd.DataFrame, titulo: str) -> pd.DataFrame:
    """MAE relativo al ingenuo, mediana entre paises, con su prueba.

    Se normaliza por pais antes de agregar: Argentina y Venezuela tienen una volatilidad
    que es un orden de magnitud mayor que la de Chile, y un promedio crudo de MAE seria un
    promedio de las volatilidades nacionales, no de la calidad de los modelos.

    La significancia (R-06) va en dos niveles: por pais, cuantos dan una mejora con
    Diebold-Mariano p < 0,05; entre paises, Wilcoxon sobre log(MAE relativo). Los paises
    son las observaciones independientes.
    """
    agregado = rel.groupby(["modelo", "regimen"]).agg(
        mediana=("mae_rel", "median"), n_paises=("mae_rel", "size"),
        paises_sig=("gana_sig", "sum"), p_wilcoxon=("mae_rel", _wilcoxon))
    pivote = agregado.unstack("regimen")
    pivote.columns = [f"{m}_{r}" for m, r in pivote.columns]
    pivote = pivote.sort_values("mediana_calma")

    print(f"\n{'=' * 88}\n{titulo}\n"
          f"MAE mediano relativo al ingenuo (1,00 = igual que el ingenuo; menor es mejor)\n"
          f"{'=' * 88}")
    print(f"{'modelo':28s} {'calma':>8s} {'p Wilc':>7s} {'sig/n':>7s}   "
          f"{'ruptura':>8s} {'p Wilc':>7s} {'sig/n':>7s}")
    print("-" * 88)

    def bloque(r, reg):
        med, pw = r.get(f"mediana_{reg}"), r.get(f"p_wilcoxon_{reg}")
        n, sig = r.get(f"n_paises_{reg}"), r.get(f"paises_sig_{reg}")
        if not pd.notna(med):
            return f"{'-':>8s} {'-':>7s} {'-':>7s}"
        pw_t = f"{pw:7.3f}" if pd.notna(pw) else f"{'-':>7s}"
        conteo = f"{int(sig)}/{int(n)}"
        return f"{med:8.3f} {pw_t} {conteo:>7s}"

    for modelo, r in pivote.iterrows():
        print(f"{modelo[:28]:28s} {bloque(r, 'calma')}   {bloque(r, 'ruptura')}")
    print("-" * 88)
    print("p Wilc: Wilcoxon entre paises sobre log(MAE relativo). "
          "sig/n: paises con mejora DM p < 0,05 / paises evaluados.")
    return pivote


def _cerrar(detalle: pd.DataFrame, pista: str, nombre: str) -> None:
    detalle.to_csv(SALIDAS / f"pista_{pista}_detalle.csv", index=False)
    tabla = tabla_por_regimen(detalle, f"PISTA {pista.upper()} - mejor modelo por pais "
                                       f"y regimen ({nombre})")
    tabla.to_csv(SALIDAS / f"pista_{pista}_por_pais.csv", index=False)
    rel = relativo_por_pais(detalle)
    rel.to_csv(SALIDAS / f"pista_{pista}_relativo_pais.csv", index=False)
    pivote = ranking_agregado(rel, f"PISTA {pista.upper()} - agregado LATAM")
    pivote.to_csv(SALIDAS / f"pista_{pista}_agregado.csv")


def pista_c() -> None:
    print("\n" + "#" * 98)
    print("#  PISTA C - PIB real trimestral, LATAM (FMI IFS via DBnomics)")
    print("#" * 98)

    trim = latam.descargar_trimestral_latam()
    if trim.empty:
        print("! sin datos trimestrales")
        return
    ajustadas = sorted(trim.loc[trim.ajuste == "ajustada", "iso3"].unique())
    if ajustadas:
        print(f"  AVISO R-05: serie ajustada estacionalmente (sin alternativa en el IFS) "
              f"en {len(ajustadas)} paises: {', '.join(ajustadas)}")

    partes = []
    for iso3 in sorted(trim.iso3.unique()):
        y = latam.serie_crecimiento_trimestral(trim, iso3)
        partes.append(corrida_pais(y, iso3, min_entrenamiento=40))

    detalle = pd.concat([p for p in partes if not p.empty], ignore_index=True)
    _cerrar(detalle, "c", "trimestral")


def frontera_latam(largo: pd.DataFrame) -> pd.DataFrame:
    """La frontera de cobertura de cada pais, medida antes de modelar (R-08).

    `n33`, `n20`, `n14`: anios completos al exigir las k variables de mayor cobertura del
    pais. `n_panel` x `k_panel`: el panel contiguo mas grande con n/p >= 3.
    """
    filas = []
    for iso3, sub in largo.groupby("iso3"):
        ancho = sub.pivot_table(index="anio", columns="variable", values="valor")
        cobertura = ancho.notna().sum().sort_values(ascending=False)
        fila = dict(iso3=iso3, pais=sub.pais.iloc[0])
        for k in (33, 20, 14):
            fila[f"n{k}"] = (len(ancho[list(cobertura.index[:k])].dropna())
                             if len(cobertura) >= k else 0)
        panel, _ = latam.panel_pais(largo, iso3, min_ratio=3.0)
        fila.update(n_panel=len(panel), k_panel=panel.shape[1])
        filas.append(fila)
    return pd.DataFrame(filas)


def pista_d() -> None:
    print("\n" + "#" * 98)
    print("#  PISTA D - crecimiento anual del PIB, 20 paises (Banco Mundial)")
    print("#" * 98)

    largo = latam.descargar_anual_latam(datos.INDICADORES)
    frontera = frontera_latam(largo)
    frontera.to_csv(SALIDAS / "frontera_latam.csv", index=False)
    print(f"  frontera: con 33 variables, {int((frontera.n33 == 0).sum())} de "
          f"{len(frontera)} paises quedan con cero anios completos")
    partes = []
    for iso3 in sorted(largo.iso3.unique()):
        # El catalogo es univariado: el objetivo no se recorta al panel de ~20 variables,
        # que solo decide la muestra de los modelos que las usan (B-005).
        # Sin los tramos rotos de la fuente (B-010): Honduras queda corta y sale.
        y = latam.serie_anual(largo, iso3).rename(iso3)
        if y.empty:
            print(f"  {iso3:18s} sin serie de crecimiento")
            continue
        partes.append(corrida_pais(y, iso3, min_entrenamiento=30))

    detalle = pd.concat([p for p in partes if not p.empty], ignore_index=True)
    _cerrar(detalle, "d", "anual")


def main() -> None:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    pista_c()
    pista_d()
    print(f"\n\nResultados en {SALIDAS}")


if __name__ == "__main__":
    main()
