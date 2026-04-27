from epub_content_extractor.extractor import (
    _build_footnote_index,
    _html_to_blocks,
    _remove_inline_footnote_markers,
)


def test_html_to_blocks_preserves_paragraph_spacing() -> None:
    blocks = _html_to_blocks("<html><body><p>Hello <b>world</b>.</p><p>Next.</p></body></html>", 0)

    assert [block.text for block in blocks] == ["Hello world.", "Next."]


def test_inline_bracket_marker_removed_when_matching_footnote_exists() -> None:
    blocks = _html_to_blocks(
        "<p>He was late[1] before answering.</p><p>[1] He missed the train.</p>",
        0,
    )
    blocks[1].position_ratio = 0.9
    footnote_index = _build_footnote_index(blocks)

    text = _remove_inline_footnote_markers(blocks[0].text, footnote_index, blocks)

    assert text == "He was late before answering."


def test_parenthesized_reference_is_kept_without_confidence() -> None:
    blocks = _html_to_blocks("<p>As shown in Figure (1), the result is stable.</p>", 0)

    text = _remove_inline_footnote_markers(blocks[0].text, {}, blocks)

    assert text == "As shown in Figure (1), the result is stable."
