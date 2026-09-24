"""LATAM: el mismo laboratorio, veinte paises.

Un solo pais no distingue un hallazgo de una casualidad. Correr el mismo protocolo sobre
veinte economias convierte "el Random Forest gana fuera del COVID" de anecdota en algo
contrastable: o el patron se repite en la mayoria de los paises, o no existe.

Dos pistas, igual que en Colombia:
  A (anual)     Banco Mundial, 1961-2025, ~20 variables macro por pais.
  C (trimestral) FMI IFS via DBnomics, PIB real. Es la unica fuente trimestral
                 homogenea para toda la region: cada oficina nacional publica su propio
                 indicador mensual (IMACEC, IGAE, EMAE, IBC-Br) con definiciones que no
                 son comparables entre si.

Se trabaja en variacion interanual. La regla (R-05) es preferir la serie SIN ajuste
estacional, porque el ajuste se reestima con la serie completa y mete futuro en el
backtest. **Excepcion declarada (B-003):** para los 8 paises con serie trimestral util,
el IFS solo publica la version ajustada (`NGDP_R_SA_XDC`); no hay alternativa sin ajustar
en la misma fuente. Se usa la ajustada, la columna `ajuste` del parquet lo registra y la
corrida lo imprime. Consecuencia: los errores de la Pista C pueden ser algo optimistas
para todos los modelos por igual, porque el filtro estacional ya vio el futuro.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .datos import tramo_contiguo

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesado"

# ISO3 para el Banco Mundial, ISO2 para el FMI.
PAISES = {
    "ARG": ("AR", "Argentina"), "BOL": ("BO", "Bolivia"), "BRA": ("BR", "Brasil"),
    "CHL": ("CL", "Chile"), "COL": ("CO", "Colombia"), "CRI": ("CR", "Costa Rica"),
    "DOM": ("DO", "Rep. Dominicana"), "ECU": ("EC", "Ecuador"),
    "SLV": ("SV", "El Salvador"), "GTM": ("GT", "Guatemala"),
    "HND": ("HN", "Honduras"), "MEX": ("MX", "Mexico"), "NIC": ("NI", "Nicaragua"),
    "PAN": ("PA", "Panama"), "PRY": ("PY", "Paraguay"), "PER": ("PE", "Peru"),
    "URY": ("UY", "Uruguay"), "VEN": ("VE", "Venezuela"),
    "CUB": ("CU", "Cuba"), "HTI": ("HT", "Haiti"),
}


def _json(url: str, intentos: int = 3, espera: float = 2.0, timeout: int = 45):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "macro-lab/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == intentos - 1:
                raise
            time.sleep(espera * (i + 1))
    return None


# Tramos de la fuente que se sabe que estan rotos (B-010). Se enmascaran antes de cortar
# el tramo contiguo: un dato imposible no se corrige ni se interpola, se quita.
DEFECTOS: dict[tuple[str, str], tuple[int, int]] = {
    ("HND", "pib_crecimiento"): (1990, 1999),
    ("HND", "pib_per_capita"): (1990, 1999),
    ("HND", "pib_real"): (1990, 1999),
}


def enmascarar(largo: pd.DataFrame) -> pd.DataFrame:
    """El panel largo sin los tramos declarados en DEFECTOS."""
    fuera = pd.Series(False, index=largo.index)
    for (iso3, var), (a, b) in DEFECTOS.items():
        fuera |= (largo.iso3 == iso3) & (largo.variable == var) & largo.anio.between(a, b)
    return largo[~fuera]


def serie_anual(largo: pd.DataFrame, iso3: str, variable: str = "pib_crecimiento") -> pd.Series:
    """Una variable anual de una economia, sin defectos declarados y en su tramo contiguo."""
    s = (enmascarar(largo).query("iso3 == @iso3 and variable == @variable")
         .set_index("anio").valor.sort_index())
    return tramo_contiguo(s)


# ------------------------------------------------------------------ Pista A LATAM

def descargar_anual_latam(indicadores: dict[str, str], forzar: bool = False) -> pd.DataFrame:
    """Panel largo pais-anio-variable. Una peticion por pais y variable, con reintentos.

    La peticion multipais del Banco Mundial se cae por timeout con veinte codigos, asi
    que se pide uno a uno. Es mas lento y es lo que funciona.
    """
    destino = PROC / "latam_anual.parquet"
    if destino.exists() and not forzar:
        return pd.read_parquet(destino)

    PROC.mkdir(parents=True, exist_ok=True)
    filas = []
    for iso3, (_, nombre) in PAISES.items():
        obtenidas = 0
        for var, codigo in indicadores.items():
            url = (f"https://api.worldbank.org/v2/country/{iso3}/indicator/{codigo}"
                   f"?format=json&per_page=300")
            try:
                bruto = _json(url)
                for x in (bruto[1] or []):
                    if x["value"] is not None:
                        filas.append(dict(iso3=iso3, pais=nombre, anio=int(x["date"]),
                                          variable=var, valor=float(x["value"])))
                obtenidas += 1
            except Exception:
                pass
            time.sleep(0.08)
        print(f"  {nombre:18s} {obtenidas}/{len(indicadores)} variables")

    df = pd.DataFrame(filas)
    df.to_parquet(destino, index=False)
    return df


def panel_pais(largo: pd.DataFrame, iso3: str, min_ratio: float = 3.0
               ) -> tuple[pd.DataFrame, list[str]]:
    """Del panel largo al cuadro anio x variable de un pais, recortado por cobertura."""
    ancho = (largo[largo.iso3 == iso3]
             .pivot_table(index="anio", columns="variable", values="valor"))
    cobertura = ancho.notna().sum().sort_values(ascending=False)
    elegidas, mejor = [], None
    for k in range(3, len(cobertura) + 1):
        sub = tramo_contiguo(ancho[list(cobertura.index[:k])].dropna())
        if len(sub) / k >= min_ratio:
            mejor, elegidas = sub, list(cobertura.index[:k])
    if mejor is None:
        return pd.DataFrame(), []
    fuera = [c for c in ancho.columns if c not in elegidas]
    return mejor, fuera


# ------------------------------------------------------------- Pista C LATAM

# Real GDP, domestic currency. `_SA_` es la version ajustada estacionalmente.
IFS_PIB_NSA = "Q.{iso2}.NGDP_R_XDC"
IFS_PIB_SA = "Q.{iso2}.NGDP_R_SA_XDC"


def _serie_dbnomics(sid: str) -> pd.Series | None:
    url = f"https://api.db.nomics.world/v22/series/{sid}?observations=1"
    try:
        d = _json(url)
    except Exception:
        return None
    docs = d.get("series", {}).get("docs", [])
    if not docs:
        return None
    o = docs[0]
    pares = [(p, v) for p, v in zip(o["period"], o["value"], strict=True) if v is not None]
    if not pares:
        return None
    idx = pd.PeriodIndex([p for p, _ in pares], freq="Q")
    return pd.Series([float(v) for _, v in pares], index=idx).sort_index()


def descargar_trimestral_latam(forzar: bool = False) -> pd.DataFrame:
    """PIB real trimestral por pais. Prefiere la serie sin ajuste estacional."""
    destino = PROC / "latam_trimestral.parquet"
    if destino.exists() and not forzar:
        return pd.read_parquet(destino)

    PROC.mkdir(parents=True, exist_ok=True)
    filas = []
    for iso3, (iso2, nombre) in PAISES.items():
        elegida, ajuste = None, None
        for plantilla, etiqueta in ((IFS_PIB_NSA, "sin ajuste"), (IFS_PIB_SA, "ajustada")):
            s = _serie_dbnomics("IMF/IFS/" + plantilla.format(iso2=iso2))
            if s is not None and len(s) >= 40:
                elegida, ajuste = s, etiqueta
                break
        if elegida is None:
            print(f"  {nombre:18s} sin serie trimestral utilizable")
            continue
        print(f"  {nombre:18s} {len(elegida):3d} trimestres  "
              f"{elegida.index[0]} -> {elegida.index[-1]}  ({ajuste})")
        for per, val in elegida.items():
            filas.append(dict(iso3=iso3, pais=nombre, periodo=str(per),
                              pib_real=val, ajuste=ajuste))
        time.sleep(0.2)

    df = pd.DataFrame(filas)
    df.to_parquet(destino, index=False)
    return df


def serie_crecimiento_trimestral(df: pd.DataFrame, iso3: str) -> pd.Series:
    """Variacion interanual del PIB real, en porcentaje."""
    sub = df[df.iso3 == iso3].copy()
    if sub.empty:
        return pd.Series(dtype=float)
    s = pd.Series(sub.pib_real.to_numpy(),
                  index=pd.PeriodIndex(sub.periodo, freq="Q")).sort_index()
    return (s.pct_change(4) * 100).dropna().rename(iso3).replace([np.inf, -np.inf], np.nan).dropna()
