# macro-lab-colombia

Laboratorio de modelos de pronóstico para el crecimiento económico agregado de Colombia.
Compara la escalera completa — desde la caminata aleatoria hasta LSTM y CNN — bajo un
único protocolo de evaluación con origen móvil.

**La pregunta que responde no es "¿qué modelo predice el crecimiento?" sino "¿alguno de
estos modelos le gana al pronóstico ingenuo, y con qué margen?".** Son preguntas
distintas y la segunda es la honesta.

---

## El hallazgo que decide el diseño

Se pidieron a la API del Banco Mundial las 33 variables macro de las ocho categorías
habituales (actividad, laboral, precios, monetario, externo, fiscal, demografía,
bienestar). **Las 33 existen para Colombia.** Ese no es el problema.

El problema es la intersección:

| Variables exigidas | Años completos | Rango | n/p |
|---|---|---|---|
| 14 | 66 | 1960–2025 | 4,71 |
| 20 | 62 | 1961–2024 | 3,10 |
| 24 | 37 | 1987–2024 | 1,54 |
| 28 | 34 | 1991–2024 | 1,21 |
| 31 | 20 | 1999–2024 | 0,65 |
| **33** | **13** | **2012–2024** | **0,39** |

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
laboral la lleva a 62. **Ese es el precio real de cada variable, y casi nunca se calcula
antes de modelar.**

### Consecuencia: dos pistas, no una

| | Pista A | Pista B |
|---|---|---|
| Objetivo | Crecimiento anual del PIB real | Variación anual del ISE |
| Fuente | Banco Mundial | DANE, anexo ISE |
| Observaciones | ~62 anuales | 246 mensuales |
| Variables | ~20 macro | univariada |
| Para qué sirve | Modelos con exógenas, factores, regularización | Estacionalidad y redes neuronales |

Las redes profundas solo se evalúan en serio en la Pista B. Con 62 observaciones
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

La comparación contra la referencia usa **Diebold-Mariano pareado**. Una diferencia de
MAE sin prueba de significancia no distingue una mejora real del ruido de muestreo.

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

```bash
uv sync
uv run python -m macro_lab.main
```

El anexo ISE del DANE debe estar en `datos/crudo/anex-ISE-12actividades.xlsx`.
Los datos del Banco Mundial se descargan solos y se cachean en `datos/procesado/`.

Salidas en `salidas/`: `frontera_cobertura.csv`, `pista_a_resumen.csv`,
`pista_b_resumen.csv` y el detalle por origen de cada pista.

---

## Qué NO hace este laboratorio

- **No mezcla frecuencias por relleno.** Si una variable es anual, se queda anual.
  Repetir un valor anual en doce meses fabrica variación que no existe. Es el error que
  la tesis de origen cometió con el PIB departamental y le costó el capítulo de rezagos.
- **No selecciona hiperparámetros mirando el error de prueba.**
- **No promedia modelos elegidos por su desempeño en la misma muestra donde se miden.**
- **No presenta un ganador sin decir por cuánto gana y si esa diferencia es
  significativa.**

## Licencia de datos

Banco Mundial: CC BY 4.0. DANE: uso público con atribución.

---

## Resultados

Ver **[RESULTADOS.md](RESULTADOS.md)** para las tablas completas. En una línea:

> En la serie mensual y fuera del COVID, Random Forest y LSTM le ganan al pronóstico
> ingenuo por 17–24 % con p < 0,03. Durante 2020–2021 caen al fondo de la tabla y ganan
> AR(1) y el ingenuo. En la serie anual, con 62 observaciones, **ningún** modelo se
> distingue del ingenuo — y añadir las 20 variables macro empeora el pronóstico.

---

## Extensión LATAM

20 países, el mismo protocolo. Ver **[RESULTADOS_LATAM.md](RESULTADOS_LATAM.md)**.

> El hallazgo de Colombia **no se replicó: se invirtió**. Misma economía, mismo período de
> ruptura, dos frecuencias, conclusiones opuestas y ambas significativas. La frontera de
> cobertura sí generaliza, y es peor: en 18 de 20 países exigir las 33 variables deja cero
> años completos. La combinación por régimen funciona donde hay datos para probarla (+17,3 %
> sobre el ingenuo, con un interruptor que reacciona un mes tarde y no anticipa).

```bash
uv run python -m macro_lab.lab_latam
uv run python -m macro_lab.lab_combinacion
```
