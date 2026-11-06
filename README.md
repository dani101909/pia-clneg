# CleanPro - Diseño Arquitectural del Sistema (Unidad 3)

Universidad Autónoma de Nuevo León (UANL)  
Facultad de Ingeniería Mecánica y Eléctrica (FIME)  
Materia: Componentes de Lógica de Negocio  
Grupo: 001 | Hora: N1 | Periodo: Agosto - Diciembre 2026  
Equipo 12  

Integrantes:
- Pérez Ordaz Andrés Daniel (2163200)
- Ramos Ortiz Patricia Lizeth (2161739)
- Esquivel Anaya Jonathan (2160886)
Docente: Miguel Ángel Gómez Marroquín

## Empresa
CleanPro (Servicios de limpieza residencial y empresarial).

## Alcance
Proceso operativo central que abarca desde la aceptación de la cotización, programación tentativa, confirmación de cuadrilla el día previo, ejecución en sitio, gestión de incidencias/extras y validación de invariantes de cierre para facturación (Casos de uso CU-01 a CU-05).

## Instrucciones de Revisión
Para clonar, revisar y evaluar la propuesta arquitectónica, la documentación y el código base del sistema, siga los pasos a continuación:

1. Clonar el repositorio ejecutando en su terminal el comando: git clone https://github.com/dani101909/cleanpro.git
2. Revisar la documentación formal y de diseño ingresando a la carpeta docs/ (informe de arquitectura, ADRs y bitácora de IA) y a la carpeta diagrams/ (diagramas de clases y de secuencia).
3. Inspeccionar el código fuente ingresando a la carpeta src/, el cual se encuentra estructurado bajo arquitectura limpia separando Dominio, Aplicación e Infraestructura.
4. Ejecutar las pruebas unitarias localizadas en la carpeta tests/ para verificar la validación de las reglas de negocio e invariantes.

## Enlaces a Entregables
- Informe de arquitectura, ADRs, matriz local y bitácora de IA: Carpeta docs/
- Diagramas de dominio, clases y secuencia: Carpeta diagrams/
- Matriz de Trazabilidad (Google Docs): https://docs.google.com/document/d/1gGs4kaGNKgj43VDIDVSF5UncehzW-hUVukFS5CLn5ns/edit
- Código base (Estructura DDD): Carpeta src/
- Pruebas unitarias seleccionadas: Carpeta tests/