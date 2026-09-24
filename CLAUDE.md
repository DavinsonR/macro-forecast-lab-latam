# CLAUDE.md · macro-forecast-lab-latam

Laboratorio de pronóstico del crecimiento económico agregado: Colombia y 20 países de
América Latina. Compara AR, MA, ARMA, ARIMA, SARIMAX, VAR, regularizados, árboles, MLP,
LSTM y CNN bajo un único protocolo de origen móvil.

No es un proyecto de producción. Es un experimento cuyo producto son **tablas de error
con su significancia**, no un pronóstico publicado.

## Reglas duras

- **R-01** Documentación y mensajes de commit en español, sin emojis. Identificadores,
  columnas y módulos en inglés o en español sin acentos (la consola de Windows es cp1252).
- **R-02** Solo `uv` (`uv sync`, `uv run`, `uv add`). Nunca `pip install`.
- **R-03** Ninguna frecuencia se rellena. Si una variable es anual, se queda anual.
  Repetir un valor anual en cuatro trimestres o doce meses fabrica variación que no
  existe; es el error que la tesis de origen cometió con el PIB departamental.
- **R-04** Ningún modelo ve un dato posterior a su origen de pronóstico. Los escaladores
  se ajustan solo con el tramo de entrenamiento; las redes paran temprano contra una
  validación recortada del propio entrenamiento.
- **R-05** No se usan series ajustadas estacionalmente cuando existe la alternativa sin
  ajustar: el ajuste se reestima con la serie completa y mete futuro en el backtest.
  Cuando no hay alternativa (PIB trimestral del FMI), se declara en el módulo.
- **R-06** Ningún ranking se publica sin la prueba de Diebold-Mariano contra la
  referencia. Una diferencia de MAE sin `p` no distingue mejora de ruido.
- **R-07** Un modelo con cobertura menor al 90 % queda fuera del ordenamiento. Un fallo
  no puede disfrazarse de victoria por haber competido solo en los orígenes fáciles.
- **R-08** Antes de elegir un método se mide su supuesto. La frontera de cobertura
  (cuántos años sobreviven al exigir k variables) se calcula **antes** de modelar.
- **R-09** No se seleccionan hiperparámetros mirando el error de prueba, ni se promedian
  modelos elegidos por su desempeño en la muestra donde se miden.
- **R-10** Todo hallazgo que dependa de un subperíodo elegido después de ver los datos se
  reporta como hipótesis, no como conclusión.
- **R-11** Antes de arreglar un error, entrada en `docs/BITACORA.md` con id, causa raíz y
  la regla que lo habría evitado. Después, el arreglo.
- **R-12** Todo corte por subperíodo usa el período **pronosticado** (`objetivo`), vía
  `backtest.regimen`. El origen es el último dato visto, no el error que se mide.

## Comandos

```bash
uv sync                                   # entorno (incluye torch)
uv run python -m macro_lab.main           # pistas A (anual COL) y B (ISE mensual)
uv run python -m macro_lab.robustez       # partición por subperíodo
uv run python -m macro_lab.lab_latam      # pistas C (trimestral) y D (anual, 20 países)
uv run python -m macro_lab.lab_combinacion  # combinación por régimen
uv run python -m macro_lab.lab_frecuencia   # frecuencia, ajuste o fuente (D-007)
uv run python -m macro_lab.exportar_web     # contrato web: web/forecast-lab/*.json
```

```bash
uv run python -m pytest -q                # invariantes del protocolo, sin red, segundos
uv run ruff check                         # lint (no se impone ruff format)
```

Las pruebas (`tests/`) protegen el protocolo, no la calidad del pronóstico: nada ve el
futuro, la cobertura filtra, el régimen se asigna por el período pronosticado, no hay
años saltados. La puerta de calidad de los resultados sigue siendo la columna de
cobertura y la de `p` (cruda y ajustada por Holm). CI corre ambas en cada PR.

## Dónde está qué

- `macro_lab/datos.py` — Banco Mundial (33 indicadores) y parser del anexo ISE del DANE
- `macro_lab/latam.py` — 20 países: anual del Banco Mundial, trimestral del FMI vía DBnomics
- `macro_lab/modelos.py` — el zoológico, todos tras la misma interfaz `predecir(y, h, X)`
- `macro_lab/backtest.py` — origen móvil, resumen con cobertura, Diebold-Mariano y Holm,
  `regimen()` por período pronosticado
- `macro_lab/combinacion.py` — pesos por régimen; el interruptor solo mira el pasado
- `macro_lab/robustez.py`, `lab_latam.py`, `lab_combinacion.py`, `lab_frecuencia.py` — corridas
- `tests/` — pruebas del protocolo con datos sintéticos
- `macro_lab/exportar_web.py` y `web/forecast-lab/` — el contrato con davirson.com/labs/macro-forecast;
  se copia tal cual a `public/forecast-lab/` del sitio. Tras re-correr, re-exportar y re-copiar
- `salidas/` — resultados versionados: resúmenes, agregados y detalle por origen

## Resultados y su fragilidad

`RESULTADOS.md` (Colombia) y `RESULTADOS_LATAM.md` (región). Desde 1.0.0 casi nada
sobrevive a Holm; lo robusto es que **en calma el AR(1) le gana al ingenuo en toda la
región**. La aparente inversión de Colombia entre frecuencias la produce la referencia:
el ingenuo es mucho más difícil de batir a un mes vista que a un trimestre (D-007).
Cualquier cambio que toque
los modelos o el protocolo debe volver a correr ambos y actualizar los dos documentos.

## Fuentes y licencias

Banco Mundial CC BY 4.0 · DANE uso público con atribución · FMI IFS vía DBnomics.
