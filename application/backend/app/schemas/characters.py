from pydantic import BaseModel, Field


class NewCharacterBody(BaseModel):
    name: str | None = None
    gender: str | None = None


class AutofillBody(BaseModel):
    description: str
    character: dict


class RandomizeBody(BaseModel):
    character: dict


class AutoVoiceBody(BaseModel):
    gender: str
    age: str
    exclude: list[str] = []


class PreviewBody(BaseModel):
    character: dict
    emotion: str = "neutral"
    width: int = Field(default=400, ge=100, le=1200)
    height: int = Field(default=500, ge=100, le=1200)


class VoiceBody(BaseModel):
    voice_id: str
    auto: bool = True
    pitch: float = 0.0
    speed: float = 0.0


class VoiceSampleBody(BaseModel):
    voice: VoiceBody
    text: str | None = Field(default=None, max_length=300)
