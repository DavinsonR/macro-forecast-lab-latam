# Resultados del laboratorio

> **Aviso posterior.** La extensión a 20 países ([RESULTADOS_LATAM.md](RESULTADOS_LATAM.md))
> sometió a prueba el hallazgo de abajo y **no se replicó: se invirtió**. Sobre el PIB
> trimestral colombiano del FMI, en el mismo período de ruptura, el LSTM le gana al ingenuo
> por +21,8 % (p = 0,018) — lo contrario de lo que esta página reporta con el ISE mensual
> (−60,7 %, p = 0,019). Las dos son significativas. Lo de abajo sigue siendo correcto para
> la serie y la frecuencia que usa; no es general.

Corrida del 18-sep-2026. 26 modelos en la pista anual, 19 en la mensual, todos bajo
origen móvil con ventana expansiva y reajuste completo en cada origen.

---

## El hallazgo principal

**Reportar solo el ranking de muestra completa habría sido engañoso, y el laboratorio
existe para demostrarlo.**

En la serie mensual, sobre la muestra completa, el ganador es AR(1) — un modelo de un
parámetro — y le gana al ingenuo por 7,4 %. Parecería la historia clásica de "lo simple
gana".

Al partir la ventana de prueba en subperíodos, la historia se invierte:

| Modelo | Muestra completa | Sin COVID | Solo COVID | Post-2022 |
|---|---|---|---|---|
| | MAE (puesto) | MAE (puesto) | MAE (puesto) | MAE (puesto) |
| Random Forest | 2,103 (3) | **1,382 (1)** | 5,169 (10) | **1,744 (1)** |
| LSTM(16) v12 | 2,431 (14) | **1,460 (2)** | 6,560 (17) | 1,910 (2) |
| LSTM(32) v24 | 2,262 (12) | **1,501 (3)** | 5,499 (13) | 1,920 (3) |
| AR(1) | **2,080 (2)** | 1,697 (11) | **3,707 (1)** | 2,137 (9) |
| Ingenuo | 2,246 (8) | 1,814 (14) | 4,082 (2) | 2,292 (12) |

**Los modelos flexibles son claramente mejores en tiempos normales y catastróficamente
peores durante la ruptura estructural.** El promedio de muestra completa esconde las dos
cosas: el COVID es el 19 % de los orígenes de prueba y una fracción mucho mayor del
error total, así que arrastra el promedio y castiga justo a los modelos que mejor
funcionan el resto del tiempo.

Esto no es un detalle de presentación. Es la diferencia entre concluir "las redes no
sirven para el PIB colombiano" y concluir "las redes sirven bien salvo cuando más
falta hacen".

---

## Pista B — ISE mensual, 246 observaciones, 126 orígenes

### Muestra completa

Un solo modelo le gana al ingenuo de forma significativa:

| # | Modelo | MAE | vs ingenuo | p |
|---|---|---|---|---|
| 1 | ARMA(2,2) | 2,073 | +7,7 % | 0,083 |
| 2 | **AR(1)** | **2,080** | **+7,4 %** | **0,039** ✱ |
| 3 | Random Forest | 2,103 | +6,4 % | 0,393 |
| 8 | *Ingenuo* | *2,246* | *ref* | — |
| 12 | LSTM(32) v24 | 2,262 | −0,7 % | 0,937 |
| 15 | CNN 1D v12 | 2,525 | −12,4 % | 0,258 |
| 17 | CNN 1D v24 | 2,808 | −25,0 % | 0,019 ✱ peor |
| 18 | MLP | 3,841 | −71,0 % | 0,001 ✱ peor |
| 19 | Ingenuo estacional | 5,449 | −142,6 % | 0,000 ✱ peor |

El ingenuo estacional es el peor de todos por construcción, no por mala suerte: el
objetivo ya es una variación interanual, así que la estacionalidad ya está removida y
repetirla la vuelve a inyectar. Vale la pena dejarlo en la tabla como control negativo.

### Sin COVID (102 orígenes, excluye 2020–2021)

Ocho modelos le ganan al ingenuo de forma significativa, y el ingenuo cae al puesto 14:

| # | Modelo | MAE | vs ingenuo | p |
|---|---|---|---|---|
| 1 | Random Forest | 1,382 | **+23,8 %** | 0,001 ✱ |
| 2 | LSTM(16) v12 | 1,460 | **+19,5 %** | 0,006 ✱ |
| 3 | LSTM(32) v24 | 1,501 | **+17,3 %** | 0,026 ✱ |
| 4 | ARMA(2,2) | 1,544 | +14,9 % | 0,001 ✱ |
| 5 | Ridge sobre rezagos | 1,555 | +14,3 % | 0,039 ✱ |
| 6 | AR(12) | 1,562 | +13,9 % | 0,044 ✱ |
| 7 | ARIMA(1,1,1) | 1,581 | +12,8 % | 0,001 ✱ |
| 8 | ARIMA(2,1,2) | 1,581 | +12,8 % | 0,002 ✱ |
| 14 | *Ingenuo* | *1,814* | *ref* | — |

**En tiempos normales el LSTM sí funciona**, y la mejora es significativa al 1 %. Es lo
contrario de lo que sugería la muestra completa.

---

## Pista A — crecimiento anual del PIB, 62 observaciones, 32 orígenes

### Muestra completa

| # | Modelo | MAE | vs ingenuo | p |
|---|---|---|---|---|
| 1 | AR(1)+COVID | 2,257 | +19,0 % | 0,169 |
| 2 | ARMA(1,1)+COVID | 2,275 | +18,4 % | 0,181 |
| 3 | LSTM | 2,315 | +17,0 % | 0,248 |
| 5 | Media histórica | 2,381 | +14,6 % | 0,399 |
| 13 | SARIMAX(1,0,0)+macro | 2,592 | +7,0 % | 0,208 |
| 20 | *Ingenuo* | *2,788* | *ref* | — |
| 22 | Factores PCA + AR | 2,821 | −1,2 % | 0,919 |
| 25 | VAR(2) | 3,477 | −24,7 % | 0,098 |
| 26 | MLP | 5,120 | −83,6 % | 0,021 ✱ peor |

**Ningún modelo le gana al ingenuo de forma significativa. Ni uno.** Los únicos
resultados significativos son negativos. Y al excluir el COVID tampoco aparece nada: el
mejor es MA(1) con +10,3 % y p = 0,428.

### Las 20 variables macro no aportan nada

Es el resultado que más contradice la intuición y el que más conviene mirar:

| Enfoque | MAE | Puesto de 26 |
|---|---|---|
| AR(1)+COVID — solo la propia serie | 2,257 | 1 |
| Media histórica — ni siquiera eso | 2,381 | 5 |
| SARIMAX + 20 variables macro | 2,592 | 13 |
| Factores PCA + AR sobre las 20 | 2,821 | 22 |
| VAR(2) con las 4 más correlacionadas | 3,477 | 25 |

Desempleo, inflación, tipo de cambio, crédito, exportaciones, IED, remesas, deuda,
población, urbanización: **ninguna combinación de las 20 mejora sobre usar únicamente la
historia del propio PIB.** Con 62 observaciones anuales no hay grados de libertad para
estimar lo que aportan, y el costo en varianza supera cualquier ganancia en sesgo.

Esto no dice que la macro no importe para el crecimiento. Dice que **no ayuda a
pronosticarlo con esta cantidad de datos**, que es una afirmación distinta y más
modesta.

---

## Lo que el laboratorio establece

1. **Con 62 observaciones anuales no se distingue ningún modelo del ingenuo.** La pista
   A no tiene poder estadístico. Cualquier ranking que se publique de ella es ruido.
2. **Con 246 observaciones mensuales sí se distingue, y bastante.** Fuera del COVID, el
   Random Forest y el LSTM ganan por 17–24 % con p < 0,03.
3. **La ventaja de los modelos flexibles desaparece exactamente en la ruptura.** En
   2020–2021 el AR(1) y el ingenuo quedan primero y segundo, y los LSTM caen al fondo.
4. **Añadir variables macro empeora el pronóstico anual.** Todas las especificaciones
   con exógenas quedan por debajo de la univariada.
5. **Pedir las 33 variables a la vez deja 13 años.** El costo de cada variable en
   historia perdida hay que calcularlo antes de modelar, no después.

## Lo que NO establece

- No dice qué modelo usar para 2027. Para eso hace falta decidir primero si se espera
  un período normal o una ruptura, que es justamente lo que no se sabe de antemano.
- No prueba que las redes sean superiores: su ventaja vive en un subperíodo elegido
  después de ver los datos. Es una hipótesis para probar fuera de muestra, no una
  conclusión.
- No cubre horizontes mayores a un paso. Todo lo anterior es h=1.

## Próximo paso natural

Una combinación con pesos que cambian según el régimen — flexible en calma, encogida
hacia el ingenuo cuando la volatilidad reciente se dispara — es la lectura directa de la
tabla del hallazgo principal. Pero el interruptor de régimen tiene que estimarse solo
con información disponible en cada origen, o se vuelve el mismo mirar-adelante que este
protocolo existe para evitar.

---

## Reproducir

```bash
uv sync
uv run python -m macro_lab.main      # las dos pistas
uv run python -m macro_lab.robustez  # la partición por subperíodo
```

Salidas en `salidas/`: resúmenes, detalle por origen y tablas de robustez.
