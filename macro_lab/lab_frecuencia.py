"""Frecuencia, ajuste o fuente: el ISE remuestreado a trimestral.

`uv run python -m macro_lab.lab_frecuencia`

En la ruptura de Colombia el LSTM pierde contra el ingenuo con el ISE mensual y gana con
el PIB trimestral del FMI. Las dos series difieren en frecuencia, fuente y ajuste
estacional a la vez. Este modulo las separa con tres brazos trimestrales sobre la misma
muestra y el mismo catalogo de la Pista C (pre-registro en D-007 de la bitacora):

  A  ISE sin ajuste (Cuadro 1), promedio trimestral   A vs ISE mensual: frecuencia
  B  ISE ajustado (Cuadro 2), promedio trimestral     A vs B: ajuste
  C  PIB real del FMI, ajustado                       B vs C: fuente

El brazo B usa una serie ajustada a proposito: el ajuste es lo que se mide. Es un
control diagnostico, no un resultado de pronostico (R-05).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import backtest, datos, latam
from .lab_latam import RUPTURA, catalogo_latam

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"
ISE_XLSX = RAIZ / "datos" / "crudo" / "anex-ISE-12actividades.xlsx"
MIN_ENTRENAMIENTO = 40  # el de la Pista C

BRAZOS = {
    "A": "ISE trimestral sin ajuste",
    "B": "ISE trimestral ajustado",
    "C": "PIB FMI ajustado",
}


def _interanual(s: pd.Series) -> pd.Series:
    return (s.pct_change(4) * 100).dropna()


def series_brazos() -> dict[str, pd.Series]:
    """Las tres series en variacion interanual, recortadas a su muestra comun."""
    crudas = {
        "A": _interanual(datos.a_trimestral(datos.serie_ise(ISE_XLSX, "Cuadro 1"))),
        "B": _interanual(datos.a_trimestral(datos.serie_ise(ISE_XLSX, "Cuadro 2"))),
        "C": latam.serie_crecimiento_trimestral(latam.descargar_trimestral_latam(), "COL"),
    }
    comun = crudas["A"].index
    for s in crudas.values():
        comun = comun.intersection(s.index)
    return {k: s.loc[comun].rename(k) for k, s in crudas.items()}


def resumen_por_regimen(detalle: pd.DataFrame) -> pd.DataFrame:
    detalle = detalle.copy()
    detalle["regimen"] = backtest.regimen(detalle, RUPTURA)
    partes = []
    for (brazo, reg), g in detalle.groupby(["brazo", "regimen"]):
        r = backtest.resumen(g)
        r.insert(0, "regimen", reg)
        r.insert(0, "brazo", brazo)
        partes.append(r)
    return pd.concat(partes, ignore_index=True)


def _mensual_lstm() -> dict | None:
    """La cifra de referencia del ISE mensual, de la Pista B ya corrida."""
    ruta = SALIDAS / "pista_b_detalle.csv"
    if not ruta.exists():
        return None
    d = pd.read_csv(ruta)
    d = d[backtest.regimen(d, RUPTURA) == "ruptura"]
    r = backtest.resumen(d).set_index("modelo")
    return r.loc["LSTM(16) v12"].to_dict() if "LSTM(16) v12" in r.index else None


def veredicto(signos: dict[str, bool]) -> str:
    """La regla pre-registrada en D-007, aplicada sin interpretar."""
    a, b, c = signos["A"], signos["B"], signos["C"]
    if a and c:
        return "manda la FRECUENCIA (A gana, como C)"
    if not a and b:
        return "manda el AJUSTE (A pierde, B gana)"
    if not a and not b and c:
        return "manda la FUENTE (A y B pierden, solo C gana)"
    return "NO CONCLUYENTE (patron fuera de las tres predicciones)"


def main() -> None:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    brazos = series_brazos()
    y0 = next(iter(brazos.values()))
    print(f"muestra comun: {y0.index[0]} a {y0.index[-1]}, {len(y0)} trimestres, "
          f"{len(y0) - MIN_ENTRENAMIENTO} origenes")

    partes = []
    for k, y in brazos.items():
        print(f"\n  brazo {k} - {BRAZOS[k]}")
        det = backtest.origen_movil(y, catalogo_latam(), h=1,
                                    min_entrenamiento=MIN_ENTRENAMIENTO)
        det.insert(0, "brazo", k)
        partes.append(det)
    detalle = pd.concat(partes, ignore_index=True)
    detalle.to_csv(SALIDAS / "frecuencia_detalle.csv", index=False)

    tabla = resumen_por_regimen(detalle)
    tabla.to_csv(SALIDAS / "frecuencia_resumen.csv", index=False)

    print(f"\n{'=' * 96}\nFRECUENCIA, AJUSTE O FUENTE - Colombia, ganancia sobre el ingenuo "
          f"(regimen del periodo pronosticado)\n{'=' * 96}")
    print(f"{'brazo':34s} {'modelo':14s} {'calma':>24s} {'ruptura':>24s}")
    print("-" * 96)

    def celda(fila):
        if fila is None or pd.isna(fila["mae"]):
            return f"{'-':>24s}"
        if pd.isna(fila["ganancia_pct"]):
            return f"{fila['mae']:7.3f}   (ref)          "
        return (f"{fila['ganancia_pct']:+7.1f}% p={fila['dm_p']:.3f} "
                f"H={fila['dm_p_holm']:.2f}")

    ref = _mensual_lstm()
    if ref is not None:
        print(f"{'ISE mensual sin ajuste (Pista B)':34s} {'LSTM(16) v12':14s} "
              f"{'':>24s} {celda(ref)}")
    for k in BRAZOS:
        for modelo in ("LSTM(16)", "AR(1)", "Ingenuo"):
            filas = {}
            for reg in ("calma", "ruptura"):
                sel = tabla[(tabla.brazo == k) & (tabla.regimen == reg)
                            & (tabla.modelo == modelo)]
                filas[reg] = sel.iloc[0].to_dict() if len(sel) else None
            etiqueta = f"{k}  {BRAZOS[k]}" if modelo == "LSTM(16)" else ""
            print(f"{etiqueta:34s} {modelo:14s} {celda(filas['calma'])} "
                  f"{celda(filas['ruptura'])}")
    print("-" * 96)

    lstm = tabla[(tabla.modelo == "LSTM(16)") & (tabla.regimen == "ruptura")
                 ].set_index("brazo").ganancia_pct
    signos = {k: bool(lstm.get(k, 0) > 0) for k in BRAZOS}
    print("\nSigno del LSTM en la ruptura: "
          + ", ".join(f"{k} {'gana' if v else 'pierde'}" for k, v in signos.items()))
    print(f"Regla pre-registrada (D-007): {veredicto(signos)}")
    print("Direccion, no significancia: 8 trimestres de ruptura por brazo (R-10).")
    print(f"\nSalidas en {SALIDAS}")


if __name__ == "__main__":
    main()
