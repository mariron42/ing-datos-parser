"""Pruebas del registro extensible de procesadores."""

from etl import ActionRegistry, BaseActionProcessor, build_default_registry


class FakeSAPProcessor(BaseActionProcessor):
    """Procesador ficticio que representa una futura extension (otro sistema)."""

    @property
    def action_name(self) -> str:
        return "register_user"

    @property
    def system_name(self) -> str:
        return "SAP"

    def matches(self, initial_message: str) -> bool:
        return "sap/register_user" in initial_message

    def process_operation(self, op_id: str, lines: list) -> dict | None:
        return {"id": op_id, "acción": self.action_name, "sistema": self.system_name}


def operacion(mensaje: str) -> list[dict]:
    return [{"timestamp": "2026-09-01T00:00:00Z", "level": "INFO",
             "message": mensaje, "full_line": mensaje}]


def test_el_registro_por_defecto_trae_admanager_resetuser():
    registry = build_default_registry()
    operations = {"aaa1": operacion("GET /v3/users_admin/resetuser?sAMAccountName_requester=a&sAMAccountName_target=b 200")}

    records = registry.process_operations(operations)

    assert len(records) == 1
    assert records[0]["sistema"] == "ADManager"


def test_se_puede_registrar_un_sistema_nuevo_sin_tocar_el_motor():
    registry = ActionRegistry()
    registry.register(FakeSAPProcessor())

    records = registry.process_operations({"bbb2": operacion("POST /sap/register_user")})

    assert records == [{"id": "bbb2", "acción": "register_user", "sistema": "SAP"}]


def test_enabled_actions_filtra_los_procesadores_activos():
    registry = ActionRegistry()
    registry.register(FakeSAPProcessor())
    operations = {"bbb2": operacion("POST /sap/register_user")}

    assert registry.process_operations(operations, enabled_actions=["register_user"])
    assert registry.process_operations(operations, enabled_actions=["resetuser"]) == []


def test_operaciones_no_reconocidas_o_vacias_se_ignoran():
    registry = build_default_registry()

    records = registry.process_operations({
        "aaa1": operacion("GET /v3/healthcheck"),
        "bbb2": [],
    })

    assert records == []
