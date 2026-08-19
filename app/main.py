from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.strength import analyze

app = FastAPI(
    title="Password Strength API",
    description="Scores password strength. Input is never logged or stored.",
    version="0.1.0",
)


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@app.get("/health")
def health():
    """Liveness probe used by the container and the pipeline."""
    return {"status": "ok"}


@app.post("/analyze")
def analyze_password(request: PasswordRequest):
    """Score a password. The response deliberately omits the input value."""
    return analyze(request.password)