# ADR-006 · State Machine del Servicio definida por una tabla de transiciones

**Estado:** Aceptada

## Contexto
El Servicio recorre un ciclo de vida con estados y reglas de paso (BPMN de la U2, invariantes S1 a S13): confirmar cuadrilla, iniciar, terminar, declarar sin reemplazo, cerrar para facturación, cancelar, negar acceso y dar por no realizado. El requisito del curso exige una State Machine.

## Alternativas
- **Condicionales (`if estado == ...`) dentro de Servicio:** simple al inicio, pero las transiciones válidas quedan dispersas y es fácil permitir un paso inválido.
- **Patrón State con una clase por estado:** flexible, pero produce muchas clases para transiciones que son datos.
- **Tabla `(estado, disparador) → estado` en una máquina genérica:** las transiciones se leen en un solo lugar y se pueden probar de forma exhaustiva.

## Decisión
`MaquinaDeEstados` (`src/domain/maquina_estados.py`) se define solo con una tabla. El Servicio tiene 8 estados (Programado, CuadrillaConfirmada, EnEjecucion, Terminado, CerradoParaFacturacion, EnRiesgo, NoRealizado, Cancelado) y 8 disparadores, y su tabla está en `src/domain/estado_servicio.py`. Una transición no definida lanza un error de negocio (`TRANSICION_INVALIDA`, HTTP 409) con el estado y el disparador.

## Consecuencias
Las transiciones se verifican en pruebas (`tests/test_maquina_estados.py`) y la interfaz muestra «no es posible en el estado actual» como comportamiento de la máquina, no como error. Tres disparadores (`CANCELAR`, `NEGAR_ACCESO`, `DAR_POR_NO_REALIZADO`) ya existen en la tabla, pero sus casos de uso no se programaron.

## Trazabilidad
US-04, US-07, US-08, US-13, US-16, US-17; BPMN completo.
