# BRD · CleanPro (Equipo 12)

**Documento de requerimientos de negocio, refinado a partir del trabajo de las Unidades 2 y 3.**
Empresa: CleanPro, servicios de limpieza residencial y empresarial. Curso: Componentes de Lógica de Negocios, UANL-FIME. Equipo: Andrés Daniel Pérez Ordaz (2163200), Jonathan Esquivel Anaya (2160886) y Patricia Lizeth Ramos Ortiz (2161739).

> **Nota sobre la numeración.** El BRD original no numera sus reglas ni sus requisitos no funcionales. La numeración BR, RNF y NEC es del equipo y sigue el orden del texto del BRD de la U2 (hallazgo H-07 del informe de la U3). Los criterios Gherkin completos de las 19 historias y el BPMN completo se entregaron en la U2; aquí se resumen y se enlazan con el código. Los escenarios del apéndice cubren los casos de uso implementados.

## 1. Contexto y problema

CleanPro presta servicios de limpieza a hogares y empresas con cuadrillas de personal operativo. El negocio identificó tres problemas: errores de facturación, poca evidencia de las incidencias y los extras ocurridos en sitio, y el riesgo de que cada supervisor aplique las políticas de forma distinta (cortesía, extras, reprogramaciones). El sistema busca que el ciclo del servicio, desde la cotización hasta el cierre para facturación, siga reglas únicas, deje evidencia de quién hizo qué y cuándo, y no permita cerrar un servicio con pendientes.

## 2. Alcance

**Dentro del alcance:** cotización con folio y estimación, programación tentativa al aceptarla, confirmación de cuadrilla el día previo según disponibilidad real, ejecución en sitio (inicio y término), incidencias (ausencia, acceso negado, material especial, daño), extras en sitio, ajuste por inmueble mayor, reprogramación y cancelación, cierre para facturación, panel operativo e historial del servicio, y control de acceso por rol.

**Fuera del alcance:** optimización de rutas, integración contable, nómina y la entidad Factura (la facturación es un sistema externo; el dominio solo emite el evento de cierre, ADR-004).

## 3. Actores

- **Cliente:** acepta la cotización y consulta lo suyo.
- **Coordinador:** emite cotizaciones, confirma la cuadrilla el día previo y confirma los extras fuera de catálogo.
- **Supervisor:** reporta ausencias, registra inicio y término, documenta incidencias y registra extras en sitio.
- **Administración:** reasigna personal, revisa incidencias, cierra para facturación y administra las políticas.
- **Sistema de facturación (externo):** recibe el evento de cierre.

## 4. Necesidades del negocio

- **NEC-01:** disponibilidad real de cuadrillas.
- **NEC-02:** cotización con folio, datos completos y programación tentativa.
- **NEC-03:** mecanismo formal para reportar y atender ausencias.
- **NEC-04:** captura estructurada de incidencias y extras con evidencia.
- **NEC-05:** ajustes de precio y tiempo por inmueble mayor al reportado.
- **NEC-06:** reglas de reprogramación y de material especial.
- **NEC-07:** reportes operativos (panel e historial).

## 5. Reglas de negocio

- **BR-01:** una cotización no compromete cuadrilla; solo la aceptación del cliente genera una programación tentativa.
- **BR-02:** la asignación final de personal se confirma un día antes, según disponibilidad real.
- **BR-03:** toda ausencia se reporta al detectarse y queda como incidencia vinculada al servicio.
- **BR-04:** un extra del catálogo lo acepta el supervisor; si modifica el precio de forma significativa o está fuera de catálogo, requiere al coordinador.
- **BR-05:** si el inmueble es mayor al reportado, el coordinador recalcula y el cliente acepta el ajuste antes de continuar.
- **BR-06:** la reprogramación de última hora la solicita el cliente y la decide Administración.
- **BR-07:** un servicio no se cierra para facturación con incidencias o extras sin documentar.
- **BR-08:** modificar o cancelar un servicio programado corresponde al coordinador; Administración queda notificada.

## 6. Requisitos no funcionales

- **RNF-01:** los cambios de estado de un servicio son visibles para Administración sin demoras significativas.
- **RNF-02:** las funciones sensibles (ajustes, reprogramaciones, cierre) están limitadas por rol. *Implementado con autenticación por token y autorización por rol en la API (ADR-005), y validación del permiso en el dominio.*
- **RNF-03:** toda modificación relevante conserva quién, cuándo y por qué. *Implementado con el historial del servicio.*
- **RNF-04:** los valores no confirmados (tiempo de cortesía, cobro por acceso negado, penalización por reprogramación tardía, criterio de precio significativo) son configurables, no inventados (ADR-003).

## 7. Historias de usuario

Las 19 historias de la U2, con su criterio de aceptación en Gherkin, están en el entregable de la U2. Resumen y estado en el código:

- **US-01 y US-02:** solicitar y emitir la cotización con folio y estimación. *Implementado: emisión con folio único (el cálculo automático de la estimación no se programó; la captura la hace quien emite).*
- **US-03:** aceptar la cotización y generar la programación tentativa (CU-01). *Implementado.*
- **US-04:** confirmar cuadrilla el día previo (CU-02). *Implementado.*
- **US-05:** consultar disponibilidad de cuadrillas por fecha. *Implementado.*
- **US-06 y US-07:** reportar ausencia y reasignar personal, o declarar el servicio en riesgo si no hay reemplazo (CU-03). *Implementado.*
- **US-08:** registrar inicio y término del servicio. *Implementado.*
- **US-09:** documentar incidencias. *Implementado.*
- **US-10:** registrar extra en sitio, del catálogo o fuera de él (CU-04). *Implementado.*
- **US-11:** ajuste por inmueble mayor. *Diseñado; la transición y el modelo existen, el caso de uso no se programó.*
- **US-12:** material especial. *Diseñado (tipo de incidencia existente).*
- **US-13:** acceso negado. *Diseñado (estado NoRealizado y transición existentes).*
- **US-14 y US-15:** solicitud y decisión de reprogramación. *Diseñado.*
- **US-16:** modificar o cancelar un servicio. *Diseñado (estado Cancelado y transición existentes).*
- **US-17:** cerrar para facturación (CU-05). *Implementado.*
- **US-18:** panel operativo de estados. *Implementado (consulta de lectura, CQRS básico).*
- **US-19:** historial del servicio. *Implementado.*

## 8. Proceso (BPMN)

El BPMN de la U2 tiene cinco carriles (Cliente, Coordinador, Supervisor, Administración y Facturación) y va de «Solicitar cotización» a «Facturar servicio», con los gateways «¿Aceptada?», «¿Cuadrilla disponible?», «¿Reemplazo encontrado?», «¿Acceso permitido?» y «¿Pendientes por documentar?». Cada gateway corresponde a una regla del dominio o a una transición de la State Machine (ver `docs/TRAZABILIDAD.md`).

## 9. Glosario

El glosario de dominio está en `docs/Glosario_Actualizado.pdf`. Los nombres del código usan sus términos (Cotización, Folio, Servicio, Programación tentativa, Confirmación de cuadrilla, Incidencia, Extra, Catálogo de extras, Servicio en riesgo, Cierre para facturación).

## 10. Supuestos y pendientes sobre la U2

Los valores que la U2 deja sin definir no se inventaron; quedan configurables: tiempo de cortesía, cobro por acceso negado, penalización por reprogramación tardía, criterio de precio significativo y catálogo de extras. Tampoco están definidos el tarifario, la moneda, las unidades de superficie ni si el folio de cotización y el de servicio son el mismo (en el código se asume el mismo folio, ADR-002). Los datos de `datos_demo.py` son ilustrativos, no tarifas reales.

## Apéndice A. Escenarios Gherkin de los casos implementados

```gherkin
Característica: Aceptar cotización (CU-01, BR-01)
  Escenario: El cliente acepta una cotización vigente
    Dado una cotización vigente del cliente
    Cuando el cliente la acepta con una fecha de servicio
    Entonces la cotización queda Aceptada
    Y se crea un servicio Programado con el mismo folio y sin cuadrilla

  Escenario: No se acepta una cotización que no está vigente
    Dado una cotización ya aceptada
    Cuando el cliente intenta aceptarla otra vez
    Entonces se rechaza con COTIZACION_NO_VIGENTE

Característica: Confirmar cuadrilla el día previo (CU-02, BR-02)
  Escenario: El coordinador confirma una cuadrilla libre
    Dado un servicio Programado con fecha
    Cuando el coordinador confirma una cuadrilla libre en esa fecha
    Entonces el servicio pasa a CuadrillaConfirmada

  Escenario: La cuadrilla ya está ocupada
    Dado una cuadrilla confirmada en otro servicio el mismo día
    Cuando el coordinador intenta confirmarla
    Entonces se rechaza con CUADRILLA_NO_DISPONIBLE

Característica: Ausencia y reasignación (CU-03, BR-03)
  Escenario: Ausencia sin reemplazo
    Dado un servicio con cuadrilla confirmada
    Cuando el supervisor reporta una ausencia y Administración no encuentra sustituto
    Entonces se crea una incidencia y el servicio pasa a EnRiesgo

Característica: Extras en sitio (CU-04, BR-04)
  Escenario: Extra fuera de catálogo
    Dado un servicio en ejecución
    Cuando el supervisor registra un extra que no está en el catálogo
    Entonces queda pendiente de confirmación del coordinador

Característica: Cierre para facturación (CU-05, BR-07)
  Escenario: Cierre bloqueado por pendientes
    Dado un servicio terminado con una incidencia sin revisar
    Cuando Administración intenta cerrarlo para facturación
    Entonces se rechaza con CIERRE_BLOQUEADO e indica qué falta

  Escenario: Cierre exitoso
    Dado un servicio terminado sin pendientes
    Cuando Administración lo cierra
    Entonces pasa a CerradoParaFacturacion y se emite ServicioCerradoParaFacturacion

Característica: Control de acceso por rol (RNF-02)
  Escenario: Un rol sin permiso no puede cerrar
    Dado un supervisor autenticado
    Cuando intenta cerrar un servicio para facturación
    Entonces recibe 403 SIN_PERMISO
```
