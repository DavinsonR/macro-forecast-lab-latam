"""El laboratorio sobre LATAM. `uv run python -m macro_lab.lab_latam`

Un pais no distingue un hallazgo de una casualidad. La pregunta que este modulo responde
es si el patron encontrado en Colombia -flexibles en calma, simples en la ruptura- se
repite cuando se corre el mismo protocolo, sin tocar nada, sobre las demas economias.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import backtest, combinacion, datos, latam
from .modelos import Modelo, _naive, _deriva, _red, _sarimax, _supervisado

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


def _anio(origen: str) -> int:
    return int(str(origen)[:4])


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
    """Por pais y por regimen: que familia gana."""
    detalle = detalle.copy()
    detalle["anio"] = detalle.origen.map(_anio)
    detalle["regimen"] = detalle.anio.isin(RUPTURA).map({True: "ruptura", False: "calma"})

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
            ganancia_pct=top.ganancia_pct, p=top.dm_p, n=int(top.n),
        ))
    tabla = pd.DataFrame(filas)

    print(f"\n{'=' * 98}\n{titulo}\n{'=' * 98}")
    print(f"{'pais':6s} {'regimen':9s} {'mejor modelo':24s} {'familia':14s} "
          f"{'MAE':>7s} {'ingenuo':>8s} {'gana':>7s} {'p':>7s}")
    print("-" * 98)
    for _, r in tabla.sort_values(["iso3", "regimen"]).iterrows():
        gan = f"{r.ganancia_pct:+6.1f}%" if pd.notna(r.ganancia_pct) else "     -"
        p = f"{r.p:7.3f}" if pd.notna(r.p) else "      -"
        ing = f"{r.mae_ingenuo:8.3f}" if pd.notna(r.mae_ingenuo) else "       -"
        print(f"{r.iso3:6s} {r.regimen:9s} {r.mejor[:24]:24s} {r.familia[:14]:14s} "
              f"{r.mae:7.3f} {ing} {gan} {p}")
    print("-" * 98)

    print("\n--- Cuantas veces gana cada familia ---")
    conteo = (tabla.groupby(["regimen", "familia"]).size()
              .unstack(fill_value=0))
    print(conteo.to_string())
    return tabla


def ranking_agregado(detalle: pd.DataFrame, titulo: str) -> pd.DataFrame:
    """MAE relativo al ingenuo, promediado entre paises.

    Se normaliza por pais antes de promediar: Argentina y Venezuela tienen una
    volatilidad que es un orden de magnitud mayor que la de Chile, y un promedio crudo de
    MAE seria un promedio de las volatilidades nacionales, no de la calidad de los modelos.
    """
    detalle = detalle.copy()
    detalle["anio"] = detalle.origen.map(_anio)
    detalle["regimen"] = detalle.anio.isin(RUPTURA).map({True: "ruptura", False: "calma"})

    filas = []
    for (iso3, reg), g in detalle.groupby(["iso3", "regimen"]):
        mae = g.groupby("modelo").error.apply(lambda e: e.abs().mean())
        cob = g.groupby("modelo").error.apply(lambda e: e.notna().mean())
        base = mae.get("Ingenuo")
        if base is None or not pd.notna(base) or base == 0:
            continue
        for modelo, v in mae.items():
            # Sin cobertura no hay comparacion: el MAE saldria de los origenes faciles.
            if cob.get(modelo, 0) < 0.90:
                continue
            filas.append(dict(iso3=iso3, regimen=reg, modelo=modelo, mae_rel=v / base))

    rel = pd.DataFrame(filas)
    pivote = (rel.pivot_table(index="modelo", columns="regimen", values="mae_rel",
                              aggfunc="median")
              .sort_values("calma"))

    print(f"\n{'=' * 78}\n{titulo}\n"
          f"MAE mediano relativo al ingenuo (1,00 = igual que el ingenuo; menor es mejor)\n"
          f"{'=' * 78}")
    print(f"{'modelo':28s} {'calma':>9s} {'ruptura':>9s} {'diferencia':>11s}")
    print("-" * 78)
    for modelo, r in pivote.iterrows():
        calma, rup = r.get("calma"), r.get("ruptura")
        c_txt = f"{calma:9.3f}" if pd.notna(calma) else f"{'-':>9s}"
        r_txt = f"{rup:9.3f}" if pd.notna(rup) else f"{'-':>9s}"
        dif = f"{rup - calma:+11.2f}" if pd.notna(calma) and pd.notna(rup) else f"{'-':>11s}"
        print(f"{modelo[:28]:28s} {c_txt} {r_txt} {dif}")
    print("-" * 78)
    return pivote


def pista_c() -> None:
    print("\n" + "#" * 98)
    print("#  PISTA C - PIB real trimestral, LATAM (FMI IFS via DBnomics)")
    print("#" * 98)

    trim = latam.descargar_trimestral_latam()
    if trim.empty:
        print("! sin datos trimestrales")
        return

    partes = []
    for iso3 in sorted(trim.iso3.unique()):
        y = latam.serie_crecimiento_trimestral(trim, iso3)
        partes.append(corrida_pais(y, iso3, min_entrenamiento=40))

    detalle = pd.concat([p for p in partes if not p.empty], ignore_index=True)
    detalle.to_csv(SALIDAS / "pista_c_detalle.csv", index=False)

    tabla_por_regimen(detalle, "PISTA C - mejor modelo por pais y regimen (trimestral)")
    pivote = ranking_agregado(detalle, "PISTA C - agregado LATAM")
    pivote.to_csv(SALIDAS / "pista_c_agregado.csv")


def pista_d() -> None:
    print("\n" + "#" * 98)
    print("#  PISTA D - crecimiento anual del PIB, 20 paises (Banco Mundial)")
    print("#" * 98)

    largo = latam.descargar_anual_latam(datos.INDICADORES)
    partes = []
    for iso3 in sorted(largo.iso3.unique()):
        panel, _ = latam.panel_pais(largo, iso3, min_ratio=3.0)
        if panel.empty or "pib_crecimiento" not in panel.columns:
            print(f"  {iso3:18s} sin panel viable")
            continue
        y = panel["pib_crecimiento"]
        partes.append(corrida_pais(y, iso3, min_entrenamiento=30))

    detalle = pd.concat([p for p in partes if not p.empty], ignore_index=True)
    detalle.to_csv(SALIDAS / "pista_d_detalle.csv", index=False)

    tabla_por_regimen(detalle, "PISTA D - mejor modelo por pais y regimen (anual)")
    pivote = ranking_agregado(detalle, "PISTA D - agregado LATAM")
    pivote.to_csv(SALIDAS / "pista_d_agregado.csv")


def main() -> None:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    pista_c()
    pista_d()
    print(f"\n\nResultados en {SALIDAS}")


if __name__ == "__main__":
    main()
