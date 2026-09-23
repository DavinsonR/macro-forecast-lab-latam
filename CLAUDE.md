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

## Comandos

```bash
uv sync                                   # entorno (incluye torch)
uv run python -m macro_lab.main           # pistas A (anual COL) y B (ISE mensual)
uv run python -m macro_lab.robustez       # partición por subperíodo
uv run python -m macro_lab.lab_latam      # pistas C (trimestral) y D (anual, 20 países)
uv run python -m macro_lab.lab_combinacion  # combinación por régimen
```

No hay suite de pruebas. La puerta de calidad es la columna de cobertura y la de `p`.

## Dónde está qué

- `macro_lab/datos.py` — Banco Mundial (33 indicadores) y parser del anexo ISE del DANE
- `macro_lab/latam.py` — 20 países: anual del Banco Mundial, trimestral del FMI vía DBnomics
- `macro_lab/modelos.py` — el zoológico, todos tras la misma interfaz `predecir(y, h, X)`
- `macro_lab/backtest.py` — origen móvil, resumen con cobertura y Diebold-Mariano
- `macro_lab/combinacion.py` — pesos por régimen; el interruptor solo mira el pasado
- `macro_lab/robustez.py`, `lab_latam.py`, `lab_combinacion.py` — corridas
- `salidas/` — resultados versionados: resúmenes, agregados y detalle por origen

## Resultados y su fragilidad

`RESULTADOS.md` (Colombia) y `RESULTADOS_LATAM.md` (región). El hallazgo central del
segundo es que el del primero **no se replica: se invierte**. Cualquier cambio que toque
los modelos o el protocolo debe volver a correr ambos y actualizar los dos documentos.

## Fuentes y licencias

Banco Mundial CC BY 4.0 · DANE uso público con atribución · FMI IFS vía DBnomics.
