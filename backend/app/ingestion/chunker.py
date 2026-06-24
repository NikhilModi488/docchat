"""
app/ingestion/chunker.py
========================
Chunking layer.

Default strategy is **page-wise chunking with overlap** (`RAG_CHUNK_STRATEGY=page`):
each page becomes one chunk, and a sliding window of the previous page's tail is
prepended so context that straddles a page boundary is not lost. Pages longer
than `max_page_chars` are sub-split (with overlap) so the embedder doesn't
silently truncate them. This keeps every chunk anchored to a real page number,
which makes citations and the in-app PDF page viewer exact.

Set `RAG_CHUNK_STRATEGY=recursive` to fall back to classic size-based
RecursiveCharacterTextSplitter chunking.

Every chunk carries `source`, `page_number`, a deterministic `chunk_id`
(`filename::p{page}::c{index}`), and a short `preview`.
"""

from __future__ import annotations

from collections import OrderedDict

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        strategy: str | None = None,
        max_page_chars: int | None = None,
    ) -> None:
        cfg = settings.ingestion
        self.chunk_size = chunk_size or cfg.chunk_size
        self.chunk_overlap = chunk_overlap or cfg.chunk_overlap
        self.strategy = (strategy or cfg.chunk_strategy).lower()
        self.max_page_chars = max_page_chars or cfg.max_page_chars
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=list(cfg.separators),
            length_function=len,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def chunk(self, docs: list[Document]) -> list[Document]:
        if self.strategy == "recursive":
            chunks = self._chunk_recursive(docs)
        else:
            chunks = self._chunk_pagewise(docs)
        logger.info(
            "Chunked %d page(s) into %d chunks (strategy=%s, overlap=%d, max_page=%d)",
            len(docs), len(chunks), self.strategy, self.chunk_overlap, self.max_page_chars,
        )
        return chunks

    # ------------------------------------------------------------------ #
    # Page-wise strategy (default)
    # ------------------------------------------------------------------ #
    def _chunk_pagewise(self, docs: list[Document]) -> list[Document]:
        # Group page-Documents by source, preserving order.
        by_source: "OrderedDict[str, list[Document]]" = OrderedDict()
        for d in docs:
            by_source.setdefault(d.metadata.get("source", "unknown"), []).append(d)

        out: list[Document] = []
        for source, pages in by_source.items():
            # Sort by page number so cross-page overlap uses the true predecessor.
            pages = sorted(pages, key=lambda d: int(d.metadata.get("page_number", 0)))
            for idx, page in enumerate(pages):
                text = page.page_content
                page_no = int(page.metadata.get("page_number", idx + 1))
                counter = 0  # index resets per page: p{n}::c0, c1, … for sub-splits

                # Cross-page overlap: prepend a SMALL tail of the previous page for
                # context continuity across the boundary. Cap it to a quarter of the
                # previous page so a short page is never swallowed whole — otherwise
                # adjacent page-chunks become near-duplicates and a chunk's leading
                # text (and preview) belongs to the wrong page.
                prepend = ""
                if self.chunk_overlap > 0 and idx > 0:
                    prev = pages[idx - 1].page_content
                    cap = min(self.chunk_overlap, len(prev) // 4)
                    prev_tail = prev[-cap:] if cap > 0 else ""
                    if prev_tail:
                        prepend = f"{prev_tail}\n"
                text = f"{prepend}{text}"

                # Sub-split only if the (overlapped) page is too large to embed cleanly.
                pieces = (
                    self._splitter.split_text(text)
                    if len(text) > self.max_page_chars
                    else [text]
                )

                for piece in pieces:
                    if not piece.strip():
                        continue
                    meta = dict(page.metadata)
                    meta["chunk_id"] = f"{source}::p{page_no}::c{counter}"
                    # Preview reflects the chunk's OWN page: drop the prepended
                    # previous-page tail from the first sub-piece.
                    own = piece[len(prepend):] if counter == 0 and prepend else piece
                    meta["preview"] = own[:120].replace("\n", " ").strip()
                    out.append(Document(page_content=piece, metadata=meta))
                    counter += 1
        return out

    # ------------------------------------------------------------------ #
    # Recursive strategy (opt-in)
    # ------------------------------------------------------------------ #
    def _chunk_recursive(self, docs: list[Document]) -> list[Document]:
        chunks = self._splitter.split_documents(docs)
        counters: dict[str, int] = {}
        for chunk in chunks:
            source = chunk.metadata.get("source", "unknown")
            page = chunk.metadata.get("page_number", 0)
            idx = counters.get(source, 0)
            counters[source] = idx + 1
            chunk.metadata["chunk_id"] = f"{source}::p{page}::c{idx}"
            chunk.metadata["preview"] = chunk.page_content[:120].replace("\n", " ")
        return chunks
