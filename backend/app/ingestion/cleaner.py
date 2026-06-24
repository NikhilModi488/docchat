"""
app/ingestion/cleaner.py
========================
Text cleaning / normalisation layer (pure string ops, no I/O).

Cleaner text means better embeddings and better retrieval: unicode
normalisation, hyphen-linebreak rejoining, control-char stripping, and
whitespace collapsing.
"""

from __future__ import annotations

import re
import unicodedata

from langchain_core.documents import Document


class TextCleaner:
    _MULTISPACE = re.compile(r"[ \t]+")
    _MULTINEWLINE = re.compile(r"\n{3,}")
    _HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")
    _CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    def clean_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = self._HYPHEN_LINEBREAK.sub(r"\1\2", text)
        text = self._CONTROL_CHARS.sub("", text)
        text = self._MULTISPACE.sub(" ", text)
        text = self._MULTINEWLINE.sub("\n\n", text)
        return text.strip()

    def clean_documents(self, docs: list[Document]) -> list[Document]:
        cleaned: list[Document] = []
        for doc in docs:
            text = self.clean_text(doc.page_content)
            if text:
                doc.page_content = text
                cleaned.append(doc)
        return cleaned
