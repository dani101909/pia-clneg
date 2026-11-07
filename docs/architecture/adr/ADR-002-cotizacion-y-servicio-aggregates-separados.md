# ADR-002 · Cotización y Servicio como Aggregates separados; la disponibilidad se deriva de los servicios confirmados

**Estado:** Aceptada

## Contexto
La cotización termina su ciclo al ser aceptada o rechazada (Vigente, Aceptada, Rechazada), mientras que el Servicio continúa desde la programación tentativa hasta el cierre para facturación (US-19). Además, US-05 pide mostrar la disponibilidad por cuadrilla a partir de los servicios ya confirmados. La U2 deja abierto si el folio es uno solo o dos (hallazgo H-01).

## Alternativas
- **Un solo Aggregate Cotización-Servicio:** consistencia inmediata, pero mezcla dos ciclos de vida distintos y crece sin límite.
- **Cuadrilla con agenda propia:** la confirmación modificaría dos Aggregates (Servicio y Cuadrilla) en una transacción.
- **Aggregates separados vinculados por Folio, con disponibilidad derivada:** cada transacción modifica un Aggregate y la disponibilidad sale de los servicios confirmados.

## Decisión
Cotizacion y Servicio son Aggregates distintos que comparten el mismo Folio (supuesto pendiente de validar con el negocio). Cuadrilla no guarda agenda: su disponibilidad en una fecha se calcula con `AsignadorDeCuadrilla` a partir de los servicios confirmados (`ServicioRepository.obtenerConfirmadosPorFecha`).

## Consecuencias
Transacciones pequeñas y coherencia con US-05. Costo: aceptar la cotización crea el Servicio en la misma transacción (excepción documentada a la regla de un Aggregate por transacción) y la regla de que una cuadrilla no se confirma en dos servicios el mismo día debe protegerse dentro de la transacción.

## Trazabilidad
BR-01, BR-02; US-03, US-04, US-05, US-19; CU-01, CU-02.
