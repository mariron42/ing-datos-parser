# Funcionamiento del ETL

## 1. Selección de archivos

`cli.py` recibe los argumentos. `discovery.py` considera como entradas diarias
los archivos `.log` cuyo nombre contiene una fecha calendario válida
`YYYY-MM-DD`. Sin argumentos se elige el más reciente; `--date` recupera una
fecha anterior y `--all` procesa todos en orden cronológico.

`--log-file` es la excepción deliberada: permite procesar una ruta explícita
aunque su nombre no siga la convención diaria.

## 2. Extracción de operaciones

`LogReader` recorre cada archivo una sola vez. Una expresión regular separa:

- timestamp;
- nivel del evento;
- `operation_Id`;
- mensaje.

Las líneas con el mismo `operation_Id` se agrupan. Una línea sin encabezado se
adjunta como continuación de la operación actual; esto permite interpretar JSON
multilínea. El identificador conecta todos los eventos de una misma solicitud.

## 3. Selección del procesador

`ActionRegistry` examina todos los mensajes de cada operación. El procesador de
ADManager reconoce `/users_admin/resetuser`; el de SAP reconoce exactamente
`/v2/sap/register_user`. La coincidencia no depende de que la solicitud sea la
primera línea.

La lista `DEFAULT_ENABLED_ACTIONS` habilita `resetuser` y `register_user`. El
registro permite activar un subconjunto durante pruebas o futuras ejecuciones.

## 4. Transformación

Cada procesador localiza la solicitud inicial y extrae sus parámetros. Después
separa dos tareas:

1. Los módulos de evidencia leen respuestas de sistemas externos y conservan
   hechos: usuario encontrado, `DESCRIPTION`, `OFFICE`, `OU_NAME`, mensaje de
   SAP y estado del ticket.
2. Los módulos de resultados combinan esos hechos con la respuesta de nuestra
   API para elegir un mensaje humano.

No se copia el código HTTP al resultado. Cuando falta evidencia o una respuesta
está dañada, el proceso deja una advertencia y utiliza un mensaje que expresa la
incertidumbre. No interpreta una respuesta ilegible como prueba de que un usuario
no existe.

## 5. Carga idempotente

`CSVStorageManager` crea el directorio de salida cuando hace falta y adquiere un
bloqueo asociado al archivo. El bloqueo cubre lectura, deduplicación y escritura,
por lo que dos procesos concurrentes no pierden los registros del otro.

La clave principal es `id`, derivada de `operation_Id`. Como compatibilidad, una
fila sin identificador utiliza timestamp, solicitante, objetivo y acción. Una
clave que ya existe se conserva sin modificaciones; una clave nueva recibe
`updated_at` en UTC.

Las filas se ordenan por timestamp. La salida se escribe primero en un archivo
temporal del mismo directorio, se sincroniza al disco y se reemplaza mediante
`os.replace`. Si la escritura falla, el CSV anterior permanece intacto y el
temporal se elimina.

## Consecuencia de la idempotencia

Reprocesar los mismos logs produce cero inserciones y no cambia ningún byte del
CSV. Si cambian reglas de negocio para operaciones ya cargadas, se debe generar
un reporte nuevo desde todos los logs; el proceso incremental no sobrescribe el
historial existente.
