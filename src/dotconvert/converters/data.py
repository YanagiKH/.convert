from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from ..errors import DotConvertError
from ..registry import normalize_extension


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


def _load_csv(source: Path) -> list[dict[str, str]]:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(handle, dialect=dialect))


def _load(source: Path) -> Any:
    extension = normalize_extension(".tar.gz" if source.name.lower().endswith(".tar.gz") else source.suffix)
    if extension == ".json":
        return json.loads(source.read_text(encoding="utf-8-sig"))
    if extension == ".yaml":
        return yaml.safe_load(source.read_text(encoding="utf-8-sig"))
    if extension == ".csv":
        return _load_csv(source)
    if extension == ".xml":
        root = ET.parse(source).getroot()
        return {root.tag: _xml_to_value(root)}
    raise DotConvertError(f"Unsupported data source: {extension}")


def _rows_for_csv(value: Any) -> tuple[list[str], list[dict[str, Any]]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise DotConvertError("CSV output requires a list of flat objects or one flat object.")
    rows = list(value)
    for row in rows:
        for item in row.values():
            if isinstance(item, (dict, list, tuple, set)):
                raise DotConvertError("Nested data cannot be written to CSV without losing structure.")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if str(key) not in fields:
                fields.append(str(key))
    return fields, [{str(key): item for key, item in row.items()} for row in rows]


def convert_data(source: Path, destination: Path, target_extension: str) -> None:
    target = normalize_extension(target_extension)
    try:
        value = _load(source)
        if target == ".json":
            destination.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif target == ".yaml":
            destination.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
        elif target == ".csv":
            fields, rows = _rows_for_csv(value)
            with destination.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
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
    except (OSError, ValueError, csv.Error, ET.ParseError, yaml.YAMLError) as exc:
        raise DotConvertError(f"Data conversion failed: {exc}") from exc
