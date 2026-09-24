"""Contraste directo de la combinacion por regimen sobre el ISE mensual de Colombia.

Solo las piezas que importan para la pregunta: los dos extremos (ingenuo y AR(1) por el
lado robusto, Random Forest y LSTM por el flexible) y las combinaciones que intentan
quedarse con lo mejor de ambos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import backtest, combinacion, datos
from .modelos import Modelo, _naive, _red, _sarimax, _supervisado

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"
ISE_XLSX = RAIZ / "datos" / "crudo" / "anex-ISE-12actividades.xlsx"
RUPTURA = [2020, 2021]


def catalogo() -> list[Modelo]:
    from sklearn.ensemble import RandomForestRegressor

    return [
        Modelo("Ingenuo", "referencia", _naive),
        Modelo("AR(1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 0, 0), trend="c")),
        Modelo("Random Forest", "aprendizaje", _supervisado,
               params=dict(estimador=RandomForestRegressor(n_estimators=400, random_state=7),
                           n_lags=12)),
        Modelo("LSTM(16) v12", "red neuronal", _red,
               params=dict(arquitectura="lstm", ventana=12, unidades=16)),
    ] + combinacion.catalogo_combinaciones()


def main() -> None:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    ise = datos.serie_ise(ISE_XLSX)
    y = (ise.pct_change(12) * 100).dropna().rename("ise_var_anual")
    print(f"ISE, variacion anual: {len(y)} observaciones")

    rastro = combinacion.rastro_pesos(y, min_entrenamiento=120)
    rastro.to_csv(SALIDAS / "combinacion_pesos.csv", index=False)
    rastro["anio"] = rastro.origen.str[:4].astype(int)
    print("\n--- Peso medio al modelo robusto, por ano ---")
    print("(el interruptor solo ve el pasado en cada origen)")
    for anio, g in rastro.groupby("anio"):
        barra = "#" * int(round(g.peso_robusto.mean() * 40))
        print(f"  {anio}  {g.peso_robusto.mean():.2f}  {barra}")

    detalle = backtest.origen_movil(y, catalogo(), h=1, min_entrenamiento=120)
    detalle.to_csv(SALIDAS / "combinacion_detalle.csv", index=False)
    detalle["regimen"] = backtest.regimen(detalle, RUPTURA)

    tramos = {
        "completo": detalle,
        "calma": detalle[detalle.regimen == "calma"],
        "ruptura": detalle[detalle.regimen == "ruptura"],
    }
    columnas = {}
    for etiqueta, sub in tramos.items():
        t = backtest.resumen(sub).set_index("modelo")
        columnas[f"mae_{etiqueta}"] = t.mae.where(t.rankeable)
        columnas[f"ganancia_{etiqueta}"] = t.ganancia_pct.where(t.rankeable)
        columnas[f"p_{etiqueta}"] = t.dm_p.where(t.rankeable)
        columnas[f"cobertura_{etiqueta}"] = t.cobertura
    tabla = pd.DataFrame(columnas).sort_values("mae_completo")
    tabla.to_csv(SALIDAS / "combinacion_resumen.csv")

    print(f"\n{'=' * 96}\nCOMBINACION POR REGIMEN - MAE por tramo, % sobre el ingenuo y p "
          f"de Diebold-Mariano\n(regimen del mes pronosticado; las piezas se eligieron "
          f"mirando esta serie: hipotesis, R-10)\n{'=' * 96}")
    print(f"{'modelo':28s} {'completo':>22s} {'calma':>22s} {'ruptura':>22s}")
    print("-" * 96)
    for modelo, r in tabla.iterrows():
        def celda(tramo):
            v, g, p = r[f"mae_{tramo}"], r[f"ganancia_{tramo}"], r[f"p_{tramo}"]
            if pd.isna(v):
                return f"{'-':>22s}"
            if modelo == "Ingenuo":
                return f"{v:7.3f}   (ref)       "
            p_txt = f"{p:5.3f}" if pd.notna(p) else "  -  "
            return f"{v:7.3f} {g:+6.1f}% p={p_txt}"
        print(f"{modelo[:28]:28s} {celda('completo')} {celda('calma')} {celda('ruptura')}")
    print("-" * 96)
    print(f"\nSalidas en {SALIDAS}")


if __name__ == "__main__":
    main()
