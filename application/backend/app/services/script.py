from engine.script.parser import parse_script


def validate_script(script: str) -> dict:
    return parse_script(script).to_dict()
