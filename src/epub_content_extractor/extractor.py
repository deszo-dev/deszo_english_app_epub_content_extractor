from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
import unicodedata
import warnings

from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
from ebooklib import ITEM_DOCUMENT
from ebooklib import epub
import ftfy
import regex
from rapidfuzz import fuzz

from .models import BlockDebugInfo, Chapter, ExtractedDocument

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib.epub")

BLOCK_TAGS = ["p", "div", "section", "article", "li", "blockquote"]
HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
DIALOGUE_MARKERS = ["-", '"', "'", "—", "“", "‘"]
MIN_CHARS = 25
MIN_ALPHA_RATIO = 0.6
MAX_DIGIT_RATIO = 0.3
KEEP_SCORE = 0.3
DROP_SCORE = 0.0

BOILERPLATE = [
    "all rights reserved",
    "copyright",
    "isbn",
    "published by",
    "project gutenberg",
    "table of contents",
]

REFERENCE_WORDS = {"equation", "figure", "fig", "table", "appendix", "example"}


@dataclass(slots=True)
class TextBlock:
    text: str
    tag: str
    position: int
    chapter_index: int
    position_ratio: float = 0.0


@dataclass(slots=True)
class BlockFeatures:
    length_chars: int
    length_words: int
    avg_word_length: float
    punctuation_ratio: float
    alpha_ratio: float
    digit_ratio: float
    sentence_count: int
    is_uppercase: bool
    has_dialogue_markers: bool
    starts_with_number: bool
    ends_with_punctuation: bool
    repetition_score: float
    footnote_lines_ratio: float


def extract_text(epub_path: str | Path, *, debug_dir: str | Path | None = None) -> str:
    document = extract_epub(epub_path, debug_dir=debug_dir)
    return document.to_text()


def extract_epub(epub_path: str | Path, *, debug_dir: str | Path | None = None) -> ExtractedDocument:
    book = epub.read_epub(str(epub_path), options={"ignore_ncx": True})
    chapters: list[Chapter] = []
    debug_blocks: list[BlockDebugInfo] = []
    seen_texts: list[str] = []

    document_items = [item for item in book.get_items() if item.get_type() == ITEM_DOCUMENT]

    for chapter_index, item in enumerate(document_items):
        html = item.get_content().decode("utf-8", errors="replace")
        if _is_gutenberg_boilerplate_document(html):
            continue
        blocks = _html_to_blocks(html, chapter_index)
        footnote_index = _build_footnote_index(blocks)
        scored_blocks = _score_blocks(blocks, seen_texts, footnote_index)
        kept_blocks = _apply_context(scored_blocks)

        paragraphs: list[str] = []
        for block, features, score, keep, reasons in kept_blocks:
            text = _remove_inline_footnote_markers(block.text, footnote_index, blocks)
            text = _remove_residual_noise(text)
            text = _normalize_text(text)
            if keep and text:
                paragraphs.append(text)

            debug_blocks.append(
                BlockDebugInfo(
                    chapter_index=block.chapter_index,
                    position=block.position,
                    tag=block.tag,
                    text=block.text,
                    score=round(score, 4),
                    keep=keep,
                    reasons=reasons,
                    features=asdict(features),
                )
            )

        paragraphs = _merge_fragments(paragraphs)
        if paragraphs:
            chapters.append(Chapter(title="", paragraphs=paragraphs))

        seen_texts.extend(block.text for block, *_ in kept_blocks)

    document = ExtractedDocument(chapters=chapters, debug_blocks=debug_blocks)
    if debug_dir is not None:
        _write_debug(debug_dir, document)
    return document


def _html_to_blocks(html: str, chapter_index: int) -> list[TextBlock]:
    soup = BeautifulSoup(html, "lxml")
    for unwanted in soup(["script", "style", "nav", "img", "svg"]):
        unwanted.decompose()

    tags = soup.find_all(BLOCK_TAGS + HEADING_TAGS)
    blocks: list[TextBlock] = []
    for tag in tags:
        if tag.name in {"div", "section", "article"} and tag.find(BLOCK_TAGS + HEADING_TAGS):
            continue
        text = tag.get_text(" ", strip=True)
        text = _normalize_text(text)
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


def _extract_features(block: TextBlock, seen_texts: list[str]) -> BlockFeatures:
    text = block.text
    chars = len(text)
    words = regex.findall(r"\p{L}+(?:['-]\p{L}+)?", text)
    letters = sum(1 for char in text if char.isalpha())
    digits = sum(1 for char in text if char.isdigit())
    punctuation = sum(1 for char in text if unicodedata.category(char).startswith("P"))
    sentence_count = len(re.findall(r"[.!?]+(?:\s|$)", text))
    repetition_score = _repetition_score(text, seen_texts)
    footnote_lines_ratio = _footnote_lines_ratio(text)

    return BlockFeatures(
        length_chars=chars,
        length_words=len(words),
        avg_word_length=(sum(len(word) for word in words) / len(words)) if words else 0.0,
        punctuation_ratio=punctuation / chars if chars else 0.0,
        alpha_ratio=letters / chars if chars else 0.0,
        digit_ratio=digits / chars if chars else 0.0,
        sentence_count=sentence_count,
        is_uppercase=_is_uppercase_text(text),
        has_dialogue_markers=any(marker in text for marker in DIALOGUE_MARKERS),
        starts_with_number=bool(re.match(r"^\s*\(?\d+", text)),
        ends_with_punctuation=bool(re.search(r"[.!?;:,'\")\]]$", text)),
        repetition_score=repetition_score,
        footnote_lines_ratio=footnote_lines_ratio,
    )


def _score_blocks(
    blocks: list[TextBlock],
    seen_texts: list[str],
    footnote_index: dict[str, str],
) -> list[tuple[TextBlock, BlockFeatures, float, bool, list[str]]]:
    scored = []
    for block in blocks:
        features = _extract_features(block, seen_texts)
        penalty = 0.0
        boost = 0.0
        reasons: list[str] = []
        hard_drop = False
        lower_text = block.text.lower()

        if block.tag in HEADING_TAGS:
            penalty += 1.0
            hard_drop = True
            reasons.append("heading_removed")
        if features.length_chars < MIN_CHARS:
            penalty += 0.5
            reasons.append("short_block")
        if features.has_dialogue_markers:
            boost += 0.4
            reasons.append("dialogue_preserved")
        if features.alpha_ratio < MIN_ALPHA_RATIO:
            penalty += 0.7
            reasons.append("low_alpha_ratio")
        if features.digit_ratio > MAX_DIGIT_RATIO:
            penalty += 0.6
            reasons.append("digit_heavy")
        if features.repetition_score > 0.9:
            penalty += 1.0
            reasons.append("repeated_block")
        if _looks_like_toc(block.text):
            penalty += 1.0
            hard_drop = True
            reasons.append("toc_like")
        if features.sentence_count == 0:
            penalty += 0.5
            reasons.append("no_sentence_punctuation")
        if features.length_chars > 80:
            boost += 0.3
            reasons.append("long_text_block")
        if features.is_uppercase and features.length_chars < 80:
            penalty += 0.6
            reasons.append("short_uppercase")
        if block.chapter_index == 0 and block.position < 10:
            penalty += 0.3
            reasons.append("front_matter_position")
        if any(pattern in lower_text for pattern in BOILERPLATE):
            penalty += 1.0
            hard_drop = True
            reasons.append("boilerplate")
        if _is_chapter_heading(block.text):
            penalty += 1.0
            hard_drop = True
            reasons.append("chapter_heading_removed")
        if _is_footnote_block(block, features):
            penalty += 1.2
            hard_drop = True
            reasons.append("footnote_block")
        if footnote_index and _is_probable_footnote_block(block.text):
            penalty += 0.8
            hard_drop = True
            reasons.append("indexed_footnote_block")

        score = 1.0 - penalty + boost
        keep = score >= DROP_SCORE and not hard_drop
        scored.append((block, features, score, keep, reasons))
    return scored


def _apply_context(
    scored_blocks: list[tuple[TextBlock, BlockFeatures, float, bool, list[str]]],
) -> list[tuple[TextBlock, BlockFeatures, float, bool, list[str]]]:
    result = []
    scores = [item[2] for item in scored_blocks]
    for index, item in enumerate(scored_blocks):
        block, features, score, keep, reasons = item
        if score < DROP_SCORE:
            start = max(0, index - 2)
            end = min(len(scored_blocks), index + 3)
            neighbor_scores = scores[start:index] + scores[index + 1 : end]
            if neighbor_scores and sum(neighbor_scores) / len(neighbor_scores) >= KEEP_SCORE:
                keep = True
                reasons = [*reasons, "kept_by_neighbors"]
        result.append((block, features, score, keep, reasons))
    return _drop_weak_sections(result)


def _drop_weak_sections(
    scored_blocks: list[tuple[TextBlock, BlockFeatures, float, bool, list[str]]],
) -> list[tuple[TextBlock, BlockFeatures, float, bool, list[str]]]:
    result = []
    weak_run = 0
    for block, features, score, keep, reasons in scored_blocks:
        if score < DROP_SCORE:
            weak_run += 1
        else:
            weak_run = 0
        if weak_run >= 5:
            keep = False
            reasons = [*reasons, "weak_section"]
        result.append((block, features, score, keep, reasons))
    return result


def _build_footnote_index(blocks: list[TextBlock]) -> dict[str, str]:
    footnotes: dict[str, str] = {}
    for block in blocks:
        if block.position_ratio < 0.65:
            continue
        for bracket_id, dotted_id, note_text in re.findall(
            r"(?:^|\n)\s*(?:\[(\d+)\]|(\d+)\.)\s+(.+)",
            block.text,
        ):
            marker_id = bracket_id or dotted_id
            if marker_id:
                footnotes[marker_id] = note_text.strip()
    return footnotes


def _remove_inline_footnote_markers(
    text: str,
    footnote_index: dict[str, str],
    chapter_blocks: list[TextBlock],
) -> str:
    marker_count = sum(len(re.findall(r"\[\d+\]|\(\d+\)", block.text)) for block in chapter_blocks)

    def bracket_replacer(match: re.Match[str]) -> str:
        marker_id = match.group(1)
        if marker_id in footnote_index:
            return ""
        confidence = _inline_marker_confidence(text, match, bool(footnote_index), marker_count, bracket=True)
        return "" if confidence > 0.6 else match.group(0)

    def paren_replacer(match: re.Match[str]) -> str:
        marker_id = match.group(1)
        if marker_id in footnote_index:
            confidence = _inline_marker_confidence(text, match, True, marker_count, bracket=False)
            return "" if confidence > 0.6 else match.group(0)
        confidence = _inline_marker_confidence(text, match, bool(footnote_index), marker_count, bracket=False)
        return "" if confidence > 0.8 else match.group(0)

    text = re.sub(r"\[(\d+)\]", bracket_replacer, text)
    text = re.sub(r"\((\d+)\)", paren_replacer, text)
    return _normalize_text(text)


def _inline_marker_confidence(
    text: str,
    match: re.Match[str],
    chapter_has_footnotes: bool,
    marker_count: int,
    *,
    bracket: bool,
) -> float:
    confidence = 0.0
    if chapter_has_footnotes:
        confidence += 0.5
    if marker_count > 3:
        confidence += 0.3
    if bracket:
        confidence += 0.2

    start, end = match.span()
    before = text[max(0, start - 24) : start]
    after = text[end : min(len(text), end + 24)]
    context = f"{before} {after}".lower()

    if re.search(r"\w\s*$", before) or re.match(r"^[.,;:]?", after):
        confidence += 0.3
    if re.match(r"^\s*\(\d+\)\s+[A-Z]", text[start:]):
        confidence -= 0.7
    if any(word in context for word in REFERENCE_WORDS):
        confidence -= 0.5
    return confidence


def _normalize_text(text: str) -> str:
    text = ftfy.fix_text(text)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\xa0", " ")
    text = regex.sub(r"[ \t]+", " ", text)
    text = regex.sub(r"\s+([,.;:!?])", r"\1", text)
    text = regex.sub(r"([\(\[\{])\s+", r"\1", text)
    text = regex.sub(r"\s+([\)\]\}])", r"\1", text)
    text = regex.sub(r"\s+\n", "\n", text)
    text = regex.sub(r"\n\s+", "\n", text)
    return text.strip()


def _merge_fragments(paragraphs: list[str]) -> list[str]:
    merged: list[str] = []
    for paragraph in paragraphs:
        if not merged:
            merged.append(paragraph)
            continue
        previous = merged[-1]
        if not re.search(r"[.!?\"')\]]$", previous) and paragraph[:1].islower():
            merged[-1] = f"{previous} {paragraph}"
        else:
            merged.append(paragraph)
    return merged


def _remove_residual_noise(text: str) -> str:
    if re.fullmatch(r"page\s+\d+", text, flags=re.IGNORECASE):
        return ""
    if re.fullmatch(r"[\-*_\s]{3,}", text):
        return ""
    return text


def _is_gutenberg_boilerplate_document(html: str) -> bool:
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True).lower()
    if not text:
        return True
    if text.startswith("the project gutenberg ebook") and "start of the project gutenberg ebook" in text:
        return True
    if text.startswith("*** end of the project gutenberg ebook"):
        return True
    if "full project gutenberg" in text and "license" in text and "electronic works" in text:
        return True
    return False


def _looks_like_toc(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text.strip()]
    matches = 0
    for line in lines:
        if re.search(r"\.{3,}", line):
            matches += 1
        elif re.search(r"\b(chapter|part)\s+\d+", line, flags=re.IGNORECASE):
            matches += 1
    return len(lines) >= 3 and matches / len(lines) > 0.5


def _is_chapter_heading(text: str) -> bool:
    return bool(re.fullmatch(r"\s*(chapter|part)\s+([ivxlcdm]+|\d+)\s*[:.\-]?\s*", text, flags=re.IGNORECASE))


def _is_uppercase_text(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and sum(char.isupper() for char in letters) / len(letters) > 0.8


def _repetition_score(text: str, seen_texts: list[str]) -> float:
    if not seen_texts:
        return 0.0
    normalized = text.lower().strip()
    candidates = [candidate for candidate in seen_texts if abs(len(candidate) - len(text)) <= max(20, len(text) * 0.4)]
    if not candidates:
        return 0.0
    return max(fuzz.ratio(normalized, candidate.lower().strip()) / 100 for candidate in candidates[-200:])


def _footnote_lines_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text.strip()]
    matches = sum(1 for line in lines if re.match(r"^(\[\d+\]|\d+\.)\s+\S+", line))
    return matches / len(lines) if lines else 0.0


def _is_footnote_block(block: TextBlock, features: BlockFeatures) -> bool:
    if block.position_ratio < 0.8:
        return False
    if features.footnote_lines_ratio > 0.5:
        return True
    return _is_probable_footnote_block(block.text)


def _is_probable_footnote_block(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return bool(re.match(r"^(\[\d+\]|\d+\.)\s+\S+", text))
    ids = []
    for line in lines:
        match = re.match(r"^(?:\[(\d+)\]|(\d+)\.)\s+\S+", line)
        if match:
            ids.append(int(match.group(1) or match.group(2)))
    return len(ids) >= 2 and ids == list(range(ids[0], ids[0] + len(ids)))


def _write_debug(debug_dir: str | Path, document: ExtractedDocument) -> None:
    path = Path(debug_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "blocks.json").write_text(
        json.dumps(document.debug_as_dicts(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
