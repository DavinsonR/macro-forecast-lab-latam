"""Evaluacion con origen movil y ventana expansiva.

El unico protocolo que no se enganta a si mismo: se fija un origen, se entrena solo con
lo anterior, se pronostica, se anota el error, se avanza el origen. Cada modelo se
reajusta por completo en cada origen. Es caro y es el punto.

Lo que este modulo NO hace, a proposito:
  - No selecciona hiperparametros mirando el error de prueba.
  - No promedia modelos elegidos por su desempeno en la misma muestra donde se miden.
  - No rellena el fallo de un modelo con el pronostico de otro: si un modelo no ajusta,
    queda como faltante y se reporta cuantas veces fallo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .modelos import Modelo


def origen_movil(y: pd.Series, modelos: list[Modelo], h: int = 1,
                 min_entrenamiento: int = 30, X: pd.DataFrame | None = None,
                 verbose: bool = True) -> pd.DataFrame:
    """Devuelve una fila por (modelo, origen, horizonte) con su error."""
    filas = []
    origenes = range(min_entrenamiento, len(y) - h + 1)
    total = len(list(origenes))
    if verbose:
        print(f"  origenes: {total} | horizonte: {h} | modelos: {len(modelos)}")

    for i, t in enumerate(range(min_entrenamiento, len(y) - h + 1)):
        y_tr = y.iloc[:t]
        real = y.iloc[t:t + h].to_numpy(dtype=float)
        X_tr = X.iloc[:t] if X is not None else None
        for m in modelos:
            pron = m.predecir(y_tr, h, X_tr)
            for paso in range(h):
                filas.append(dict(
                    modelo=m.nombre, familia=m.familia, origen=str(y.index[t - 1]),
                    objetivo=str(y.index[t + paso]), paso=paso + 1,
                    real=real[paso], pronostico=pron[paso],
                    error=pron[paso] - real[paso],
                ))
        if verbose and total > 6 and (i + 1) % max(total // 6, 1) == 0:
            print(f"    {i + 1}/{total}")
    return pd.DataFrame(filas)


def anio(etiqueta) -> int:
    """Anio de una etiqueta de periodo: '2020', '2020Q1' o '2020-03-01'."""
    return int(str(etiqueta)[:4])


def regimen(detalle: pd.DataFrame, ruptura=(2020, 2021)) -> pd.Series:
    """'ruptura' o 'calma' segun el anio del periodo PRONOSTICADO, no del origen.

    El error de una fila es el del objetivo. Clasificar por el origen desplaza el regimen
    un periodo: en datos anuales, el pronostico de la caida de 2020 (origen 2019) caia en
    la calma. Ver B-002 en la bitacora.
    """
    anios = detalle.objetivo.map(anio)
    return anios.isin(list(ruptura)).map({True: "ruptura", False: "calma"})


def _holm(p: pd.Series) -> pd.Series:
    """Ajuste de Holm-Bonferroni. Los NaN no cuentan como pruebas."""
    validos = p.dropna().sort_values()
    m = len(validos)
    ajustada = pd.Series(np.nan, index=p.index)
    acumulado = 0.0
    for i, (idx, v) in enumerate(validos.items()):
        acumulado = max(acumulado, min(1.0, (m - i) * v))
        ajustada[idx] = acumulado
    return ajustada


def resumen(detalle: pd.DataFrame, referencia: str = "Ingenuo",
            min_cobertura: float = 0.90) -> pd.DataFrame:
    """Tabla final: MAE, RMSE, ganancia sobre la referencia y Diebold-Mariano.

    `min_cobertura` es la salvaguarda contra el sesgo de supervivencia. Un modelo que
    revienta en los origenes dificiles y solo entrega pronostico en los faciles muestra un
    MAE bajisimo que no significa nada: no compitio en las observaciones que importaban.
    Por debajo de ese umbral el modelo se reporta pero queda fuera del ordenamiento, con
    su cobertura a la vista.
    """
    err_ref = (detalle[detalle.modelo == referencia]
               .set_index(["origen", "paso"]).error)

    filas = []
    for (nombre, familia), g in detalle.groupby(["modelo", "familia"], sort=False):
        e = g.error.dropna()
        n_fallos = int(g.error.isna().sum())
        if len(e) == 0:
            filas.append(dict(modelo=nombre, familia=familia, mae=np.nan, rmse=np.nan,
                              mae_mediano=np.nan, ganancia_pct=np.nan, dm_p=np.nan,
                              n=0, fallos=n_fallos, cobertura=0.0))
            continue
        mae, rmse = e.abs().mean(), np.sqrt((e ** 2).mean())

        ganancia, p_dm = np.nan, np.nan
        if nombre != referencia and len(err_ref):
            par = (g.set_index(["origen", "paso"]).error
                   .to_frame("m").join(err_ref.to_frame("r"), how="inner").dropna())
            if len(par) > 5:
                mae_ref = par.r.abs().mean()
                ganancia = (1 - par.m.abs().mean() / mae_ref) * 100 if mae_ref else np.nan
                d = par.m.abs() - par.r.abs()
                if d.std(ddof=1) > 0:
                    p_dm = float(stats.ttest_1samp(d, 0.0).pvalue)

        filas.append(dict(modelo=nombre, familia=familia, mae=mae, rmse=rmse,
                          mae_mediano=e.abs().median(), ganancia_pct=ganancia,
                          dm_p=p_dm, n=len(e), fallos=n_fallos,
                          cobertura=len(e) / (len(e) + n_fallos)))

    tabla = pd.DataFrame(filas)
    tabla["rankeable"] = tabla.cobertura >= min_cobertura
    # Holm solo sobre los que compiten: los excluidos por cobertura no son pruebas.
    tabla["dm_p_holm"] = _holm(tabla.dm_p.where(tabla.rankeable))
    # Los no rankeables caen al final sin competir por el primer puesto.
    return (tabla.sort_values(["rankeable", "mae"], ascending=[False, True],
                              na_position="last")
            .reset_index(drop=True))


def imprimir(tabla: pd.DataFrame, titulo: str, referencia: str = "Ingenuo") -> None:
    print(f"\n{'=' * 100}\n{titulo}\n{'=' * 100}")
    print(f"{'#':>2s} {'modelo':30s} {'familia':14s} {'MAE':>7s} {'RMSE':>7s} "
          f"{'vs ref':>8s} {'p':>7s} {'p Holm':>7s} {'cobert':>7s}")
    print("-" * 100)
    for i, r in tabla.iterrows():
        gan = "  ref  " if r.modelo == referencia else (
            f"{r.ganancia_pct:+7.1f}%" if pd.notna(r.ganancia_pct) else "      -")
        p = f"{r.dm_p:7.3f}" if pd.notna(r.dm_p) else "      -"
        ph = r.get("dm_p_holm", np.nan)
        p_holm = f"{ph:7.3f}" if pd.notna(ph) else "      -"
        mae = f"{r.mae:7.3f}" if pd.notna(r.mae) else "      -"
        rmse = f"{r.rmse:7.3f}" if pd.notna(r.rmse) else "      -"
        marca = " *" if pd.notna(ph) and ph < 0.05 and r.ganancia_pct > 0 else ""
        if not r.get("rankeable", True):
            marca += "  <-- cobertura insuficiente, fuera del ordenamiento"
        cob = f"{r.get('cobertura', 1.0) * 100:6.0f}%"
        print(f"{i + 1:2d} {r.modelo[:30]:30s} {r.familia[:14]:14s} {mae} {rmse} "
              f"{gan} {p} {p_holm} {cob}{marca}")
    print("-" * 100)
    print("* mejora sobre la referencia significativa al 5 % tras Holm "
          "(Diebold-Mariano pareado)")
