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
