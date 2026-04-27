Цель epub_content_extractor

Вход: .epub файл
Выход: чистый, линейный текст

Ключевое: сохранить семантическую структуру текста и убрать всё лишнее

Функциональные требования
1. Чтение EPUB как структуры

Использовать:

ebooklib

Требования:
извлекать только DOCUMENT элементы (главы)

игнорировать:
навигацию (nav)
стили
изображения

2. Извлечение текста из HTML

EPUB = HTML → нужно парсить

Использовать:

BeautifulSoup
Требования:
удалить все HTML-теги
корректно обрабатывать:
<p>
<h1>–<h6>
<br>
сохранить:
абзацы
базовую структуру

Ошибка, которую нельзя допустить:

склеивание предложений без пробелов
потеря пунктуации

3. 🧹 Очистка от “шума”

Это самая критичная часть для NLP.

Нужно удалять:
Метаданные:
copyright
ISBN
publisher info

Навигацию:
Table of Contents
Chapter list

Артефакты:
“Page 12”
“Chapter 1” (опционально)
повторяющиеся заголовки

Сноски:
footnote blocks — удалять агрессивно, особенно в конце главы
inline-маркеры [1], (1) — удалять осторожно и только при высокой уверенности

Production-логика для сносок:

1. Блоки сносок в конце главы
Признаки:
[1] Some explanation text...
[2] Another note...
1. Some explanation
2. Another explanation

Удалять блок, если совпадает несколько сигналов:
footnote_lines_ratio > 0.5
последовательность маркеров [1], [2], [3] или 1., 2., 3.
позиция блока > 80% главы

2. Inline-маркеры
Нельзя удалять все маркеры простым regex:
re.sub(r"\[\d+\]|\(\d+\)", "", text)

Это ломает нормальный текст:
"see Figure (1)"
"Option (1) is correct"

Стратегия:
сначала найти footnote blocks
построить footnote_index: marker_id -> note_text
удалять inline [1] только если marker_id найден в footnote_index
для (1) использовать более строгую эвристику

Inline confidence:
chapter_has_footnotes -> +0.5
count_inline_markers > 3 -> +0.3
маркер стоит после слова или около конца предложения -> +0.3
enumeration вроде "(1) First step" -> -0.7
рядом слова equation, figure, table -> -0.5

Финальное решение:
if confidence > 0.6:
    remove_marker()
else:
    keep()

Ключевой принцип:
не удалять inline-маркеры вслепую; сначала связывать их со структурными footnote blocks, затем применять fallback scoring.

4. Семантическая сегментация
Требования:
сохранять:
границы абзацев
логические блоки текста
не ломать:
предложения
диалоги
кавычки

5. Нормализация текста
Обязательные шаги:
Unicode normalization (NFC)
замена:
\xa0 → пробел
множественные пробелы → один
удаление:
лишних переносов строк

6. Линейная сборка текста
Требования:
объединить главы в правильном порядке
вставлять:
\n\n между абзацами
\n\n\n между главами

чтобы downstream NLP понимал структуру

7. Гарантии качества (очень важно)

Extractor должен обеспечивать:

Нет “склеенных” слов
Нет обрезанных предложений
Минимум мусора
Читаемость текста человеком

Рекомендуемые библиотеки
lxml
→ быстрее и точнее парсинг
regex
→ сложные паттерны очистки
ftfy
→ исправление “битого” текста
readability-lxml
→ если EPUB грязный (редко нужно)

Минимальный API

class ExtractedDocument:
    chapters: List[Chapter]

class Chapter:
    title: str
    paragraphs: List[str]

Принципиальная модель

Фильтрация = не удаление по одному правилу, а скoring + классификация блоков текста

Raw HTML → Blocks → Feature Extraction → Scoring → Classification → Clean Text

Это ключевое отличие от “наивного” подхода

Шаг 1. Декомпозиция на блоки

После парсинга через:

BeautifulSoup
Извлекаем блоки:
BLOCK_TAGS = ["p", "div", "section", "article", "li", "blockquote"]

Каждый блок:

class TextBlock:
    text: str
    tag: str
    position: int
    chapter_index: int
Шаг 2. Feature extraction (очень важно)

Для каждого блока считаем признаки:

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
Шаг 3. Правила (production-grade)
1. Length-based filtering
if features.length_chars < 25:
    penalty += 0.5

НО:

if features.has_dialogue_markers:
    penalty -= 0.4

не ломаем диалоги

2. Alphabet ratio (очень сильный сигнал)
alpha_ratio = letters / total_chars

if alpha_ratio < 0.6:
    penalty += 0.7

Удаляет:

мусор
символы
nav
3. Digit-heavy blocks
if features.digit_ratio > 0.3:
    penalty += 0.6

Удаляет:

ISBN
страницы
списки
4. Repetition detection
if block.text in seen_blocks:
    penalty += 1.0

Или fuzzy:

similarity > 0.9 → penalty

Удаляет:

headers
footers
5. TOC detection (критично)

Паттерны:

r"(chapter|part)\s+\d+"
r"\.{3,}"
if many_lines_match_pattern:
    mark_as_toc = True
6. Sentence structure check
if features.sentence_count == 0:
    penalty += 0.5

НО:

if features.length_chars > 80:
    penalty -= 0.3
7. Dialogue preservation
DIALOGUE_MARKERS = ["—", "\"", "'"]

if any(marker in text for marker in DIALOGUE_MARKERS):
    boost += 0.4
8. Uppercase detection
if features.is_uppercase and features.length_chars < 80:
    penalty += 0.6

Удаляет:

заголовки
metadata
9. Positional heuristics

В начале EPUB часто мусор:

if chapter_index == 0 and position < 10:
    penalty += 0.7
10. Boilerplate patterns
BOILERPLATE = [
    "all rights reserved",
    "copyright",
    "isbn",
    "published by",
]
if any(pattern in text.lower()):
    penalty += 1.0

11. Footnote handling
Footnote blocks:
if block.position_ratio > 0.8 and footnote_lines_ratio > 0.5:
    penalty += 1.0

Inline markers:
if marker_id in chapter_footnote_index:
    remove_marker
elif confidence > 0.6:
    remove_marker
else:
    keep_marker

Шаг 4. Scoring
score = base_score - penalty + boost
Пример:
if score < 0:
    drop_block
elif score < 0.3:
    maybe_keep
else:
    keep

Шаг 5. Контекстная фильтрация (очень мощно)
1. Neighbor validation
if block is weak BUT neighbors are strong:
    keep
2. Density clustering
window = 5 blocks

if avg_score(window) high:
    keep all
3. Section detection

Если подряд:

много слабых блоков → skip section
Шаг 6. Post-processing

После фильтрации:

1. Склейка:
paragraphs = merge_if_no_sentence_end()
2. Удаление мусора:
remove_lines_like:
- "Page 12"
- "***"
3. Нормализация:
пробелы
Unicode

Production thresholds (рекомендованные)
MIN_CHARS = 25
MIN_ALPHA_RATIO = 0.6
MAX_DIGIT_RATIO = 0.3
REPETITION_THRESHOLD = 0.9

KEEP_SCORE = 0.3
DROP_SCORE = 0.0

Библиотеки
BeautifulSoup
regex
ftfy
rapidfuzz
