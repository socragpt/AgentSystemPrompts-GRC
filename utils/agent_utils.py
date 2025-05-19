import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Section:
    """Represents a section from the system prompt."""
    title: str
    context: Optional[str] = None
    instructions: List[str] = field(default_factory=list)
    list_items: List[str] = field(default_factory=list)


def parse_system_prompt(xml_path: str) -> List[Section]:
    """Parse a SystemPrompt.xml file into structured sections."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    sections: List[Section] = []
    current: Optional[Section] = None

    for elem in root:
        if elem.tag == "section_title":
            if current:
                sections.append(current)
            current = Section(title=(elem.text or "").strip())
        elif current is not None:
            if elem.tag == "context":
                current.context = ("".join(elem.itertext())).strip()
            elif elem.tag == "instructions":
                current.instructions.append("".join(elem.itertext()).strip())
            elif elem.tag == "list":
                for item in elem.findall("item"):
                    text = "".join(item.itertext()).strip()
                    if text:
                        current.list_items.append(text)
    if current:
        sections.append(current)
    return sections


def generate_prompt(sections: List[Section]) -> str:
    """Generate a simple text prompt from parsed sections."""
    lines: List[str] = []
    for sec in sections:
        lines.append(f"# {sec.title}")
        if sec.context:
            lines.append(sec.context)
        for inst in sec.instructions:
            lines.append(f"- {inst}")
        if sec.list_items:
            for item in sec.list_items:
                lines.append(f"* {item}")
        lines.append("")
    return "\n".join(lines).strip()
