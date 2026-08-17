"""Parse, validate, and render the XML governance baseline."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class PromptValidationError(ValueError):
    """Raised when a prompt document does not satisfy the baseline structure."""


@dataclass(frozen=True)
class Section:
    """A section from the system prompt."""

    title: str
    context: Optional[str] = None
    instructions: List[str] = field(default_factory=list)
    list_items: List[str] = field(default_factory=list)

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


def parse_system_prompt(xml_path: str) -> List[Section]:
    """Parse a ``SystemPrompt.xml`` document into structured sections."""

    path = Path(xml_path)
    try:
        tree = ET.parse(str(path))
    except (ET.ParseError, OSError) as exc:
        raise PromptValidationError(f"Unable to parse {path}: {exc}") from exc

    root = tree.getroot()
    if root.tag != "system_prompt":
        raise PromptValidationError(
            f"Expected root element 'system_prompt', found '{root.tag}'"
        )

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
                instructions=list(current_instructions),
                list_items=list(current_items),
            )
        )

    for element in root:
        if element.tag == "section_title":
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
            current_context = _normalized_text(element)
        elif element.tag == "instructions":
            text = _normalized_text(element)
            if text:
                current_instructions.append(text)
        elif element.tag == "list":
            for item in element.findall("item"):
                text = _list_item_text(item)
                if text:
                    current_items.append(text)

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
