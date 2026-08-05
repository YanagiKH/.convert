from __future__ import annotations

import csv
import datetime as dt
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from ..errors import DotConvertError
from ..registry import extension_for_path, normalize_extension

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


def _xml_to_value(element: ET.Element) -> Any:
    children = list(element)
    node: dict[str, Any] = {}
    if element.attrib:
        node["@attributes"] = dict(element.attrib)
    text = (element.text or "").strip()
    if text:
        node["#text"] = text
    grouped: dict[str, list[Any]] = {}
    for child in children:
        grouped.setdefault(child.tag, []).append(_xml_to_value(child))
    for tag, values in grouped.items():
        node[tag] = values[0] if len(values) == 1 else values
    return node if node else text


def _value_to_xml(tag: str, value: Any) -> ET.Element:
    element = ET.Element(tag)
    if isinstance(value, dict):
        attrs = value.get("@attributes")
        if isinstance(attrs, dict):
            element.attrib.update({str(key): str(item) for key, item in attrs.items()})
        if "#text" in value:
            element.text = str(value["#text"])
        for key, item in value.items():
            if key in {"@attributes", "#text"}:
                continue
            if isinstance(item, list):
                for child in item:
                    element.append(_value_to_xml(str(key), child))
            else:
                element.append(_value_to_xml(str(key), item))
    elif isinstance(value, list):
        for item in value:
            element.append(_value_to_xml("item", item))
    elif value is not None:
        element.text = str(value)
    return element


def _load_delimited(source: Path, delimiter: str | None = None) -> list[dict[str, str]]:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        if delimiter is None:
            sample = handle.read(8192)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            return list(csv.DictReader(handle, dialect=dialect))
        return list(csv.DictReader(handle, delimiter=delimiter))


def _load(source: Path) -> Any:
    extension = extension_for_path(source)
    if extension == ".json":
        return json.loads(source.read_text(encoding="utf-8-sig"))
    if extension == ".jsonl":
        values: list[Any] = []
        for line_number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.strip():
                try:
                    values.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise DotConvertError(f"Invalid JSON Lines record at line {line_number}: {exc}") from exc
        return values
    if extension == ".yaml":
        return yaml.safe_load(source.read_text(encoding="utf-8-sig"))
    if extension == ".toml":
        with source.open("rb") as handle:
            return tomllib.load(handle)
    if extension == ".csv":
        return _load_delimited(source)
    if extension == ".tsv":
        return _load_delimited(source, "\t")
    if extension == ".xml":
        root = ET.parse(source).getroot()
        return {root.tag: _xml_to_value(root)}
    raise DotConvertError(f"Unsupported data source: {extension}")


def _rows_for_delimited(value: Any) -> tuple[list[str], list[dict[str, Any]]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise DotConvertError("Delimited output requires a list of flat objects or one flat object.")
    rows = list(value)
    for row in rows:
        for item in row.values():
            if isinstance(item, (dict, list, tuple, set)):
                raise DotConvertError("Nested data cannot be written to CSV or TSV without losing structure.")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if str(key) not in fields:
                fields.append(str(key))
    return fields, [{str(key): item for key, item in row.items()} for row in rows]


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DotConvertError("TOML output cannot safely represent non-finite numbers.")
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, list) and all(not isinstance(item, dict) for item in value):
        return "[" + ", ".join(_toml_scalar(item) for item in value) + "]"
    raise DotConvertError(f"TOML output cannot safely represent {type(value).__name__} values.")


def _dump_toml(value: Any) -> str:
    if not isinstance(value, dict):
        raise DotConvertError("TOML output requires an object at the document root.")
    lines: list[str] = []

    def write_table(table: dict[str, Any], path: tuple[str, ...]) -> None:
        scalars = {key: item for key, item in table.items() if not isinstance(item, dict)}
        children = {key: item for key, item in table.items() if isinstance(item, dict)}
        if path:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append("[" + ".".join(json.dumps(part, ensure_ascii=False) for part in path) + "]")
        for key, item in scalars.items():
            lines.append(f"{json.dumps(str(key), ensure_ascii=False)} = {_toml_scalar(item)}")
        for key, item in children.items():
            write_table(item, (*path, str(key)))

    write_table(value, ())
    return "\n".join(lines).rstrip() + "\n"


def convert_data(source: Path, destination: Path, target_extension: str) -> None:
    target = normalize_extension(target_extension)
    try:
        value = _load(source)
        if target == ".json":
            destination.write_text(
                json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        elif target == ".jsonl":
            records = value if isinstance(value, list) else [value]
            destination.write_text(
                "".join(json.dumps(item, ensure_ascii=False, default=str) + "\n" for item in records),
                encoding="utf-8",
            )
        elif target == ".yaml":
            destination.write_text(
                yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        elif target == ".toml":
            destination.write_text(_dump_toml(value), encoding="utf-8")
        elif target in {".csv", ".tsv"}:
            fields, rows = _rows_for_delimited(value)
            with destination.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fields,
                    extrasaction="raise",
                    delimiter="\t" if target == ".tsv" else ",",
                )
                writer.writeheader()
                writer.writerows(rows)
        elif target == ".xml":
            if isinstance(value, dict) and len(value) == 1:
                root_name, root_value = next(iter(value.items()))
            else:
                root_name, root_value = "root", value
            root = _value_to_xml(str(root_name), root_value)
            ET.indent(root, space="  ")
            ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
        else:
            raise DotConvertError(f"Unsupported data target: {target}")
    except DotConvertError:
        raise
    except (OSError, ValueError, csv.Error, ET.ParseError, yaml.YAMLError) as exc:
        raise DotConvertError(f"Data conversion failed: {exc}") from exc
