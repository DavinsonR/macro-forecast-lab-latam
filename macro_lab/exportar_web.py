"""El contrato con la pagina web: `web/forecast-lab/*.json`.

`uv run python -m macro_lab.exportar_web`

La pagina del laboratorio en el sitio personal (davirson.com, /labs/macro-forecast) no
corre modelos: lee estos JSON, que salen de `salidas/` y de los datos versionados. Es el
mismo contrato que la tesis tiene con su atlas: una carpeta que se copia tal cual a
`public/forecast-lab/` del sitio.

Nada se recalcula distinto de como lo hace el laboratorio: las series se construyen con
las mismas funciones (`tramo_contiguo`, `serie_crecimiento_trimestral`), y cada pronostico
se alinea con su periodo objetivo y se comprueba contra el valor real del detalle. Si
algo no cuadra, el exportador falla en vez de publicar una serie corrida un periodo.
"""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__, backtest, datos, latam

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"
DESTINO = RAIZ / "web" / "forecast-lab"
RUPTURA = (2020, 2021)

# Los que la pagina deja comparar. Uno por familia, mas la combinacion que se diseno en
# el ISE: es la que el lector tiene que poder ver fallar fuera de el.
MODELOS = ["Ingenuo", "AR(1)", "ARIMA(1,1,1)", "Random Forest", "LSTM(16)",
           "Comb. RF/AR(1) suave"]
ID = {"Ingenuo": "naive", "AR(1)": "ar1", "ARIMA(1,1,1)": "arima", "Random Forest": "rf",
      "LSTM(16)": "lstm", "Comb. RF/AR(1) suave": "comb"}

# El laboratorio guarda los nombres sin tildes (la consola de Windows es cp1252, R-01);
# la pagina los publica bien escritos.
NOMBRE_ES = {"MEX": "México", "PER": "Perú", "PAN": "Panamá", "HTI": "Haití",
             "DOM": "Rep. Dominicana"}

NOMBRE_EN = {
    "ARG": "Argentina", "BOL": "Bolivia", "BRA": "Brazil", "CHL": "Chile",
    "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Rep.", "ECU": "Ecuador",
    "SLV": "El Salvador", "GTM": "Guatemala", "HND": "Honduras", "MEX": "Mexico",
    "NIC": "Nicaragua", "PAN": "Panama", "PRY": "Paraguay", "PER": "Peru",
    "URY": "Uruguay", "VEN": "Venezuela", "CUB": "Cuba", "HTI": "Haiti",
}


def _r(v, nd=2):
    """Redondeo para el JSON; NaN pasa a null (un fallo no es un cero)."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    return round(float(v), nd)


def _entero(v):
    return None if pd.isna(v) else int(v)


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                                       text=True).strip()
    except Exception:
        return "desconocido"


def _series(detalle: pd.DataFrame, y_de: dict[str, pd.Series], min_ent: int) -> list[dict]:
    """Una entrada por pais: la serie completa y el pronostico de cada modelo por origen."""
    salida = []
    for iso3, y in y_de.items():
        det = detalle[detalle.iso3 == iso3]
        if det.empty:
            continue
        etiquetas = [str(i) for i in y.index]
        objetivos = etiquetas[min_ent:]
        pron = {}
        for modelo in MODELOS:
            d = det[det.modelo == modelo].set_index("objetivo")
            d.index = d.index.astype(str)
            if list(d.index) != objetivos:
                raise ValueError(f"{iso3}/{modelo}: objetivos no alinean con la serie")
            reales = y.iloc[min_ent:].to_numpy()
            if not np.allclose(d.real.to_numpy(), reales, atol=1e-6):
                raise ValueError(f"{iso3}/{modelo}: el real del detalle no es la serie")
            pron[ID[modelo]] = [_r(v) for v in d.pronostico]
        salida.append(dict(
            iso3=iso3, inicio=etiquetas[0], o0=min_ent,
            y=[_r(v) for v in y], pron=pron,
        ))
    return salida


def _relativo(nombre: str) -> list[dict]:
    rel = pd.read_csv(SALIDAS / f"pista_{nombre}_relativo_pais.csv")
    rel = rel[rel.modelo.isin(MODELOS)]
    return [dict(iso3=r.iso3, regimen=r.regimen, modelo=ID[r.modelo], rel=_r(r.mae_rel, 3),
                 p=_r(r.dm_p, 3), sig=bool(r.gana_sig)) for r in rel.itertuples()]


def _agregado(nombre: str) -> list[dict]:
    ag = pd.read_csv(SALIDAS / f"pista_{nombre}_agregado.csv")
    filas = []
    for r in ag.itertuples():
        fila = dict(modelo=r.modelo, id=ID.get(r.modelo))
        for reg in ("calma", "ruptura"):
            fila[reg] = dict(
                mediana=_r(getattr(r, f"mediana_{reg}"), 3),
                p=_r(getattr(r, f"p_wilcoxon_{reg}"), 3),
                n=_entero(getattr(r, f"n_paises_{reg}")),
                sig=_entero(getattr(r, f"paises_sig_{reg}")),
            )
        filas.append(fila)
    return filas


def _frontera(largo: pd.DataFrame) -> list[dict]:
    """Por pais, anios completos y contiguos al exigir las k variables de mayor cobertura."""
    salida = []
    for iso3, sub in largo.groupby("iso3"):
        ancho = sub.pivot_table(index="anio", columns="variable", values="valor")
        cobertura = ancho.notna().sum().sort_values(ascending=False)
        completos, contiguos = [], []
        for k in range(1, len(datos.INDICADORES) + 1):
            if k > len(cobertura):
                completos.append(0)
                contiguos.append(0)
                continue
            sub_k = ancho[list(cobertura.index[:k])].dropna()
            completos.append(len(sub_k))
            contiguos.append(len(datos.tramo_contiguo(sub_k)))
        salida.append(dict(iso3=iso3, completos=completos, contiguos=contiguos))
    return salida


def _holm_colombia() -> list[dict]:
    """La tabla del ISE en calma, con la p cruda y la ajustada: para ver caer los asteriscos."""
    d = pd.read_csv(SALIDAS / "pista_b_detalle.csv")
    t = backtest.resumen(d[backtest.regimen(d, RUPTURA) == "calma"])
    t = t[t.modelo != "Ingenuo"]
    return [dict(modelo=r.modelo, ganancia=_r(r.ganancia_pct, 1), p=_r(r.dm_p, 4),
                 holm=_r(r.dm_p_holm, 4)) for r in t.itertuples()]


def _frecuencia() -> list[dict]:
    t = pd.read_csv(SALIDAS / "frecuencia_resumen.csv")
    t = t[(t.regimen == "ruptura") & t.modelo.isin(["LSTM(16)", "Ingenuo", "AR(1)"])]
    filas = [dict(brazo=r.brazo, modelo=ID[r.modelo], mae=_r(r.mae), ganancia=_r(r.ganancia_pct, 1),
                  p=_r(r.dm_p, 3), holm=_r(r.dm_p_holm, 3)) for r in t.itertuples()]
    b = pd.read_csv(SALIDAS / "pista_b_detalle.csv")
    r = backtest.resumen(b[backtest.regimen(b, RUPTURA) == "ruptura"]).set_index("modelo")
    for modelo, mid in (("LSTM(16) v12", "lstm"), ("Ingenuo", "naive"), ("AR(1)", "ar1")):
        f = r.loc[modelo]
        filas.append(dict(brazo="M", modelo=mid, mae=_r(f.mae), ganancia=_r(f.ganancia_pct, 1),
                          p=_r(f.dm_p, 3), holm=_r(f.dm_p_holm, 3)))
    return filas


def _escribir(nombre: str, obj) -> int:
    ruta = DESTINO / nombre
    texto = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    ruta.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)

    largo = pd.read_parquet(datos.PROC / "latam_anual.parquet")
    trim = pd.read_parquet(datos.PROC / "latam_trimestral.parquet")

    y_anual = {}
    for iso3 in sorted(largo.iso3.unique()):
        s = (largo[(largo.iso3 == iso3) & (largo.variable == "pib_crecimiento")]
             .set_index("anio").valor.sort_index())
        y_anual[iso3] = datos.tramo_contiguo(s)
    y_trim = {iso3: latam.serie_crecimiento_trimestral(trim, iso3)
              for iso3 in sorted(trim.iso3.unique())}

    anual = _series(pd.read_csv(SALIDAS / "pista_d_detalle.csv"), y_anual, 30)
    trimestral = _series(pd.read_csv(SALIDAS / "pista_c_detalle.csv"), y_trim, 40)

    nombres = latam.PAISES
    meta = dict(
        version=__version__, commit=_commit(), generado=date.today().isoformat(),
        repositorio="https://github.com/DavinsonR/macro-forecast-lab-latam",
        ruptura=list(RUPTURA),
        paises=[dict(iso3=k, es=NOMBRE_ES.get(k, v[1]), en=NOMBRE_EN[k], trimestral=k in y_trim)
                for k, v in sorted(nombres.items())],
        modelos=[dict(id=ID[m], nombre=m) for m in MODELOS],
        trimestral_ajustada=sorted(trim.loc[trim.ajuste == "ajustada", "iso3"].unique().tolist()),
    )
    resumen = dict(
        agregado=dict(anual=_agregado("d"), trimestral=_agregado("c")),
        relativo=dict(anual=_relativo("d"), trimestral=_relativo("c")),
        frontera=_frontera(largo),
        holm=_holm_colombia(),
        frecuencia=_frecuencia(),
    )

    pesos = {
        "meta.json": _escribir("meta.json", meta),
        "series_anual.json": _escribir("series_anual.json", anual),
        "series_trimestral.json": _escribir("series_trimestral.json", trimestral),
        "resumen.json": _escribir("resumen.json", resumen),
    }
    for nombre, n in pesos.items():
        print(f"  {nombre:24s} {n / 1024:6.1f} KB")
    print(f"Contrato web en {DESTINO}")


if __name__ == "__main__":
    main()
