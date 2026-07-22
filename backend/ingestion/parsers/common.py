"""Shared block construction for text-oriented parsers."""

import re
from typing import List

from ..cleaning import clean_text, split_paragraphs
from ..types import ParsedBlock, ParsedDocument


def plain_text_document(text: str) -> ParsedDocument:
    cleaned = clean_text(text)
    return ParsedDocument(text=cleaned, blocks=[ParsedBlock(text=paragraph) for paragraph in split_paragraphs(cleaned)])


def markdown_document(text: str) -> ParsedDocument:
    cleaned = clean_text(text)
    blocks: List[ParsedBlock] = []
    heading = None
    paragraph_lines: List[str] = []
    for line in cleaned.split("\n") + [""]:
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            if paragraph_lines:
                blocks.append(ParsedBlock(text="\n".join(paragraph_lines), section_heading=heading))
                paragraph_lines = []
            heading = match.group(1)
        elif line.strip():
            paragraph_lines.append(line)
        elif paragraph_lines:
            blocks.append(ParsedBlock(text="\n".join(paragraph_lines), section_heading=heading))
            paragraph_lines = []
    return ParsedDocument(text=cleaned, blocks=blocks)
