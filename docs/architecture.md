1. Цель системы

Extractor должен преобразовывать .epub в чистый, линейный текст, сохраняя семантику и удаляя шум

2. Архитектурный принцип
Raw EPUB
  → HTML Parsing
  → Block Extraction
  → Feature Extraction
  → Scoring
  → Classification
  → Post-processing
  → Clean Text
3. Двухуровневая архитектура
3.1 Runtime слой (Python)
ebooklib → чтение EPUB
BeautifulSoup / lxml → парсинг
regex / ftfy → очистка
pipeline → обработка
3.2 Formal слой (Coq)

Coq описывает:

модель данных
правила фильтрации
scoring
инварианты качества

👉 Coq = спецификация, Python = реализация

4. Модель данных
Runtime (Python)
class TextBlock:
    text: str
    tag: str
    position: int
    chapter_index: int
Formal (Coq)
Record TextBlock := {
  text : string;
  tag : string;
  position : nat;
  chapter_index : nat
}.
5. Feature Extraction
Python
length_chars
alpha_ratio
digit_ratio
sentence_count
dialogue markers
Coq контракт
Parameter extract_features : TextBlock -> BlockFeatures.

Axiom feature_soundness :
  forall b,
    let f := extract_features b in
    (0 <= f.(alpha_ratio) <= 1)%Q.
6. Scoring система
Python (реализация)
score = base_score - penalty + boost
Coq (формализация)
Definition final_score (s : Score) : Q :=
  s.(base_score) - s.(penalty) + s.(boost).
7. Правила фильтрации
7.1 Alpha ratio (ключевой сигнал)

Python:

if alpha_ratio < 0.6:
    penalty += 0.7

Coq:

Definition alpha_penalty (f : BlockFeatures) : Q :=
  if Qlt_bool f.(alpha_ratio) (6#10) then 0.7 else 0.
7.2 Digit-heavy блоки
if digit_ratio > 0.3 → penalty
7.3 Dialogue preservation
if has_dialogue_markers → boost
7.4 Uppercase / metadata
if uppercase & short → penalty
8. Классификация
Inductive BlockDecision :=
| Keep
| Maybe
| Drop.
if score < 0      → Drop
if score < 0.3    → Maybe
else              → Keep
9. Footnote система (критично)
Архитектурный принцип

❗ Нельзя удалять inline markers напрямую

Pipeline
1. Найти footnote blocks
2. Построить индекс
3. Обработать inline markers
Coq модель
Definition inline_confidence (ctx : InlineContext) : Q := ...
if confidence > 0.6 → remove
else keep
10. Контекстная фильтрация
Python
neighbor validation
density clustering
section skipping
Coq (абстракция)
(* слабый блок сохраняется если окружён сильными *)
11. Post-processing
merge broken paragraphs
remove artifacts
normalize Unicode
12. Финальная сборка
"\n\n"   → между абзацами  
"\n\n\n" → между главами
13. Инварианты качества
Coq
Definition quality_guarantee (doc : ExtractedDocument) : Prop :=
  forall p,
    paragraph p ->
      no_word_gluing p /\
      sentence_integrity p /\
      readability p.
14. Production thresholds
Параметр	Значение
MIN_CHARS	25
MIN_ALPHA_RATIO	0.6
MAX_DIGIT_RATIO	0.3
KEEP_SCORE	0.3
15. Ключевое отличие архитектуры

❌ Наивный подход

regex → удалить всё подряд

✅ Production модель

Blocks → Features → Scoring → Classification
16. Гарантии системы

Extractor обеспечивает:

отсутствие склеенных слов
сохранение предложений
минимальный шум
читаемость человеком
17. Расширяемость
Coq слой позволяет:
доказывать корректность правил
валидировать изменения эвристик
фиксировать регрессии
18. Дальнейшее развитие
Можно добавить:
Coq proofs:
“мусорный блок всегда удаляется”
Property-based testing (Hypothesis)
Автогенерация тестов из Coq