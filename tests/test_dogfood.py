from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_governance import (
    evaluate_action,
    load_action_request,
    load_policy_bundle,
    validate_action_request,
    validate_policy_bundle,
)
from agent_governance.cli import main as cli_main
from dogfood.record_observation import (
    load_observation_schema,
    record_observation,
    validate_observation,
)


ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "dogfood"
POLICY = DOGFOOD / "policy.json"
EXPECTED = DOGFOOD / "expected.json"
TRUSTED_BOUNDARIES = {"identity.dogfood-local"}


def reason_codes(result):
    return [item["code"] for item in result.as_dict()["reasons"]]


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DogfoodPhaseOneTests(unittest.TestCase):
    """Dogfood 0 Phase 1 checks for AUT, DEC, EVD, and DX requirements."""

    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy_bundle(str(POLICY))
        cls.expected = json.loads(EXPECTED.read_text(encoding="utf-8"))

    def test_policy_is_valid_fail_closed_and_contains_planned_actors(self):
        # AUT-001, AUT-003, AUT-006, DEC-003
        self.assertEqual([], validate_policy_bundle(self.policy))
        self.assertEqual("deny", self.policy["bundle"]["default_effect"])
        self.assertEqual(
            {
                "human.maintainer",
                "agent.developer",
                "agent.reviewer",
                "service.github",
            },
            {item["id"] for item in self.policy["actors"]},
        )

    def test_expected_manifest_covers_exactly_fourteen_baseline_scenarios(self):
        # DX-007
        cases = self.expected["cases"]
        self.assertEqual(14, len(cases))
        self.assertEqual(14, len({item["id"] for item in cases}))
        self.assertEqual(
            14,
            len(list((DOGFOOD / "requests").glob("*.json"))),
        )
        for case in cases:
            self.assertTrue((ROOT / case["request_path"]).is_file())

    def test_every_fixture_matches_expected_decision_and_is_deterministic(self):
        # AUT-001, AUT-003, AUT-006, DEC-001..007, EVD-001, DX-007
        for case in self.expected["cases"]:
            with self.subTest(case=case["id"]):
                request = load_action_request(str(ROOT / case["request_path"]))
                request_issues = validate_action_request(request)
                self.assertEqual(case["valid_request"], not request_issues)

                first = evaluate_action(
                    self.policy,
                    request,
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                )
                second = evaluate_action(
                    deepcopy(self.policy),
                    deepcopy(request),
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                )
                self.assertEqual(first, second)

                result = first.as_dict()
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
                self.assertTrue(result["proposed_evidence_record"]["proposal_only"])

    def test_sdk_and_cli_are_equivalent_for_every_fixture(self):
        # DEC-005, DX-003
        exit_codes = {"allow": 0, "require_approval": 3, "deny": 4}
        for case in self.expected["cases"]:
            with self.subTest(case=case["id"]):
                request_path = ROOT / case["request_path"]
                sdk = evaluate_action(
                    self.policy,
                    load_action_request(str(request_path)),
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                ).as_dict()
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli_main(
                        [
                            "policy",
                            "evaluate",
                            str(POLICY),
                            str(request_path),
                            "--trusted-identity-boundary",
                            "identity.dogfood-local",
                        ]
                    )
                self.assertEqual(exit_codes[sdk["disposition"]], exit_code)
                self.assertEqual("", stderr.getvalue())
                self.assertEqual(sdk, json.loads(stdout.getvalue()))

    def test_stale_policy_context_fails_closed(self):
        # AUT-006, DEC-003
        request = load_action_request(
            str(DOGFOOD / "requests" / "01_repository_read_allowed.json")
        )
        request["requested_at"] = "2026-12-01T12:30:00Z"
        authentication = request["principal"]["authentication"]
        authentication["authenticated_at"] = "2026-12-01T12:00:00Z"
        authentication["expires_at"] = "2026-12-01T14:00:00Z"

        result = evaluate_action(
            self.policy,
            request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )

        self.assertEqual("deny", result.disposition)
        self.assertIn("policy.stale", reason_codes(result))

    def test_reviewer_can_inspect_but_cannot_edit(self):
        # AUT-003, DEC-003
        request = load_action_request(
            str(DOGFOOD / "requests" / "01_repository_read_allowed.json")
        )
        request["actor_id"] = "agent.reviewer"
        allowed = evaluate_action(
            self.policy,
            request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )
        self.assertEqual("allow", allowed.disposition)

        request.update(
            {
                "capability_id": "capability.documentation-edit",
                "action": "documentation.edit",
                "resource_id": "data.repository-documents",
            }
        )
        denied = evaluate_action(
            self.policy,
            request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )
        self.assertEqual("deny", denied.disposition)
        self.assertIn("authority.not_granted", reason_codes(denied))

    def test_non_baseline_modeled_capabilities_have_explicit_results(self):
        # AUT-003, DEC-001, DEC-003
        base = load_action_request(
            str(DOGFOOD / "requests" / "03_documentation_edit_allowed.json")
        )
        cases = (
            (
                "capability.source-edit",
                "source.edit",
                "data.repository-source",
                "allow",
                "control.allow",
            ),
            (
                "capability.tests-edit",
                "tests.edit",
                "data.repository-tests",
                "allow",
                "control.allow",
            ),
            (
                "capability.dependency-change",
                "dependency.change",
                "data.package-metadata",
                "require_approval",
                "control.require_approval",
            ),
            (
                "capability.remote-delete",
                "github.remote-delete",
                "service.github-repository",
                "deny",
                "control.deny",
            ),
            (
                "capability.release-create",
                "github.release",
                "service.github-repository",
                "deny",
                "control.deny",
            ),
        )
        for capability_id, action, resource_id, disposition, reason_code in cases:
            with self.subTest(capability=capability_id):
                request = deepcopy(base)
                request.update(
                    {
                        "capability_id": capability_id,
                        "action": action,
                        "resource_id": resource_id,
                    }
                )
                result = evaluate_action(
                    self.policy,
                    request,
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                )
                self.assertEqual(disposition, result.disposition)
                self.assertIn(reason_code, reason_codes(result))

    def test_observation_schema_is_closed_and_non_enforcing(self):
        # EVD-004, DX-005
        schema = load_observation_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["enforced"]["const"])
        self.assertEqual("shadow", schema["properties"]["mode"]["const"])
        self.assertTrue(
            schema["properties"]["proposed_evidence"]["properties"][
                "proposal_only"
            ]["const"]
        )
        for field in (
            "raw_parameters",
            "prompt",
            "chain_of_thought",
            "secret",
            "credential",
            "personal_data",
        ):
            self.assertNotIn(field, schema["properties"])

    def test_recorder_retains_minimized_reproducible_artifacts(self):
        # DEC-005, EVD-001, EVD-004, DX-005
        request_path = DOGFOOD / "requests" / "01_repository_read_allowed.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            observation_path = record_observation(
                policy_path=POLICY,
                request_path=request_path,
                output_dir=output,
                observation_id="observation.dogfood.001",
                observed_at="2026-08-22T12:31:00Z",
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=False,
                normalization_duration_ms=45000,
                mapping_confidence="exact",
                friction_code="none",
            )
            observation = json.loads(observation_path.read_text(encoding="utf-8"))
            self.assertEqual([], validate_observation(observation))
            self.assertFalse(observation["enforced"])
            self.assertEqual("shadow", observation["mode"])
            self.assertFalse(observation["action_occurred"])

            for section, filename in (
                ("request", "request.json"),
                ("policy", "policy.json"),
                ("decision", "decision.json"),
                ("proposed_evidence", "proposed-evidence.json"),
            ):
                artifact = observation_path.parent / "artifacts" / filename
                self.assertTrue(artifact.is_file())
                self.assertEqual(observation[section]["sha256"], sha256_file(artifact))

            retained_policy = load_policy_bundle(
                str(observation_path.parent / "artifacts" / "policy.json")
            )
            retained_request = load_action_request(
                str(observation_path.parent / "artifacts" / "request.json")
            )
            reproduced = evaluate_action(
                retained_policy,
                retained_request,
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            ).as_dict()
            retained_decision = json.loads(
                (observation_path.parent / "artifacts" / "decision.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(retained_decision, reproduced)

            rows = (output / "observations.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(1, len(rows))
            self.assertEqual(observation, json.loads(rows[0]))

    def test_observation_validation_rejects_prohibited_and_incomplete_records(self):
        # EVD-004, DX-005
        request_path = DOGFOOD / "requests" / "01_repository_read_allowed.json"
        with tempfile.TemporaryDirectory() as directory:
            observation_path = record_observation(
                policy_path=POLICY,
                request_path=request_path,
                output_dir=Path(directory),
                observation_id="observation.dogfood.validation",
                observed_at="2026-08-22T12:31:00Z",
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=False,
                normalization_duration_ms=1000,
                mapping_confidence="exact",
                friction_code="none",
            )
            observation = json.loads(observation_path.read_text(encoding="utf-8"))

        raw_parameters = deepcopy(observation)
        raw_parameters["request"]["raw_parameters"] = {"token": "not-retained"}
        self.assertTrue(validate_observation(raw_parameters))

        full_prompt = deepcopy(observation)
        full_prompt["full_prompt"] = "not retained"
        self.assertTrue(validate_observation(full_prompt))

        incomplete = deepcopy(observation)
        del incomplete["decision"]
        self.assertTrue(validate_observation(incomplete))

        impossible_approval = deepcopy(observation)
        impossible_approval["out_of_band_approval"] = {
            "requested": False,
            "received": True,
        }
        self.assertTrue(validate_observation(impossible_approval))

    def test_recorder_rejects_malformed_requests_and_does_not_overwrite(self):
        # DEC-003, EVD-004
        malformed = DOGFOOD / "requests" / "14_malformed_request_denied.json"
        valid = DOGFOOD / "requests" / "01_repository_read_allowed.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            common = {
                "policy_path": POLICY,
                "output_dir": output,
                "observation_id": "observation.dogfood.no-overwrite",
                "observed_at": "2026-08-22T12:31:00Z",
                "trusted_identity_boundaries": TRUSTED_BOUNDARIES,
                "maintainer_expected_disposition": "allow",
                "approval_requested": False,
                "approval_received": False,
                "action_occurred": False,
                "normalization_duration_ms": 1000,
                "mapping_confidence": "exact",
                "friction_code": "none",
            }
            with self.assertRaises(ValueError):
                record_observation(request_path=malformed, **common)

            record_observation(request_path=valid, **common)
            with self.assertRaises(FileExistsError):
                record_observation(request_path=valid, **common)

    def test_live_observations_are_ignored_and_untracked(self):
        # DX-005
        ignore_rules = (DOGFOOD / ".gitignore").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertIn("observations/", ignore_rules)
        tracked = subprocess.run(
            ["git", "ls-files", "--", "dogfood/observations"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual("", tracked.stdout)


if __name__ == "__main__":
    unittest.main()
