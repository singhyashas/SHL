from __future__ import annotations

from fastapi import FastAPI

from app.agent import respond
from app.schemas import ChatRequest, ChatResponse, HealthResponse


app = FastAPI(title="Conversational SHL Assessment Recommender")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return respond(request)
