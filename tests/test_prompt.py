from pathlib import Path
import tempfile
import unittest

from agent_governance.prompt import (
    PromptValidationError,
    generate_prompt,
    parse_system_prompt,
    validate_sections,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "SystemPrompt.xml"


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


if __name__ == "__main__":
    unittest.main()
