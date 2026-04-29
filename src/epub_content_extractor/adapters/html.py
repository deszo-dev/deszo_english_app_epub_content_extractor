from __future__ import annotations

from bs4 import BeautifulSoup

from epub_content_extractor.core.constants import BLOCK_TAGS, HEADING_TAGS
from epub_content_extractor.core.models import TextBlock
from epub_content_extractor.core.text import normalize_text


def html_to_blocks(html: str, chapter_index: int) -> list[TextBlock]:
    soup = BeautifulSoup(html, "lxml")
    for unwanted in soup(["script", "style", "nav", "img", "svg"]):
        unwanted.decompose()

    tags = soup.find_all([*BLOCK_TAGS, *HEADING_TAGS])
    blocks: list[TextBlock] = []
    for tag in tags:
        if tag.name in {"div", "section", "article"} and tag.find(
            [*BLOCK_TAGS, *HEADING_TAGS]
        ):
            continue
        text = normalize_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        blocks.append(
            TextBlock(
                text=text,
                tag=tag.name or "",
                position=len(blocks),
                chapter_index=chapter_index,
            )
        )

    total = max(len(blocks) - 1, 1)
    for block in blocks:
        block.position_ratio = block.position / total
    return blocks
