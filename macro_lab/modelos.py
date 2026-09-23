"""El zoologico de modelos, todos detras de la misma interfaz.

Cada modelo recibe la serie objetivo hasta el origen de pronostico y, si los usa, los
regresores hasta ese mismo punto. Devuelve h pronosticos. Nada mas. Esa uniformidad es
lo que permite que la comparacion sea limpia: el unico que cambia es el modelo.

Tres reglas que se aplican a todos sin excepcion:
  - El ajuste ocurre dentro de `predecir`, con los datos que recibe y ninguno mas.
    Ningun modelo ve un dato posterior a su origen.
  - Los escaladores se ajustan solo con el tramo de entrenamiento.
  - Las redes fijan semilla y paran temprano contra una validacion recortada del propio
    entrenamiento, nunca contra el tramo de prueba.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


@dataclass
class Modelo:
    """Interfaz comun. `familia` agrupa para las tablas de resultados."""

    nombre: str
    familia: str
    fn: object
    usa_exogenas: bool = False
    params: dict = field(default_factory=dict)

    def predecir(self, y: pd.Series, h: int, X: pd.DataFrame | None = None) -> np.ndarray:
        try:
            salida = self.fn(y, h, X, **self.params)
            salida = np.asarray(salida, dtype=float).ravel()
            if salida.shape[0] != h or not np.all(np.isfinite(salida)):
                return np.full(h, np.nan)
            return salida
        except Exception:
            return np.full(h, np.nan)


# ------------------------------------------------------------------ referencias

def _naive(y, h, X=None):
    return np.repeat(y.iloc[-1], h)


def _naive_estacional(y, h, X=None, periodo=12):
    ultimos = y.iloc[-periodo:].to_numpy()
    return np.array([ultimos[i % periodo] for i in range(h)])


def _media(y, h, X=None, ventana=None):
    tramo = y if ventana is None else y.iloc[-ventana:]
    return np.repeat(tramo.mean(), h)


def _deriva(y, h, X=None):
    pendiente = (y.iloc[-1] - y.iloc[0]) / max(len(y) - 1, 1)
    return y.iloc[-1] + pendiente * np.arange(1, h + 1)


# ------------------------------------------------------- familia Box-Jenkins

def _sarimax(y, h, X=None, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0),
             trend=None, usar_x=False, covid=False):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    exog = None
    exog_fut = None
    piezas, piezas_fut = [], []

    if usar_x and X is not None:
        alineado = X.reindex(y.index).ffill()
        piezas.append(alineado.to_numpy(dtype=float))
        piezas_fut.append(np.repeat(alineado.to_numpy(dtype=float)[-1:], h, axis=0))

    if covid:
        d = _dummies_covid(y.index)
        piezas.append(d)
        piezas_fut.append(_dummies_covid(_indice_futuro(y.index, h)))

    if piezas:
        exog = np.hstack(piezas)
        exog_fut = np.hstack(piezas_fut)

    modelo = SARIMAX(y.to_numpy(dtype=float), order=order, seasonal_order=seasonal_order,
                     trend=trend, exog=exog,
                     enforce_stationarity=False, enforce_invertibility=False)
    ajuste = modelo.fit(disp=False)
    return ajuste.forecast(steps=h, exog=exog_fut)


def _var(y, h, X=None, maxlags=2, n_vars=4):
    """VAR sobre el objetivo y las exogenas mas correlacionadas."""
    from statsmodels.tsa.api import VAR

    if X is None:
        raise ValueError("VAR necesita companeras")
    alineado = X.reindex(y.index).ffill().bfill()
    corr = alineado.apply(lambda c: abs(np.corrcoef(c, y)[0, 1]) if c.std() > 0 else 0)
    elegidas = list(corr.sort_values(ascending=False).index[:n_vars])
    datos = pd.concat([y.rename("__objetivo__"), alineado[elegidas]], axis=1).dropna()
    datos = datos.loc[:, datos.std() > 0]
    lags = min(maxlags, max(1, (len(datos) - 5) // (datos.shape[1] + 1)))
    ajuste = VAR(datos.to_numpy(dtype=float)).fit(lags)
    pron = ajuste.forecast(datos.to_numpy(dtype=float)[-lags:], steps=h)
    return pron[:, 0]


# ------------------------------------------------- utilidades de supervisado

def _dummies_covid(idx) -> np.ndarray:
    """Dos columnas: caida 2020 y rebote 2021. Sin esto el ARIMA aprende un ciclo falso."""
    if isinstance(idx, pd.DatetimeIndex):
        anios = idx.year.to_numpy()
    else:
        anios = np.asarray(idx, dtype=int)
    return np.column_stack([(anios == 2020).astype(float), (anios == 2021).astype(float)])


def _indice_futuro(idx, h):
    """Los h periodos siguientes, en el mismo tipo de indice que la serie.

    El PeriodIndex va primero y no es un detalle: las series trimestrales de LATAM lo
    usan, y `np.arange` sobre objetos Period revienta. Cuando reventaba, todo modelo
    recursivo (Random Forest, Ridge y las combinaciones que los invocan) devolvia NaN en
    esos origenes; los NaN se descartaban al promediar y el modelo quedaba evaluado solo
    sobre los origenes donde sobrevivio. Es decir: parecia el mejor por no haber
    competido. De ahi la regla de cobertura minima en `backtest.resumen`.
    """
    if isinstance(idx, pd.PeriodIndex):
        return pd.period_range(idx[-1] + 1, periods=h, freq=idx.freq)
    if isinstance(idx, pd.DatetimeIndex):
        paso = pd.infer_freq(idx) or "MS"
        return pd.date_range(idx[-1], periods=h + 1, freq=paso)[1:]
    return np.arange(idx[-1] + 1, idx[-1] + 1 + h)


def _matriz_rezagos(y: pd.Series, n_lags: int, X: pd.DataFrame | None = None,
                    lags_x: int = 1):
    """Ventanas deslizantes. La fila de t contiene solo informacion hasta t-1."""
    valores = y.to_numpy(dtype=float)
    filas, objetivo = [], []
    xs = None
    if X is not None:
        xs = X.reindex(y.index).ffill().bfill().to_numpy(dtype=float)
    inicio = max(n_lags, lags_x)
    for t in range(inicio, len(valores)):
        fila = list(valores[t - n_lags:t][::-1])
        if xs is not None:
            for k in range(1, lags_x + 1):
                fila.extend(xs[t - k])
        filas.append(fila)
        objetivo.append(valores[t])
    return np.asarray(filas), np.asarray(objetivo)


def _ultima_fila(y: pd.Series, n_lags: int, X: pd.DataFrame | None = None, lags_x: int = 1):
    valores = y.to_numpy(dtype=float)
    fila = list(valores[-n_lags:][::-1])
    if X is not None:
        xs = X.reindex(y.index).ffill().bfill().to_numpy(dtype=float)
        for k in range(0, lags_x):
            fila.extend(xs[len(xs) - 1 - k])
    return np.asarray(fila, dtype=float).reshape(1, -1)


def _supervisado(y, h, X=None, estimador=None, n_lags=3, usar_x=False, escalar=True):
    """Recursivo: el pronostico de t+1 entra como rezago para t+2."""
    from sklearn.preprocessing import StandardScaler

    Xs = X if usar_x else None
    M, obj = _matriz_rezagos(y, n_lags, Xs)
    if len(M) < 8:
        raise ValueError("muy pocas filas")

    escalador = StandardScaler().fit(M) if escalar else None
    M_esc = escalador.transform(M) if escalar else M
    estimador.fit(M_esc, obj)

    serie = y.copy()
    salida = []
    for _ in range(h):
        fila = _ultima_fila(serie, n_lags, Xs)
        fila_esc = escalador.transform(fila) if escalar else fila
        siguiente = float(estimador.predict(fila_esc)[0])
        salida.append(siguiente)
        paso = _indice_futuro(serie.index, 1)
        serie = pd.concat([serie, pd.Series([siguiente], index=paso)])
    return np.asarray(salida)


def _factores_ar(y, h, X=None, n_factores=3, n_lags=2):
    """Modelo de factores: PCA sobre las macro, luego una regresion sobre los factores.

    Es la respuesta clasica a tener muchas variables y pocas observaciones. En vez de
    elegir variables, se comprime todo a unos pocos factores comunes.
    """
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    if X is None:
        raise ValueError("el modelo de factores necesita el bloque macro")
    alineado = X.reindex(y.index).ffill().bfill()
    escalador = StandardScaler().fit(alineado)
    pca = PCA(n_components=min(n_factores, alineado.shape[1], len(alineado) - 2))
    factores = pd.DataFrame(pca.fit_transform(escalador.transform(alineado)),
                            index=alineado.index)
    return _supervisado(y, h, factores, estimador=LinearRegression(),
                        n_lags=n_lags, usar_x=True)


# ------------------------------------------------------------ redes neuronales

def _ventanas(serie: np.ndarray, ventana: int):
    X, Y = [], []
    for t in range(ventana, len(serie)):
        X.append(serie[t - ventana:t])
        Y.append(serie[t])
    return np.asarray(X, dtype=np.float32), np.asarray(Y, dtype=np.float32)


def _red(y, h, X=None, arquitectura="lstm", ventana=12, unidades=16,
         epocas=300, semilla=7, paciencia=30):
    """LSTM o CNN 1D sobre la serie estandarizada.

    Deliberadamente pequenas: con unos cientos de observaciones, una red grande memoriza
    el entrenamiento y no generaliza. El tamano es parte del resultado, no un descuido.
    """
    import torch
    from torch import nn

    torch.manual_seed(semilla)
    np.random.seed(semilla)

    valores = y.to_numpy(dtype=np.float64)
    mu, sigma = valores.mean(), valores.std()
    if sigma == 0:
        raise ValueError("serie constante")
    z = ((valores - mu) / sigma).astype(np.float32)

    Xv, Yv = _ventanas(z, ventana)
    if len(Xv) < 24:
        raise ValueError("serie muy corta para una red")

    corte = max(int(len(Xv) * 0.85), len(Xv) - 24)
    Xtr, Ytr = Xv[:corte], Yv[:corte]
    Xva, Yva = Xv[corte:], Yv[corte:]

    class LSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.rnn = nn.LSTM(1, unidades, batch_first=True)
            self.sal = nn.Linear(unidades, 1)

        def forward(self, x):
            o, _ = self.rnn(x.unsqueeze(-1))
            return self.sal(o[:, -1]).squeeze(-1)

    class CNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.red = nn.Sequential(
                nn.Conv1d(1, unidades, kernel_size=3, padding=1), nn.ReLU(),
                nn.Conv1d(unidades, unidades, kernel_size=3, padding=1), nn.ReLU(),
                nn.AdaptiveAvgPool1d(1))
            self.sal = nn.Linear(unidades, 1)

        def forward(self, x):
            return self.sal(self.red(x.unsqueeze(1)).squeeze(-1)).squeeze(-1)

    red = LSTM() if arquitectura == "lstm" else CNN()
    opt = torch.optim.Adam(red.parameters(), lr=0.01)
    perdida = nn.MSELoss()

    tXtr, tYtr = torch.from_numpy(Xtr), torch.from_numpy(Ytr)
    tXva, tYva = torch.from_numpy(Xva), torch.from_numpy(Yva)

    mejor, mejor_estado, sin_mejora = np.inf, None, 0
    for _ in range(epocas):
        red.train()
        opt.zero_grad()
        perdida(red(tXtr), tYtr).backward()
        opt.step()
        red.eval()
        with torch.no_grad():
            val = float(perdida(red(tXva), tYva)) if len(Xva) else float(perdida(red(tXtr), tYtr))
        if val < mejor - 1e-6:
            mejor, sin_mejora = val, 0
            mejor_estado = {k: v.clone() for k, v in red.state_dict().items()}
        else:
            sin_mejora += 1
            if sin_mejora >= paciencia:
                break
    if mejor_estado is not None:
        red.load_state_dict(mejor_estado)

    red.eval()
    hist = list(z)
    salida = []
    with torch.no_grad():
        for _ in range(h):
            entrada = torch.from_numpy(np.asarray([hist[-ventana:]], dtype=np.float32))
            siguiente = float(red(entrada))
            hist.append(siguiente)
            salida.append(siguiente * sigma + mu)
    return np.asarray(salida)


# ------------------------------------------------------------------ catalogos

def catalogo_anual() -> list[Modelo]:
    """Pista A: ~60 observaciones anuales. Ordenes bajos, regularizacion, factores."""
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import ElasticNet, Lasso, Ridge
    from sklearn.neural_network import MLPRegressor

    M = []
    M += [
        Modelo("Ingenuo", "referencia", _naive),
        Modelo("Media historica", "referencia", _media),
        Modelo("Media 5 anios", "referencia", _media, params=dict(ventana=5)),
        Modelo("Deriva", "referencia", _deriva),
    ]
    M += [
        Modelo("AR(1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 0, 0), trend="c")),
        Modelo("AR(2)", "Box-Jenkins", _sarimax, params=dict(order=(2, 0, 0), trend="c")),
        Modelo("MA(1)", "Box-Jenkins", _sarimax, params=dict(order=(0, 0, 1), trend="c")),
        Modelo("MA(2)", "Box-Jenkins", _sarimax, params=dict(order=(0, 0, 2), trend="c")),
        Modelo("ARMA(1,1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 0, 1), trend="c")),
        Modelo("ARMA(2,1)", "Box-Jenkins", _sarimax, params=dict(order=(2, 0, 1), trend="c")),
        Modelo("ARIMA(1,1,1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 1, 1))),
        Modelo("ARIMA(2,1,0)", "Box-Jenkins", _sarimax, params=dict(order=(2, 1, 0))),
        Modelo("AR(1)+COVID", "Box-Jenkins", _sarimax,
               params=dict(order=(1, 0, 0), trend="c", covid=True)),
        Modelo("ARMA(1,1)+COVID", "Box-Jenkins", _sarimax,
               params=dict(order=(1, 0, 1), trend="c", covid=True)),
    ]
    M += [
        Modelo("SARIMAX(1,0,0)+macro", "con exogenas", _sarimax, usa_exogenas=True,
               params=dict(order=(1, 0, 0), trend="c", usar_x=True)),
        Modelo("SARIMAX(1,0,1)+macro+COVID", "con exogenas", _sarimax, usa_exogenas=True,
               params=dict(order=(1, 0, 1), trend="c", usar_x=True, covid=True)),
        Modelo("VAR(2)", "con exogenas", _var, usa_exogenas=True,
               params=dict(maxlags=2, n_vars=4)),
    ]
    M += [
        Modelo("Ridge", "regularizado", _supervisado, usa_exogenas=True,
               params=dict(estimador=Ridge(alpha=10.0), n_lags=2, usar_x=True)),
        Modelo("Lasso", "regularizado", _supervisado, usa_exogenas=True,
               params=dict(estimador=Lasso(alpha=0.5, max_iter=20000), n_lags=2, usar_x=True)),
        Modelo("ElasticNet", "regularizado", _supervisado, usa_exogenas=True,
               params=dict(estimador=ElasticNet(alpha=0.5, l1_ratio=0.5, max_iter=20000),
                           n_lags=2, usar_x=True)),
        Modelo("Factores PCA + AR", "regularizado", _factores_ar, usa_exogenas=True,
               params=dict(n_factores=3, n_lags=2)),
    ]
    M += [
        Modelo("Random Forest", "aprendizaje", _supervisado, usa_exogenas=True,
               params=dict(estimador=RandomForestRegressor(n_estimators=400, random_state=7,
                                                          min_samples_leaf=2),
                           n_lags=2, usar_x=True)),
        Modelo("Gradient Boosting", "aprendizaje", _supervisado, usa_exogenas=True,
               params=dict(estimador=GradientBoostingRegressor(random_state=7, max_depth=2,
                                                              n_estimators=200),
                           n_lags=2, usar_x=True)),
        Modelo("MLP", "aprendizaje", _supervisado, usa_exogenas=True,
               params=dict(estimador=MLPRegressor(hidden_layer_sizes=(16,), max_iter=3000,
                                                  random_state=7, early_stopping=False),
                           n_lags=2, usar_x=True)),
    ]
    M += [
        Modelo("LSTM", "red neuronal", _red,
               params=dict(arquitectura="lstm", ventana=4, unidades=8)),
        Modelo("CNN 1D", "red neuronal", _red,
               params=dict(arquitectura="cnn", ventana=4, unidades=8)),
    ]
    return M


def catalogo_mensual() -> list[Modelo]:
    """Pista B: ~258 observaciones mensuales. Aqui si caben estacionalidad y redes."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor

    M = []
    M += [
        Modelo("Ingenuo", "referencia", _naive),
        Modelo("Ingenuo estacional", "referencia", _naive_estacional),
        Modelo("Deriva", "referencia", _deriva),
    ]
    M += [
        Modelo("AR(1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 0, 0), trend="c")),
        Modelo("AR(12)", "Box-Jenkins", _sarimax, params=dict(order=(12, 0, 0), trend="c")),
        Modelo("MA(2)", "Box-Jenkins", _sarimax, params=dict(order=(0, 0, 2), trend="c")),
        Modelo("ARMA(2,2)", "Box-Jenkins", _sarimax, params=dict(order=(2, 0, 2), trend="c")),
        Modelo("ARIMA(1,1,1)", "Box-Jenkins", _sarimax, params=dict(order=(1, 1, 1))),
        Modelo("ARIMA(2,1,2)", "Box-Jenkins", _sarimax, params=dict(order=(2, 1, 2))),
        Modelo("SARIMA(1,1,1)(1,1,1,12)", "estacional", _sarimax,
               params=dict(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))),
        Modelo("SARIMA(2,1,1)(0,1,1,12)", "estacional", _sarimax,
               params=dict(order=(2, 1, 1), seasonal_order=(0, 1, 1, 12))),
        Modelo("SARIMAX(1,1,1)(1,1,1,12)+COVID", "estacional", _sarimax,
               params=dict(order=(1, 1, 1), seasonal_order=(1, 1, 1, 12), covid=True)),
    ]
    M += [
        Modelo("Ridge sobre rezagos", "regularizado", _supervisado,
               params=dict(estimador=Ridge(alpha=1.0), n_lags=12)),
        Modelo("Random Forest", "aprendizaje", _supervisado,
               params=dict(estimador=RandomForestRegressor(n_estimators=400, random_state=7),
                           n_lags=12)),
        Modelo("MLP", "aprendizaje", _supervisado,
               params=dict(estimador=MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=4000,
                                                  random_state=7), n_lags=12)),
    ]
    M += [
        Modelo("LSTM(16) v12", "red neuronal", _red,
               params=dict(arquitectura="lstm", ventana=12, unidades=16)),
        Modelo("LSTM(32) v24", "red neuronal", _red,
               params=dict(arquitectura="lstm", ventana=24, unidades=32)),
        Modelo("CNN 1D v12", "red neuronal", _red,
               params=dict(arquitectura="cnn", ventana=12, unidades=16)),
        Modelo("CNN 1D v24", "red neuronal", _red,
               params=dict(arquitectura="cnn", ventana=24, unidades=32)),
    ]
    return M
