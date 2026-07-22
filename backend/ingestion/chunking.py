"""Deterministic paragraph-aware chunking for parsed documents."""

import re
import uuid
from typing import Iterable, List, Optional, Tuple

from .cleaning import split_paragraphs
from .types import ChunkDraft, ParsedBlock, ParsedDocument


class SemanticChunker:
    """Creates deterministic chunks while retaining page and section metadata."""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: ParsedDocument, document_id: str) -> List[ChunkDraft]:
        blocks = document.blocks or [ParsedBlock(text=document.text)]
        drafts: List[ChunkDraft] = []
        char_cursor = 0

        for page_number, section_heading, paragraphs in self._group_paragraphs(blocks):
            for content in self._chunk_paragraphs(paragraphs):
                position = len(drafts)
                chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{position}:{content}"))
                drafts.append(
                    ChunkDraft(
                        chunk_id=chunk_id,
                        content=content,
                        position=position,
                        page_number=page_number,
                        section_heading=section_heading,
                        char_start=char_cursor,
                        char_end=char_cursor + len(content),
                    )
                )
                char_cursor += len(content) + 2
        return drafts

    def _group_paragraphs(
        self, blocks: Iterable[ParsedBlock]
    ) -> Iterable[Tuple[Optional[int], Optional[str], List[str]]]:
        current_key = None
        paragraphs: List[str] = []
        for block in blocks:
            key = (block.page_number, block.section_heading)
            block_paragraphs = split_paragraphs(block.text)
            if current_key is not None and key != current_key and paragraphs:
                yield current_key[0], current_key[1], paragraphs
                paragraphs = []
            current_key = key
            paragraphs.extend(block_paragraphs)
        if current_key is not None and paragraphs:
            yield current_key[0], current_key[1], paragraphs

    def _chunk_paragraphs(self, paragraphs: List[str]) -> Iterable[str]:
        buffer: List[str] = []
        for paragraph in paragraphs:
            for part in self._split_long_paragraph(paragraph):
                candidate = "\n\n".join(buffer + [part])
                if buffer and len(candidate) > self.chunk_size:
                    content = "\n\n".join(buffer)
                    yield content
                    overlap = self._overlap_text(content)
                    overlap_candidate = "\n\n".join([overlap, part]) if overlap else part
                    buffer = [overlap, part] if len(overlap_candidate) <= self.chunk_size else [part]
                else:
                    buffer.append(part)
        if buffer:
            yield "\n\n".join(buffer)

    def _split_long_paragraph(self, paragraph: str) -> Iterable[str]:
        remaining = paragraph
        while len(remaining) > self.chunk_size:
            boundary = remaining.rfind(" ", 0, self.chunk_size + 1)
            boundary = boundary if boundary > 0 else self.chunk_size
            yield remaining[:boundary].strip()
            remaining = remaining[boundary:].strip()
        if remaining:
            yield remaining

    def _overlap_text(self, content: str) -> str:
        if not self.chunk_overlap:
            return ""
        overlap = content[-self.chunk_overlap :]
        boundary = re.search(r"\s", overlap)
        if boundary:
            overlap = overlap[boundary.end() :]
        return overlap.strip()
