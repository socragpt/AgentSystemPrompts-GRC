"""Parse, validate, and render the XML governance baseline."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import List, Optional, Tuple


class PromptValidationError(ValueError):
    """Raised when a prompt document does not satisfy the baseline structure."""


@dataclass(frozen=True)
class Section:
    """A section from the system prompt."""

    title: str
    context: Optional[str] = None
    instructions: Tuple[str, ...] = field(default_factory=tuple)
    list_items: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """Return whether the section has no context, instructions, or list items."""

        return not (self.context or self.instructions or self.list_items)


def _normalized_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _list_item_text(item: ET.Element) -> str:
    strong = item.find("strong")
    instructions = item.find("instructions")
    if strong is not None and instructions is not None:
        return f"{_normalized_text(strong)}: {_normalized_text(instructions)}"
    return _normalized_text(item)


def _reject_attributes(element: ET.Element) -> None:
    if element.attrib:
        names = ", ".join(sorted(element.attrib))
        raise PromptValidationError(
            f"Element '{element.tag}' has unsupported attributes: {names}"
        )


def _validate_inline_content(element: ET.Element) -> None:
    """Require inline markup to consist only of plain ``strong`` elements."""

    _reject_attributes(element)
    for child in element:
        if child.tag != "strong":
            raise PromptValidationError(
                f"Element '{element.tag}' contains unsupported element '{child.tag}'"
            )
        _reject_attributes(child)
        if list(child):
            raise PromptValidationError(
                "Element 'strong' must not contain nested elements"
            )


def _validate_list(element: ET.Element) -> None:
    """Validate list structure before any policy text is flattened."""

    _reject_attributes(element)
    for item in element:
        if item.tag != "item":
            raise PromptValidationError(
                f"Element 'list' contains unsupported element '{item.tag}'"
            )
        _reject_attributes(item)
        instructions = [child for child in item if child.tag == "instructions"]
        strong = [child for child in item if child.tag == "strong"]
        unknown = [
            child.tag
            for child in item
            if child.tag not in {"strong", "instructions"}
        ]
        if unknown:
            raise PromptValidationError(
                f"Element 'item' contains unsupported element '{unknown[0]}'"
            )
        if len(instructions) > 1:
            raise PromptValidationError(
                "Element 'item' must not contain multiple instructions elements"
            )
        if instructions and len(strong) != 1:
            raise PromptValidationError(
                "A structured item must contain exactly one strong label"
            )
        if instructions and (
            (item.text or "").strip()
            or any((child.tail or "").strip() for child in item)
        ):
            raise PromptValidationError(
                "A structured item must not contain text outside its label and instructions"
            )
        for child in strong:
            _validate_inline_content(child)
        for child in instructions:
            _validate_inline_content(child)


def parse_system_prompt(xml_path: str) -> List[Section]:
    """Parse a ``SystemPrompt.xml`` document into structured sections."""

    path = Path(xml_path)
    try:
        source = path.read_bytes()
        if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", source, flags=re.IGNORECASE):
            raise PromptValidationError(
                f"Unable to parse {path}: DTD and entity declarations are not allowed"
            )
        root = ET.fromstring(source)
    except (ET.ParseError, OSError) as exc:
        raise PromptValidationError(f"Unable to parse {path}: {exc}") from exc

    if root.tag != "system_prompt":
        raise PromptValidationError(
            f"Expected root element 'system_prompt', found '{root.tag}'"
        )
    _reject_attributes(root)

    sections: List[Section] = []
    current_title: Optional[str] = None
    current_context: Optional[str] = None
    current_instructions: List[str] = []
    current_items: List[str] = []

    def append_current() -> None:
        if current_title is None:
            return
        sections.append(
            Section(
                title=current_title,
                context=current_context,
                instructions=tuple(current_instructions),
                list_items=tuple(current_items),
            )
        )

    for element in root:
        if element.tag == "section_title":
            _validate_inline_content(element)
            append_current()
            current_title = _normalized_text(element)
            if not current_title:
                raise PromptValidationError("Section titles must not be empty")
            current_context = None
            current_instructions = []
            current_items = []
            continue

        if current_title is None:
            raise PromptValidationError(
                f"Element '{element.tag}' appears before the first section_title"
            )

        if element.tag == "context":
            _validate_inline_content(element)
            if current_context is not None:
                raise PromptValidationError(
                    f"Section '{current_title}' contains multiple context elements"
                )
            current_context = _normalized_text(element)
        elif element.tag == "instructions":
            _validate_inline_content(element)
            text = _normalized_text(element)
            if text:
                current_instructions.append(text)
        elif element.tag == "list":
            _validate_list(element)
            for item in element.findall("item"):
                text = _list_item_text(item)
                if text:
                    current_items.append(text)
        else:
            raise PromptValidationError(
                f"Section '{current_title}' contains unsupported element '{element.tag}'"
            )

    append_current()
    if not sections:
        raise PromptValidationError("The prompt must contain at least one section")
    return sections


def validate_sections(sections: List[Section]) -> List[str]:
    """Return non-fatal structural warnings for parsed sections."""

    warnings: List[str] = []
    seen = set()
    for section in sections:
        if section.title in seen:
            warnings.append(f"Duplicate section title: {section.title}")
        seen.add(section.title)
        if section.is_empty:
            warnings.append(f"Section has no content: {section.title}")
    return warnings


def generate_prompt(sections: List[Section]) -> str:
    """Render parsed sections as a plain-text prompt."""

    lines: List[str] = []
    for section in sections:
        lines.append(f"# {section.title}")
        if section.context:
            lines.append(section.context)
        lines.extend(f"- {instruction}" for instruction in section.instructions)
        lines.extend(f"* {item}" for item in section.list_items)
        lines.append("")
    return "\n".join(lines).strip()
