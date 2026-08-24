from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
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
from dogfood.report_observations import ObservationReportError, report_observations


ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "dogfood"
POLICY = DOGFOOD / "policy.json"
EXPECTED = DOGFOOD / "expected.json"
TRUSTED_BOUNDARIES = {"identity.dogfood-local"}


def fixed_recorder_clock():
    return datetime(2026, 8, 22, 12, 32, tzinfo=timezone.utc)


def reason_codes(result):
    return [item["code"] for item in result.as_dict()["reasons"]]


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DogfoodTests(unittest.TestCase):
    """Dogfood 0 checks for AUT, DEC, EVD, and DX requirements."""

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

    def test_expected_manifest_covers_exactly_fifteen_baseline_scenarios(self):
        # DX-007
        cases = self.expected["cases"]
        self.assertEqual(15, len(cases))
        self.assertEqual(15, len({item["id"] for item in cases}))
        self.assertEqual(
            15,
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

    def test_local_branch_creation_is_developer_only_reversible_and_single_action(self):
        # AUT-003, DEC-001, DEC-003
        request = load_action_request(
            str(DOGFOOD / "requests" / "15_local_branch_create_allowed.json")
        )
        allowed = evaluate_action(
            self.policy,
            request,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        ).as_dict()
        self.assertEqual("allow", allowed["disposition"])
        self.assertEqual(1, allowed["effective_constraints"]["max_action_count"])
        self.assertTrue(allowed["effective_constraints"]["require_reversible"])

        reviewer = deepcopy(request)
        reviewer["actor_id"] = "agent.reviewer"
        reviewer_result = evaluate_action(
            self.policy,
            reviewer,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )
        self.assertEqual("deny", reviewer_result.disposition)
        self.assertIn("authority.not_granted", reason_codes(reviewer_result))

        irreversible = deepcopy(request)
        irreversible["context"]["reversible"] = False
        irreversible_result = evaluate_action(
            self.policy,
            irreversible,
            trusted_identity_boundaries=TRUSTED_BOUNDARIES,
        )
        self.assertEqual("deny", irreversible_result.disposition)
        self.assertIn(
            "constraint.reversibility_required", reason_codes(irreversible_result)
        )

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
        self.assertEqual("0.2", schema["properties"]["schema_version"]["const"])
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
                activity_id="activity.dogfood.repository-read",
                action_reported_at="2026-08-22T12:31:00Z",
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=False,
                material=False,
                decision_usefulness="useful",
                normalization_duration_ms=45000,
                mapping_confidence="exact",
                friction_codes=(),
                clock=fixed_recorder_clock,
            )
            observation = json.loads(observation_path.read_text(encoding="utf-8"))
            self.assertEqual([], validate_observation(observation))
            self.assertFalse(observation["enforced"])
            self.assertEqual("shadow", observation["mode"])
            self.assertFalse(observation["action_occurred"])
            self.assertEqual("2026-08-22T12:32:00Z", observation["recorded_at"])
            self.assertEqual(
                "2026-08-22T12:31:00Z", observation["action_reported_at"]
            )
            self.assertTrue(observation["request"]["valid"])

            for section, filename in (
                ("request", "request.json"),
                ("policy", "policy.json"),
                ("decision", "decision.json"),
                ("proposed_evidence", "proposed-evidence.json"),
            ):
                artifact = observation_path.parent / "artifacts" / filename
                self.assertTrue(artifact.is_file())
                expected_digest = observation[section].get(
                    "artifact_sha256", observation[section]["sha256"]
                )
                self.assertEqual(expected_digest, sha256_file(artifact))

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
                activity_id="activity.dogfood.validation",
                action_reported_at=None,
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=False,
                material=False,
                decision_usefulness="unknown",
                normalization_duration_ms=1000,
                mapping_confidence="exact",
                friction_codes=("goal-assumption", "identity-assumption"),
                clock=fixed_recorder_clock,
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

        duplicate_friction = deepcopy(observation)
        duplicate_friction["friction_codes"] = [
            "goal-assumption",
            "goal-assumption",
        ]
        self.assertTrue(validate_observation(duplicate_friction))

    def test_recorder_retains_invalid_requests_fail_closed_and_does_not_overwrite(self):
        # DEC-003, EVD-001, EVD-004
        malformed = DOGFOOD / "requests" / "14_malformed_request_denied.json"
        valid = DOGFOOD / "requests" / "01_repository_read_allowed.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            common = {
                "policy_path": POLICY,
                "output_dir": output,
                "observation_id": "observation.dogfood.no-overwrite",
                "activity_id": "activity.dogfood.invalid-request",
                "action_reported_at": "2026-08-22T12:31:00Z",
                "trusted_identity_boundaries": TRUSTED_BOUNDARIES,
                "maintainer_expected_disposition": "deny",
                "approval_requested": False,
                "approval_received": False,
                "action_occurred": False,
                "material": False,
                "decision_usefulness": "useful",
                "normalization_duration_ms": 1000,
                "mapping_confidence": "exact",
                "friction_codes": ("request-construction",),
                "clock": fixed_recorder_clock,
            }
            observation_path = record_observation(request_path=malformed, **common)
            observation = json.loads(observation_path.read_text(encoding="utf-8"))
            self.assertFalse(observation["request"]["valid"])
            self.assertEqual("deny", observation["decision"]["disposition"])
            self.assertIn(
                "request.schema.required", observation["decision"]["reason_codes"]
            )
            self.assertEqual([], observation["decision"]["approval_requirement_ids"])

            invalid_identifier = json.loads(malformed.read_text(encoding="utf-8"))
            invalid_identifier["action"] = "not a valid identifier"
            invalid_path = Path(directory) / "invalid-identifier.json"
            invalid_path.write_text(json.dumps(invalid_identifier), encoding="utf-8")
            invalid_observation = record_observation(
                request_path=invalid_path,
                **{
                    **common,
                    "observation_id": "observation.dogfood.invalid-identifier",
                },
            )
            invalid_value = json.loads(
                invalid_observation.read_text(encoding="utf-8")
            )
            self.assertIsNone(invalid_value["action"]["action"])

            invalid_number = load_action_request(str(valid))
            invalid_number["context"]["requested_constraints"][
                "max_duration_seconds"
            ] = 1.5
            invalid_number_path = Path(directory) / "invalid-number.json"
            invalid_number_path.write_text(
                json.dumps(invalid_number), encoding="utf-8"
            )
            number_observation = record_observation(
                request_path=invalid_number_path,
                **{
                    **common,
                    "observation_id": "observation.dogfood.invalid-number",
                },
            )
            number_value = json.loads(
                number_observation.read_text(encoding="utf-8")
            )
            self.assertNotEqual(
                number_value["request"]["sha256"],
                number_value["request"]["artifact_sha256"],
            )
            report = report_observations(
                output_dir=output,
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            )
            self.assertEqual(3, report["metrics"]["invalid_requests"]["numerator"])

            with self.assertRaises(FileExistsError):
                record_observation(request_path=valid, **common)

    def test_recorder_rejects_unknown_invalid_request_fields(self):
        # EVD-004
        request = load_action_request(
            str(DOGFOOD / "requests" / "01_repository_read_allowed.json")
        )
        request["raw_parameters"] = {"secret": "not-retained"}
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown fields"):
                record_observation(
                    policy_path=POLICY,
                    request_path=request_path,
                    output_dir=Path(directory) / "output",
                    observation_id="observation.dogfood.unknown-field",
                    activity_id="activity.dogfood.unknown-field",
                    action_reported_at=None,
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                    maintainer_expected_disposition="deny",
                    approval_requested=False,
                    approval_received=False,
                    action_occurred=False,
                    material=False,
                    decision_usefulness="useful",
                    normalization_duration_ms=1000,
                    mapping_confidence="ambiguous",
                    friction_codes=("request-construction",),
                    clock=fixed_recorder_clock,
                )

    def test_reporter_verifies_v02_and_legacy_v01_observations(self):
        # DEC-005, EVD-001, EVD-004, DX-006
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            first_path = record_observation(
                policy_path=POLICY,
                request_path=DOGFOOD / "requests" / "01_repository_read_allowed.json",
                output_dir=output,
                observation_id="observation.dogfood.report-v02",
                activity_id="activity.dogfood.report-read",
                action_reported_at="2026-08-22T12:31:00Z",
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=True,
                material=False,
                decision_usefulness="useful",
                normalization_duration_ms=1000,
                mapping_confidence="exact",
                friction_codes=(),
                clock=fixed_recorder_clock,
            )
            second_path = record_observation(
                policy_path=POLICY,
                request_path=DOGFOOD / "requests" / "03_documentation_edit_allowed.json",
                output_dir=output,
                observation_id="observation.dogfood.report-v01",
                activity_id="activity.dogfood.report-edit",
                action_reported_at="2026-08-22T12:31:00Z",
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=True,
                material=True,
                decision_usefulness="useful",
                normalization_duration_ms=3000,
                mapping_confidence="exact",
                friction_codes=(),
                clock=fixed_recorder_clock,
            )
            legacy = json.loads(second_path.read_text(encoding="utf-8"))
            legacy["schema_version"] = "0.1"
            legacy["observed_at"] = legacy.pop("action_reported_at")
            legacy.pop("activity_id")
            legacy.pop("recorded_at")
            legacy.pop("material")
            legacy.pop("decision_usefulness")
            legacy.pop("friction_codes")
            legacy["friction_code"] = "none"
            legacy["request"].pop("valid")
            legacy["request"].pop("artifact_sha256")
            second_path.write_text(
                json.dumps(legacy, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            first = json.loads(first_path.read_text(encoding="utf-8"))
            (output / "observations.jsonl").write_text(
                "\n".join(
                    json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                    for item in (first, legacy)
                )
                + "\n",
                encoding="utf-8",
            )

            report = report_observations(
                output_dir=output,
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            )
            self.assertTrue(report["verified"])
            self.assertEqual(2, report["observations"]["count"])
            self.assertEqual(
                {"0.1": 1, "0.2": 1}, report["observations"]["schema_versions"]
            )
            self.assertEqual(
                {"numerator": 1, "denominator": 1, "percentage": 100.0},
                report["metrics"]["mapping_coverage"],
            )
            self.assertEqual(2000.0, report["metrics"]["normalization_effort"]["median_ms"])

    def test_reporter_groups_retries_and_rejects_cross_observation_paths(self):
        # EVD-001, EVD-004, DX-006
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            paths = []
            for observation_id, request_name, expected in (
                (
                    "observation.dogfood.retry-1",
                    "14_malformed_request_denied.json",
                    "deny",
                ),
                (
                    "observation.dogfood.retry-2",
                    "01_repository_read_allowed.json",
                    "allow",
                ),
            ):
                paths.append(
                    record_observation(
                        policy_path=POLICY,
                        request_path=DOGFOOD / "requests" / request_name,
                        output_dir=output,
                        observation_id=observation_id,
                        activity_id="activity.dogfood.retry",
                        action_reported_at=None,
                        trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                        maintainer_expected_disposition=expected,
                        approval_requested=False,
                        approval_received=False,
                        action_occurred=False,
                        material=False,
                        decision_usefulness="useful",
                        normalization_duration_ms=1000,
                        mapping_confidence="exact",
                        friction_codes=("request-construction",),
                        clock=fixed_recorder_clock,
                    )
                )

            report = report_observations(
                output_dir=output,
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            )
            self.assertEqual(2, report["observations"]["count"])
            self.assertEqual(1, report["observations"]["logical_activity_count"])
            self.assertEqual(
                {"numerator": 1, "denominator": 2, "percentage": 50.0},
                report["metrics"]["invalid_requests"],
            )

            first = json.loads(paths[0].read_text(encoding="utf-8"))
            second = json.loads(paths[1].read_text(encoding="utf-8"))
            first["request"]["artifact_ref"] = second["request"]["artifact_ref"]
            paths[0].write_text(
                json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (output / "observations.jsonl").write_text(
                "\n".join(
                    json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                    for item in (first, second)
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ObservationReportError, "escapes its observation directory"
            ):
                report_observations(
                    output_dir=output,
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                )

    def test_reporter_fails_on_digest_or_index_corruption(self):
        # EVD-001, EVD-004, DX-006
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            observation_path = record_observation(
                policy_path=POLICY,
                request_path=DOGFOOD / "requests" / "01_repository_read_allowed.json",
                output_dir=output,
                observation_id="observation.dogfood.corrupt",
                activity_id="activity.dogfood.corrupt",
                action_reported_at=None,
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                maintainer_expected_disposition="allow",
                approval_requested=False,
                approval_received=False,
                action_occurred=False,
                material=False,
                decision_usefulness="unknown",
                normalization_duration_ms=1000,
                mapping_confidence="exact",
                friction_codes=(),
                clock=fixed_recorder_clock,
            )
            decision_path = observation_path.parent / "artifacts" / "decision.json"
            decision_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ObservationReportError, "digest mismatch"):
                report_observations(
                    output_dir=output,
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                )

            decision = evaluate_action(
                self.policy,
                load_action_request(
                    str(DOGFOOD / "requests" / "01_repository_read_allowed.json")
                ),
                trusted_identity_boundaries=TRUSTED_BOUNDARIES,
            ).to_json()
            decision_path.write_text(decision, encoding="utf-8")
            (output / "observations.jsonl").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ObservationReportError, "directory set differ"):
                report_observations(
                    output_dir=output,
                    trusted_identity_boundaries=TRUSTED_BOUNDARIES,
                )

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
