from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import io
import tempfile
import unittest

from agent_governance.cli import main as cli_main
from agent_governance.prompt import (
    PromptValidationError,
    generate_prompt,
    parse_system_prompt,
    validate_sections,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "examples" / "legacy" / "SystemPrompt.xml"


class PromptTests(unittest.TestCase):
    def test_baseline_parses_and_contains_safety_hierarchy(self):
        sections = parse_system_prompt(str(BASELINE))

        self.assertGreaterEqual(len(sections), 26)
        titles = [section.title for section in sections]
        self.assertIn("Instruction Precedence", titles)
        rendered = generate_prompt(sections)
        self.assertIn("Only authorized Goals may be pursued", rendered)
        self.assertNotIn("All Goals must be pursued", rendered)

    def test_nested_list_item_renders_as_label_and_instruction(self):
        sections = parse_system_prompt(str(BASELINE))
        decision = next(
            section for section in sections if section.title == "Decision Making Process"
        )

        self.assertTrue(decision.list_items[0].startswith("Evaluate Impact: "))

    def test_baseline_has_no_structural_warnings(self):
        warnings = validate_sections(parse_system_prompt(str(BASELINE)))

        self.assertEqual([], warnings)

    def test_invalid_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.xml"
            path.write_text("<not_a_prompt />", encoding="utf-8")

            with self.assertRaises(PromptValidationError):
                parse_system_prompt(str(path))

    def test_doctype_and_entity_declarations_are_rejected(self):
        xml = (
            '<!DOCTYPE system_prompt [<!ENTITY unsafe "expanded">]>'
            '<system_prompt><section_title>Policy</section_title>'
            '<context>&unsafe;</context></system_prompt>'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.xml"
            path.write_text(xml, encoding="utf-8")

            with self.assertRaisesRegex(
                PromptValidationError, "DTD and entity declarations are not allowed"
            ):
                parse_system_prompt(str(path))

    def test_unknown_top_level_element_is_rejected(self):
        xml = (
            "<system_prompt><section_title>Policy</section_title>"
            "<unknown>must not disappear</unknown></system_prompt>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unknown.xml"
            path.write_text(xml, encoding="utf-8")

            with self.assertRaisesRegex(
                PromptValidationError, "unsupported element 'unknown'"
            ):
                parse_system_prompt(str(path))

    def test_duplicate_context_is_rejected(self):
        xml = (
            "<system_prompt><section_title>Policy</section_title>"
            "<context>first</context><context>second</context></system_prompt>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate-context.xml"
            path.write_text(xml, encoding="utf-8")

            with self.assertRaisesRegex(
                PromptValidationError, "multiple context elements"
            ):
                parse_system_prompt(str(path))

    def test_nested_list_content_is_rejected(self):
        xml = (
            "<system_prompt><section_title>Policy</section_title><list>"
            "<group><item>must not disappear</item></group>"
            "</list></system_prompt>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested-list.xml"
            path.write_text(xml, encoding="utf-8")

            with self.assertRaisesRegex(
                PromptValidationError, "unsupported element 'group'"
            ):
                parse_system_prompt(str(path))

    def test_structured_list_item_cannot_hide_mixed_text(self):
        xml = (
            "<system_prompt><section_title>Policy</section_title><list><item>"
            "hidden<strong>Label</strong><instructions>Do this</instructions>tail"
            "</item></list></system_prompt>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed-list.xml"
            path.write_text(xml, encoding="utf-8")

            with self.assertRaisesRegex(
                PromptValidationError, "must not contain text outside"
            ):
                parse_system_prompt(str(path))

    def test_render_refuses_structural_warnings(self):
        xml = (
            "<system_prompt><section_title>Duplicate</section_title>"
            "<context>first</context><section_title>Duplicate</section_title>"
            "<context>second</context></system_prompt>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "warning.xml"
            path.write_text(xml, encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = cli_main(["render", str(path)])

        self.assertEqual(1, result)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("Duplicate section title", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
