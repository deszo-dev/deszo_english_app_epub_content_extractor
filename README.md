# EPUB Content Extractor

## English

`epub_content_extractor` is a planned EPUB-to-clean-text extractor designed for downstream NLP workflows. Its goal is to read an `.epub` file as a structured book, extract only meaningful document content, remove navigation and publishing noise, and produce clean linear text while preserving paragraph and chapter semantics.

The project is intended for open publication and may be used for non-commercial purposes.

### Purpose

Input:

- `.epub` file

Output:

- clean, readable, linear text
- preserved paragraph boundaries
- preserved chapter order
- minimal metadata, navigation, footnotes, duplicated headers, and other noise

The key design principle is to preserve the semantic structure of the source text while removing everything that does not belong to the actual book content.

### Architecture Summary

The extractor should process EPUB files as structured content rather than as raw text dumps:

```text
EPUB -> DOCUMENT items -> HTML -> Blocks -> Features -> Scoring -> Classification -> Clean Text
```

Recommended processing stages:

1. Read EPUB structure with `ebooklib`.
2. Extract only `DOCUMENT` items, usually chapters.
3. Parse HTML with `BeautifulSoup` and optionally `lxml`.
4. Convert relevant tags such as `p`, `h1`-`h6`, `br`, `div`, `section`, `article`, `li`, and `blockquote` into text blocks.
5. Calculate block-level features: length, word count, punctuation ratio, alphabetic ratio, digit ratio, sentence count, dialogue markers, repetition score, and positional metadata.
6. Score each block using production-grade heuristics instead of relying on one-off deletion rules.
7. Classify blocks as content, weak content, or noise.
8. Apply contextual filtering with neighboring blocks and density windows.
9. Normalize Unicode, spaces, line breaks, and paragraph boundaries.
10. Assemble the final text with `\n\n` between paragraphs and `\n\n\n` between chapters.

### Quality Guarantees

The extractor should aim to provide:

- no glued words or sentences
- no truncated sentences
- minimal boilerplate and navigation noise
- human-readable output
- stable paragraph and chapter boundaries
- dialogue preservation
- punctuation preservation

### Public API

```python
from epub_content_extractor import extract_document, extract_text_from_epub

document = extract_document("book.epub")
text = extract_text_from_epub("book.epub")
```

The `extract_text_from_epub()` helper is based on `extract_document()` and returns `ExtractedDocument.to_text()`.

```python
class ExtractedDocument:
    chapters: list[Chapter]


class Chapter:
    title: str
    paragraphs: list[str]
```

### CLI

```bash
epub-content-extractor book.epub -o book.txt
```

Write debug information with block scores, features, and keep/drop reasons:

```bash
epub-content-extractor book.epub -o book.txt --debug debug_book -d
```

CLI writes only extracted text to stdout. Logs and errors go to stderr. Exit code `0`
means success, `1` means expected input/data error, and `2+` means system error.

### Recommended Libraries

- `ebooklib` for EPUB structure
- `beautifulsoup4` for HTML parsing
- `lxml` for faster and stricter parsing
- `regex` for advanced cleanup patterns
- `ftfy` for fixing broken text encoding
- `rapidfuzz` for fuzzy repetition detection
- `readability-lxml` for unusually noisy EPUB files

For the detailed architecture, see [docs/architecture.md](docs/architecture.md) and [docs/architecture.en.md](docs/architecture.en.md).

### License And Use

This project is intended to be published with a non-commercial use license. You may use, study, modify, and share it for non-commercial purposes. Commercial use is not permitted without separate permission from the project owner.

## Русский

`epub_content_extractor` - это проект extractor-а для преобразования EPUB в чистый линейный текст, пригодный для downstream NLP-задач. Цель проекта - читать `.epub` как структурированную книгу, извлекать только содержательные части, удалять навигационный и издательский шум и сохранять семантику глав и абзацев.

Проект планируется к открытой публикации и может использоваться без коммерческого умысла.

### Назначение

Вход:

- `.epub` файл

Выход:

- чистый, читаемый, линейный текст
- сохраненные границы абзацев
- сохраненный порядок глав
- минимум метаданных, навигации, сносок, повторяющихся заголовков и другого шума

Ключевой принцип: сохранить семантическую структуру исходного текста и убрать все, что не относится к содержанию книги.

### Краткая Архитектура

Extractor должен обрабатывать EPUB как структуру, а не как простой текстовый дамп:

```text
EPUB -> DOCUMENT items -> HTML -> Blocks -> Features -> Scoring -> Classification -> Clean Text
```

Рекомендуемые этапы обработки:

1. Читать структуру EPUB через `ebooklib`.
2. Извлекать только элементы `DOCUMENT`, обычно главы.
3. Парсить HTML через `BeautifulSoup`, при необходимости с `lxml`.
4. Преобразовывать релевантные теги `p`, `h1`-`h6`, `br`, `div`, `section`, `article`, `li`, `blockquote` в текстовые блоки.
5. Считать признаки каждого блока: длину, количество слов, долю пунктуации, долю букв, долю цифр, количество предложений, маркеры диалога, повторяемость и позицию.
6. Оценивать блоки через scoring и production-grade эвристики, а не удалять текст по одному простому правилу.
7. Классифицировать блоки как содержательный текст, слабый содержательный текст или шум.
8. Применять контекстную фильтрацию с учетом соседних блоков и плотности хорошего текста.
9. Нормализовать Unicode, пробелы, переносы строк и границы абзацев.
10. Собирать итоговый текст с `\n\n` между абзацами и `\n\n\n` между главами.

### Гарантии Качества

Extractor должен стремиться обеспечивать:

- отсутствие склеенных слов и предложений
- отсутствие обрезанных предложений
- минимум boilerplate, навигации и мусора
- читаемый человеком результат
- стабильные границы абзацев и глав
- сохранение диалогов
- сохранение пунктуации

### Публичный API

```python
from epub_content_extractor import extract_document, extract_text_from_epub

document = extract_document("book.epub")
text = extract_text_from_epub("book.epub")
```

Вспомогательная функция `extract_text_from_epub()` основана на `extract_document()` и возвращает `ExtractedDocument.to_text()`.

```python
class ExtractedDocument:
    chapters: list[Chapter]


class Chapter:
    title: str
    paragraphs: list[str]
```

### CLI

```bash
epub-content-extractor book.epub -o book.txt
```

Debug-режим сохраняет scores, features и причины keep/drop для каждого блока:

```bash
epub-content-extractor book.epub -o book.txt --debug debug_book -d
```

CLI пишет в stdout только извлеченный текст. Логи и ошибки идут в stderr. Код `0`
означает успех, `1` - ожидаемую ошибку входных данных, `2+` - системную ошибку.

### Рекомендуемые Библиотеки

- `ebooklib` для чтения структуры EPUB
- `beautifulsoup4` для HTML-парсинга
- `lxml` для более быстрого и точного парсинга
- `regex` для сложных паттернов очистки
- `ftfy` для исправления битого текста
- `rapidfuzz` для fuzzy-поиска повторов
- `readability-lxml` для особенно грязных EPUB-файлов

Подробная архитектура описана в [docs/architecture.md](docs/architecture.md) и [docs/architecture.en.md](docs/architecture.en.md).

### Лицензия И Использование

Проект предполагается публиковать с лицензией для некоммерческого использования. Его можно использовать, изучать, изменять и распространять в некоммерческих целях. Коммерческое использование не разрешено без отдельного согласия владельца проекта.
