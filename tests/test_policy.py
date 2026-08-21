from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_governance.cli import main as cli_main
from agent_governance.policy import (
    compile_policy_bundle,
    load_policy_bundle,
    validate_policy_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "policies" / "multi_agent_operations.json"


def load_example():
    return load_policy_bundle(str(EXAMPLE))


def issue_codes(bundle):
    return {issue.code for issue in validate_policy_bundle(bundle)}


class PolicyBundleTests(unittest.TestCase):
    def test_example_is_valid_and_fail_closed(self):
        bundle = load_example()

        self.assertEqual([], validate_policy_bundle(bundle))
        self.assertEqual("deny", bundle["bundle"]["default_effect"])

    def test_compilation_is_independent_of_unordered_input_arrays(self):
        original = load_example()
        reordered = deepcopy(original)
        for collection in (
            "actors",
            "roles",
            "resources",
            "capabilities",
            "approvals",
            "delegations",
            "exceptions",
        ):
            reordered[collection].reverse()
        reordered["policies"].reverse()
        for actor in reordered["actors"]:
            actor["roles"].reverse()
        for role in reordered["roles"]:
            role["capabilities"].reverse()
        for policy in reordered["policies"]:
            policy["controls"].reverse()
            policy["provenance"]["authored_by"].reverse()
            policy["provenance"]["approved_by"].reverse()
            for control in policy["controls"]:
                control["capability_ids"].reverse()
                control["evidence_fields"].reverse()
                for field in ("actor_ids", "role_ids"):
                    if field in control["subjects"]:
                        control["subjects"][field].reverse()
        for approval in reordered["approvals"]:
            approval["approver_role_ids"].reverse()
            approval["bind_to"].reverse()
        for delegation in reordered["delegations"]:
            delegation["capability_ids"].reverse()

        self.assertEqual(
            compile_policy_bundle(original), compile_policy_bundle(reordered)
        )

    def test_unknown_fields_and_dangling_references_fail_closed(self):
        bundle = load_example()
        bundle["actors"][0]["typo"] = True
        bundle["capabilities"][0]["resource_id"] = "tool.missing"

        issues = validate_policy_bundle(bundle)

        self.assertIn("schema.unknown_field", {issue.code for issue in issues})
        self.assertIn("reference.not_found", {issue.code for issue in issues})
        self.assertEqual(
            "/capabilities/0/resource_id",
            next(issue.path for issue in issues if issue.code == "reference.not_found"),
        )

    def test_malformed_nested_values_report_errors_without_crashing(self):
        bundle = load_example()
        bundle["actors"][0]["roles"] = [{"not": "an id"}]
        bundle["roles"][0]["capabilities"] = [["not-an-id"]]
        bundle["exceptions"][0]["replacement_effect"] = {"not": "an effect"}

        issues = validate_policy_bundle(bundle)

        self.assertTrue(issues)
        self.assertIn("schema.type", {issue.code for issue in issues})

    def test_duplicate_ids_are_rejected_across_entity_types(self):
        bundle = load_example()
        bundle["resources"][0]["id"] = bundle["actors"][0]["id"]

        issues = validate_policy_bundle(bundle)

        self.assertIn("id.duplicate", {issue.code for issue in issues})

    def test_delegation_cannot_amplify_authority(self):
        bundle = load_example()
        owner = next(role for role in bundle["roles"] if role["id"] == "role.operations-owner")
        owner["capabilities"].remove("capability.email-send")

        issues = validate_policy_bundle(bundle)

        self.assertTrue(
            any(
                issue.code == "delegation.escalation"
                and "capability.email-send" in issue.message
                for issue in issues
            )
        )

    def test_delegation_cycles_are_rejected(self):
        bundle = load_example()
        downstream = next(
            item
            for item in bundle["delegations"]
            if item["id"] == "delegation.researcher-to-communicator"
        )
        downstream["to_actor_id"] = "human.operations-owner"

        self.assertIn("delegation.cycle", issue_codes(bundle))

    def test_exception_must_narrow_subjects_and_capabilities(self):
        bundle = load_example()
        exception = bundle["exceptions"][0]
        exception["subjects"] = {"any": True}
        exception["capability_ids"].append("capability.email-draft")

        issues = [
            issue for issue in validate_policy_bundle(bundle) if issue.code == "exception.scope"
        ]

        self.assertGreaterEqual(len(issues), 2)

    def test_invalid_lifecycle_is_rejected(self):
        bundle = load_example()
        bundle["delegations"][0]["valid_until"] = "2026-07-01T00:00:00Z"

        self.assertIn("lifecycle.invalid", issue_codes(bundle))

    def test_cli_compiles_both_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli_main(
                    [
                        "policy",
                        "compile",
                        str(EXAMPLE),
                        "--output-dir",
                        directory,
                    ]
                )

            text_path = Path(directory) / "agent-policy.txt"
            data_path = Path(directory) / "decision-data.json"
            self.assertEqual(0, result)
            self.assertTrue(text_path.is_file())
            self.assertTrue(data_path.is_file())
            self.assertIn("FAIL-CLOSED RULE", text_path.read_text(encoding="utf-8"))
            self.assertIn(
                "ROLES AND BASELINE CAPABILITIES",
                text_path.read_text(encoding="utf-8"),
            )
            self.assertIn("RESOURCES", text_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "deny",
                json.loads(data_path.read_text(encoding="utf-8"))["resolution"]["default_effect"],
            )

    def test_cli_json_errors_are_machine_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = cli_main(
                    ["policy", "validate", str(path), "--format", "json"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(2, result)
        self.assertFalse(payload["valid"])
        self.assertEqual("json.syntax", payload["errors"][0]["code"])
        self.assertEqual("", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
