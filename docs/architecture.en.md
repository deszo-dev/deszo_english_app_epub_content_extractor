# EPUB Content Extractor Architecture

## Goal

`epub_content_extractor` converts an `.epub` file into clean, linear text.

Input:

- `.epub` file

Output:

- clean linear text
- preserved paragraph structure
- preserved chapter order
- minimal non-content noise

The most important requirement is to preserve the semantic structure of the text while removing everything unnecessary for downstream NLP processing.

## Functional Requirements

### 1. Read EPUB As A Structure

Use:

- `ebooklib`

Requirements:

- extract only `DOCUMENT` items, usually chapters
- ignore navigation files
- ignore styles
- ignore images

### 2. Extract Text From HTML

EPUB content is HTML, so it must be parsed instead of stripped with plain regular expressions.

Use:

- `BeautifulSoup`
- optionally `lxml`

Requirements:

- remove HTML tags
- correctly handle `p`, `h1`-`h6`, and `br`
- preserve paragraphs
- preserve the basic text structure

Mistakes that must be avoided:

- joining sentences without spaces
- losing punctuation

### 3. Remove Noise

Noise removal is the most critical part for NLP quality.

Remove metadata:

- copyright notices
- ISBN values
- publisher information

Remove navigation:

- Table of Contents
- chapter lists

Remove artifacts:

- `Page 12`
- `Chapter 1`, when it is only boilerplate
- duplicated headers

Remove footnotes:

- footnote blocks, aggressively, especially near the end of a chapter
- inline markers such as `[1]` and `(1)`, cautiously and only with high confidence

Production footnote strategy:

1. End-of-chapter footnote blocks

Typical shapes:

```text
[1] Some explanation text...
[2] Another note...
1. Some explanation
2. Another explanation
```

Drop a block when several signals match:

- `footnote_lines_ratio > 0.5`
- sequential markers such as `[1]`, `[2]`, `[3]` or `1.`, `2.`, `3.`
- block position is after 80% of the chapter

2. Inline markers

Do not remove all markers with a blind regular expression:

```python
re.sub(r"\[\d+\]|\(\d+\)", "", text)
```

This breaks valid text such as:

- `see Figure (1)`
- `Option (1) is correct`

Recommended strategy:

- detect footnote blocks first
- build `footnote_index: marker_id -> note_text`
- remove inline `[1]` markers only when the marker id exists in `footnote_index`
- apply stricter heuristics for `(1)`

Inline confidence:

- `chapter_has_footnotes` adds `0.5`
- `count_inline_markers > 3` adds `0.3`
- marker appears after a word or near sentence punctuation adds `0.3`
- enumeration such as `(1) First step` subtracts `0.7`
- nearby words such as `equation`, `figure`, or `table` subtract `0.5`

Final decision:

```python
if confidence > 0.6:
    remove_marker()
else:
    keep()
```

Key principle: do not remove inline markers blindly. Link them to structural footnote blocks first, then use fallback scoring.

### 4. Semantic Segmentation

Preserve:

- paragraph boundaries
- logical text blocks

Do not break:

- sentences
- dialogue
- quotation marks

### 5. Text Normalization

Required steps:

- Unicode normalization with NFC
- replace `\xa0` with a regular space
- collapse multiple spaces into one
- remove excessive line breaks

### 6. Linear Text Assembly

Requirements:

- merge chapters in the correct order
- insert `\n\n` between paragraphs
- insert `\n\n\n` between chapters

This helps downstream NLP preserve the source structure.

### 7. Quality Guarantees

The extractor should provide:

- no glued words
- no truncated sentences
- minimal noise
- human-readable text

## Recommended Libraries

- `ebooklib` for EPUB structure
- `BeautifulSoup` for HTML parsing
- `lxml` for faster and more accurate parsing
- `regex` for complex cleanup patterns
- `ftfy` for fixing broken text
- `rapidfuzz` for fuzzy duplicate detection
- `readability-lxml` for unusually noisy EPUB files

## Minimal API

```python
class ExtractedDocument:
    chapters: list[Chapter]


class Chapter:
    title: str
    paragraphs: list[str]
```

## Core Model

Filtering is not a single-rule deletion process. It should be based on scoring and text block classification.

```text
Raw HTML -> Blocks -> Feature Extraction -> Scoring -> Classification -> Clean Text
```

This is the key difference from a naive extractor.

## Step 1. Decompose HTML Into Blocks

After parsing HTML with `BeautifulSoup`, extract text blocks from:

```python
BLOCK_TAGS = ["p", "div", "section", "article", "li", "blockquote"]
```

Each block should carry text and position metadata:

```python
class TextBlock:
    text: str
    tag: str
    position: int
    chapter_index: int
```

## Step 2. Feature Extraction

Calculate features for every block:

```python
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
```

## Step 3. Production-Grade Rules

### Length-Based Filtering

```python
if features.length_chars < 25:
    penalty += 0.5
```

But dialogue should be protected:

```python
if features.has_dialogue_markers:
    penalty -= 0.4
```

### Alphabet Ratio

Alphabet ratio is a strong signal:

```python
alpha_ratio = letters / total_chars

if alpha_ratio < 0.6:
    penalty += 0.7
```

This helps remove:

- garbage
- symbol-heavy blocks
- navigation fragments

### Digit-Heavy Blocks

```python
if features.digit_ratio > 0.3:
    penalty += 0.6
```

This helps remove:

- ISBN data
- page numbers
- list-like noise

### Repetition Detection

```python
if block.text in seen_blocks:
    penalty += 1.0
```

Or fuzzy matching:

```python
if similarity > 0.9:
    penalty += 1.0
```

This helps remove:

- headers
- footers
- repeated boilerplate

### Table Of Contents Detection

Important patterns:

```python
r"(chapter|part)\s+\d+"
r"\.{3,}"
```

If many lines match these patterns, the block or section should be marked as a table of contents.

### Sentence Structure Check

```python
if features.sentence_count == 0:
    penalty += 0.5
```

But long blocks without obvious punctuation may still be meaningful:

```python
if features.length_chars > 80:
    penalty -= 0.3
```

### Dialogue Preservation

```python
DIALOGUE_MARKERS = ["-", "\"", "'", "—"]

if any(marker in text for marker in DIALOGUE_MARKERS):
    boost += 0.4
```

### Uppercase Detection

```python
if features.is_uppercase and features.length_chars < 80:
    penalty += 0.6
```

This helps remove:

- short headings
- metadata labels

### Positional Heuristics

The beginning of an EPUB often contains front matter and noise:

```python
if chapter_index == 0 and position < 10:
    penalty += 0.7
```

### Boilerplate Patterns

```python
BOILERPLATE = [
    "all rights reserved",
    "copyright",
    "isbn",
    "published by",
]

if any(pattern in text.lower() for pattern in BOILERPLATE):
    penalty += 1.0
```

### Footnote Handling

Footnote blocks:

```python
if block.position_ratio > 0.8 and footnote_lines_ratio > 0.5:
    penalty += 1.0
```

Inline markers:

```python
if marker_id in chapter_footnote_index:
    remove_marker
elif confidence > 0.6:
    remove_marker
else:
    keep_marker
```

## Step 4. Scoring

```python
score = base_score - penalty + boost
```

Example:

```python
if score < 0:
    drop_block
elif score < 0.3:
    maybe_keep
else:
    keep
```

## Step 5. Contextual Filtering

### Neighbor Validation

If a weak block is surrounded by strong content blocks, keep it.

### Density Clustering

Use a window of nearby blocks:

```python
window = 5
```

If the average score inside the window is high, keep all blocks in that window.

### Section Detection

If many weak blocks appear consecutively, skip the whole section.

## Step 6. Post-Processing

After filtering:

1. Merge fragments when a paragraph does not end with sentence punctuation.
2. Remove residual lines such as `Page 12` or `***`.
3. Normalize spaces and Unicode.

Example:

```python
paragraphs = merge_if_no_sentence_end()
```

## Recommended Production Thresholds

```python
MIN_CHARS = 25
MIN_ALPHA_RATIO = 0.6
MAX_DIGIT_RATIO = 0.3
REPETITION_THRESHOLD = 0.9

KEEP_SCORE = 0.3
DROP_SCORE = 0.0
```
