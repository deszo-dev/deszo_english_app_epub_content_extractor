from __future__ import annotations

import json
from pathlib import Path

from epub_content_extractor.core.models import ExtractedDocument


def write_debug(debug_dir: str | Path, document: ExtractedDocument) -> None:
    path = Path(debug_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "blocks.json").write_text(
        json.dumps(document.debug_as_dicts(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
