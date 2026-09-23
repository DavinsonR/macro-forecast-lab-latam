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
    detalle["anio"] = detalle.origen.str[:4].astype(int)

    tramos = {
        "completo": detalle,
        "calma": detalle[~detalle.anio.isin(RUPTURA)],
        "ruptura": detalle[detalle.anio.isin(RUPTURA)],
    }
    columnas = {}
    for etiqueta, sub in tramos.items():
        t = backtest.resumen(sub).set_index("modelo")
        columnas[etiqueta] = t.mae
    tabla = pd.DataFrame(columnas).sort_values("completo")
    tabla.to_csv(SALIDAS / "combinacion_resumen.csv")

    base = tabla.loc["Ingenuo"]
    print(f"\n{'=' * 84}\nCOMBINACION POR REGIMEN - MAE por tramo "
          f"(y % de mejora sobre el ingenuo)\n{'=' * 84}")
    print(f"{'modelo':28s} {'completo':>18s} {'calma':>18s} {'ruptura':>18s}")
    print("-" * 84)
    for modelo, r in tabla.iterrows():
        def celda(col):
            v, b = r[col], base[col]
            if pd.isna(v):
                return f"{'-':>18s}"
            if modelo == "Ingenuo":
                return f"{v:8.3f}   (ref)  "
            return f"{v:8.3f} ({(1 - v / b) * 100:+5.1f}%)"
        print(f"{modelo[:28]:28s} {celda('completo')} {celda('calma')} {celda('ruptura')}")
    print("-" * 84)
    print(f"\nSalidas en {SALIDAS}")


if __name__ == "__main__":
    main()
