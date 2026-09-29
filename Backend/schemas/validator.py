import jsonschema

def validate_schema(data: dict, schema: dict) -> None:
    """
    Valida un dizionario dati contro un contratto JSON Schema.
    Solleva jsonschema.exceptions.ValidationError se il payload non è conforme.
    """
    jsonschema.validate(instance=data, schema=schema)