"""app/api/schemas.py — Pydantic request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- auth -----------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=4, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# --- chat -----------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None


class RagasScore(BaseModel):
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0


class QueryResponse(BaseModel):
    response: str = ""
    citations: list = []
    chunks: list = []
    pdf_name: str = ""
    pdf_path: str = ""
    page_numbers: list[int] = []
    recommendation_questions: list[str] = []
    ragas_score: RagasScore = RagasScore()
    conversation_id: str = ""
    language: str = ""
    response_time: float = 0.0
    token_usage: dict = {}
    message_id: int | None = None


# --- conversations --------------------------------------------------------
class RenameRequest(BaseModel):
    title: str


# --- feedback -------------------------------------------------------------
class FeedbackRequest(BaseModel):
    message_id: int
    rating: str  # "up" | "down"
    comment: str = ""
