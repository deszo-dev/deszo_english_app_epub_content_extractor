"""Batch-style usage built from repeated public API calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
from epub_content_extractor import build_canonical_text, extract_epub_content


from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

def write_minimal_epub(path: Path, title: str = "Minimal Valid EPUB") -> None:
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
"""
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:00000000-0000-4000-8000-000000000001</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>en</dc:language>
    <dc:creator>Jane Example</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>
    <item id="chap1" href="chapter_1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="chap1"/></spine>
</package>
"""
    nav_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head><title>Navigation</title></head>
  <body><nav epub:type="toc"><ol><li><a href="chapter_1.xhtml">Chapter 1</a></li></ol></nav></body>
</html>
"""
    chapter_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body><h1>Chapter 1</h1><p>Hello world.</p></body>
</html>
"""
    with ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)
        zf.writestr("OEBPS/chapter_1.xhtml", chapter_xhtml)

def value(obj, key):
    return obj[key] if isinstance(obj, dict) else getattr(obj, key)


with TemporaryDirectory() as tmp:
    paths = []
    for idx in range(2):
        input_path = Path(tmp) / f"book_{idx + 1}.epub"
        write_minimal_epub(input_path, title=f"Book {idx + 1}")
        paths.append(input_path)
    results = [extract_epub_content(path, config={}) for path in paths]
    assert len(results) == 2
    assert all(value(result, "status") == "succeeded" for result in results)
    texts = [build_canonical_text(value(result, "book")) for result in results]
    assert all("Hello world." in text for text in texts)
