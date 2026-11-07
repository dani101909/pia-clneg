# ADR-008 · Persistencia SQL con un Repository por Aggregate; SQLite en desarrollo y PostgreSQL en producción

**Estado:** Aceptada

## Contexto
La U3 propuso repositorios en memoria y dejó la persistencia real para el PIA. El enunciado pide base de datos, Docker Compose con DB y despliegue. Los repositorios deben seguir siendo sustituibles sin cambiar la capa de aplicación.

## Alternativas
- **ORM completo:** reduce SQL manual, pero agrega una dependencia grande y oculta el mapeo de Aggregates.
- **Solo SQLite:** simple, pero no se parece a producción y no sirve en despliegue gratuito con disco efímero.
- **SQL explícito con una capa mínima para SQLite y PostgreSQL:** un Repository por Aggregate, el mismo SQL en ambos motores y la URL de la base en una variable de entorno.

## Decisión
`BaseDeDatos` y `Conexion` (`src/infrastructure/base_de_datos.py`) abren SQLite o PostgreSQL según `DATABASE_URL`. Hay un Repository SQL por Aggregate (`sql_repositorios.py`) y una Unit of Work, con una conexión y una transacción por petición HTTP. Los repositorios SQL pasan la misma batería de contrato que los de memoria (`tests/test_contrato_repositorios.py`), y el CI repite los casos de uso sobre PostgreSQL 16 real.

## Consecuencias
Se puede cambiar de motor con una variable de entorno y los tests de contrato evitan que una implementación rompa a la capa de aplicación. Costo: SQL escrito a mano y el cuidado de mantenerlo compatible con los dos motores. Las pruebas de PostgreSQL solo corren donde hay un servidor (el CI).

## Trazabilidad
RNF-03; todos los casos de uso; requisito de producción del PIA.
