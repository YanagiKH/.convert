from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path

from ..errors import DotConvertError
from ..registry import normalize_extension


class _TextExtractor(HTMLParser):
    BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        lines = [line.rstrip() for line in "".join(self.parts).splitlines()]
        compact: list[str] = []
        blank = False
        for line in lines:
            if line.strip():
                compact.append(line.strip())
                blank = False
            elif not blank:
                compact.append("")
                blank = True
        return "\n".join(compact).strip() + "\n"


def _read_text(source: Path) -> str:
    raw = source.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp950", "shift_jis", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DotConvertError("The text encoding could not be detected safely.")


def _html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return parser.text()


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def _markdown_to_html(value: str) -> str:
    output: list[str] = []
    paragraph: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{_inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for line in value.splitlines():
        if line.strip().startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        item = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_inline_markdown(heading.group(2))}</h{level}>")
        elif item:
            flush_paragraph()
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_inline_markdown(item.group(1))}</li>")
        elif not line.strip():
            flush_paragraph()
            close_list()
        else:
            close_list()
            paragraph.append(line.strip())
    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return "\n".join(output)


def convert_text(source: Path, destination: Path, target_extension: str) -> None:
    source_extension = normalize_extension(source.suffix)
    target = normalize_extension(target_extension)
    try:
        value = _read_text(source)
        if source.name.lower().endswith((".html", ".htm")):
            plain = _html_to_text(value)
            markdown_text = plain
        else:
            plain = value
            markdown_text = value

        if target == ".txt":
            output = plain
        elif target == ".md":
            output = markdown_text
        elif target == ".html":
            if source_extension == ".html":
                output = value
            elif source_extension == ".md":
                body = _markdown_to_html(value)
                output = f"<!doctype html>\n<html lang=\"en\">\n<head><meta charset=\"utf-8\"><title>{html.escape(source.stem)}</title></head>\n<body>\n{body}\n</body>\n</html>\n"
            else:
                escaped = html.escape(value)
                output = f"<!doctype html>\n<html lang=\"en\">\n<head><meta charset=\"utf-8\"><title>{html.escape(source.stem)}</title></head>\n<body><pre>{escaped}</pre></body>\n</html>\n"
        else:
            raise DotConvertError(f"Unsupported text target: {target}")
        destination.write_text(output, encoding="utf-8", newline="\n")
    except (OSError, UnicodeError) as exc:
        raise DotConvertError(f"Text conversion failed: {exc}") from exc
