# ADR-004 · Facturación fuera del dominio: el cierre emite un evento mediante FacturacionPort

**Estado:** Aceptada

## Contexto
La facturación y la integración contable están fuera del alcance del BRD. El dominio solo debe decir cuándo un servicio es facturable (BR-07), sin acoplarse a un sistema contable.

## Alternativas
- **Entidad Factura dentro del dominio:** amplía el alcance a algo que el BRD excluye y acopla el modelo a reglas fiscales.
- **Llamada directa al sistema contable desde el Aggregate:** acopla el dominio a un sistema externo.
- **Evento de dominio y puerto de salida:** el dominio emite el hecho y la infraestructura decide qué hacer con él.

## Decisión
El Aggregate Servicio produce el evento `ServicioCerradoParaFacturacion` (`src/domain/eventos.py`) y la capa de aplicación lo entrega mediante `FacturacionPort` (`src/application/puertos.py`). No se modela la entidad Factura.

## Consecuencias
CleanPro no queda acoplado al sistema contable; el adaptador de facturación puede cambiarse sin tocar el dominio. Costo: hoy el adaptador es una implementación de demostración; la integración real queda fuera del alcance.

## Trazabilidad
BR-07; US-17; CU-05; BPMN: «Facturar servicio».
