# ADR-007 · Specification para reglas de negocio componibles y explicables

**Estado:** Aceptada

## Contexto
Varias reglas son condiciones que se combinan y que además deben poder explicarse al usuario: «el servicio es cerrable» exige que la State Machine admita el cierre y que no haya pendientes por documentar (BR-07), y el cierre bloqueado debe decir qué falta (US-17). El requisito del curso exige el patrón Specification.

## Alternativas
- **Condicionales en los servicios de aplicación:** repiten la regla y no explican por qué falla.
- **Métodos booleanos en el Aggregate:** centralizan, pero no se componen ni devuelven el motivo.
- **Specification con operadores Y, O y No:** cada regla es un objeto pequeño, se combina y devuelve sus razones de incumplimiento.

## Decisión
`Especificacion` (`src/domain/specification.py`) con los operadores `Y`, `O` y `No` y el método `razonesDeIncumplimiento`. Las reglas concretas están en `src/domain/especificaciones.py`: `CuadrillaLibreEnFecha`, `ExtraRequiereConfirmacion`, `EmpleadoDisponibleParaCubrir`, `ServicioAdmite`, `SinPendientesPorDocumentar`, y las composiciones `servicioCerrableParaFacturacion()` y `servicioCancelable()`.

## Consecuencias
El mensaje de cierre bloqueado sale de las razones de la especificación, sin duplicar la regla. Costo: más clases pequeñas y la disciplina de usarlas en lugar de condicionales sueltos.

## Trazabilidad
BR-02, BR-04, BR-07; US-04, US-07, US-10, US-16, US-17.
