"""Adquisicion de datos. Dos pistas, porque los datos mandan.

Pista A (anual): Banco Mundial, 33 indicadores macro de Colombia desde 1960.
Pista B (mensual): ISE del DANE, 2005-01 a 2026-06, agregado y 15 series sectoriales.

La regla que gobierna este modulo: ninguna serie se rellena, se interpola ni se repite
para cuadrar frecuencias. Si una variable es anual, se queda anual. Mezclar frecuencias
por relleno fabrica informacion que no existe (es el error que la tesis de origen cometio
con el PIB departamental y le costo el capitulo de rezagos).
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CRUDO = RAIZ / "datos" / "crudo"
PROC = RAIZ / "datos" / "procesado"

# --------------------------------------------------------------------------- Pista A

INDICADORES = {
    # 1. Actividad economica
    "pib_real": "NY.GDP.MKTP.KD",
    "pib_crecimiento": "NY.GDP.MKTP.KD.ZG",
    "pib_per_capita": "NY.GDP.PCAP.KD",
    "productividad": "SL.GDP.PCAP.EM.KD",
    # 2. Mercado laboral
    "desempleo": "SL.UEM.TOTL.ZS",
    "participacion_laboral": "SL.TLF.CACT.ZS",
    "empleo_poblacion": "SL.EMP.TOTL.SP.ZS",
    # 3. Precios
    "inflacion_ipc": "FP.CPI.TOTL.ZG",
    "deflactor_pib": "NY.GDP.DEFL.KD.ZG",
    # 4. Politica monetaria y financiera
    "tasa_interes_real": "FR.INR.RINR",
    "m3_pib": "FM.LBL.BMNY.GD.ZS",
    "credito_privado_pib": "FS.AST.PRVT.GD.ZS",
    "tipo_cambio": "PA.NUS.FCRF",
    "reservas": "FI.RES.TOTL.CD",
    # 5. Sector externo
    "exportaciones_pib": "NE.EXP.GNFS.ZS",
    "importaciones_pib": "NE.IMP.GNFS.ZS",
    "cuenta_corriente_pib": "BN.CAB.XOKA.GD.ZS",
    "ied_pib": "BX.KLT.DINV.WD.GD.ZS",
    "remesas_pib": "BX.TRF.PWKR.DT.GD.ZS",
    # 6. Finanzas publicas
    "deuda_publica_pib": "GC.DOD.TOTL.GD.ZS",
    "ingresos_tributarios_pib": "GC.TAX.TOTL.GD.ZS",
    "gasto_publico_pib": "NE.CON.GOVT.ZS",
    # 7. Demografia
    "poblacion": "SP.POP.TOTL",
    "crecimiento_poblacional": "SP.POP.GROW",
    "poblacion_15_64": "SP.POP.1564.TO.ZS",
    "urbanizacion": "SP.URB.TOTL.IN.ZS",
    "migracion_neta": "SM.POP.NETM",
    # 8. Distribucion y bienestar
    "gini": "SI.POV.GINI",
    "pobreza_nacional": "SI.POV.NAHC",
    "pobreza_extrema": "SI.POV.DDAY",
    "consumo_hogares_pib": "NE.CON.PRVT.ZS",
    "esperanza_vida": "SP.DYN.LE00.IN",
    "inversion_pib": "NE.GDI.TOTL.ZS",
}

CATEGORIA = {
    "pib_real": "1-actividad", "pib_crecimiento": "1-actividad",
    "pib_per_capita": "1-actividad", "productividad": "1-actividad",
    "desempleo": "2-laboral", "participacion_laboral": "2-laboral",
    "empleo_poblacion": "2-laboral",
    "inflacion_ipc": "3-precios", "deflactor_pib": "3-precios",
    "tasa_interes_real": "4-monetario", "m3_pib": "4-monetario",
    "credito_privado_pib": "4-monetario", "tipo_cambio": "4-monetario",
    "reservas": "4-monetario",
    "exportaciones_pib": "5-externo", "importaciones_pib": "5-externo",
    "cuenta_corriente_pib": "5-externo", "ied_pib": "5-externo",
    "remesas_pib": "5-externo",
    "deuda_publica_pib": "6-fiscal", "ingresos_tributarios_pib": "6-fiscal",
    "gasto_publico_pib": "6-fiscal",
    "poblacion": "7-demografia", "crecimiento_poblacional": "7-demografia",
    "poblacion_15_64": "7-demografia", "urbanizacion": "7-demografia",
    "migracion_neta": "7-demografia",
    "gini": "8-bienestar", "pobreza_nacional": "8-bienestar",
    "pobreza_extrema": "8-bienestar", "consumo_hogares_pib": "8-bienestar",
    "esperanza_vida": "8-bienestar", "inversion_pib": "8-bienestar",
}


def descargar_banco_mundial(pais: str = "COL", forzar: bool = False) -> pd.DataFrame:
    """Baja los indicadores anuales y los deja en una matriz anio x variable."""
    destino = PROC / "macro_anual.parquet"
    if destino.exists() and not forzar:
        return pd.read_parquet(destino)

    CRUDO.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    series, bitacora = {}, []
    for nombre, codigo in INDICADORES.items():
        url = (f"https://api.worldbank.org/v2/country/{pais}/indicator/{codigo}"
               f"?format=json&per_page=300")
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                bruto = json.load(r)
            puntos = {int(x["date"]): x["value"]
                      for x in (bruto[1] or []) if x["value"] is not None}
            if puntos:
                series[nombre] = pd.Series(puntos, name=nombre)
                bitacora.append(dict(variable=nombre, codigo=codigo, n=len(puntos),
                                     desde=min(puntos), hasta=max(puntos),
                                     categoria=CATEGORIA[nombre]))
        except Exception as exc:  # pragma: no cover - red
            print(f"  ! {nombre}: {type(exc).__name__}")
        time.sleep(0.1)

    df = pd.DataFrame(series).sort_index()
    df.index.name = "anio"
    df.to_parquet(destino)
    pd.DataFrame(bitacora).to_csv(PROC / "macro_anual_cobertura.csv", index=False)
    return df


def frontera_cobertura(df: pd.DataFrame) -> pd.DataFrame:
    """Cuantos anios completos sobreviven a medida que se exigen mas variables.

    Es el diagnostico que decide el diseno del laboratorio: pedir las 33 variables a la
    vez deja 13 anios, y con 13 observaciones no se estima nada.

    `n_anios` cuenta anios completos; `n_contiguos` y `ratio_n_p`, solo el tramo
    consecutivo final, que es lo que un modelo de rezagos puede usar (B-004).
    """
    cobertura = df.notna().sum().sort_values(ascending=False)
    filas = []
    for k in range(3, len(cobertura) + 1):
        sub = df[list(cobertura.index[:k])].dropna()
        cont = tramo_contiguo(sub)
        filas.append(dict(
            k_variables=k, n_anios=len(sub), n_contiguos=len(cont),
            desde=int(cont.index.min()) if len(cont) else None,
            hasta=int(cont.index.max()) if len(cont) else None,
            ratio_n_p=len(cont) / k,
            entra=cobertura.index[k - 1],
        ))
    return pd.DataFrame(filas)


def tramo_contiguo(df):
    """El tramo de anios consecutivos mas largo que termina en el ultimo anio presente.

    `dropna()` por filas quita un anio incompleto pero deja pegados a sus vecinos, y un
    modelo de rezagos trata 1985 -> 1987 como un solo anio (B-004). Aqui se corta en el
    ultimo hueco: se pierde historia vieja, no se fabrica continuidad.
    """
    if len(df) == 0:
        return df
    anios = np.asarray(df.index, dtype=int)
    huecos = np.flatnonzero(np.diff(anios) != 1)
    inicio = huecos[-1] + 1 if len(huecos) else 0
    return df.iloc[inicio:]


def panel_anual(df: pd.DataFrame, min_ratio: float = 3.0) -> pd.DataFrame:
    """El panel anual mas grande que respeta un ratio n/p minimo.

    No se eligen las variables por criterio economico sino por cobertura, y luego se
    reporta cuales quedaron fuera. Elegirlas a mano mirando el resultado seria el sesgo
    de seleccion que este laboratorio existe para evitar.
    """
    frontera = frontera_cobertura(df)
    viables = frontera[frontera.ratio_n_p >= min_ratio]
    k = int(viables.k_variables.max())
    cobertura = df.notna().sum().sort_values(ascending=False)
    elegidas = list(cobertura.index[:k])
    return tramo_contiguo(df[elegidas].dropna())


# --------------------------------------------------------------------------- Pista B

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def parsear_ise(ruta_xlsx: Path, cuadro: str = "Cuadro 1") -> pd.DataFrame:
    """Anexo ISE del DANE a una matriz mes x actividad.

    `Cuadro 1` son datos originales, `Cuadro 2` ajustados por efecto estacional y de
    calendario, `Cuadro 3` tendencia-ciclo. Para pronosticar se usa el Cuadro 1: el
    ajuste estacional del DANE usa la serie completa, incluido el futuro respecto de
    cualquier origen de pronostico, y meterlo en un backtest seria mirar adelante.
    """
    import openpyxl

    wb = openpyxl.load_workbook(ruta_xlsx, read_only=True, data_only=True)
    filas = list(wb[cuadro].iter_rows(values_only=True))
    wb.close()

    anios_fila, meses_fila = filas[10], filas[11]
    fechas, columnas = [], []
    anio_actual = None
    for j in range(3, len(meses_fila)):
        crudo_anio = anios_fila[j] if j < len(anios_fila) else None
        if crudo_anio not in (None, ""):
            anio_actual = int(str(crudo_anio)[:4])
        mes = meses_fila[j]
        if anio_actual is None or mes in (None, ""):
            continue
        nombre_mes = str(mes).strip()
        if nombre_mes not in MESES:
            continue
        fechas.append(pd.Timestamp(year=anio_actual, month=MESES.index(nombre_mes) + 1, day=1))
        columnas.append(j)

    datos = {}
    for i in range(13, 29):
        if i >= len(filas):
            break
        concepto = filas[i][2]
        if concepto in (None, ""):
            continue
        nombre = str(concepto).strip()
        valores = []
        for j in columnas:
            v = filas[i][j] if j < len(filas[i]) else None
            valores.append(float(v) if isinstance(v, (int, float)) else np.nan)
        datos[nombre] = valores

    df = pd.DataFrame(datos, index=pd.DatetimeIndex(fechas, name="fecha"))
    return df.sort_index()


def serie_ise(ruta_xlsx: Path) -> pd.Series:
    """Solo el agregado: el ISE total, mensual."""
    df = parsear_ise(ruta_xlsx)
    columna = [c for c in df.columns if c.lower().startswith("indicador de seguimiento")]
    if not columna:
        raise ValueError(f"no encuentro el agregado en {list(df.columns)}")
    return df[columna[0]].rename("ise").dropna()
