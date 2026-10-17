from pydantic import BaseModel


class ScriptBody(BaseModel):
    script: str
