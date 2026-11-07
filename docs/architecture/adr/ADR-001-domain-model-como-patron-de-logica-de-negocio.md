# ADR-001 · Domain Model como patrón de lógica de negocio, con Transaction Script solo para lecturas

**Estado:** Aceptada

## Contexto
CleanPro necesita proteger invariantes que cruzan Servicio, Incidencia y Extra: no cerrar para facturación con pendientes (BR-07, US-17), no confirmar cuadrilla sin validar disponibilidad (BR-02, US-04), no registrar el término antes del inicio (US-08) y no continuar un ajuste sin aceptación del cliente (BR-05, US-11). El BRD identifica como problemas los errores de facturación y la poca evidencia de incidencias y extras, y advierte que cada supervisor podría aplicar las políticas de forma distinta. El sistema no es grande (19 historias, 5 actores); lo complejo son los estados y las invariantes.

## Alternativas
- **Transaction Script:** simple y rápido, pero repite la verificación de BR-07 en cada procedimiento que decida si un servicio es facturable y traslada al código el riesgo de políticas aplicadas de forma distinta.
- **Table Module:** encaja con datos tabulares y reportes, pero las reglas quedan repartidas por tabla (BR-03 y BR-07 cruzan tres) y haría falta otra capa coordinadora, que terminaría siendo Transaction Script con otro nombre.
- **Domain Model:** cada invariante vive en un solo lugar (el Aggregate Servicio) y usa el lenguaje del glosario. Cuesta más modelar y exige mapeo a persistencia.

## Decisión
Domain Model para el flujo que cambia el estado de un Servicio (CU-01 a CU-05 y el resto del ciclo de vida). Transaction Script solo para consultas que no cambian estado ni protegen invariantes: disponibilidad (US-05), panel operativo (US-18) e historial (US-19). Table Module queda descartado.

## Consecuencias
Las invariantes se aplican en un solo lugar y ninguna pantalla puede saltárselas; el código reutiliza el glosario. Costos: más esfuerzo de modelado y una capa de mapeo a persistencia. Riesgo: sobre-modelar (convertir cada tabla en entidad), por eso el modelo se acota al flujo central.

## Trazabilidad
BR-02, BR-05, BR-07; RNF-03, RNF-04; US-04, US-08, US-11, US-17; CU-01 a CU-05. Código: `src/domain/`.
