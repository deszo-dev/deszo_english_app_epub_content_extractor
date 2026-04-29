from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from ebooklib import ITEM_DOCUMENT, epub

from epub_content_extractor.exceptions import EpubReadError, InputValidationError

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib.epub")


@dataclass(frozen=True, slots=True)
class HtmlDocument:
    html: str
    chapter_index: int


def read_epub_documents(epub_path: str | Path) -> list[HtmlDocument]:
    path = Path(epub_path)
    validate_epub_path(path)
    try:
        book = epub.read_epub(str(path), options={"ignore_ncx": True})
    except Exception as exc:
        raise EpubReadError(f"cannot read EPUB: {path}") from exc

    documents: list[HtmlDocument] = []
    document_items = [
        item for item in book.get_items() if item.get_type() == ITEM_DOCUMENT
    ]
    for chapter_index, item in enumerate(document_items):
        html = item.get_content().decode("utf-8", errors="replace")
        if is_gutenberg_boilerplate_document(html):
            continue
        documents.append(HtmlDocument(html=html, chapter_index=chapter_index))
    return documents


def validate_epub_path(path: Path) -> None:
    if not path.exists():
        raise InputValidationError(f"input file does not exist: {path}")
    if not path.is_file():
        raise InputValidationError(f"input path is not a file: {path}")
    if path.suffix.lower() != ".epub":
        raise InputValidationError(f"input file must have .epub suffix: {path}")


def is_gutenberg_boilerplate_document(html: str) -> bool:
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True).lower()
    if not text:
        return True
    if (
        text.startswith("the project gutenberg ebook")
        and "start of the project gutenberg ebook" in text
    ):
        return True
    if text.startswith("*** end of the project gutenberg ebook"):
        return True
    return (
        "full project gutenberg" in text
        and "license" in text
        and "electronic works" in text
    )
