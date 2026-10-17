from pydantic import BaseModel


class ProjectCreateBody(BaseModel):
    title: str | None = None


class SettingsChanges(BaseModel):
    aspect: str | None = None
    music: bool | None = None
    quality: str | None = None


class ProjectChanges(BaseModel):
    title: str | None = None
    script: str | None = None
    settings: SettingsChanges | None = None


class CastBody(BaseModel):
    library_id: str


class CastBackgroundBody(BaseModel):
    library_id: str | None = None


class ScriptGenerateBody(BaseModel):
    idea: str
    length: str = "short"
    use_library: bool = True
