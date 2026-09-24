# Bitácora

Errores (B-NNN) y decisiones (D-NNN). Entrada antes del arreglo, según R-11.

---

## B-001 · Un fallo se disfrazó de victoria (18-sep-2026)

**Síntoma.** La primera corrida de la Pista C daba a las combinaciones por régimen
ganando en los 8 países, con márgenes enormes. Demasiado bueno.

**Causa raíz.** `modelos._indice_futuro` contemplaba `DatetimeIndex` y enteros, pero no
`PeriodIndex`. Las series trimestrales de LATAM usan `PeriodIndex`, y `np.arange` sobre
objetos `Period` lanza excepción. Todo modelo recursivo — Random Forest, Ridge y las
combinaciones que los invocan — reventaba en esos orígenes.

**Por qué no se vio de inmediato.** `Modelo.predecir` atrapa la excepción y devuelve
`NaN`, que es el comportamiento correcto. Pero el resumen descartaba los `NaN` al
promediar, de modo que el modelo quedaba evaluado **solo sobre los orígenes donde
sobrevivió**. Las combinaciones sobrevivían justo cuando el interruptor iba a pleno
robusto y no llamaba al modelo flexible: los orígenes volátiles. Parecían las mejores por
no haber competido.

**Magnitud.** México: el "ganador" tenía MAE 0,750 calculado sobre **7 de 77** orígenes.
Corregido, Random Forest gana con 1,582 sobre 77 de 77.

**Arreglo.** `_indice_futuro` atiende `PeriodIndex` primero.

**Regla que lo habría evitado: R-07**, añadida a raíz de esto. `backtest.resumen` calcula
cobertura por modelo y deja fuera del ordenamiento a cualquiera por debajo del 90 %,
mostrando la cobertura en la tabla.

**Validación posterior.** La regla atrapó un segundo caso por su cuenta:
`Comb. LSTM/AR(1) suave` tiene 79 % de cobertura en la calma anual —el LSTM no ajusta con
tramos de entrenamiento cortos— y quedó excluido del agregado de la Pista D.

---

## D-001 · Dos pistas en vez de una (18-sep-2026)

Se midió la frontera de cobertura antes de modelar (R-08): exigir las 33 variables macro
deja 13 años en Colombia y **cero en 18 de 20 países**. Con eso no se estima nada.

De ahí la separación: una pista anual con ~20 variables y ~62 años para los modelos con
exógenas, y una pista de alta frecuencia univariada (246 meses del ISE) donde las redes
tienen material para aprender. Mezclarlas habría exigido rellenar frecuencias, prohibido
por R-03.

---

## D-002 · El interruptor de régimen reacciona, no anticipa (18-sep-2026)

La combinación podría haberse calibrado marcando 2020–2021 a mano. Habría dado mejores
números y no habría valido nada.

El umbral se estima con la volatilidad móvil del propio tramo de entrenamiento en cada
origen. Consecuencia medida: en el origen de febrero de 2020 el peso robusto es 0,00 y el
modelo se come entero el primer mes del choque (−6,3 %); reacciona en marzo y se queda
hasta noviembre. **Un mes de rezago es el precio de no hacer trampa**, y el rastro
completo está en `salidas/combinacion_pesos.csv` para auditarlo.

---

# Auditoría previa al release v1.0.0 (23-sep-2026)

Entradas escritas antes de los arreglos (R-11). La magnitud de cada una se mide con la
corrida corregida y se anota al final, en "Efecto medido".

## B-002 · El régimen se asignaba por el año del origen, no del objetivo

**Síntoma.** En la Pista A la fila con origen 2019 tiene `real = -7,19`: es el pronóstico
de la caída de 2020, y `robustez`, `lab_latam` y `lab_combinacion` la contaban como
"calma". La "ruptura" anual eran los objetivos 2021 (rebote) y 2022.

**Causa raíz.** `origen_movil` guarda el origen (último dato visto), y las tablas por
subperíodo clasifican con `_anio(origen)`. El error que se mide es el del período
siguiente. En datos anuales el desfase es de un año entero; en trimestral y mensual, de
un período en cada borde.

**Regla que lo habría evitado.** R-10 se aplica sobre el período que se pronostica. Nueva
columna `objetivo` en el detalle; toda partición por régimen usa `backtest.regimen`, que
mira el objetivo.

## B-003 · Las series trimestrales del FMI son ajustadas estacionalmente, sin declararlo

**Síntoma.** Las 8 series de `latam_trimestral.parquet` tienen `ajuste == "ajustada"`.
`latam.py` decía usar la serie sin ajuste.

**Causa raíz.** `descargar_trimestral_latam` prefiere la serie sin ajuste y cae a la
ajustada si no existe; en los 8 países no existe. El respaldo se anotó en una columna,
pero ni el módulo ni `RESULTADOS_LATAM.md` lo declararon.

**Regla que lo habría evitado.** R-05 ya lo exigía. Se declara en el módulo, en los
resultados y se imprime al correr.

## B-004 · Años no contiguos tratados como consecutivos

**Síntoma.** El panel anual de Colombia salta 1986 y 1989; Argentina, Brasil y Nicaragua
tienen huecos parecidos. Los modelos de rezagos tratan 1985 → 1987 como un año.

**Causa raíz.** `panel_anual` y `panel_pais` hacen `dropna()` por filas: quitan el año
incompleto pero dejan los vecinos pegados.

**Regla que lo habría evitado.** R-03 en su forma general: no fabricar continuidad. Se
conserva el tramo contiguo más largo que termina en el último año completo.

## B-005 · La Pista D recortaba el objetivo al panel multivariable

**Síntoma.** Venezuela entraba con 48 de 65 años; Haití con 53.

**Causa raíz.** `pista_d` tomaba `pib_crecimiento` del panel recortado por cobertura de
~20 variables, aunque su catálogo es univariado y no usa ninguna.

**Regla que lo habría evitado.** R-08: la frontera de cobertura decide la muestra de los
modelos que usan esas variables, no la de los que no las usan.

## B-006 · La combinación rellenaba el fallo del flexible con el robusto

**Causa raíz.** `_combinar` devolvía el pronóstico robusto cuando el flexible no era
finito. Es rellenar un fallo con otro modelo, lo que el protocolo prohíbe, y lo esconde
de la columna de cobertura.

**Regla que lo habría evitado.** R-07. Ahora el fallo se propaga como faltante.

## B-007 · SARIMAX con macro: X contemporáneo al ajustar, X del origen al pronosticar

**Causa raíz.** El ajuste regresaba y_t sobre X_t; el pronóstico de y_{T+1} usaba X_T.
No es fuga, es una especificación distinta entre ajuste y pronóstico que castiga a las
exógenas. Se rezagan un período, igual que en `_matriz_rezagos`.

**Regla que lo habría evitado.** R-04 leída completa: el modelo que se ajusta debe ser el
que se usa en el origen.

## B-008 · `_dummies_covid` no atendía `PeriodIndex`

Latente: hoy ningún modelo trimestral usa las dummies, pero reventaría igual que B-001.
Se lee el año con `.year` en los índices de fecha y periodo.

## D-003 · Tablas publicadas sin `p` y un ordenamiento sin filtro de cobertura

La tabla de combinación (+17,3 %) y el agregado LATAM no llevaban prueba; `robustez`
ordenaba incluyendo modelos con cobertura menor al 90 %. Se añaden Diebold-Mariano por
tramo, Wilcoxon entre países para el agregado, y el filtro de cobertura (R-06, R-07).

## D-004 · La combinación sobre el ISE es hipótesis, no conclusión

Las piezas (Random Forest y AR(1)) se eligieron después de ver la tabla de robustez del
ISE, y la combinación se mide sobre el mismo ISE. Por R-09 y R-10 ese resultado es
hipótesis. La prueba fuera de muestra es LATAM, donde la combinación entra sin retocar.

## D-005 · Corrección por comparaciones múltiples

Con ~25 modelos contra la referencia al 5 %, uno o dos "significativos" salen por azar.
`resumen` añade `dm_p_holm` (Holm sobre los modelos rankeables) y el asterisco usa la p
ajustada. La p sin ajustar sigue en la tabla.

## D-006 · Las exógenas anuales no son de tiempo real (encontrado al re-correr)

**Síntoma.** Tras B-007, `SARIMAX(1,0,0)+macro` acierta 2022, 2023 y 2024 casi al
decimal (MAE 0,047 en tres orígenes; en 2017 falla por 4,6 pp).

**Diagnóstico.** No es fuga del backtest: rehecho a mano, el pronóstico usa solo datos
hasta el origen. Quitando una variable a la vez, el acierto depende de `esperanza_vida`
(sin ella el MAE post-2022 sube a 5,07). La esperanza de vida cae en 2020–2021 por el
COVID y el modelo la usa como indicador de la pandemia que anticipa el rebote.

**Causa raíz.** El Banco Mundial publica la serie revisada: la esperanza de vida de 2021
se estimó después, con la mortalidad ya conocida, y la de 2023–2024 es proyección de la
ONU. En 2021 nadie tenía ese dato. Es mirar adelante por el vintage, no por el código.

**Decisión.** No se corrige (no hay vintages en tiempo real para 33 indicadores y 20
países); se declara. Ningún resultado de subperíodo con menos de 6 orígenes entra en un
ranking, y los resultados advierten que las exógenas anuales son datos revisados.

## B-009 · La "Comb. 50/50 RF-AR(1)" no era 50/50 (encontrado al re-correr)

**Síntoma.** En la ruptura mensual da exactamente el mismo error que el AR(1), y en calma
casi el mismo (+6,9 % contra +6,9 %).

**Causa raíz.** Se implementó como el interruptor suave con `cuantil=0.0`. El umbral pasa
a ser la volatilidad mínima de la muestra, la actual casi siempre lo duplica y el peso
robusto se satura en 1: en el ISE, 98 % de los orígenes son AR(1) puro (peso medio 0,99).
La etiqueta prometía una mezcla fija que el código nunca calculó.

**Arreglo.** Se renombra a `Comb. RF/AR(1) umbral min`, que describe lo que hace. Los
números no cambian (es el mismo cálculo), así que se renombra también en las salidas en
vez de volver a correr. Una combinación 50/50 fija queda sin probar.

**Regla que lo habría evitado.** R-08 aplicada a los modelos: antes de interpretar una
combinación se mira su rastro de pesos, no solo su error.

---

## D-007 · Experimento: ISE remuestreado a trimestral (pre-registro, 23-sep-2026)

Escrito **antes** de correr, para que el resultado no se pueda reinterpretar después.

**Pregunta.** En la ruptura de Colombia, el LSTM pierde contra el ingenuo con el ISE
mensual (−62,2 %) y gana con el PIB trimestral del FMI (+21,0 %). Las dos series
difieren en tres cosas a la vez: frecuencia, fuente y ajuste estacional (el ISE va sin
ajuste; el FMI, ajustado, B-003). El experimento las separa.

**Brazos**, los tres trimestrales, en variación interanual y sobre la misma muestra
(2006T1–2025T1, 37 orígenes). Todos usan el catálogo de la Pista C sin retocar y
`min_entrenamiento = 40`:

| Brazo | Serie | Ajuste | Contraste |
|---|---|---|---|
| A | ISE Cuadro 1, promedio trimestral del índice | sin ajuste | A vs ISE mensual: frecuencia |
| B | ISE Cuadro 2, promedio trimestral del índice | ajustado | A vs B: ajuste |
| C | PIB real FMI | ajustado | B vs C: fuente |

El promedio trimestral de un índice mensual agrega de alta a baja frecuencia; no
rellena nada (R-03). El brazo B usa una serie ajustada a propósito, porque el ajuste es
justo lo que se quiere medir. Es un control diagnóstico, no un resultado de pronóstico
(R-05). El brazo C debe reproducir la Pista C de Colombia (LSTM +21,0 % en la ruptura):
si no la reproduce, el experimento no vale.

**Predicciones**, sobre el signo de la ganancia del LSTM contra el ingenuo en la ruptura
(objetivos 2020–2021):

- Si manda la **frecuencia**: A gana, como C.
- Si manda el **ajuste**: A pierde y B gana.
- Si manda la **fuente**: A y B pierden y solo C gana.
- Cualquier otro patrón (por ejemplo, A gana y B pierde) queda como no concluyente.

**Límite declarado de antemano.** La ruptura tiene 8 trimestres por brazo. Ninguna
diferencia va a ser significativa tras Holm. El resultado será de dirección, y como la
partición 2020–2021 se eligió después de ver los datos, es hipótesis (R-10) sea cual sea.

### D-007 · Resultado (corrida del 23-sep-2026)

**Validación.** El brazo C reproduce la Pista C de Colombia: LSTM +21,0 %, p = 0,027. El
experimento vale.

Ganancia del LSTM sobre el ingenuo en la ruptura (8 trimestres por brazo):

| Brazo | LSTM vs ingenuo | p | p Holm |
|---|---|---|---|
| ISE mensual sin ajuste (Pista B, referencia) | −62,2 % | 0,019 | 0,24 |
| A · ISE trimestral sin ajuste | +21,8 % | 0,049 | 0,59 |
| B · ISE trimestral ajustado | +17,6 % | 0,094 | 1,00 |
| C · PIB FMI ajustado | +21,0 % | 0,027 | 0,33 |

**Regla pre-registrada: manda la frecuencia.** Con el mismo ISE sin ajustar, pasar de
mensual a trimestral invierte el signo. Ni el ajuste (A contra B) ni la fuente (B contra
C) lo mueven. En variación interanual las tres series trimestrales son casi la misma
(correlación ≥ 0,996).

**Mecanismo (hallado después de correr, así que es lectura, no predicción).** La que
cambia es la referencia, no la red. El MAE del LSTM en la ruptura es parecido en las dos
frecuencias (6,5 pp mensual; 6,0 pp trimestral). El del ingenuo va de 4,0 pp a un mes
vista a 7,7 pp a un trimestre vista. En plena caída, "igual que el mes pasado" es muy
difícil de batir y "igual que el trimestre pasado" no. La "frecuencia" que manda es, en
concreto, **cuánto se aleja el horizonte de un paso**.

**Límites.** Nada es significativo tras Holm. La partición 2020–2021 se eligió después de
ver los datos (R-10). Y la hipótesis de 0.1.0 ("con datos trimestrales la red se adapta
más rápido") **queda descartada** en su forma original: la red no mejora, empeora la
referencia.

---

## B-010 · La serie de Honduras del Banco Mundial trae un empalme roto (23-sep-2026)

**Síntoma.** Construyendo el panel descriptivo de la web, Honduras salió primera en
crecimiento promedio de la región desde 1980. Su serie `NY.GDP.MKTP.KD.ZG` marca
crecimientos reales de 21 a 29 % por año entre 1990 y 1997 (y un 11,58 idéntico en 1998
y 1999). El PIB per cápita en dólares constantes se triplica en esos mismos años.

**Diagnóstico.** No es un fenómeno económico: ninguna otra economía de la región muestra
una racha así (se barrieron las 20 buscando tres o más años seguidos por encima de 12 %;
solo aparece Honduras), y las cifras publicadas por otras fuentes para esa década están en
el rango de 0 a 6 %. Es un empalme defectuoso de la serie a precios constantes en la
fuente.

**Magnitud.** Honduras entraba a la Pista D con los objetivos de 1991 en adelante: sus
primeros siete orígenes pronosticaban crecimientos inexistentes y su error relativo al
ingenuo se calculaba sobre ellos.

**Arreglo.** `latam.DEFECTOS` declara el tramo (Honduras, 1990–1999) y
`latam.serie_anual` lo enmascara antes de cortar el tramo contiguo. Lo que queda (2000 en
adelante) es más corto que el mínimo de la pista, así que Honduras sale de la Pista D, que
pasa a 19 economías. Como cada economía se evalúa por separado y con semillas fijas, las
tablas se recalculan quitando sus filas del detalle: es idéntico a volver a correr. El
panel web enmascara el mismo tramo y lo dice.

**Regla que lo habría evitado.** R-08 extendida a la plausibilidad: antes de modelar,
barrer cada serie buscando rachas imposibles, no solo huecos. Queda como prueba
(`test_ninguna_racha_imposible`).
