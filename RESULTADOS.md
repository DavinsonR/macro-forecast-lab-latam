# Resultados del laboratorio: Colombia

Corrida del 23-sep-2026, versión 1.0.0. 26 modelos en la pista anual y 19 en la mensual,
todos con origen móvil, ventana expansiva y reajuste completo en cada origen. Horizonte
de un paso.

> **Qué cambió respecto de la versión 0.1.0 (18-sep-2026).** Una auditoría encontró
> errores que movían las conclusiones; están en `docs/BITACORA.md` (B-002 a B-008,
> D-003 a D-006). Los tres que más pesan aquí:
>
> - **Los regímenes se asignaban por el año del origen, no del período pronosticado.** En
>   la pista anual, la caída de 2020 contaba como "calma". Corregido.
> - **Las p ahora se ajustan por comparaciones múltiples (Holm).** Con 19 a 26 modelos
>   contra el ingenuo, una p cruda de 0,04 no dice nada. El AR(1) mensual, que en 0.1.0
>   era "el único que le gana al ingenuo de forma significativa" (p = 0,039), queda en
>   p ajustada 0,504.
> - **El panel anual tenía años saltados**: se pasaba de 1985 a 1987 como si fuera un
>   año. Ahora se usa el tramo contiguo 1961–2024, con 15 regresores en vez de 17.
>
> En las tablas, **p** es Diebold-Mariano pareado contra el ingenuo y **p Holm** es la
> ajustada. ✱ marca una mejora significativa al 5 % tras Holm.

---

## El hallazgo principal

**Sobre la muestra completa ningún modelo le gana al ingenuo de forma significativa, ni
en la serie anual ni en la mensual. La diferencia aparece al separar la calma de la
ruptura, y entonces va en sentidos opuestos.**

ISE mensual, error por período pronosticado:

| Modelo | Muestra completa | Calma (sin 2020–2021) | Ruptura (2020–2021) | Post-2022 |
|---|---|---|---|---|
| | MAE (puesto) | MAE (puesto) | MAE (puesto) | MAE (puesto) |
| Random Forest | 2,103 (3) | **1,393 (1)** | 5,120 (12) | **1,745 (1)** |
| LSTM(16) v12 | 2,431 (14) | **1,476 (2)** | 6,491 (17) | 1,915 (2) |
| LSTM(32) v24 | 2,262 (12) | 1,527 (3) | 5,389 (13) | 1,944 (3) |
| AR(1) | 2,080 (2) | 1,707 (11) | **3,664 (1)** | 2,118 (7) |
| Ingenuo | 2,246 (8) | 1,833 (14) | 4,002 (2) | 2,292 (12) |

Los modelos flexibles ganan en calma y pierden en la ruptura. El promedio de la muestra
completa esconde las dos cosas: la ruptura es el 19 % de los orígenes y una parte mucho
mayor del error total.

**Estatus: hipótesis (R-10).** La partición 2020–2021 se eligió después de ver los datos.
En calma la ventaja del Random Forest sí sobrevive a Holm (p ajustada 0,008). El colapso
de los flexibles en la ruptura es grande pero **ninguno es significativo tras Holm**: con
24 meses de ruptura no hay poder para afirmarlo.

---

## Pista B: ISE mensual, 246 observaciones, 126 orígenes

### Muestra completa

| # | Modelo | MAE | vs ingenuo | p | p Holm |
|---|---|---|---|---|---|
| 1 | ARMA(2,2) | 2,073 | +7,7 % | 0,083 | 0,995 |
| 2 | AR(1) | 2,080 | +7,4 % | 0,039 | 0,504 |
| 3 | Random Forest | 2,103 | +6,4 % | 0,393 | 1,000 |
| 8 | *Ingenuo* | *2,246* | *ref* | — | — |
| 12 | LSTM(32) v24 | 2,262 | −0,7 % | 0,937 | 1,000 |
| 17 | CNN 1D v24 | 2,808 | −25,0 % | 0,019 | 0,261 |
| 18 | MLP | 3,841 | −71,0 % | 0,001 | 0,017 ✱ *peor* |
| 19 | Ingenuo estacional | 5,449 | −142,6 % | 0,000 | 0,000 ✱ *peor* |

Ninguna mejora sobrevive a Holm. Lo único significativo es negativo: el MLP y el
ingenuo estacional. Este último es el peor por construcción: el objetivo ya es una
variación interanual, sin estacionalidad, y repetir los doce meses anteriores la vuelve a
meter. Queda como control negativo.

### Calma (102 orígenes, objetivos fuera de 2020–2021)

| # | Modelo | MAE | vs ingenuo | p | p Holm |
|---|---|---|---|---|---|
| 1 | Random Forest | 1,393 | **+24,0 %** | 0,000 | **0,008** ✱ |
| 2 | LSTM(16) v12 | 1,476 | +19,5 % | 0,006 | 0,067 |
| 3 | LSTM(32) v24 | 1,527 | +16,7 % | 0,030 | 0,332 |
| 4 | ARMA(2,2) | 1,554 | **+15,2 %** | 0,000 | **0,008** ✱ |
| 5 | ARIMA(1,1,1) | 1,586 | **+13,5 %** | 0,000 | **0,007** ✱ |
| 6 | ARIMA(2,1,2) | 1,590 | **+13,2 %** | 0,001 | **0,017** ✱ |
| 14 | *Ingenuo* | *1,833* | *ref* | — | — |

Cuatro modelos le ganan al ingenuo en calma tras Holm. El LSTM queda en el borde
(0,067): en 0.1.0 se reportó como "significativo al 1 %", y eso no se sostiene.

### Ruptura (24 orígenes, objetivos en 2020–2021)

| # | Modelo | MAE | vs ingenuo | p | p Holm |
|---|---|---|---|---|---|
| 1 | AR(1) | 3,664 | +8,5 % | 0,317 | 1,000 |
| 2 | *Ingenuo* | *4,002* | *ref* | — | — |
| 12 | Random Forest | 5,120 | −27,9 % | 0,104 | 0,909 |
| 17 | LSTM(16) v12 | 6,491 | −62,2 % | 0,019 | 0,241 |

---

## Pista A: crecimiento anual del PIB, 64 años contiguos, 34 orígenes

### Muestra completa

| # | Modelo | MAE | vs ingenuo | p | p Holm |
|---|---|---|---|---|---|
| 1 | LSTM | 2,202 | +20,0 % | 0,163 | 1,000 |
| 2 | AR(1)+COVID | 2,216 | +19,5 % | 0,143 | 1,000 |
| 3 | ARMA(1,1)+COVID | 2,229 | +19,0 % | 0,152 | 1,000 |
| 5 | Media histórica | 2,339 | +15,0 % | 0,366 | 1,000 |
| 6 | AR(1) | 2,349 | +14,6 % | 0,092 | 1,000 |
| 18 | *Ingenuo* | *2,751* | *ref* | — | — |
| 22 | Factores PCA + AR | 2,853 | −3,7 % | 0,771 | 1,000 |
| 23 | VAR(2) | 2,995 | −8,9 % | 0,536 | 1,000 |
| 25 | SARIMAX(1,0,0)+macro | 3,235 | −17,6 % | 0,287 | 1,000 |
| 26 | MLP | 6,125 | −122,6 % | 0,005 | 0,123 |

**Ningún modelo se distingue del ingenuo, ni a favor ni en contra, tras Holm.** En
calma (32 orígenes) tampoco: el mejor es MA(1), con +15,6 % y p = 0,257. La ruptura anual
tiene 2 orígenes (objetivos 2020 y 2021) y no admite prueba.

### Las variables macro no ayudan

| Enfoque | MAE | Puesto de 26 |
|---|---|---|
| AR(1)+COVID: solo la propia serie | 2,216 | 2 |
| Media histórica: ni siquiera eso | 2,339 | 5 |
| Factores PCA + AR sobre las 15 | 2,853 | 22 |
| VAR(2) con las 4 más correlacionadas | 2,995 | 23 |
| SARIMAX(1,0,1) + 15 macro + COVID | 3,000 | 24 |
| SARIMAX(1,0,0) + 15 macro | 3,235 | 25 |

Las cuatro especificaciones con exógenas quedan por debajo del ingenuo. Con 64
observaciones anuales no hay grados de libertad para estimar lo que aportan. Esto no
dice que la macro no importe para el crecimiento. Dice que **con esta cantidad de datos
no ayuda a pronosticarlo**, que es una afirmación más modesta.

**Advertencia sobre los datos (D-006).** Las exógenas del Banco Mundial son series
revisadas, no las que se conocían en cada año. El caso extremo: el SARIMAX con macro
acierta 2022–2024 casi al decimal (MAE 0,05) porque la esperanza de vida de 2020–2021,
estimada después con la mortalidad del COVID ya conocida, funciona como indicador de la
pandemia. Son tres orígenes sin prueba posible y no entran en ningún ranking, pero
muestran que un backtest con datos revisados puede favorecer a las exógenas.

---

## Lo que el laboratorio establece

1. **Sobre la muestra completa, ningún modelo le gana al ingenuo de forma significativa**
   en ninguna de las dos pistas, una vez que se corrige por comparaciones múltiples.
2. **En calma mensual sí hay ganancia.** Random Forest (+24,0 %), ARMA(2,2), ARIMA(1,1,1)
   y ARIMA(2,1,2) le ganan al ingenuo con p ajustada < 0,02.
3. **Con 64 observaciones anuales no se distingue ningún modelo.** La pista A no tiene
   poder estadístico.
4. **Las variables macro empeoran el pronóstico anual.** Las cuatro especificaciones con
   exógenas quedan por debajo del ingenuo.
5. **Pedir las 33 variables a la vez deja 13 años.** El costo de cada variable en
   historia perdida se calcula antes de modelar (`salidas/frontera_cobertura.csv`).

## Lo que NO establece

- Que los flexibles colapsen en la ruptura. La dirección es clara y la magnitud grande,
  pero ninguna diferencia sobrevive a Holm con 24 meses, y la partición se eligió después
  de ver los datos. Es una hipótesis.
- Qué modelo usar para 2027. Eso depende de si viene un período normal o una ruptura, y
  eso no se sabe de antemano.
- Nada sobre horizontes mayores a un paso.

---

## Reproducir

```bash
uv sync
uv run python -m macro_lab.main      # pistas A y B
uv run python -m macro_lab.robustez  # partición por subperíodo
```

Salidas en `salidas/`: `pista_*_resumen.csv` (con `dm_p` y `dm_p_holm`),
`pista_*_detalle.csv` (una fila por modelo y origen, con `objetivo`) y
`pista_*_robustez.csv`.
