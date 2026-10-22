
from fastapi import FastAPI

app = FastAPI(
    title="Indie Project Management Platform",
    description="A lightweight project management API for indie game developers.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
