"""Corrida completa del laboratorio. `uv run python -m macro_lab.main`"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import backtest, datos, modelos

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"
ISE_XLSX = RAIZ / "datos" / "crudo" / "anex-ISE-12actividades.xlsx"


def seccion(txt: str) -> None:
    print(f"\n\n{'#' * 92}\n#  {txt}\n{'#' * 92}")


def pista_a() -> None:
    seccion("PISTA A - crecimiento anual del PIB de Colombia (Banco Mundial, 1961-2025)")

    macro = datos.descargar_banco_mundial()
    print(f"matriz cruda: {macro.shape[0]} anios x {macro.shape[1]} variables "
          f"({macro.index.min()}-{macro.index.max()})")

    frontera = datos.frontera_cobertura(macro)
    frontera.to_csv(SALIDAS / "frontera_cobertura.csv", index=False)
    print("\n--- La frontera que decide el diseno ---")
    print(f"{'k vars':>7s} {'n anios':>8s} {'rango':>11s} {'n/p':>6s}  entra")
    for _, r in frontera.iterrows():
        if r.k_variables % 4 == 0 or r.ratio_n_p < 3.2:
            print(f"{int(r.k_variables):7d} {int(r.n_anios):8d} "
                  f"{int(r.desde)}-{int(r.hasta)} {r.ratio_n_p:6.2f}  {r.entra}")

    panel = datos.panel_anual(macro, min_ratio=3.0)
    fuera = [c for c in macro.columns if c not in panel.columns]
    print(f"\npanel elegido: {panel.shape[0]} anios x {panel.shape[1]} variables "
          f"({panel.index.min()}-{panel.index.max()}), n/p = {panel.shape[0] / panel.shape[1]:.2f}")
    print(f"quedan fuera por cobertura ({len(fuera)}): {', '.join(fuera)}")

    y = panel["pib_crecimiento"].copy()
    X = panel.drop(columns=["pib_crecimiento", "pib_real", "pib_per_capita"], errors="ignore")
    print(f"objetivo: crecimiento del PIB real | regresores: {X.shape[1]}")

    detalle = backtest.origen_movil(y, modelos.catalogo_anual(), h=1,
                                    min_entrenamiento=30, X=X)
    detalle.to_csv(SALIDAS / "pista_a_detalle.csv", index=False)
    tabla = backtest.resumen(detalle)
    tabla.to_csv(SALIDAS / "pista_a_resumen.csv", index=False)
    backtest.imprimir(tabla, "PISTA A - error a 1 ano, origen movil, "
                             f"{detalle.origen.nunique()} origenes (pp de crecimiento)")


def pista_b() -> None:
    seccion("PISTA B - ISE mensual de Colombia (DANE, 2005-01 a 2026-06)")

    if not ISE_XLSX.exists():
        print(f"! falta {ISE_XLSX}. Copia el anexo ISE del DANE ahi.")
        return

    ise = datos.serie_ise(ISE_XLSX)
    ise.to_frame().to_parquet(datos.PROC / "ise_mensual.parquet")
    print(f"ISE agregado: {len(ise)} meses ({ise.index.min():%Y-%m} a {ise.index.max():%Y-%m})")

    crecimiento = (ise.pct_change(12) * 100).dropna().rename("ise_var_anual")
    print(f"objetivo: variacion anual del ISE | {len(crecimiento)} observaciones")
    print(f"minimo historico: {crecimiento.min():.1f} % en {crecimiento.idxmin():%Y-%m}")

    detalle = backtest.origen_movil(crecimiento, modelos.catalogo_mensual(), h=1,
                                    min_entrenamiento=120)
    detalle.to_csv(SALIDAS / "pista_b_detalle.csv", index=False)
    tabla = backtest.resumen(detalle)
    tabla.to_csv(SALIDAS / "pista_b_resumen.csv", index=False)
    backtest.imprimir(tabla, "PISTA B - error a 1 mes, origen movil, "
                             f"{detalle.origen.nunique()} origenes (pp de variacion anual)")


def main() -> None:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    datos.PROC.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 200)
    pista_a()
    pista_b()
    print(f"\n\nResultados en {SALIDAS}")


if __name__ == "__main__":
    main()
