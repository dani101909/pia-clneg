# ADR-003 · Políticas pendientes de validar como ConfiguracionDePoliticas, pasadas como parámetro

**Estado:** Aceptada

## Contexto
El BRD deja pendientes el tiempo de cortesía, el cobro por acceso negado, la penalización por reprogramación tardía, el criterio de precio «significativo» y el catálogo de extras, y exige que queden configurables (RNF-04). Ninguno de estos valores existe en la U2 y no deben inventarse.

## Alternativas
- **Valores fijos en el código:** rápido, pero obliga a editar el Aggregate cada vez que el negocio valide un valor e implica inventar cifras.
- **Condicionales por política dentro de Servicio:** cada política nueva modifica el Aggregate (viola el principio abierto/cerrado).
- **Aggregate de soporte ConfiguracionDePoliticas versionado:** los valores cambian sin tocar el dominio.

## Decisión
Crear el Aggregate de soporte `ConfiguracionDePoliticas` (`src/domain/configuracion.py`), modificable solo por Administración. Las entidades no lo consultan: los servicios de dominio (`PoliticaDeExtras`) lo reciben como parámetro, obtenido por `ConfiguracionRepository`.

## Consecuencias
Se pueden aplicar políticas sin inventar valores y cambiar una no obliga a modificar Servicio. Costo: una dependencia extra en los servicios de aplicación que las usan y definir qué ocurre mientras una política no tenga valor.

## Trazabilidad
BR-04; RNF-02, RNF-03, RNF-04; US-10, US-13, US-15; CU-04.
