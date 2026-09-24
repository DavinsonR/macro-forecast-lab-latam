# macro-forecast-lab-latam

Laboratorio de modelos de pronóstico del crecimiento económico agregado: Colombia en
detalle y 20 países de América Latina. Compara la escalera completa — desde la caminata
aleatoria hasta LSTM y CNN — bajo un único protocolo de evaluación con origen móvil.

**La pregunta que responde no es "¿qué modelo predice el crecimiento?" sino "¿alguno de
estos modelos le gana al pronóstico ingenuo, y con qué margen?".** Son preguntas
distintas y la segunda es la honesta.

---

## El hallazgo que decide el diseño

Se pidieron a la API del Banco Mundial las 33 variables macro de las ocho categorías
habituales (actividad, laboral, precios, monetario, externo, fiscal, demografía,
bienestar). **Las 33 existen para Colombia.** Ese no es el problema.

El problema es la intersección:

| Variables exigidas | Años completos | Tramo contiguo | Rango contiguo | n/p |
|---|---|---|---|---|
| 14 | 66 | 66 | 1960–2025 | 4,71 |
| 18 | 64 | 64 | 1961–2024 | 3,56 |
| 20 | 62 | 35 | 1990–2024 | 1,75 |
| 24 | 37 | 35 | 1990–2024 | 1,46 |
| 28 | 34 | 34 | 1991–2024 | 1,21 |
| 31 | 20 | 17 | 2008–2024 | 0,55 |
| **33** | **13** | **13** | **2012–2024** | **0,39** |

"Tramo contiguo" es lo que un modelo de rezagos puede usar: los años completos que no
tienen huecos en medio. Con 20 variables hay 62 años completos, pero los huecos de 1986 y
1989 dejan solo 35 consecutivos. La versión 0.1.0 contaba los 62 (B-004).

**Pedir las 33 variables a la vez deja 13 observaciones anuales.** Con 13 filas y 33
columnas no se estima nada: hay más parámetros que datos, y cualquier modelo ajusta
perfecto en muestra y no vale nada fuera de ella.

Las cinco variables que estrangulan la muestra son del bloque de bienestar y fiscal:

| Variable | Años disponibles |
|---|---|
| Pobreza nacional | 13 (2012–2024) |
| Deuda pública % PIB | 21 (1998–2024) |
| Ingresos tributarios % PIB | 21 (1998–2024) |
| Gini | 30 |
| Pobreza extrema | 30 |

Renunciar a esas cinco lleva la muestra de 13 a 34 años. Renunciar también al bloque
laboral, al monetario y al externo la lleva a 64 contiguos, con 18 variables. **Ese es el precio real de cada variable, y casi nunca se calcula
antes de modelar.**

### Consecuencia: dos pistas, no una

| | Pista A | Pista B |
|---|---|---|
| Objetivo | Crecimiento anual del PIB real | Variación anual del ISE |
| Fuente | Banco Mundial | DANE, anexo ISE |
| Observaciones | 64 anuales contiguas | 246 mensuales |
| Variables | 15 macro | univariada |
| Para qué sirve | Modelos con exógenas, factores, regularización | Estacionalidad y redes neuronales |

Las redes profundas solo se evalúan en serio en la Pista B. Con 64 observaciones
anuales, un LSTM no tiene de dónde aprender; se corre igual, y el resultado es parte de
lo que el laboratorio reporta.

---

## Protocolo de evaluación

**Origen móvil con ventana expansiva.** Se fija un origen, se entrena solo con lo
anterior, se pronostica, se anota el error, se avanza el origen. Cada modelo se reajusta
por completo en cada origen.

Reglas que el código hace cumplir:

- Ningún modelo ve un dato posterior a su origen de pronóstico.
- Los escaladores se ajustan solo con el tramo de entrenamiento.
- Las redes fijan semilla y paran temprano contra una validación recortada del propio
  entrenamiento, nunca contra el tramo de prueba.
- Si un modelo no converge en un origen, queda como faltante y se reporta el conteo de
  fallos. No se rellena con el pronóstico de otro.
- **Se usa el ISE sin ajuste estacional** (Cuadro 1). El ajuste estacional del DANE usa
  la serie completa, incluido el futuro respecto de cualquier origen: meterlo en un
  backtest sería mirar adelante.

- Los regímenes (calma, ruptura) se asignan por el **período pronosticado**, no por el
  origen.
- Una serie anual no salta años: se usa el tramo contiguo más largo.

La comparación contra la referencia usa **Diebold-Mariano pareado**, con la p ajustada
por **Holm** porque cada tabla prueba de 8 a 26 modelos a la vez. Entre países se usa
Wilcoxon. Una diferencia de MAE sin prueba no distingue una mejora real del ruido.

---

## Modelos

**Referencias** — ingenuo, ingenuo estacional, media histórica, media móvil, deriva.

**Box-Jenkins** — AR(1), AR(2), AR(12), MA(1), MA(2), ARMA(1,1), ARMA(2,1), ARMA(2,2),
ARIMA(1,1,1), ARIMA(2,1,0), ARIMA(2,1,2), y variantes con dummies de COVID.

**Estacionales** — SARIMA(1,1,1)(1,1,1,12), SARIMA(2,1,1)(0,1,1,12), SARIMAX con COVID.

**Con exógenas** — SARIMAX + bloque macro, VAR(2).

**Regularizados** — Ridge, Lasso, ElasticNet, factores PCA + AR.

**Aprendizaje** — Random Forest, Gradient Boosting, MLP.

**Redes** — LSTM (ventanas 12 y 24), CNN 1D (ventanas 12 y 24).

---

## Uso

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.12.

```bash
uv sync
uv run python -m macro_lab.main             # pistas A (anual COL) y B (ISE mensual)
uv run python -m macro_lab.robustez         # partición por subperíodo
uv run python -m macro_lab.lab_latam        # pistas C (trimestral) y D (anual, 20 países)
uv run python -m macro_lab.lab_combinacion  # combinación por régimen
uv run python -m macro_lab.lab_frecuencia   # ISE remuestreado a trimestral
uv run python -m macro_lab.pronostico       # pronóstico 2026-2027 con bandas (D-008)
```

Los datos van versionados en `datos/` (anexo ISE del DANE y caché del Banco Mundial y
del FMI, descargados el 18-sep-2026), así que todo corre sin red. Las corridas completas
tardan del orden de una hora en un portátil.

Salidas en `salidas/`: resúmenes con cobertura, `dm_p` y `dm_p_holm`; detalle por origen
con el período pronosticado (`objetivo`); agregados LATAM; fronteras de cobertura.

## En la web

El laboratorio tiene una versión interactiva en
[davirson.com/es/labs/macro-forecast](https://davirson.com/es/labs/macro-forecast): el visitante
juega contra el ingenuo, mueve el origen del backtest, recorre la región y activa la corrección de
Holm. La página no corre modelos: lee `web/forecast-lab/*.json`, que genera
`uv run python -m macro_lab.exportar_web` a partir de `salidas/`. El exportador comprueba que cada
pronóstico cuadre con su período y con el valor real antes de escribir.

La página abre con un tablero descriptivo de las 20 economías y el **pronóstico 2026–2027**
de crecimiento (`pronostico.json`): un AR(1) por economía, con bandas al 80 y 95 % y, al
lado, cuántas veces esas bandas contuvieron el dato real en el backtest (D-008).

## Pruebas

```bash
uv run python -m pytest -q
uv run ruff check
```

Las pruebas no miden si un modelo pronostica bien: comprueban que el protocolo no se
engañe a sí mismo (nada ve el futuro, la cobertura filtra, el régimen se asigna por el
período pronosticado, no hay años saltados, la combinación no rellena fallos). CI las
corre en cada PR. Los errores encontrados y cómo se corrigieron están en
[docs/BITACORA.md](docs/BITACORA.md).

---

## Qué NO hace este laboratorio

- **No mezcla frecuencias por relleno.** Si una variable es anual, se queda anual.
  Repetir un valor anual en doce meses fabrica variación que no existe. Es el error que
  la tesis de origen cometió con el PIB departamental y le costó el capítulo de rezagos.
- **No selecciona hiperparámetros mirando el error de prueba.**
- **No promedia modelos elegidos por su desempeño en la misma muestra donde se miden.**
- **No presenta un ganador sin decir por cuánto gana y si esa diferencia es
  significativa.**
- **No publica una banda sin medir si cumple.** El pronóstico 2026–2027 va con la
  cobertura empírica de sus bandas, economía por economía.

## Licencias

Código: MIT (`LICENSE`). Datos: Banco Mundial, CC BY 4.0; DANE, uso público con
atribución; FMI International Financial Statistics, vía DBnomics, bajo los términos del
FMI. Para citar el laboratorio: `CITATION.cff`.

---

## Resultados

Ver **[RESULTADOS.md](RESULTADOS.md)** para las tablas completas. En una línea:

> Sobre la muestra completa, ningún modelo le gana al ingenuo de forma significativa
> tras corregir por comparaciones múltiples. En la calma mensual sí: Random Forest
> (+24 %) y tres ARIMA/ARMA, con p ajustada < 0,02. En la serie anual ningún modelo se
> distingue del ingenuo, y añadir las variables macro empeora el pronóstico.

---

## Extensión LATAM

20 países, el mismo protocolo. Ver **[RESULTADOS_LATAM.md](RESULTADOS_LATAM.md)**.

> El resultado más robusto es modesto: **en calma, el AR(1) le gana al ingenuo en toda la
> región** (8 de 8 países trimestrales; mediana 0,86 del error del ingenuo en 19 anuales,
> Wilcoxon p = 0,001). Ningún ranking por país sobrevive a Holm. La combinación por
> régimen que funcionaba en el ISE no se replica fuera de él. La frontera de cobertura sí
> generaliza: en 17 de 20 países, exigir las 33 variables deja cero años completos.
