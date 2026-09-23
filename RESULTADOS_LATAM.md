# Resultados — extensión LATAM

Corrida del 18-sep-2026. El mismo protocolo de `RESULTADOS.md`, sin tocar nada, sobre
20 países de América Latina.

Un país no distingue un hallazgo de una casualidad. Esta extensión existe para someter a
prueba el resultado de Colombia. **No sobrevivió.**

---

## 1. El hallazgo principal: Colombia se contradice a sí misma

Colombia aparece en dos pistas, con dos fuentes y dos frecuencias, sobre el **mismo
período de ruptura** (2020–2021). El resultado es opuesto, y significativo en ambas
direcciones:

| Fuente | Frecuencia | Modelo | vs ingenuo | p |
|---|---|---|---|---|
| ISE, DANE | mensual, 246 obs | LSTM(16) | **−60,7 %** | 0,019 ✱ *peor* |
| PIB real, FMI | trimestral, 81 obs | LSTM(16) | **+21,8 %** | 0,018 ✱ *mejor* |

Misma economía, mismos años, misma familia de modelo, conclusiones contrarias, ambas
significativas al 5 %.

**Lo que esto establece:** el resultado de un ejercicio de comparación de modelos puede
depender más de la frecuencia y de la fuente elegidas que del modelo. Cualquier ranking
publicado sin declarar esas dos decisiones es una afirmación más débil de lo que aparenta
— incluido el de `RESULTADOS.md`.

Hipótesis para explicarlo, sin contrastar: 246 observaciones mensuales le dan a un LSTM
material para aprender la dinámica de calma que 80 trimestres no dan; pero en la ruptura,
con datos trimestrales, la red se adapta más rápido que un AR(1) anclado a su media. Para
contrastarlo habría que remuestrear el ISE a trimestral y volver a correr. Es el
siguiente experimento, no una conclusión.

---

## 2. La frontera de cobertura generaliza, y es peor

La restricción encontrada en Colombia no era una peculiaridad colombiana:

| | 33 variables | 20 variables | 14 variables |
|---|---|---|---|
| **Mediana LATAM** | **0 años** | 54 años | 66 años |
| Países con menos de 20 años completos | **20 de 20** | — | — |

En **18 de los 20 países, exigir las 33 variables deja cero años completos.** Solo
Colombia (13), Perú (16) y México (3) tienen alguno, y ninguno llega a 20.

Dicho de otro modo: **Colombia y Perú son las economías mejor documentadas de la
región**, y aun así ninguna sostiene el conjunto completo de variables macro que un
ejercicio de este tipo pediría por defecto.

Los paneles finalmente utilizables, recortados hasta n/p ≥ 3, van de 48 años × 16
variables (Venezuela) a 64 × 19 (Chile, Costa Rica, México, Uruguay y otros).

---

## 3. Pista C — PIB trimestral, 8 países

Cobertura: Argentina, Brasil, Chile, Colombia, Costa Rica, Ecuador, Honduras, México.
Los otros doce no tienen serie trimestral con 40 o más trimestres en el IFS; se sondearon
cinco códigos alternativos por país y no hay nada.

### Agregado (MAE mediano relativo al ingenuo)

| Modelo | Calma | Ruptura |
|---|---|---|
| AR(1) | **0,948** | 0,866 |
| ARIMA(1,1,1) | 0,952 | 1,075 |
| *Ingenuo* | *1,000* | *1,000* |
| Random Forest | 1,065 | 0,864 |
| LSTM(16) | 1,083 | **0,811** |

### Quién gana, por país

| Régimen | Box-Jenkins | Redes | Aprendizaje | Regularizado | Combinación |
|---|---|---|---|---|---|
| Calma | **4** | 1 | 1 | 1 | 1 |
| Ruptura | **0** | **5** | 2 | 1 | 0 |

**Simples en calma, flexibles en la ruptura.** Es el patrón inverso al de Colombia
mensual.

**Advertencia de poder:** solo **2 de 16** comparaciones son significativas — Argentina
(+44,6 %, p = 0,023) y Colombia (+21,8 %, p = 0,018), ambas LSTM en ruptura. Con 8
trimestres de ruptura por país no hay poder estadístico. El conteo de familias es
sugerente; las pruebas individuales, casi todas mudas.

---

## 4. Pista D — crecimiento anual, 20 países

### Calma

| Modelo | MAE mediano relativo al ingenuo |
|---|---|
| AR(1) | **0,899** |
| Comb. 50/50 RF-AR(1) | 0,918 |
| ARIMA(1,1,1) | 0,920 |
| LSTM(16) | 0,972 |
| *Ingenuo* | *1,000* |
| Random Forest | 1,031 |

Box-Jenkins gana en 9 de 20 países, las combinaciones en 5, las redes en 3, y el ingenuo
en 3.

**Pero la significancia es la que se esperaría por azar:** 3 de 20 países dan p < 0,05
(Dominicana, Panamá, El Salvador). Probando 20 países al 5 %, uno esperaría un acierto
por azar; tres no es evidencia fuerte, y ninguna corrección por comparaciones múltiples
los deja en pie.

### Ruptura — no contrastable

La tabla por país muestra a las redes y las combinaciones ganando en 13 de 20 países, con
LSTM en 0,403 relativo al ingenuo. **Ese número no se debe reportar como hallazgo.**

La ruptura anual tiene **exactamente 2 orígenes por país** — 2020 y 2021. Ninguna prueba
de Diebold-Mariano es posible (requiere más de 5 pares), y en la tabla todas las columnas
de p salen vacías por esa razón. Dos observaciones no distinguen un modelo de otro.

---

## 5. La combinación por régimen — sí funciona

Sobre el ISE mensual de Colombia, que es la única serie con observaciones suficientes
para contrastarla:

| Modelo | Completo | Calma | Ruptura |
|---|---|---|---|
| **Comb. RF/AR(1) suave** | **1,859 (+17,3 %)** | 1,423 (+21,5 %) | 3,708 (**+9,2 %**) |
| Random Forest solo | 2,103 (+6,4 %) | **1,382 (+23,8 %)** | 5,169 (**−26,6 %**) |
| AR(1) solo | 2,080 (+7,4 %) | 1,697 (+6,5 %) | 3,707 (+9,2 %) |
| LSTM(16) solo | 2,431 (−8,2 %) | 1,460 (+19,5 %) | 6,560 (−60,7 %) |
| *Ingenuo* | *2,246* | *1,814* | *4,082* |

La combinación conserva casi toda la ventaja del Random Forest en calma (+21,5 % contra
+23,8 %) y **elimina su colapso en la ruptura** (+9,2 % contra −26,6 %). Sobre la muestra
completa le gana a sus dos componentes: **+17,3 % frente a +6,4 % y +7,4 %.**

### El interruptor no anticipa: reacciona

El peso que asignó al modelo robusto, mes a mes, calculado **solo con datos anteriores a
cada origen**:

| Origen | Peso robusto | Real en t+1 |
|---|---|---|
| 2020-01 | 0,00 | +3,6 % |
| 2020-02 | **0,00** | **−6,3 %** ← se lo pierde |
| 2020-03 | **1,00** | −20,2 % ← reacciona |
| 2020-04 … 2020-11 | 1,00 | −17,4 … −2,2 % |
| 2020-12 | 0,00 | −3,4 % |

Cuesta **un mes de rezago**: no ve venir la pandemia, la detecta al mes siguiente y se
queda mientras dura. Ese rezago es el precio de no hacer trampa, y está a la vista en
`salidas/combinacion_pesos.csv` para que cualquiera lo audite.

---

## 6. Un error que habría invertido el titular

La primera corrida de la Pista C daba a las combinaciones ganando en los 8 países. Era
falso.

`_indice_futuro` solo contemplaba `DatetimeIndex`; las series trimestrales de LATAM usan
`PeriodIndex`. Todo modelo recursivo — Random Forest, Ridge y las combinaciones que los
invocan — reventaba y devolvía `NaN`. Los `NaN` se descartaban al promediar, de modo que
**el modelo quedaba evaluado solo sobre los orígenes donde sobrevivió**.

México, antes y después:

| | con el error | corregido |
|---|---|---|
| "Ganador" | Comb. RF/ingenuo, MAE 0,750 | Random Forest, MAE 1,582 |
| Observaciones reales | **7 de 77** | 77 de 77 |
| Fallos de Random Forest | 77 de 77 | 0 |

Parecía el mejor por no haber competido.

**Además del arreglo se añadió una regla de protocolo:** `backtest.resumen` calcula ahora
la cobertura de cada modelo y **deja fuera del ordenamiento a cualquiera por debajo del
90 %**, mostrando su cobertura. La regla ya atrapó un segundo caso por su cuenta —
`Comb. LSTM/AR(1) suave` tiene 79 % de cobertura en la calma anual, porque el LSTM no
ajusta con series de entrenamiento cortas, y quedó excluido del agregado.

---

## 7. Qué queda establecido

1. **El resultado de Colombia no se replica; se invierte.** Y en el caso más directo
   —misma economía, mismo período— se invierte con significancia en ambos sentidos.
2. **La frontera de cobertura es una restricción regional, no colombiana.** 18 de 20
   países no tienen un solo año con las 33 variables.
3. **La combinación por régimen funciona donde hay datos para probarla**, con un
   interruptor que solo mira el pasado y cuesta un mes de rezago.
4. **En calma, los modelos simples llevan ventaja en LATAM.** AR(1) es el mejor agregado
   en las dos pistas. Pero la significancia por país es la del azar.
5. **La ruptura anual no es contrastable.** Dos observaciones por país.

## Qué NO queda establecido

- Que las redes sirvan o no sirvan. Depende de la frecuencia, y eso es justo lo que este
  ejercicio no controló.
- Nada sobre la ruptura en datos anuales.
- Ningún ranking por país: con 20 países y pruebas al 5 %, los tres aciertos en calma son
  compatibles con el azar.

## Reproducir

```bash
uv run python -m macro_lab.lab_latam        # pistas C y D
uv run python -m macro_lab.lab_combinacion  # combinación por régimen
```
