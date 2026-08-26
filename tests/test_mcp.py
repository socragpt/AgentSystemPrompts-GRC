from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_governance import (
    MCPNormalizationResult,
    MCPShadowResult,
    evaluate_action,
    evaluate_mcp_shadow,
    load_action_request,
    load_approval_grant,
    load_approval_verification_state,
    load_mcp_adapter_mapping,
    load_mcp_call_proposal,
    load_policy_bundle,
    normalize_mcp_call,
    validate_action_request,
    validate_mcp_adapter_mapping,
    validate_mcp_call_proposal,
    verify_approval_grant,
)
from agent_governance.cli import main as cli_main


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "examples" / "policies" / "multi_agent_operations.json"
MAPPING_PATH = ROOT / "examples" / "mcp" / "mapping.json"
PROPOSALS = ROOT / "examples" / "mcp" / "proposals"
EXPECTED_REQUESTS = ROOT / "examples" / "mcp" / "expected-requests"
GRANT_PATH = ROOT / "examples" / "mcp" / "approval-grant.json"
STATE_PATH = ROOT / "examples" / "approval_states" / "current.json"
TRUSTED_BOUNDARIES = {"identity.reference"}


def load_policy():
    return load_policy_bundle(str(POLICY_PATH))


def load_mapping():
    return load_mcp_adapter_mapping(str(MAPPING_PATH))


def load_proposal(name="browser-read.json"):
    return load_mcp_call_proposal(str(PROPOSALS / name))


def reason_codes(result):
    value = result.as_dict() if hasattr(result, "as_dict") else result
    return [reason["code"] for reason in value["reasons"]]


class MCPShadowTests(unittest.TestCase):
    """MCP v0.1 conformance for INT-001..003, DX-003/005/009, and EVD-001."""

    def test_examples_validate_and_normalize_to_exact_hand_authored_requests(self):
        mapping = load_mapping()
        self.assertEqual([], validate_mcp_adapter_mapping(mapping))
        for proposal_name, request_name in (
            ("browser-read.json", "browser-read.json"),
            ("email-send.json", "email-send.json"),
        ):
            with self.subTest(proposal=proposal_name):
                proposal = load_proposal(proposal_name)
                self.assertEqual([], validate_mcp_call_proposal(proposal))
                result = normalize_mcp_call(proposal, mapping)
                expected = load_action_request(str(EXPECTED_REQUESTS / request_name))
                self.assertIsInstance(result, MCPNormalizationResult)
                self.assertEqual("normalized", result.outcome)
                self.assertEqual(expected, result.action_request)
                self.assertEqual([], validate_action_request(result.action_request))

    def test_shadow_embeds_byte_identical_shared_evaluator_result(self):
        policy = load_policy()
        mapping = load_mapping()
        proposal = load_proposal()
        expected_request = load_action_request(
            str(EXPECTED_REQUESTS / "browser-read.json")
        )
        expected_decision = evaluate_action(
            policy,
            expected_request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()

        result = evaluate_mcp_shadow(
            policy,
            mapping,
            proposal,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()

        self.assertEqual("evaluated", result["outcome"])
        self.assertEqual("allow", result["decision_result"]["disposition"])
        self.assertEqual(expected_request, result["action_request"])
        self.assertEqual(expected_decision, result["decision_result"])
        self.assertEqual("shadow", result["mode"])
        self.assertTrue(result["proposal_only"])
        self.assertTrue(result["proposed_evidence_record"]["proposal_only"])

    def test_allow_deny_and_require_approval_use_unchanged_decision_semantics(self):
        cases = (
            ("browser-read.json", "allow", "control.allow"),
            ("denied.json", "deny", "authority.capability_not_found"),
            ("email-send.json", "require_approval", "control.require_approval"),
        )
        for proposal_name, disposition, decision_reason in cases:
            with self.subTest(proposal=proposal_name):
                result = evaluate_mcp_shadow(
                    load_policy(),
                    load_mapping(),
                    load_proposal(proposal_name),
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                ).as_dict()
                self.assertEqual(disposition, result["decision_result"]["disposition"])
                self.assertIn(
                    decision_reason,
                    [reason["code"] for reason in result["decision_result"]["reasons"]],
                )

    def test_satisfied_approval_is_unchanged_and_never_changes_disposition(self):
        policy = load_policy()
        mapping = load_mapping()
        proposal = load_proposal("email-send.json")
        grant = load_approval_grant(str(GRANT_PATH))
        state = load_approval_verification_state(str(STATE_PATH))
        without_grant = evaluate_mcp_shadow(
            policy,
            mapping,
            proposal,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()
        expected_verification = verify_approval_grant(
            policy,
            without_grant["action_request"],
            without_grant["decision_result"],
            grant,
            state,
        ).as_dict()

        result = evaluate_mcp_shadow(
            policy,
            mapping,
            proposal,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            grant=grant,
            verification_state=state,
        ).as_dict()

        self.assertEqual("require_approval", result["decision_result"]["disposition"])
        self.assertEqual("satisfied", result["approval_verification_result"]["outcome"])
        self.assertEqual(expected_verification, result["approval_verification_result"])

    def test_untrusted_annotations_cannot_change_request_or_decision(self):
        policy = load_policy()
        mapping = load_mapping()
        plain = evaluate_mcp_shadow(
            policy,
            mapping,
            load_proposal("browser-read.json"),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()
        spoofed = evaluate_mcp_shadow(
            policy,
            mapping,
            load_proposal("browser-read-spoofed-annotations.json"),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()

        self.assertEqual(plain["action_request"], spoofed["action_request"])
        self.assertEqual(plain["decision_result"], spoofed["decision_result"])
        self.assertNotEqual(
            plain["proposal"]["proposal_sha256"],
            spoofed["proposal"]["proposal_sha256"],
        )
        serialized = json.dumps(spoofed, sort_keys=True)
        self.assertNotIn("Ignore the mapping", serialized)
        self.assertNotIn("server_claimed_name", serialized)
        self.assertNotIn('"arguments"', serialized)
        self.assertNotIn('"annotations"', serialized)

    def test_unknown_server_and_unmapped_tool_reject_before_evaluation(self):
        cases = (
            ("unknown-server.json", "mcp.mapping.unknown_server", "/server_id"),
            ("unmapped-tool.json", "mcp.mapping.unmapped_tool", "/tool_name"),
        )
        for proposal_name, code, path in cases:
            with self.subTest(proposal=proposal_name):
                result = evaluate_mcp_shadow(
                    load_policy(), load_mapping(), load_proposal(proposal_name)
                ).as_dict()
                self.assertEqual("normalization_rejected", result["outcome"])
                self.assertIsNone(result["decision_result"])
                self.assertEqual(code, result["reasons"][0]["code"])
                self.assertEqual(path, result["reasons"][0]["path"])

    def test_ambiguous_mapping_is_invalid_at_validation_time(self):
        mapping = load_mapping()
        mapping["entries"].append(deepcopy(mapping["entries"][0]))
        issues = validate_mcp_adapter_mapping(mapping)
        self.assertEqual(["mcp.mapping.ambiguous_key"], [issue.code for issue in issues])
        self.assertEqual("/entries/4", issues[0].path)
        self.assertEqual("/entries/0", issues[0].related_path)

        result = evaluate_mcp_shadow(load_policy(), mapping, load_proposal()).as_dict()
        self.assertEqual("invalid_input", result["outcome"])
        self.assertIsNone(result["decision_result"])
        self.assertTrue(result["proposed_evidence_record"]["proposal_only"])

    def test_mapping_unknown_fields_versions_and_lifecycle_are_invalid(self):
        unknown = load_mapping()
        unknown["entries"][0]["server_title"] = "server-claimed-name"
        unsupported = load_mapping()
        unsupported["schema_version"] = "9.9"
        invalid_lifecycle = load_mapping()
        invalid_lifecycle["mapping"]["review_at"] = invalid_lifecycle["mapping"][
            "effective_at"
        ]
        cases = (
            (unknown, "mcp.mapping.schema.unknown_field", "/entries/0/server_title"),
            (unsupported, "mcp.mapping.schema_version.unsupported", "/schema_version"),
            (invalid_lifecycle, "mcp.mapping.lifecycle_invalid", "/mapping/review_at"),
        )
        for mapping, code, path in cases:
            with self.subTest(code=code):
                issues = validate_mcp_adapter_mapping(mapping)
                self.assertEqual([code], [issue.code for issue in issues])
                self.assertEqual(path, issues[0].path)
                result = normalize_mcp_call(load_proposal(), mapping)
                self.assertEqual("invalid_input", result.outcome)

    def test_malformed_unknown_and_unsupported_proposal_fields_are_invalid(self):
        malformed = load_proposal("malformed.json")
        unknown = load_proposal()
        unknown["capability_id"] = "capability.spoofed"
        unsupported = load_proposal()
        unsupported["schema_version"] = "9.9"
        cases = (
            (malformed, "mcp.proposal.schema.required", "/"),
            (unknown, "mcp.proposal.schema.unknown_field", "/capability_id"),
            (unsupported, "mcp.proposal.schema_version.unsupported", "/schema_version"),
        )
        for proposal, code, path in cases:
            with self.subTest(code=code):
                result = normalize_mcp_call(proposal, load_mapping()).as_dict()
                self.assertEqual("invalid_input", result["outcome"])
                self.assertEqual(code, result["reasons"][0]["code"])
                self.assertEqual(path, result["reasons"][0]["path"])

    def test_arguments_are_never_coerced_and_floats_reject(self):
        float_result = normalize_mcp_call(
            load_proposal("float-arguments.json"), load_mapping()
        ).as_dict()
        self.assertEqual("rejected", float_result["outcome"])
        self.assertEqual("mcp.arguments.uncanonicalizable", float_result["reasons"][0]["code"])

        non_object = load_proposal()
        non_object["arguments"] = []
        non_object_result = normalize_mcp_call(non_object, load_mapping()).as_dict()
        self.assertEqual("invalid_input", non_object_result["outcome"])
        self.assertEqual("mcp.proposal.schema.type", non_object_result["reasons"][0]["code"])

    def test_lifecycle_missing_context_and_constraint_conflict_fail_closed(self):
        mapping = load_mapping()
        stale = deepcopy(mapping)
        stale["mapping"]["review_at"] = "2026-08-20T00:00:00Z"
        stale_result = normalize_mcp_call(load_proposal(), stale)
        self.assertEqual("rejected", stale_result.outcome)
        self.assertEqual(["mcp.mapping.stale"], reason_codes(stale_result))

        missing = normalize_mcp_call(
            load_proposal("missing-context.json"), mapping
        )
        self.assertEqual("rejected", missing.outcome)
        self.assertEqual(["mcp.context.missing_constraints"], reason_codes(missing))

        conflict_proposal = load_proposal()
        conflict_proposal["requested_constraints"] = deepcopy(
            mapping["entries"][0]["requested_constraints"]
        )
        equal = normalize_mcp_call(conflict_proposal, mapping)
        self.assertEqual("normalized", equal.outcome)
        conflict_proposal["requested_constraints"]["max_action_count"] = 2
        conflict = normalize_mcp_call(conflict_proposal, mapping)
        self.assertEqual("rejected", conflict.outcome)
        self.assertEqual(["mcp.context.constraints_conflict"], reason_codes(conflict))

    def test_equivalent_reordering_is_deterministic_and_inputs_are_not_mutated(self):
        policy = load_policy()
        mapping = load_mapping()
        proposal = load_proposal()
        reordered_mapping = deepcopy(mapping)
        reordered_mapping["entries"].reverse()
        reordered_mapping["mapping"]["provenance"]["authored_by"].reverse()
        reordered_mapping["mapping"]["provenance"]["approved_by"].reverse()
        originals = deepcopy((policy, mapping, proposal))

        first = evaluate_mcp_shadow(
            policy, mapping, proposal, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        second = evaluate_mcp_shadow(
            deepcopy(policy),
            reordered_mapping,
            deepcopy(proposal),
            trusted_identity_boundaries=reversed(sorted(TRUSTED_BOUNDARIES)),
        )

        self.assertEqual(first, second)
        self.assertEqual(originals, (policy, mapping, proposal))

    def test_cli_and_sdk_parity_and_exit_codes(self):
        normalize_sdk = normalize_mcp_call(load_proposal(), load_mapping()).as_dict()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli_main(
                ["mcp", "normalize", str(MAPPING_PATH), str(PROPOSALS / "browser-read.json")]
            )
        self.assertEqual(0, exit_code)
        self.assertEqual(normalize_sdk, json.loads(stdout.getvalue()))

        cases = (
            ("browser-read.json", 0, None, None, None),
            ("email-send.json", 3, None, None, None),
            ("denied.json", 4, None, None, None),
            ("unmapped-tool.json", 6, None, None, None),
            ("malformed.json", 2, None, None, None),
            ("email-send.json", 3, str(GRANT_PATH), str(STATE_PATH), "satisfied"),
        )
        for proposal_name, expected_exit, grant, state, approval_outcome in cases:
            with self.subTest(proposal=proposal_name, grant=grant):
                argv = [
                    "mcp",
                    "shadow",
                    str(POLICY_PATH),
                    str(MAPPING_PATH),
                    str(PROPOSALS / proposal_name),
                    "--trusted-identity-boundary",
                    "identity.reference",
                ]
                if grant is not None:
                    argv.extend(["--grant", grant, "--state", state])
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    actual_exit = cli_main(argv)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(expected_exit, actual_exit)
                if approval_outcome is not None:
                    self.assertEqual(
                        approval_outcome,
                        payload["approval_verification_result"]["outcome"],
                    )
                    self.assertEqual(
                        "require_approval", payload["decision_result"]["disposition"]
                    )

    def test_file_syntax_failure_still_emits_json_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            malformed_path = Path(directory) / "proposal.json"
            malformed_path.write_text("{", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = cli_main(
                    ["mcp", "normalize", str(MAPPING_PATH), str(malformed_path)]
                )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(2, exit_code)
        self.assertEqual("invalid_input", payload["outcome"])
        self.assertEqual("mcp.proposal.json.syntax", payload["reasons"][0]["code"])

    def test_contract_schemas_and_conformance_fixture(self):
        for name in (
            "mcp-call-proposal-v0.1.schema.json",
            "mcp-adapter-mapping-v0.1.schema.json",
            "mcp-normalization-result-v0.1.schema.json",
            "mcp-shadow-result-v0.1.schema.json",
        ):
            schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual("object", schema["type"])

        fixture = json.loads(
            (ROOT / "conformance" / "mcp-shadow-v0.1.json").read_text(
                encoding="utf-8"
            )
        )
        policy = load_policy_bundle(str(ROOT / fixture["policy_path"]))
        base_mapping = load_mcp_adapter_mapping(str(ROOT / fixture["mapping_path"]))
        results = {}
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                mapping = deepcopy(base_mapping)
                mutation = case.get("mapping_mutation")
                if mutation and mutation["operation"] == "duplicate_entry":
                    mapping["entries"].append(
                        deepcopy(mapping["entries"][mutation["entry_index"]])
                    )
                elif mutation and mutation["operation"] == "replace":
                    self.assertEqual("/mapping/review_at", mutation["path"])
                    mapping["mapping"]["review_at"] = mutation["value"]
                proposal = load_mcp_call_proposal(str(ROOT / case["proposal_path"]))
                grant = (
                    load_approval_grant(str(ROOT / case["grant_path"]))
                    if case.get("grant_path")
                    else None
                )
                state = (
                    load_approval_verification_state(str(ROOT / case["state_path"]))
                    if case.get("state_path")
                    else None
                )
                result = evaluate_mcp_shadow(
                    policy,
                    mapping,
                    proposal,
                    trusted_identity_boundaries=fixture["trusted_identity_boundaries"],
                    grant=grant,
                    verification_state=state,
                ).as_dict()
                expected = case["expected"]
                actual = {
                    "shadow_outcome": result["outcome"],
                    "normalization_outcome": result["normalization"]["outcome"],
                    "disposition": (
                        result["decision_result"]["disposition"]
                        if result["decision_result"] is not None
                        else None
                    ),
                    "reason_codes": [reason["code"] for reason in result["reasons"]],
                }
                if "approval_outcome" in expected:
                    actual["approval_outcome"] = result[
                        "approval_verification_result"
                    ]["outcome"]
                self.assertEqual(expected, actual)
                results[case["id"]] = result
                if case.get("comparison"):
                    reordered = deepcopy(mapping)
                    reordered["entries"].reverse()
                    reordered["mapping"]["provenance"]["authored_by"].reverse()
                    reordered["mapping"]["provenance"]["approved_by"].reverse()
                    repeated = evaluate_mcp_shadow(
                        deepcopy(policy),
                        reordered,
                        deepcopy(proposal),
                        trusted_identity_boundaries=fixture[
                            "trusted_identity_boundaries"
                        ],
                    ).as_dict()
                    self.assertEqual(result, repeated)
        spoofed = results["spoofed-annotation"]
        allowed = results["allow"]
        self.assertEqual(allowed["action_request"], spoofed["action_request"])
        self.assertEqual(allowed["decision_result"], spoofed["decision_result"])


if __name__ == "__main__":
    unittest.main()
