"""Un ranking que solo existe gracias a 2020 no es un ranking.

El COVID es el 8 % de las observaciones y una fraccion mucho mayor del error total.
Este modulo parte la ventana de prueba en tres y comprueba si el orden aguanta.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .backtest import resumen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"


def _anio(origen: str) -> int:
    return int(str(origen)[:4])


def particion(detalle: pd.DataFrame, nombre: str, top: int = 10) -> pd.DataFrame:
    detalle = detalle.copy()
    detalle["anio"] = detalle.origen.map(_anio)

    tramos = {
        "completo": detalle,
        "sin COVID (excluye 2020-2021)": detalle[~detalle.anio.isin([2020, 2021])],
        "solo COVID (2020-2021)": detalle[detalle.anio.isin([2020, 2021])],
        "post-COVID (2022+)": detalle[detalle.anio >= 2022],
    }

    columnas = {}
    for etiqueta, sub in tramos.items():
        if sub.empty:
            continue
        t = resumen(sub).set_index("modelo")
        columnas[etiqueta] = t.mae
        columnas[etiqueta + " |rank"] = t.mae.rank()

    tabla = pd.DataFrame(columnas)
    orden = tabla["completo"].sort_values().index
    tabla = tabla.loc[orden]

    print(f"\n{'=' * 100}\n{nombre} - MAE por subperiodo (y puesto en cada uno)\n{'=' * 100}")
    print(f"{'modelo':32s} {'completo':>9s} {'sin COVID':>10s} {'rk':>3s} "
          f"{'solo COVID':>11s} {'rk':>3s} {'post-2022':>10s} {'rk':>3s}")
    print("-" * 100)
    for modelo, r in tabla.head(top + 6).iterrows():
        def celda(k, rk):
            v = r.get(k)
            p = r.get(rk)
            return (f"{v:>10.3f} {int(p):3d}" if pd.notna(v) and pd.notna(p) else f"{'-':>10s} {'-':>3s}")
        print(f"{modelo[:32]:32s} {r['completo']:9.3f} "
              f"{celda('sin COVID (excluye 2020-2021)', 'sin COVID (excluye 2020-2021) |rank')} "
              f"{celda('solo COVID (2020-2021)', 'solo COVID (2020-2021) |rank')} "
              f"{celda('post-COVID (2022+)', 'post-COVID (2022+) |rank')}")
    print("-" * 100)
    return tabla


def main() -> None:
    for archivo, nombre in [("pista_a_detalle.csv", "PISTA A (anual)"),
                            ("pista_b_detalle.csv", "PISTA B (mensual)")]:
        ruta = SALIDAS / archivo
        if not ruta.exists():
            print(f"! falta {ruta}")
            continue
        tabla = particion(pd.read_csv(ruta), nombre)
        tabla.to_csv(SALIDAS / archivo.replace("_detalle", "_robustez"))


if __name__ == "__main__":
    main()
