# Cambios

## 1.1.0 · 23-sep-2026

### Añadido

- **Experimento de frecuencia (D-007).** `lab_frecuencia` remuestrea el ISE a trimestral
  y separa frecuencia, ajuste y fuente en la ruptura de Colombia, con predicciones
  registradas antes de correr. Resultado: manda la frecuencia, por la vía de la
  referencia. El ingenuo pasa de 4,0 pp de error a un mes vista a 7,7 pp a un trimestre
  vista, mientras el LSTM se queda en torno a 6 pp.
- `datos.a_trimestral` y `serie_ise(cuadro=...)`.

## 1.0.0 · 23-sep-2026

Primer release público. Sale de una auditoría del protocolo que encontró errores capaces
de cambiar conclusiones publicadas; cada uno tiene su entrada en `docs/BITACORA.md`
(B-002 a B-009, D-003 a D-006). Todas las salidas y los dos documentos de resultados se
regeneraron con el código corregido.

### Corregido

- **Régimen por período pronosticado (B-002).** Las particiones calma/ruptura usaban el
  año del origen. En datos anuales la caída de 2020 caía en la "calma". Ahora el detalle
  lleva la columna `objetivo` y toda partición usa `backtest.regimen`.
- **Años no contiguos (B-004).** Los paneles anuales se recortan al tramo consecutivo más
  largo; la frontera de cobertura cuenta años contiguos (`n_contiguos`).
- **Pista D con la serie completa (B-005).** El objetivo univariado ya no se recorta al
  panel multivariable.
- **La combinación ya no rellena fallos (B-006).** Si el modelo flexible falla, la
  combinación queda como faltante y cuenta en la cobertura.
- **SARIMAX con macro rezagado (B-007).** Mismo modelo al ajustar y al pronosticar.
- **Dummies COVID con `PeriodIndex` (B-008).**
- **La "Comb. 50/50 RF-AR(1)" no era 50/50 (B-009).** Era AR(1) puro en el 98 % de los
  orígenes. Se renombra `Comb. RF/AR(1) umbral min`.
- **Conteo de la frontera LATAM.** Son 17 de 20 países sin años completos con las 33
  variables, no 18. `frontera_latam.csv` ahora lo genera `lab_latam.frontera_latam`.

### Declarado

- **Serie trimestral ajustada estacionalmente (B-003).** El IFS no publica la versión
  sin ajuste para los 8 países de la Pista C. Se usa la ajustada, se declara en el
  módulo, en la corrida y en los resultados.
- **Las exógenas anuales son datos revisados (D-006).** La esperanza de vida de 2020–2021
  anticipa el rebote en el SARIMAX con macro; es vintage, no fuga del código.

### Resultados que cambian

- El AR(1) mensual deja de ser significativo sobre la muestra completa (p Holm 0,504).
- La "inversión significativa" de Colombia entre frecuencias no sobrevive a Holm.
- La combinación por régimen pasa a ser hipótesis en el ISE y no se replica en LATAM.
- Se mantiene y se fortalece: el AR(1) le gana al ingenuo en calma en toda la región.

### Añadido

- `dm_p_holm`: p de Diebold-Mariano ajustada por Holm; el asterisco la usa (D-005).
- `p` por tramo en la combinación y Wilcoxon entre países en los agregados LATAM (D-003).
- Pruebas del protocolo (`tests/`), lint con ruff, CI en GitHub Actions.
- torch solo CPU en Linux para que CI no baje CUDA.
- `CITATION.cff`, este archivo, regla R-12 en `CLAUDE.md`.

## 0.1.0 · 18-sep-2026

Laboratorio inicial: pistas A y B (Colombia), C y D (LATAM), combinación por régimen.
