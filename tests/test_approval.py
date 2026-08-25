from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_governance import (
    ApprovalVerificationResult,
    evaluate_action,
    load_action_request,
    load_approval_grant,
    load_approval_verification_state,
    load_policy_bundle,
    validate_approval_grant,
    validate_approval_verification_state,
    verify_approval_grant,
    verify_approval_grant_files,
)
from agent_governance.cli import main as cli_main


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "examples" / "policies" / "multi_agent_operations.json"
REQUEST = ROOT / "examples" / "requests" / "email_send_requires_approval.json"
ALLOWED = ROOT / "examples" / "requests" / "browser_read_allowed.json"
TRUSTED_BOUNDARIES = {"identity.reference"}


def load_policy():
    return load_policy_bundle(str(POLICY))


def load_request(path=REQUEST):
    return load_action_request(str(path))


def approval_decision(policy, request):
    return evaluate_action(
        policy,
        request,
        trusted_identity_boundaries=TRUSTED_BOUNDARIES,
    )


def verification_state(**updates):
    value = {
        "schema_version": "0.1",
        "verified_at": "2026-08-21T20:10:00Z",
        "trusted_request_identity_boundaries": ["identity.reference"],
        "trusted_approver_identity_boundaries": ["identity.reference"],
        "revoked_grant_ids": [],
        "consumed_grant_ids": [],
    }
    value.update(updates)
    return value


def approval_entry(
    actor_id="human.risk-approver",
    approval_id="approval.external-email",
    assertion_id="assertion.risk-approval-001",
):
    return {
        "approval_id": approval_id,
        "approver_actor_id": actor_id,
        "approved_at": "2026-08-21T20:04:00Z",
        "identity": {
            "trust_boundary_id": "identity.reference",
            "assertion_id": assertion_id,
            "authenticated_at": "2026-08-21T20:03:00Z",
            "expires_at": "2026-08-21T20:30:00Z",
        },
        "rationale": {
            "code": "risk.reviewed",
            "reference": "ticket:GOV-100",
        },
    }


def exact_grant(request, decision, **updates):
    result = decision.as_dict() if hasattr(decision, "as_dict") else deepcopy(decision)
    value = {
        "schema_version": "0.1",
        "grant_id": "grant.email-send-001",
        "approval_requirement_ids": [
            item["approval_id"] for item in result["approval_requirements"]
        ],
        "binding": {
            "request_id": request["request_id"],
            "request_sha256": result["request_sha256"],
            "decision_id": result["decision_id"],
            "decision_disposition": "require_approval",
            "subject_actor_id": request["actor_id"],
            "capability_id": request["capability_id"],
            "resource_id": request["resource_id"],
            "parameters_digest": request["parameters_digest"],
            "policy": deepcopy(result["policy"]),
            "scope": deepcopy(result["effective_constraints"]),
        },
        "issued_at": "2026-08-21T20:05:00Z",
        "expires_at": "2026-08-21T20:50:00Z",
        "reuse_policy": "single_use",
        "approvals": [approval_entry()],
    }
    value.update(updates)
    return value


def reason_codes(result):
    return [item["code"] for item in result.as_dict()["reasons"]]


class ApprovalGrantTests(unittest.TestCase):
    """Approval Grant v0.1 conformance for APR-002 through APR-005."""

    def test_exact_valid_grant_satisfies_without_changing_decision(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)
        original_decision = decision.to_json()

        result = verify_approval_grant(
            policy, request, decision, grant, verification_state()
        )

        self.assertIsInstance(result, ApprovalVerificationResult)
        self.assertEqual("satisfied", result.outcome)
        self.assertEqual(["approval.satisfied"], reason_codes(result))
        self.assertEqual("require_approval", decision.disposition)
        self.assertEqual(original_decision, decision.to_json())
        self.assertEqual("2026-08-21T20:50:00Z", result.as_dict()["valid_until"])
        self.assertTrue(result.proposed_evidence_record["proposal_only"])

    def test_every_exact_binding_fails_closed_when_changed(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        base = exact_grant(request, decision)
        cases = (
            ("request_id", "request.other", "approval.request_mismatch"),
            (
                "request_sha256",
                "0" * 64,
                "approval.request_mismatch",
            ),
            ("decision_id", "decision." + "0" * 64, "approval.decision_mismatch"),
            ("subject_actor_id", "agent.researcher", "approval.subject_mismatch"),
            ("capability_id", "capability.email-draft", "approval.capability_mismatch"),
            ("resource_id", "tool.browser", "approval.resource_mismatch"),
            (
                "parameters_digest",
                "sha256:" + "0" * 64,
                "approval.parameters_mismatch",
            ),
        )
        for field, value, expected_code in cases:
            with self.subTest(field=field):
                grant = deepcopy(base)
                grant["binding"][field] = value
                result = verify_approval_grant(
                    policy, request, decision, grant, verification_state()
                )
                self.assertEqual("not_satisfied", result.outcome)
                self.assertIn(expected_code, reason_codes(result))

        grant = deepcopy(base)
        grant["binding"]["policy"]["source_sha256"] = "0" * 64
        self.assertIn(
            "approval.policy_mismatch",
            reason_codes(
                verify_approval_grant(
                    policy, request, decision, grant, verification_state()
                )
            ),
        )

        grant = deepcopy(base)
        grant["binding"]["scope"]["max_action_count"] = 2
        self.assertIn(
            "approval.scope_mismatch",
            reason_codes(
                verify_approval_grant(
                    policy, request, decision, grant, verification_state()
                )
            ),
        )

    def test_missing_malformed_or_tampered_inputs_fail_closed(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)

        missing = verify_approval_grant(
            policy, request, decision, None, verification_state()
        )
        self.assertEqual("not_satisfied", missing.outcome)
        self.assertIn("grant.schema.type", reason_codes(missing))

        malformed = deepcopy(grant)
        malformed.pop("binding")
        malformed["unexpected"] = True
        malformed_result = verify_approval_grant(
            policy, request, decision, malformed, verification_state()
        )
        self.assertIn("grant.schema.required", reason_codes(malformed_result))
        self.assertIn("grant.schema.unknown_field", reason_codes(malformed_result))

        tampered_decision = decision.as_dict()
        tampered_decision["effective_constraints"]["max_action_count"] = 2
        tampered_result = verify_approval_grant(
            policy, request, tampered_decision, grant, verification_state()
        )
        self.assertIn("approval.decision_mismatch", reason_codes(tampered_result))

        invalid_state = verification_state()
        invalid_state.pop("verified_at")
        state_result = verify_approval_grant(
            policy, request, decision, grant, invalid_state
        )
        self.assertIn("state.schema.required", reason_codes(state_result))

        malformed_values = (
            ("policy", {**policy, "bundle": []}),
            ("request", {**request, "request_id": 7}),
            ("decision", {**decision.as_dict(), "disposition": "unexpected"}),
            ("grant", {**grant, "grant_id": 7}),
            ("state", {**verification_state(), "verified_at": 7}),
        )
        inputs = {
            "policy": policy,
            "request": request,
            "decision": decision,
            "grant": grant,
            "state": verification_state(),
        }
        for field, malformed_value in malformed_values:
            with self.subTest(malformed_field=field):
                values = {**inputs, field: malformed_value}
                result = verify_approval_grant(**values).as_dict()
                self.assertEqual("not_satisfied", result["outcome"])
                self.assertTrue(result["reasons"])

    def test_expired_revoked_and_reused_grants_fail_closed(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)

        expired = deepcopy(grant)
        expired["expires_at"] = "2026-08-21T20:09:00Z"
        self.assertIn(
            "approval.expired",
            reason_codes(
                verify_approval_grant(
                    policy, request, decision, expired, verification_state()
                )
            ),
        )

        revoked_state = verification_state(
            revoked_grant_ids=[grant["grant_id"]]
        )
        self.assertIn(
            "approval.revoked",
            reason_codes(
                verify_approval_grant(
                    policy, request, decision, grant, revoked_state
                )
            ),
        )

        reused_state = verification_state(
            consumed_grant_ids=[grant["grant_id"]]
        )
        self.assertIn(
            "approval.reused",
            reason_codes(
                verify_approval_grant(
                    policy, request, decision, grant, reused_state
                )
            ),
        )

    def test_quorum_separation_eligibility_and_identity_are_enforced(self):
        policy = load_policy()
        policy["actors"].append(
            {
                "id": "human.second-risk-approver",
                "kind": "human",
                "display_name": "Second Risk Approver",
                "roles": ["role.risk-approver"],
            }
        )
        policy["approvals"][0]["quorum"] = 2
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)
        insufficient = verify_approval_grant(
            policy, request, decision, grant, verification_state()
        )
        self.assertIn("approval.insufficient_quorum", reason_codes(insufficient))

        grant["approvals"].append(
            approval_entry(
                actor_id="human.second-risk-approver",
                assertion_id="assertion.risk-approval-002",
            )
        )
        self.assertEqual(
            "satisfied",
            verify_approval_grant(
                policy, request, decision, grant, verification_state()
            ).outcome,
        )

        self_policy = load_policy()
        communicator = next(
            actor
            for actor in self_policy["actors"]
            if actor["id"] == "agent.communicator"
        )
        communicator["roles"].append("role.risk-approver")
        self_decision = approval_decision(self_policy, request)
        self_grant = exact_grant(request, self_decision)
        self_grant["approvals"] = [
            approval_entry(
                actor_id="agent.communicator",
                assertion_id="assertion.self-approval-001",
            )
        ]
        self_result = verify_approval_grant(
            self_policy,
            request,
            self_decision,
            self_grant,
            verification_state(),
        )
        self.assertIn("approval.self_approved", reason_codes(self_result))

        untrusted_state = verification_state(
            trusted_approver_identity_boundaries=[]
        )
        untrusted = verify_approval_grant(
            load_policy(),
            request,
            approval_decision(load_policy(), request),
            exact_grant(request, approval_decision(load_policy(), request)),
            untrusted_state,
        )
        self.assertIn("approval.approver_untrusted", reason_codes(untrusted))

        untrusted_request_state = verification_state(
            trusted_request_identity_boundaries=[]
        )
        untrusted_request = verify_approval_grant(
            load_policy(),
            request,
            approval_decision(load_policy(), request),
            exact_grant(request, approval_decision(load_policy(), request)),
            untrusted_request_state,
        )
        self.assertIn(
            "approval.decision_mismatch", reason_codes(untrusted_request)
        )
        self.assertIn(
            "approval.decision_not_required", reason_codes(untrusted_request)
        )

        stale_identity_grant = exact_grant(
            request, approval_decision(load_policy(), request)
        )
        stale_identity_grant["approvals"][0]["identity"][
            "expires_at"
        ] = stale_identity_grant["approvals"][0]["approved_at"]
        stale_identity = verify_approval_grant(
            load_policy(),
            request,
            approval_decision(load_policy(), request),
            stale_identity_grant,
            verification_state(),
        )
        self.assertIn(
            "approval.approver_assertion_stale", reason_codes(stale_identity)
        )

    def test_expiry_cannot_exceed_rule_or_decision(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)
        grant["expires_at"] = "2026-08-21T21:06:00Z"

        result = verify_approval_grant(
            policy, request, decision, grant, verification_state()
        )

        self.assertIn("approval.expiry_exceeds_rule", reason_codes(result))
        self.assertIn("approval.expiry_exceeds_decision", reason_codes(result))

    def test_allow_or_deny_decision_cannot_be_approved(self):
        policy = load_policy()
        approval_request = load_request()
        approval = approval_decision(policy, approval_request)
        grant = exact_grant(approval_request, approval)
        allowed_request = load_request(ALLOWED)
        allowed_decision = evaluate_action(
            policy,
            allowed_request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )

        result = verify_approval_grant(
            policy,
            allowed_request,
            allowed_decision,
            grant,
            verification_state(),
        )

        self.assertEqual("not_satisfied", result.outcome)
        self.assertIn("approval.decision_not_required", reason_codes(result))

    def test_verification_is_deterministic_and_does_not_mutate_inputs(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)
        state = verification_state()
        originals = tuple(
            deepcopy(value)
            for value in (policy, request, decision.as_dict(), grant, state)
        )

        first = verify_approval_grant(policy, request, decision, grant, state)
        second = verify_approval_grant(
            deepcopy(policy),
            deepcopy(request),
            decision.as_dict(),
            deepcopy(grant),
            deepcopy(state),
        )

        self.assertEqual(first, second)
        self.assertEqual(originals[0], policy)
        self.assertEqual(originals[1], request)
        self.assertEqual(originals[2], decision.as_dict())
        self.assertEqual(originals[3], grant)
        self.assertEqual(originals[4], state)

    def test_cli_and_sdk_return_identical_verification_contracts(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)
        state = verification_state()
        sdk_result = verify_approval_grant(
            policy, request, decision, grant, state
        ).as_dict()

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            decision_path = temporary / "decision.json"
            grant_path = temporary / "grant.json"
            state_path = temporary / "state.json"
            decision_path.write_text(decision.to_json(), encoding="utf-8")
            grant_path.write_text(json.dumps(grant), encoding="utf-8")
            state_path.write_text(json.dumps(state), encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = cli_main(
                    [
                        "approval",
                        "verify",
                        str(POLICY),
                        str(REQUEST),
                        str(decision_path),
                        str(grant_path),
                        "--state",
                        str(state_path),
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertEqual(sdk_result, json.loads(stdout.getvalue()))

            missing = verify_approval_grant_files(
                str(POLICY),
                str(REQUEST),
                str(decision_path),
                str(temporary / "missing-grant.json"),
                str(state_path),
            )
            self.assertEqual("not_satisfied", missing.outcome)
            self.assertEqual(["grant.json.read"], reason_codes(missing))

    def test_contract_validators_reject_unknown_fields(self):
        policy = load_policy()
        request = load_request()
        decision = approval_decision(policy, request)
        grant = exact_grant(request, decision)
        grant["unknown"] = True
        state = verification_state()
        state["unknown"] = True

        self.assertIn(
            "schema.unknown_field",
            [issue.code for issue in validate_approval_grant(grant)],
        )
        self.assertIn(
            "schema.unknown_field",
            [issue.code for issue in validate_approval_verification_state(state)],
        )

    def test_contract_schemas_examples_and_conformance_fixture(self):
        for name in (
            "approval-grant-v0.1.schema.json",
            "approval-verification-state-v0.1.schema.json",
            "approval-verification-result-v0.1.schema.json",
        ):
            value = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual("object", value["type"])

        fixture = json.loads(
            (ROOT / "conformance" / "approval-grant-v0.1.json").read_text(
                encoding="utf-8"
            )
        )
        policy = load_policy_bundle(str(ROOT / fixture["policy_path"]))
        request = load_action_request(str(ROOT / fixture["request_path"]))
        decision = evaluate_action(
            policy,
            request,
            trusted_identity_boundaries=fixture["trusted_identity_boundaries"],
        )
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                grant = load_approval_grant(str(ROOT / case["grant_path"]))
                state = load_approval_verification_state(
                    str(ROOT / case["state_path"])
                )
                self.assertEqual([], validate_approval_grant(grant))
                self.assertEqual([], validate_approval_verification_state(state))
                result = verify_approval_grant(
                    policy, request, decision, grant, state
                ).as_dict()
                actual = {
                    "outcome": result["outcome"],
                    "reason_codes": [
                        reason["code"] for reason in result["reasons"]
                    ],
                }
                self.assertEqual(case["expected"], actual)


if __name__ == "__main__":
    unittest.main()
