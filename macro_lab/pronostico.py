"""El pronostico publicado: AR(1) hasta 2027, con bandas y su cobertura medida (D-008).

`uv run python -m macro_lab.pronostico`

Un solo modelo, el que el laboratorio mostro que le gana al ingenuo en toda la region en
calma (Pista D). Se ajusta con la serie anual completa de cada economia y se pronostica
hasta 2027. Las bandas son las del modelo, al 80 y al 95 %.

Una banda del modelo supone que el futuro se parece al pasado; en America Latina no
siempre. Por eso, con el mismo origen movil de la Pista D, se cuenta cuantas veces la
banda de un paso contuvo el dato real. Esa cobertura empirica se publica al lado: si la
banda del 95 % cubre menos, el lector lo sabe.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import datos, latam

HASTA = 2027
MIN_ENTRENAMIENTO = 30  # el de la Pista D


def _ajustar(y: np.ndarray):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    # La misma especificacion del AR(1) de las pistas (modelos.catalogo_latam).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SARIMAX(y, order=(1, 0, 0), trend="c",
                       enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)


def bandas(y: np.ndarray, pasos: int) -> list[dict]:
    """Pronostico medio y bandas al 80 y al 95 % para los proximos `pasos` periodos."""
    f = _ajustar(y).get_forecast(steps=pasos)
    media = np.asarray(f.predicted_mean)
    c80 = np.asarray(f.conf_int(alpha=0.20))
    c95 = np.asarray(f.conf_int(alpha=0.05))
    return [dict(media=float(media[h]), lo80=float(c80[h, 0]), hi80=float(c80[h, 1]),
                 lo95=float(c95[h, 0]), hi95=float(c95[h, 1])) for h in range(pasos)]


def cobertura(y: np.ndarray, min_ent: int = MIN_ENTRENAMIENTO) -> dict:
    """Cuantas veces la banda de un paso contuvo el dato real, origen por origen."""
    dentro80 = dentro95 = n = 0
    for t in range(min_ent, len(y)):
        b = bandas(y[:t], 1)[0]
        real = y[t]
        n += 1
        dentro80 += b["lo80"] <= real <= b["hi80"]
        dentro95 += b["lo95"] <= real <= b["hi95"]
    return dict(n=n, c80=dentro80 / n if n else np.nan, c95=dentro95 / n if n else np.nan)


def pronosticos(largo: pd.DataFrame) -> dict:
    """Por economia: ultimo dato, pronostico hasta HASTA y cobertura empirica."""
    salida, n80, n95, n = [], 0, 0, 0
    for iso3 in sorted(largo.iso3.unique()):
        s = latam.serie_anual(largo, iso3)
        if len(s) < MIN_ENTRENAMIENTO + 8:  # las economias de la Pista D (B-010)
            continue
        y = s.to_numpy(dtype=float)
        ultimo = int(s.index[-1])
        pasos = HASTA - ultimo
        if pasos < 1:
            continue
        cob = cobertura(y)
        n += cob["n"]
        n80 += round(cob["c80"] * cob["n"])
        n95 += round(cob["c95"] * cob["n"])
        fut = bandas(y, pasos)
        salida.append(dict(
            iso3=iso3, ultimo_anio=ultimo, ultimo=float(y[-1]),
            pronostico=[dict(anio=ultimo + h + 1, **fut[h]) for h in range(pasos)],
            cobertura=dict(n=cob["n"], c80=cob["c80"], c95=cob["c95"]),
        ))
    return dict(
        modelo="AR(1)", hasta=HASTA, economias=salida,
        cobertura_region=dict(n=n, c80=n80 / n if n else None, c95=n95 / n if n else None),
    )


def main() -> None:
    largo = pd.read_parquet(datos.PROC / "latam_anual.parquet")
    p = pronosticos(largo)
    anios = range(2025, HASTA + 1)
    print(f"{'economia':6s} {'ultimo':>12s} " + " ".join(f"{a:>22d}" for a in anios)
          + f" {'cob80':>6s} {'cob95':>6s}")
    for e in p["economias"]:
        cols = {f["anio"]: f"{f['media']:+5.1f} [{f['lo95']:+5.1f},{f['hi95']:+5.1f}]"
                for f in e["pronostico"]}
        print(f"{e['iso3']:6s} {e['ultimo_anio']} {e['ultimo']:+5.1f} "
              + " ".join(f"{cols.get(a, ''):>22s}" for a in anios)
              + f" {e['cobertura']['c80']:6.0%} {e['cobertura']['c95']:6.0%}")
    r = p["cobertura_region"]
    print(f"\nCobertura empirica de un paso en la region ({r['n']} origenes): "
          f"banda del 80 % {r['c80']:.0%}, banda del 95 % {r['c95']:.0%}")


if __name__ == "__main__":
    main()
