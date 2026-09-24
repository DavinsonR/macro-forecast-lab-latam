# Resultados: extensión LATAM

Corrida del 23-sep-2026, versión 1.0.0. El mismo protocolo de `RESULTADOS.md` sobre 20
países de América Latina.

Un país no distingue un hallazgo de una casualidad. Esta extensión existe para someter a
prueba el resultado de Colombia.

> **Qué cambió respecto de la versión 0.1.0 (18-sep-2026).** La versión anterior decía
> que el hallazgo de Colombia "se invierte, con significancia en ambos sentidos", y que
> la combinación por régimen "sí funciona". **Ninguna de las dos afirmaciones sobrevive
> a la auditoría** (`docs/BITACORA.md`, B-002 a B-009 y D-003 a D-006):
>
> - La ruptura se asignaba por el año del origen. En la pista anual, la "ruptura" eran
>   los objetivos 2021 y 2022, no la caída de 2020.
> - Las p no se corregían por comparaciones múltiples. Con Holm, ninguno de los dos lados
>   de la "inversión" de Colombia es significativo.
> - **Las 8 series trimestrales son ajustadas estacionalmente.** El IFS no publica la
>   versión sin ajustar para estos países. En 0.1.0 no se declaró; ahora sí (R-05).
> - La combinación se diseñó mirando el ISE. Fuera de él, en 28 series, no le gana al
>   AR(1) solo.
> - "Comb. 50/50 RF-AR(1)" no era una mezcla 50/50: en el 98 % de los orígenes es AR(1)
>   puro. Ahora se llama `Comb. RF/AR(1) umbral min`.

Cómo leer las tablas agregadas: **mediana** del MAE relativo al ingenuo entre países
(1,00 = igual al ingenuo, menor es mejor); **p Wilc**, Wilcoxon de rangos con signo entre
países sobre log(MAE relativo); **sig/n**, cuántos países dan una mejora con
Diebold-Mariano p < 0,05 sin ajustar, sobre cuántos se evaluaron.

---

## 1. Colombia en dos frecuencias: dirección opuesta, sin significancia

Colombia aparece en dos pistas, con dos fuentes y dos frecuencias, sobre el mismo
período de ruptura (objetivos en 2020–2021):

| Fuente | Frecuencia | Modelo | vs ingenuo en la ruptura | p | p Holm |
|---|---|---|---|---|---|
| ISE, DANE (sin ajuste) | mensual, 24 objetivos | LSTM(16) | −62,2 % | 0,019 | 0,241 |
| PIB real, FMI (ajustado) | trimestral, 8 objetivos | LSTM(16) | +21,0 % | 0,027 | 0,327 |

La dirección es opuesta. **Ninguna de las dos sobrevive a Holm.** Lo que queda es más
modesto que lo publicado en 0.1.0: la misma familia de modelos, en la misma economía y el
mismo período, apunta en sentidos contrarios según la fuente y la frecuencia, y con esta
cantidad de datos ninguna de las dos direcciones se puede afirmar.

### Qué lo produce: el ISE remuestreado a trimestral

Las dos series difieren en frecuencia, fuente y ajuste a la vez. El experimento de
`macro_lab/lab_frecuencia.py` las separa con tres brazos trimestrales sobre la misma
muestra (2006T1–2025T1, 37 orígenes) y el catálogo de la Pista C. Las predicciones se
registraron antes de correr (D-007 en la bitácora).

| Brazo | Frecuencia | Ajuste | LSTM vs ingenuo en la ruptura | p | p Holm |
|---|---|---|---|---|---|
| ISE (Pista B) | mensual | sin ajuste | −62,2 % | 0,019 | 0,24 |
| A · ISE | trimestral | sin ajuste | +21,8 % | 0,049 | 0,59 |
| B · ISE | trimestral | ajustado | +17,6 % | 0,094 | 1,00 |
| C · PIB FMI | trimestral | ajustado | +21,0 % | 0,027 | 0,33 |

**Manda la frecuencia.** Con la misma serie sin ajustar, pasar de mensual a trimestral
invierte el signo; ni el ajuste (A contra B) ni la fuente (B contra C) lo mueven. El
brazo C reproduce la cifra de la Pista C, lo que valida el montaje.

**El mecanismo es la referencia, no la red.** El LSTM se equivoca parecido en las dos
frecuencias (MAE de 6,5 pp mensual y 6,0 pp trimestral). El ingenuo, en cambio, pasa de
4,0 pp a un mes vista a 7,7 pp a un trimestre vista: en plena caída, "igual que el mes
pasado" es muy difícil de batir, y "igual que el trimestre pasado" no. La hipótesis de
0.1.0, que la red "se adapta más rápido" con datos trimestrales, queda descartada.

Todo esto es dirección, no significancia: ocho trimestres de ruptura por brazo y un
período elegido después de ver los datos (R-10). La lección que sí generaliza es de
método: **una ganancia sobre el ingenuo depende de qué tan lejos queda el paso
siguiente**, y comparar rankings entre frecuencias sin decirlo compara referencias
distintas.

---

## 2. La frontera de cobertura generaliza

La restricción encontrada en Colombia no es una peculiaridad colombiana
(`salidas/frontera_latam.csv`):

| | 33 variables | 20 variables | 14 variables |
|---|---|---|---|
| Mediana LATAM (años completos) | **0** | 54,5 | 65,5 |

**En 17 de los 20 países, exigir las 33 variables deja cero años completos.** Solo
Perú (16), Colombia (13) y México (3) tienen alguno, y ninguno llega a 20. (La versión
0.1.0 decía "18 de 20", pero listaba estos mismos tres países; el conteo correcto es 17).

Los paneles utilizables, contiguos y recortados hasta n/p ≥ 3, van de 48 años × 16
variables (Venezuela) a 64 años × 19 variables (Ecuador, Guatemala, México, Uruguay y otros).

---

## 3. Pista C: PIB trimestral, 8 países

Cobertura: Argentina, Brasil, Chile, Colombia, Costa Rica, Ecuador, Honduras y México.
Los otros doce no tienen serie trimestral con 40 o más trimestres en el IFS.

**Serie ajustada estacionalmente (B-003).** En los 8 países el IFS solo publica la
versión ajustada. El ajuste se reestima con la serie completa, así que ya vio el futuro
de cada origen. Eso favorece por igual a todos los modelos y puede hacer que los errores
se vean algo más bajos de lo que serían en tiempo real.

### Agregado

| Modelo | Calma | p Wilc | sig/n | Ruptura | p Wilc | sig/n |
|---|---|---|---|---|---|---|
| **AR(1)** | **0,933** | **0,008** | 2/8 | 0,894 | 0,008 | 0/8 |
| ARIMA(1,1,1) | 0,940 | 0,055 | 0/8 | 1,067 | 0,016 | 0/8 |
| Comb. RF/AR(1) umbral min | 0,945 | 0,148 | 1/8 | 0,897 | 0,008 | 0/8 |
| *Ingenuo* | *1,000* | — | — | *1,000* | — | — |
| Random Forest | 1,022 | 0,547 | 0/8 | 0,919 | 0,148 | 0/8 |
| LSTM(16) | 1,040 | 0,250 | 0/8 | **0,818** | 0,039 | 2/8 |
| Comb. RF/AR(1) suave | 1,099 | 0,383 | 0/8 | 0,899 | 0,008 | 0/8 |
| Ridge sobre rezagos | 1,253 | 0,023 | 0/8 | 0,864 | 0,109 | 0/8 |

**El AR(1) le gana al ingenuo en los 8 países, en calma y en ruptura.** Con 8 países,
p = 0,008 es el valor mínimo posible: los ocho van en la misma dirección. Es el resultado
más sólido de la pista.

Mejor modelo por país: en calma, Box-Jenkins gana en 4 de 8; en ruptura, las redes ganan
en 5 de 8. Pero **ninguna victoria individual sobrevive a Holm**. Las dos con p cruda
menor a 0,05 son las del LSTM en la ruptura de Argentina (+43,4 %, p Holm 0,189) y de
Colombia (+21,0 %, p Holm 0,327). Con 8 trimestres de ruptura por país no hay poder.

---

## 4. Pista D: crecimiento anual, 20 países

El objetivo es la serie completa y contigua de crecimiento de cada país (B-005): 35
orígenes en la mayoría de los países, 30 en El Salvador y 24 en Cuba.

### Calma

| Modelo | Mediana | p Wilc | sig/n |
|---|---|---|---|
| **AR(1)** | **0,862** | **0,001** | 4/20 |
| Comb. RF/AR(1) umbral min | 0,890 | 0,002 | 3/20 |
| ARIMA(1,1,1) | 0,891 | 0,004 | 3/20 |
| LSTM(16) | 0,919 | 0,114 | 2/20 |
| Random Forest | 0,940 | 0,956 | 0/20 |
| Comb. RF/AR(1) suave | 0,994 | 0,869 | 1/20 |
| *Ingenuo* | *1,000* | — | — |

**Entre países el AR(1) le gana al ingenuo con claridad** (mediana 0,862, p = 0,001), y
las dos variantes que en el fondo son AR(1) lo siguen. Los flexibles no se distinguen.

País por país, el mejor modelo tiene p cruda < 0,05 en 5 de 20 (Dominicana, Ecuador,
Guatemala, Panamá y Perú). Por azar se esperaría uno. **Tras Holm no queda ninguno**: la
menor p ajustada es 0,098 (Ecuador). La evidencia está en el agregado, no en los países.

`Comb. LSTM/AR(1) suave` queda fuera en calma: su cobertura es del 82 %, porque el LSTM no
ajusta con tramos de entrenamiento cortos (R-07).

### Ruptura: el ingenuo pierde por construcción

Ahora la ruptura anual sí contiene la caída de 2020 y el rebote de 2021: 2 objetivos por
país. No hay Diebold-Mariano posible con dos pares. Entre países, todos los modelos salvo la deriva le
ganan al ingenuo (medianas de 0,71 a 0,85, Wilcoxon p ≤ 0,044).

**Eso no mide habilidad.** El ingenuo pronostica para 2021 la caída de 2020 y se come el
rebote entero. Cualquier modelo que vuelva hacia la media le gana en ese año. Con dos
observaciones por país, lo único que muestra esta tabla es que el ingenuo es la peor
referencia posible justo después de un choque.

---

## 5. La combinación por régimen: hipótesis en el ISE, no se replica fuera

### En el ISE, donde se diseñó

| Modelo | Completo | Calma | Ruptura |
|---|---|---|---|
| **Comb. RF/AR(1) suave** | **1,859 (+17,3 %, p Holm 0,006)** | 1,428 (+22,1 %, 0,005) | 3,687 (+7,9 %, 1,000) |
| Random Forest solo | 2,103 (+6,4 %, 0,786) | **1,393 (+24,0 %, 0,004)** | 5,120 (−27,9 %, 0,726) |
| AR(1) solo | 2,080 (+7,4 %, 0,146) | 1,707 (+6,9 %, 0,075) | 3,664 (+8,5 %, 1,000) |
| LSTM(16) solo | 2,431 (−8,2 %, 0,786) | 1,476 (+19,5 %, 0,020) | 6,491 (−62,2 %, 0,148) |
| *Ingenuo* | *2,246* | *1,833* | *4,002* |

Sobre la muestra completa la combinación le gana al ingenuo con p Holm 0,006, y a sus dos
componentes por separado. **Pero es hipótesis (R-09, R-10, D-004):** el Random Forest y el
AR(1) se eligieron como piezas después de ver la tabla de robustez de esta misma serie. Y
en la ruptura su ventaja (+7,9 %) no es significativa.

### Fuera del ISE, donde entra sin retocar

En las 28 series de LATAM (8 trimestrales y 20 anuales), la combinación no mejora al AR(1)
solo:

| | Calma C | Ruptura C | Calma D | Ruptura D |
|---|---|---|---|---|
| AR(1) | **0,933** | 0,894 | **0,862** | 0,829 |
| Comb. RF/AR(1) suave | 1,099 | 0,899 | 0,994 | 0,830 |

En calma, donde el interruptor casi siempre va al Random Forest, la combinación hereda
la debilidad del Random Forest fuera de Colombia. **El resultado del ISE no se replica.**

### El interruptor reacciona, no anticipa

El peso asignado al modelo robusto, calculado solo con datos anteriores a cada origen
(`salidas/combinacion_pesos.csv`):

| Origen | Peso robusto | Real en t+1 |
|---|---|---|
| 2020-01 | 0,00 | +3,6 % |
| 2020-02 | **0,00** | **−6,3 %** ← se lo pierde |
| 2020-03 | **1,00** | −20,2 % ← reacciona |
| 2020-04 | 1,00 | −17,4 % |

Cuesta un mes de rezago: no ve venir la pandemia y la detecta al mes siguiente.

---

## 6. Un error que habría invertido el titular (B-001)

La primera corrida de la Pista C daba a las combinaciones ganando en los 8 países. Era
falso. `_indice_futuro` no atendía `PeriodIndex`, los modelos recursivos devolvían `NaN`
y el resumen los evaluaba solo sobre los orígenes donde sobrevivían. En México, el
"ganador" tenía MAE 0,750 calculado sobre 7 de 77 orígenes. Desde entonces
`backtest.resumen` deja fuera del ordenamiento a cualquier modelo con cobertura menor al
90 % (R-07).

---

## 7. Qué queda establecido

1. **En calma, el AR(1) le gana al ingenuo en toda la región.** En 8 de 8 países
   trimestrales (Wilcoxon p = 0,008) y en la mediana de 20 anuales (0,862, p = 0,001).
   Es el hallazgo más robusto del laboratorio.
2. **Ningún ranking por país sobrevive a la corrección por comparaciones múltiples**, en
   ninguna pista.
3. **La frontera de cobertura es regional.** En 17 de 20 países no hay un solo año con
   las 33 variables.
4. **La combinación por régimen no se replica fuera de la serie donde se diseñó.**

## Qué NO queda establecido

- Que el resultado de Colombia "se invierta" por algo del modelo. Las dos direcciones son
  opuestas, ninguna es significativa tras Holm, y el experimento de frecuencia muestra
  que lo que cambia es la dificultad de la referencia.
- Que las redes sirvan o no sirvan en la ruptura trimestral: 5 de 8 victorias, 0
  significativas.
- Nada sobre la habilidad de los modelos en la ruptura anual: dos observaciones por país
  y un ingenuo que pierde por construcción.

## Reproducir

```bash
uv run python -m macro_lab.lab_latam        # pistas C y D, frontera LATAM
uv run python -m macro_lab.lab_combinacion  # combinación por régimen
uv run python -m macro_lab.lab_frecuencia   # ISE remuestreado a trimestral (D-007)
```

Salidas: `pista_{c,d}_detalle.csv`, `pista_{c,d}_por_pais.csv`,
`pista_{c,d}_relativo_pais.csv`, `pista_{c,d}_agregado.csv`, `frontera_latam.csv`,
`combinacion_*.csv`, `frecuencia_*.csv`.
