from pydantic import BaseModel, Field


class VoiceBody(BaseModel):
    voice_id: str
    auto: bool = True
    pitch: float = 0.0
    speed: float = 0.0


class CharacterChanges(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    gender: str | None = None
    age: str | None = None
    voice: VoiceBody | None = None


class VoiceSampleBody(BaseModel):
    voice: VoiceBody
    age: str | None = None
    text: str | None = Field(default=None, max_length=300)


class GenerateBody(BaseModel):
    name: str = Field(max_length=60)
    description: str = Field(max_length=2000)
    gender: str | None = None
    age: str | None = None


class ReviseBody(BaseModel):
    feedback: str = Field(max_length=2000)


class BackgroundChanges(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
