"""
app/rag/smalltalk.py
====================
Lightweight greeting / chit-chat layer.

Before running the (expensive) retrieval pipeline, we check whether the user's
message is simple small-talk — a greeting, "how are you", thanks, goodbye, an
identity question, or "who developed you". If so we answer conversationally and
skip retrieval entirely (no citations, no RAGAS, instant response).

Detection is intentionally conservative: short messages match greeting/thanks/
bye patterns, while identity & developer questions match anywhere (they're clear
intents). This avoids hijacking real document questions that merely contain a
word like "hi" or "thanks".
"""

from __future__ import annotations

import re

DEVELOPER_NAME = "Nikhil Modi"

# --- intent patterns ------------------------------------------------------
_DEVELOPER = re.compile(
    r"\b(who|whom)\b.*\b(develop|developed|made|create|created|built|build|design|designed|"
    r"trained|program|programmed|wrote|write)\b.*\byou\b"
    r"|\byour\s+(developer|creator|author|maker|inventor|builder)\b"
    r"|who('?s| is)\s+(behind|your\s+(maker|creator|developer))\b",
    re.IGNORECASE,
)
_IDENTITY = re.compile(
    r"\b(who\s+are\s+you|what\s+are\s+you|what('?s| is)\s+your\s+name|"
    r"what\s+can\s+you\s+do|what\s+do\s+you\s+do|tell\s+me\s+about\s+yourself|"
    r"how\s+do\s+you\s+work)\b",
    re.IGNORECASE,
)
_GREETING = re.compile(
    r"^(hi|hii+|hey+|heya|hello+|hiya|yo|sup|wassup|howdy|greetings|"
    r"good\s+(morning|afternoon|evening|day)|namaste|hola)\b",
    re.IGNORECASE,
)
_HOWAREYOU = re.compile(
    r"\b(how\s+(are|r)\s+(you|u)|how('?s| is)\s+it\s+going|how\s+are\s+you\s+doing|"
    r"how\s+do\s+you\s+do|what('?s| is)\s+up|how\s+have\s+you\s+been)\b",
    re.IGNORECASE,
)
_THANKS = re.compile(r"\b(thanks|thank\s+you|thank\s+u|thx|thnx|appreciate\s+it|much\s+appreciated)\b", re.IGNORECASE)
_BYE = re.compile(r"\b(bye+|goodbye|good\s+bye|see\s+(you|ya)|see\s+u|cya|take\s+care|farewell)\b", re.IGNORECASE)

# Responses (Markdown). Picked deterministically by category.
_RESPONSES = {
    "developer": f"I was developed by **{DEVELOPER_NAME}**. 👨‍💻",
    "identity": (
        "I'm **DocChat**, your local document assistant. Upload PDFs, Word, "
        "PowerPoint, Markdown or text files and I'll answer your questions "
        "grounded in them — complete with citations and source previews. "
        "Everything runs locally and privately on your machine.\n\n"
        "Ask me anything about your uploaded documents to get started!"
    ),
    "greeting": "Hello! 👋 I'm **DocChat**. How can I help you with your documents today?",
    "howareyou": (
        "I'm doing great, thanks for asking! 😊 I'm ready to help you find "
        "answers in your documents. What would you like to know?"
    ),
    "thanks": "You're very welcome! 🙌 Happy to help — feel free to ask me anything else about your documents.",
    "bye": "Goodbye! 👋 Come back anytime you need answers from your documents. Take care!",
}


def detect(text: str) -> str | None:
    """Return a small-talk category if the message is chit-chat, else None."""
    if not text:
        return None
    msg = text.strip()
    words = re.findall(r"[a-zA-Z']+", msg)
    short = len(words) <= 6

    # Intent questions — match anywhere, any length.
    if _DEVELOPER.search(msg):
        return "developer"
    if _IDENTITY.search(msg):
        return "identity"

    # Social phrases — only for short messages to avoid false positives.
    if short:
        if _HOWAREYOU.search(msg):
            return "howareyou"
        if _GREETING.search(msg):
            return "greeting"
        if _BYE.search(msg):
            return "bye"
        if _THANKS.search(msg):
            return "thanks"
    return None


def response(category: str) -> str:
    return _RESPONSES.get(category, _RESPONSES["greeting"])
