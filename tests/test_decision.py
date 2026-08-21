from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_governance import (
    ParameterEncodingError,
    canonical_parameters_digest,
    evaluate_action,
    evaluate_action_files,
    load_action_request,
    load_policy_bundle,
    validate_action_request,
)
from agent_governance.cli import main as cli_main


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "examples" / "policies" / "multi_agent_operations.json"
ALLOWED = ROOT / "examples" / "requests" / "browser_read_allowed.json"
APPROVAL = ROOT / "examples" / "requests" / "email_send_requires_approval.json"
DENIED = ROOT / "examples" / "requests" / "unmapped_action_denied.json"
TRUSTED_BOUNDARIES = {"identity.reference"}


def load_policy():
    return load_policy_bundle(str(POLICY))


def load_request(path=ALLOWED):
    return load_action_request(str(path))


def reason_codes(result):
    return [item["code"] for item in result.as_dict()["reasons"]]


def set_request_time(request, requested_at, authenticated_at, expires_at):
    request["requested_at"] = requested_at
    authentication = request["principal"]["authentication"]
    authentication["authenticated_at"] = authenticated_at
    authentication["expires_at"] = expires_at


class DecisionContractTests(unittest.TestCase):
    """Slice B conformance for AUT-001..006, DEC-001..008, and EVD-001."""

    def test_allowed_request_cites_authority_policy_controls_and_constraints(self):
        # AUT-001, AUT-003, DEC-001, DEC-002, DEC-007, DEC-008
        result = evaluate_action(
            load_policy(),
            load_request(),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()

        self.assertEqual("allow", result["disposition"])
        self.assertEqual(
            ["delegation.owner-to-researcher"],
            result["authority"]["delegation_path"],
        )
        self.assertEqual(
            ["control.research-browser"],
            [item["control_id"] for item in result["cited_controls"]],
        )
        self.assertEqual(1, result["effective_constraints"]["max_action_count"])
        self.assertEqual(
            "bundle.multi-agent-operations", result["policy"]["bundle_id"]
        )
        self.assertEqual("2026-08-21T20:55:00Z", result["valid_until"])
        self.assertEqual(
            result["valid_until"],
            result["proposed_evidence_record"]["decision"]["valid_until"],
        )

    def test_active_exception_returns_exact_approval_requirement(self):
        # DEC-001, DEC-002; approval is described but not collected or verified.
        result = evaluate_action(
            load_policy(),
            load_request(APPROVAL),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()

        self.assertEqual("require_approval", result["disposition"])
        self.assertEqual(
            "exception.communicator-email-pilot",
            result["cited_controls"][0]["exception_id"],
        )
        requirement = result["approval_requirements"][0]
        self.assertEqual("approval.external-email", requirement["approval_id"])
        self.assertEqual(1, requirement["quorum"])
        self.assertTrue(requirement["separation_of_duties"])
        self.assertEqual(
            ["capability", "parameters_digest", "resource", "subject"],
            requirement["bind_to"],
        )

    def test_invalid_approval_quorum_cannot_produce_approval_or_allow(self):
        # AUT-006, DEC-003
        policy = load_policy()
        policy["approvals"][0]["quorum"] = 2

        result = evaluate_action(
            policy,
            load_request(APPROVAL),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("policy.approval.invalid", reason_codes(result))

    def test_inactive_exception_restores_original_deny(self):
        # AUT-006, DEC-003
        request = load_request(APPROVAL)
        set_request_time(
            request,
            "2026-09-02T20:00:00Z",
            "2026-09-02T19:55:00Z",
            "2026-09-02T20:55:00Z",
        )

        result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("exception.inactive", reason_codes(result))
        self.assertIn("control.deny", reason_codes(result))

    def test_missing_request_authority_fields_fail_closed_with_evidence(self):
        # AUT-001, DEC-003, EVD-001, DX-006
        request = load_request()
        del request["principal"]

        result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        ).as_dict()

        self.assertEqual("deny", result["disposition"])
        self.assertIsNone(result["valid_until"])
        self.assertIn(
            "request.schema.required",
            [item["code"] for item in result["reasons"]],
        )
        self.assertTrue(result["proposed_evidence_record"]["proposal_only"])
        self.assertEqual(
            result["decision_id"],
            result["proposed_evidence_record"]["decision"]["decision_id"],
        )

    def test_untrusted_or_expired_identity_assertion_cannot_allow(self):
        # AUT-002, AUT-006, DEC-003
        policy = load_policy()
        request = load_request()

        untrusted = evaluate_action(policy, request)
        self.assertEqual("deny", untrusted.disposition)
        self.assertIn("identity.boundary_untrusted", reason_codes(untrusted))

        request["principal"]["authentication"]["expires_at"] = request["requested_at"]
        expired = evaluate_action(
            policy, request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        self.assertEqual("deny", expired.disposition)
        self.assertIn("identity.assertion_expired", reason_codes(expired))

    def test_confused_deputy_principal_has_no_transitive_authority(self):
        # AUT-003, AUT-005
        request = load_request()
        request["principal"]["actor_id"] = "human.risk-approver"

        result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("authority.not_granted", reason_codes(result))

    def test_inactive_delegation_fails_closed_at_request_time(self):
        # AUT-004, AUT-006
        policy = load_policy()
        delegation = next(
            item
            for item in policy["delegations"]
            if item["id"] == "delegation.owner-to-communicator"
        )
        delegation["valid_until"] = "2026-08-20T00:00:00Z"

        result = evaluate_action(
            policy,
            load_request(APPROVAL),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("authority.delegation_inactive", reason_codes(result))

    def test_delegation_depth_bounds_multi_hop_authority(self):
        # AUT-004, DEC-003
        request = load_request()
        request.update(
            {
                "request_id": "request.communicator-review-001",
                "actor_id": "agent.communicator",
                "capability_id": "capability.review-message",
                "action": "message.send",
                "resource_id": "channel.review",
            }
        )
        request["context"]["channel_id"] = "channel.review"
        request["context"]["data_classification"] = "internal"
        request["context"]["expected_side_effects"] = ["external_communication"]
        policy = load_policy()

        allowed = evaluate_action(
            policy, request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        ).as_dict()
        self.assertEqual("allow", allowed["disposition"])
        self.assertEqual(
            [
                "delegation.owner-to-researcher",
                "delegation.researcher-to-communicator",
            ],
            allowed["authority"]["delegation_path"],
        )

        first_hop = next(
            item
            for item in policy["delegations"]
            if item["id"] == "delegation.owner-to-researcher"
        )
        first_hop["max_depth"] = 0
        denied = evaluate_action(
            policy, request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        self.assertEqual("deny", denied.disposition)
        self.assertIn("policy.delegation.escalation", reason_codes(denied))

    def test_stale_policy_bundle_fails_closed(self):
        # AUT-006, DEC-003
        request = load_request()
        set_request_time(
            request,
            "2026-11-01T00:00:00Z",
            "2026-10-31T23:55:00Z",
            "2026-11-01T00:55:00Z",
        )

        result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("policy.stale", reason_codes(result))

    def test_equal_precedence_effects_resolve_restrictively(self):
        # DEC-004
        policy = load_policy()
        control = deepcopy(policy["policies"][0]["controls"][0])
        control["id"] = "control.research-browser-deny"
        control["effect"] = "deny"
        control.pop("constraints", None)
        policy["policies"][0]["controls"].append(control)

        result = evaluate_action(
            policy, load_request(), trusted_identity_boundaries=TRUSTED_BOUNDARIES
        ).as_dict()

        self.assertEqual("deny", result["disposition"])
        self.assertIn(
            "control.restrictive_precedence",
            [item["code"] for item in result["reasons"]],
        )
        self.assertEqual(2, len(result["cited_controls"]))

    def test_overlapping_active_exceptions_fail_closed(self):
        # DEC-003
        policy = load_policy()
        overlapping = deepcopy(policy["exceptions"][0])
        overlapping["id"] = "exception.communicator-email-overlap"
        policy["exceptions"].append(overlapping)

        result = evaluate_action(
            policy,
            load_request(APPROVAL),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("exception.conflict", reason_codes(result))

    def test_data_and_reversibility_constraints_are_machine_enforced(self):
        # DEC-007, DEC-008
        request = load_request()
        request["context"]["data_classification"] = "internal"
        data_result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        self.assertEqual("deny", data_result.disposition)
        self.assertIn(
            "constraint.data_classification_denied", reason_codes(data_result)
        )

        request = load_request()
        request["context"]["reversible"] = False
        reversible_result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        self.assertEqual("deny", reversible_result.disposition)
        self.assertIn(
            "constraint.reversibility_required", reason_codes(reversible_result)
        )

    def test_numeric_constraints_only_narrow_the_requested_envelope(self):
        # AUT-004, DEC-007, DEC-008
        policy = load_policy()
        control = policy["policies"][0]["controls"][0]
        control["constraints"]["max_cost"] = {
            "amount_minor": 100,
            "currency": "USD",
        }
        request = load_request()
        requested = request["context"]["requested_constraints"]
        requested["max_cost"]["amount_minor"] = 1000
        requested["max_duration_seconds"] = 3600
        requested["max_action_count"] = 50
        requested["max_delegation_depth"] = 2

        result = evaluate_action(
            policy, request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        ).as_dict()

        self.assertEqual("allow", result["disposition"])
        effective = result["effective_constraints"]
        self.assertEqual(100, effective["max_cost"]["amount_minor"])
        self.assertEqual(1800, effective["max_duration_seconds"])
        self.assertEqual(25, effective["max_action_count"])
        self.assertEqual(0, effective["max_delegation_depth"])

    def test_channel_capability_requires_the_exact_governed_channel(self):
        # DEC-008
        request = load_request()
        request.update(
            {
                "request_id": "request.review-message-001",
                "capability_id": "capability.review-message",
                "action": "message.send",
                "resource_id": "channel.review",
            }
        )
        request["context"]["channel_id"] = "channel.review"
        request["context"]["data_classification"] = "internal"
        request["context"]["expected_side_effects"] = ["external_communication"]

        allowed = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        self.assertEqual("allow", allowed.disposition)

        request["context"]["channel_id"] = None
        denied = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        self.assertEqual("deny", denied.disposition)
        self.assertIn("request.channel_required", reason_codes(denied))

    def test_equivalent_inputs_are_deterministic_and_not_mutated(self):
        # DEC-005, DEC-006, INT-003
        policy = load_policy()
        request = load_request(APPROVAL)
        request["context"]["expected_side_effects"].append("spend")
        reordered_policy = deepcopy(policy)
        reordered_policy["actors"].reverse()
        reordered_policy["roles"].reverse()
        reordered_policy["policies"][0]["controls"].reverse()
        reordered_request = deepcopy(request)
        reordered_request["context"]["expected_side_effects"].reverse()
        original_policy = deepcopy(policy)
        original_request = deepcopy(request)

        first = evaluate_action(
            policy, request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        )
        second = evaluate_action(
            reordered_policy,
            reordered_request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )

        self.assertEqual(first, second)
        self.assertEqual(original_policy, policy)
        self.assertEqual(original_request, request)

    def test_malformed_policy_and_request_each_return_deny_evidence(self):
        # DEC-003, EVD-001, DX-006
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            bad_policy = temporary / "policy.json"
            bad_request = temporary / "request.json"
            bad_policy.write_text("{", encoding="utf-8")
            bad_request.write_text("{", encoding="utf-8")
            result = evaluate_action_files(
                str(bad_policy),
                str(bad_request),
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            )

        self.assertEqual("deny", result.disposition)
        self.assertIn("policy.json.syntax", reason_codes(result))
        self.assertIn("request.json.syntax", reason_codes(result))
        self.assertTrue(result.proposed_evidence_record["proposal_only"])

    def test_unsupported_request_version_has_stable_location_and_code(self):
        # DEC-003, DX-006, DX-009
        request = load_request()
        request["schema_version"] = "9.9"

        result = evaluate_action(
            load_policy(), request, trusted_identity_boundaries=TRUSTED_BOUNDARIES
        ).as_dict()

        self.assertEqual("deny", result["disposition"])
        issue = result["reasons"][0]
        self.assertEqual("request.schema_version.unsupported", issue["code"])
        self.assertEqual("/schema_version", issue["path"])

    def test_cli_and_sdk_return_identical_contracts(self):
        # DX-003
        sdk_result = evaluate_action(
            load_policy(),
            load_request(),
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli_main(
                [
                    "policy",
                    "evaluate",
                    str(POLICY),
                    str(ALLOWED),
                    "--trusted-identity-boundary",
                    "identity.reference",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertEqual(sdk_result, json.loads(stdout.getvalue()))

    def test_contract_schemas_and_example_requests_are_valid_documents(self):
        # DEC-001, EVD-001, INT-003
        for name in (
            "action-request-v0.1.schema.json",
            "decision-result-v0.1.schema.json",
            "proposed-evidence-record-v0.1.schema.json",
        ):
            value = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual("object", value["type"])
        for path in (ALLOWED, APPROVAL, DENIED):
            self.assertEqual([], validate_action_request(load_request(path)))

    def test_shared_conformance_fixture_uses_the_public_evaluator(self):
        # DEC-001, DEC-002, DEC-005, DX-003
        fixture = json.loads(
            (ROOT / "conformance" / "decision-contract-v0.1.json").read_text(
                encoding="utf-8"
            )
        )
        policy = load_policy_bundle(str(ROOT / fixture["policy_path"]))
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                result = evaluate_action(
                    policy,
                    load_action_request(str(ROOT / case["request_path"])),
                    trusted_identity_boundaries=fixture[
                        "trusted_identity_boundaries"
                    ],
                ).as_dict()
                evidence = result["proposed_evidence_record"]["decision"]
                actual = {
                    "disposition": result["disposition"],
                    "reason_codes": evidence["reason_codes"],
                    "cited_control_ids": evidence["cited_control_ids"],
                    "approval_requirement_ids": evidence[
                        "approval_requirement_ids"
                    ],
                }
                self.assertEqual(case["expected"], actual)

    def test_parameter_binding_is_canonical_and_rejects_ambiguous_numbers(self):
        # AUT-001, DEC-005, INT-003
        first = canonical_parameters_digest(
            {"recipient": "a@example.test", "metadata": {"priority": 1}}
        )
        second = canonical_parameters_digest(
            {"metadata": {"priority": 1}, "recipient": "a@example.test"}
        )

        self.assertEqual(first, second)
        self.assertEqual(
            "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
            canonical_parameters_digest({}),
        )
        with self.assertRaises(ParameterEncodingError):
            canonical_parameters_digest({"ambiguous_float": 1.5})


if __name__ == "__main__":
    unittest.main()
