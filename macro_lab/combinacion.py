"""Combinacion con pesos por regimen.

La tabla de robustez dice una cosa clara: los modelos flexibles ganan en calma y pierden
en la ruptura. La lectura directa es un modelo que se encoja hacia el ingenuo cuando la
volatilidad reciente se dispara y se suelte cuando no.

El riesgo evidente es hacer trampa. Si el interruptor de regimen se calibra mirando donde
estuvo el COVID, el resultado no vale nada: seria el mismo mirar-adelante que todo el
protocolo existe para evitar. Aqui el interruptor se calcula **solo con el tramo de
entrenamiento de cada origen**:

  1. Se construye la serie de volatilidad movil de la propia variable, hasta el origen.
  2. El umbral es un cuantil de esa serie, estimado con esos mismos datos y ninguno mas.
  3. La volatilidad del ultimo tramo se compara contra ese umbral.

En el primer trimestre de 2020 el modelo no sabe que viene una pandemia. Sabe que la
volatilidad reciente todavia es normal, y por eso se equivoca igual que los demas. Eso es
lo correcto: el interruptor reacciona, no anticipa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .modelos import Modelo, _naive, _red, _sarimax, _supervisado


def _peso_regimen(y: pd.Series, ventana: int, cuantil: float, suave: bool) -> float:
    """Cuanto peso va al modelo de ruptura. 0 = todo al flexible, 1 = todo al robusto."""
    d = y.diff().abs()
    vol = d.rolling(ventana).std().dropna()
    if len(vol) < 8:
        return 0.0

    umbral = float(vol.quantile(cuantil))
    actual = float(vol.iloc[-1])
    if umbral <= 0 or not np.isfinite(umbral):
        return 0.0

    if not suave:
        return 1.0 if actual > umbral else 0.0

    # Transicion lineal entre el cuantil elegido y el doble del umbral.
    if actual <= umbral:
        return 0.0
    return float(min(1.0, (actual - umbral) / umbral))


def _combinar(y, h, X=None, flexible=None, robusto=None, ventana=8,
              cuantil=0.80, suave=True, devolver_peso=False):
    w = _peso_regimen(y, ventana, cuantil, suave)

    p_rob = np.asarray(robusto(y, h, X), dtype=float)
    if w >= 0.999:
        salida = p_rob
    else:
        p_flex = np.asarray(flexible(y, h, X), dtype=float)
        if not np.all(np.isfinite(p_flex)):
            salida = p_rob
        else:
            salida = w * p_rob + (1 - w) * p_flex

    return (salida, w) if devolver_peso else salida


# ------------------------------------------------------------------ piezas

def _flex_rf(y, h, X=None):
    from sklearn.ensemble import RandomForestRegressor
    return _supervisado(y, h, X, estimador=RandomForestRegressor(
        n_estimators=400, random_state=7), n_lags=12)


def _flex_lstm(y, h, X=None):
    return _red(y, h, X, arquitectura="lstm", ventana=12, unidades=16)


def _rob_ar1(y, h, X=None):
    return _sarimax(y, h, X, order=(1, 0, 0), trend="c")


def _rob_ingenuo(y, h, X=None):
    return _naive(y, h, X)


def catalogo_combinaciones() -> list[Modelo]:
    """Las combinaciones que la tabla de robustez sugiere, mas sus dos extremos."""
    return [
        Modelo("Comb. RF/AR(1) suave", "combinacion", _combinar,
               params=dict(flexible=_flex_rf, robusto=_rob_ar1, suave=True, cuantil=0.80)),
        Modelo("Comb. RF/AR(1) dura", "combinacion", _combinar,
               params=dict(flexible=_flex_rf, robusto=_rob_ar1, suave=False, cuantil=0.80)),
        Modelo("Comb. RF/ingenuo suave", "combinacion", _combinar,
               params=dict(flexible=_flex_rf, robusto=_rob_ingenuo, suave=True, cuantil=0.80)),
        Modelo("Comb. LSTM/AR(1) suave", "combinacion", _combinar,
               params=dict(flexible=_flex_lstm, robusto=_rob_ar1, suave=True, cuantil=0.80)),
        Modelo("Comb. 50/50 RF-AR(1)", "combinacion", _combinar,
               params=dict(flexible=_flex_rf, robusto=_rob_ar1, suave=True, cuantil=0.0)),
    ]


def rastro_pesos(y: pd.Series, min_entrenamiento: int, ventana: int = 8,
                 cuantil: float = 0.80, suave: bool = True) -> pd.DataFrame:
    """El peso que el interruptor habria asignado en cada origen. Para auditarlo."""
    filas = []
    for t in range(min_entrenamiento, len(y)):
        w = _peso_regimen(y.iloc[:t], ventana, cuantil, suave)
        filas.append(dict(origen=str(y.index[t - 1]), peso_robusto=w,
                          real_siguiente=float(y.iloc[t])))
    return pd.DataFrame(filas)
