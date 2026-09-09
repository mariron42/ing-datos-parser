# Guía técnica del ETL

**Autor:** mariron42

**Proyecto:** Ingeniería de Datos - ETL de ADManager y SAP

Esta carpeta explica qué problema resuelve el código, cómo está dividido, qué
comandos utiliza y por qué se tomaron las decisiones principales. Está pensada
para una persona que clone el repositorio y necesite entenderlo antes de
ejecutarlo o modificarlo.

## Contenido

1. [Arquitectura](01-arquitectura.md): componentes y relaciones del sistema.
2. [Módulos y comandos](02-modulos-y-comandos.md): responsabilidad de cada
   archivo y herramientas utilizadas.
3. [Funcionamiento del ETL](03-flujo-etl.md): recorrido completo desde el log
   hasta el CSV.
4. [Reglas de negocio](04-reglas-de-negocio.md): decisiones para ADManager y
   SAP según la evidencia disponible.
5. [Calidad, seguridad y mantenimiento](05-calidad-y-mantenimiento.md):
   pruebas, estilo, dependencias, datos privados y forma de extender el código.

## Fuentes de requisitos

- [Tarea 1](../2026-09-01%20Tarea%201.pdf): reporte diario e idempotencia.
- `2026-09-03 Tarea 1 Parte 2.pdf`, conservado localmente: estructura
  profesional, Git, uv, Ruff y mensajes informativos.
- `2026-08-25 StatusCodes Alta SAP V2.pdf`, conservado localmente:
  clasificación de resultados del endpoint de alta SAP.

Los PDFs contienen los requisitos. Los dos documentos nuevos no se publican con
este commit; la guía contiene la explicación necesaria para comprender el
sistema. La conducta ejecutable está definida por el código y respaldada por las
pruebas de `tests/`.
