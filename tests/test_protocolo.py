"""Las reglas del protocolo, comprobadas con datos sinteticos. Sin red, en segundos.

No prueban que un modelo pronostique bien: prueban que el laboratorio no se enganta a si
mismo. Cada prueba cita el error de la bitacora o la regla que protege.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from macro_lab import backtest, combinacion, datos, modelos
from macro_lab.modelos import Modelo, _dummies_covid, _indice_futuro, _naive

RAIZ = Path(__file__).resolve().parent.parent


def _serie_anual(n=40, inicio=1980, semilla=0):
    rng = np.random.default_rng(semilla)
    return pd.Series(rng.normal(3, 2, n), index=np.arange(inicio, inicio + n))


# ------------------------------------------------------------------ R-04

def test_ningun_modelo_ve_datos_posteriores_al_origen():
    y = _serie_anual()
    X = pd.DataFrame({"x": np.arange(len(y), dtype=float)}, index=y.index)
    vistos = []

    def espia(y_tr, h, X_tr=None):
        vistos.append((y_tr.index[-1], X_tr.index[-1]))
        return np.repeat(y_tr.iloc[-1], h)

    det = backtest.origen_movil(y, [Modelo("espia", "t", espia)], h=1,
                                min_entrenamiento=30, X=X, verbose=False)
    for (ultimo_y, ultimo_x), (_, fila) in zip(vistos, det.iterrows(), strict=True):
        assert ultimo_y == ultimo_x == int(fila.origen)
        assert int(fila.objetivo) == ultimo_y + 1


def test_sarimax_con_macro_usa_x_rezagado():
    """B-007: si X_t explica y_t exacto, el modelo rezagado no puede aprovecharlo."""
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(0, 1, 60), index=np.arange(1960, 2020))
    y = 2 * x
    X = x.to_frame("x")
    pron = modelos._sarimax(y, 1, X, order=(0, 0, 0), trend="c", usar_x=True)
    # Con el X contemporaneo el pronostico seria 2 * x[2019]; rezagado no lo recupera.
    assert abs(pron[0] - 2 * x.iloc[-1]) > 0.1


# ------------------------------------------------------------------ R-07

def test_resumen_saca_del_ordenamiento_a_quien_no_cubre():
    y = _serie_anual(60)

    def fragil(y_tr, h, X=None):
        if len(y_tr) % 2:
            raise RuntimeError("revienta en la mitad de los origenes")
        return np.repeat(y.mean(), h)  # tramposo a proposito: conoce la media total

    det = backtest.origen_movil(
        y, [Modelo("Ingenuo", "referencia", _naive), Modelo("fragil", "t", fragil)],
        h=1, min_entrenamiento=30, verbose=False)
    tabla = backtest.resumen(det).set_index("modelo")
    assert not tabla.loc["fragil", "rankeable"]
    assert tabla.loc["fragil", "cobertura"] == pytest.approx(0.5)
    assert tabla.index[0] == "Ingenuo"
    assert pd.isna(tabla.loc["Ingenuo", "dm_p"])


def test_combinacion_no_rellena_el_fallo_del_flexible():
    """B-006: un flexible que falla no se sustituye por el robusto."""
    y = _serie_anual(40)

    def flexible_roto(y_tr, h, X=None):
        return np.full(h, np.nan)

    m = Modelo("comb", "combinacion", combinacion._combinar,
               params=dict(flexible=flexible_roto, robusto=_naive, cuantil=0.99))
    assert np.isnan(m.predecir(y, 1)).all()


# ------------------------------------------------------------------ R-06

def test_holm_es_monotono_y_no_menor_que_la_p_cruda():
    p = pd.Series([0.01, 0.04, np.nan, 0.03, 0.5])
    aj = backtest._holm(p)
    assert pd.isna(aj[2])
    assert (aj.dropna() >= p.dropna()).all()
    orden = p.dropna().sort_values().index
    assert aj[orden].is_monotonic_increasing
    assert aj[0] == pytest.approx(0.04)


def test_resumen_trae_p_ajustada():
    y = _serie_anual(60)
    cat = [Modelo("Ingenuo", "referencia", _naive),
           Modelo("Media", "referencia", modelos._media)]
    tabla = backtest.resumen(backtest.origen_movil(y, cat, min_entrenamiento=30,
                                                   verbose=False))
    fila = tabla.set_index("modelo").loc["Media"]
    assert fila.dm_p_holm >= fila.dm_p


# ------------------------------------------------------------------ R-10 / B-002

def test_regimen_se_asigna_por_el_periodo_pronosticado():
    y = pd.Series(np.arange(10, dtype=float), index=np.arange(2015, 2025))
    det = backtest.origen_movil(y, [Modelo("Ingenuo", "referencia", _naive)],
                                min_entrenamiento=3, verbose=False)
    reg = backtest.regimen(det).set_axis(det.origen)
    assert reg["2019"] == "ruptura"   # pronostica 2020
    assert reg["2021"] == "calma"     # pronostica 2022


def test_regimen_trimestral():
    idx = pd.period_range("2019Q1", periods=16, freq="Q")
    y = pd.Series(np.arange(16, dtype=float), index=idx)
    det = backtest.origen_movil(y, [Modelo("Ingenuo", "referencia", _naive)],
                                min_entrenamiento=4, verbose=False)
    reg = backtest.regimen(det).set_axis(det.origen)
    assert reg["2019Q4"] == "ruptura"
    assert reg["2021Q4"] == "calma"


# ------------------------------------------------------------------ B-001 / B-008

@pytest.mark.parametrize("idx", [
    pd.period_range("2019Q1", periods=8, freq="Q"),
    pd.date_range("2019-01-01", periods=24, freq="MS"),
    pd.Index(np.arange(2015, 2023)),
])
def test_indice_futuro_y_dummies_en_los_tres_tipos_de_indice(idx):
    fut = _indice_futuro(idx, 3)
    assert len(fut) == 3
    d = _dummies_covid(idx)
    assert d.shape == (len(idx), 2)
    assert d[:, 0].sum() > 0  # todos los indices cruzan 2020


def test_modelo_recursivo_funciona_con_periodindex():
    """B-001: el Random Forest revento en todos los origenes trimestrales."""
    from sklearn.linear_model import Ridge
    idx = pd.period_range("2000Q1", periods=60, freq="Q")
    y = pd.Series(np.sin(np.arange(60) / 3), index=idx)
    m = Modelo("Ridge", "regularizado", modelos._supervisado,
               params=dict(estimador=Ridge(), n_lags=4))
    assert np.isfinite(m.predecir(y, 2)).all()


# ------------------------------------------------------------------ R-03 / B-004

def test_tramo_contiguo_corta_en_el_ultimo_hueco():
    s = pd.Series(1.0, index=[1960, 1961, 1963, 1964, 1965, 1967, 1968])
    assert list(datos.tramo_contiguo(s).index) == [1967, 1968]
    sin_huecos = pd.Series(1.0, index=np.arange(1990, 2000))
    assert len(datos.tramo_contiguo(sin_huecos)) == 10


def test_panel_anual_sin_huecos_y_respeta_n_p():
    rng = np.random.default_rng(2)
    df = pd.DataFrame(rng.normal(size=(60, 6)), index=np.arange(1960, 2020),
                      columns=list("abcdef"))
    df.loc[1985, "f"] = np.nan  # la variable f abre un hueco si se exige
    panel = datos.panel_anual(df, min_ratio=3.0)
    assert (np.diff(panel.index) == 1).all()
    assert len(panel) / panel.shape[1] >= 3.0


# ------------------------------------------------------------------ R-05

@pytest.mark.skipif(not (RAIZ / "datos/crudo/anex-ISE-12actividades.xlsx").exists(),
                    reason="falta el anexo ISE")
def test_ise_se_lee_del_cuadro_sin_ajuste():
    ise = datos.serie_ise(RAIZ / "datos/crudo/anex-ISE-12actividades.xlsx")
    assert len(ise) >= 246
    assert ise.notna().all()
    assert ise.index.is_monotonic_increasing
    assert (ise.index.to_series().diff().dropna().dt.days.between(28, 31)).all()
