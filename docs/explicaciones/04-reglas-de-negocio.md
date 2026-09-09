# Reglas de negocio

## Evidencia común de ADManager

Las respuestas `SearchUser` se indexan usando `SAM_ACCOUNT_NAME`,
`sAMAccountName` o `EMPLOYEE_ID`. También se identifica el valor buscado en los
filtros `sAMAccountName:equal` y `employeeID:equal`. Una respuesta válida con
`UsersList` vacío demuestra que ese valor no fue encontrado.

Las comparaciones pasan por `normalize`: se eliminan acentos, se convierten a
minúsculas y se compactan espacios. Los nombres y oficinas originales permanecen
sin alterar en el CSV.

## Reseteo de contraseña en ADManager

| Respuesta de nuestra API | Mensaje construido con la evidencia |
| --- | --- |
| 200 | Contraseña restablecida correctamente. |
| 202 | El objetivo pertenece a Corporativo y debe usar autoservicio. |
| 403 | Oficinas distintas, solicitante sin rol permitido o objetivo en `OAT/Cedis/BY`. |
| 404 | Solicitante, objetivo o ambos no encontrados. |
| 429 | Tokens de ADManager agotados. |
| 500 | Error crítico que requiere revisión técnica. |
| 503 | Fallo de ADManager más el `statusMessage` exacto retornado. |
| 504 | Tiempo de espera de 35 segundos superado. |

Para 403 se pueden enumerar varias causas cuando la evidencia respalda más de
una. Para 404 solo se declara un usuario ausente si existe una búsqueda válida y
vacía para ese identificador.

## Alta de usuario SAP V2

El procesador utiliza `requester_username`, `target_employee_id`, `treatment` y
`job` de `/v2/sap/register_user`. Combina esa solicitud con ADManager, la
respuesta `SAP raw response` y las llamadas de Proactivanet.

| Respuesta de nuestra API | Decisión |
| --- | --- |
| 200 | El alta, la creación del ticket y su cierre fueron exitosos. |
| 202 | Si existe un POST exitoso de creación, el ticket se creó pero no cerró; sin ese evento, no pudo crearse. |
| 208 | Se confirma que el usuario ya existe cuando el mensaje de SAP contiene `ya existe`. |
| 400 | Se revisa, en orden, que el empleado sea numérico, que el tratamiento sea señor/señora y que el log no indique un puesto inexistente; el resto es causa desconocida. |
| 401 | `DESCRIPTION` no comienza con gerente o admin. Una contradicción se marca para revisión. |
| 403 | Se revisa Corporativo/OAT, oficina distinta y conflicto con el puesto solicitado. |
| 404 | Se distingue la búsqueda ausente por `sAMAccountName` de la ausente por `employeeID`. |
| 500 | Error desconocido durante el alta SAP. |
| 503 | Las validaciones pasaron, pero falló el servicio de SAP. |

Los conflictos de puesto se consolidan en un solo resultado. Se reconocen los
mensajes de puestos exclusivos de City Club y Soriana, además del alta de gerente
cuando el objetivo no figura como gerente. El patrón explícito del log tiene
prioridad porque los catálogos completos de puestos no forman parte del proyecto.

## Orden de decisión

Dentro de un mismo código se evalúan primero las causas que tienen evidencia más
concreta. Por ejemplo, para un 403 de SAP: Corporativo, oficina distinta y después
conflicto de puesto. Si ninguna coincide, el resultado declara que los logs no
permiten conocer la causa en lugar de inventarla.
