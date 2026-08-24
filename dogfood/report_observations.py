"""Verify and summarize local Dogfood 0 shadow observations."""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from agent_governance import (
    ActionRequestError,
    PolicyBundleError,
    evaluate_action,
    load_action_request,
    load_policy_bundle,
    validate_action_request,
    validate_policy_bundle,
)
if __package__:
    from dogfood.record_observation import (
        minimized_identifier,
        minimized_parameters_digest,
        validate_observation,
    )
else:
    from record_observation import (
        minimized_identifier,
        minimized_parameters_digest,
        validate_observation,
    )


ARTIFACT_SECTIONS = {
    "request": "request.json",
    "policy": "policy.json",
    "decision": "decision.json",
    "proposed_evidence": "proposed-evidence.json",
}
LEGACY_MATERIAL_CAPABILITIES = {
    "capability.branch-push",
    "capability.dependency-change",
    "capability.dependency-install",
    "capability.documentation-edit",
    "capability.force-push",
    "capability.local-commit",
    "capability.outside-task-edit",
    "capability.pull-request-create",
    "capability.remote-delete",
    "capability.remote-merge",
    "capability.release-create",
    "capability.sensitive-read",
    "capability.source-edit",
    "capability.tests-edit",
}


class ObservationReportError(ValueError):
    """Raised when a retained observation set cannot be verified."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ObservationReportError(f"Unable to read JSON from {path}: {exc}") from exc


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ObservationReportError(f"Unable to hash {path}: {exc}") from exc


def _artifact_path(root: Path, observation_id: str, artifact_ref: Any) -> Path:
    if not isinstance(artifact_ref, str):
        raise ObservationReportError(
            f"{observation_id}: artifact reference must be a string"
        )
    expected_prefix = f"{observation_id}/artifacts/"
    if not artifact_ref.startswith(expected_prefix):
        raise ObservationReportError(
            f"{observation_id}: artifact reference escapes its observation directory"
        )
    root_resolved = root.resolve()
    candidate = root / artifact_ref
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ObservationReportError(
            f"{observation_id}: artifact is missing or unreadable: {artifact_ref}"
        ) from exc
    if root_resolved not in resolved.parents or candidate.is_symlink():
        raise ObservationReportError(
            f"{observation_id}: artifact path is not contained by the output directory"
        )
    if not resolved.is_file():
        raise ObservationReportError(
            f"{observation_id}: artifact is not a regular file: {artifact_ref}"
        )
    return resolved


def _load_index(output_dir: Path) -> List[Dict[str, Any]]:
    index_path = output_dir / "observations.jsonl"
    try:
        lines = index_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ObservationReportError(f"Unable to read {index_path}: {exc}") from exc
    rows: List[Dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ObservationReportError(
                f"{index_path}:{line_number}: blank index rows are not allowed"
            )
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ObservationReportError(
                f"{index_path}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise ObservationReportError(
                f"{index_path}:{line_number}: observation row must be an object"
            )
        rows.append(value)
    return rows


def _ratio(numerator: int, denominator: int) -> Dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "percentage": (
            round((numerator / denominator) * 100, 1) if denominator else None
        ),
    }


def _timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _verify_observation(
    output_dir: Path,
    observation: Dict[str, Any],
    trusted_identity_boundaries: Iterable[str],
) -> Tuple[Dict[str, Any], bool]:
    observation_id = observation.get("observation_id", "<unknown>")
    errors = validate_observation(observation)
    if errors:
        raise ObservationReportError(
            f"{observation_id}: observation schema errors: {'; '.join(errors)}"
        )

    artifact_paths: Dict[str, Path] = {}
    for section, expected_filename in ARTIFACT_SECTIONS.items():
        artifact_ref = observation[section]["artifact_ref"]
        path = _artifact_path(output_dir, observation_id, artifact_ref)
        if path.name != expected_filename:
            raise ObservationReportError(
                f"{observation_id}: {section} points to the wrong artifact filename"
            )
        expected_digest = observation[section].get(
            "artifact_sha256", observation[section]["sha256"]
        )
        actual_digest = _sha256_file(path)
        if actual_digest != expected_digest:
            raise ObservationReportError(
                f"{observation_id}: {section} artifact digest mismatch"
            )
        artifact_paths[section] = path

    try:
        policy = load_policy_bundle(str(artifact_paths["policy"]))
        request = load_action_request(str(artifact_paths["request"]))
    except (ActionRequestError, PolicyBundleError) as exc:
        raise ObservationReportError(
            f"{observation_id}: retained artifact is not a JSON object: {exc}"
        ) from exc
    policy_issues = validate_policy_bundle(policy)
    if policy_issues:
        raise ObservationReportError(
            f"{observation_id}: retained policy is invalid: {policy_issues[0]}"
        )
    request_issues = validate_action_request(request)
    if any(issue.code == "schema.unknown_field" for issue in request_issues):
        raise ObservationReportError(
            f"{observation_id}: retained request contains unknown fields"
        )
    reproduced = evaluate_action(
        policy,
        request,
        trusted_identity_boundaries=trusted_identity_boundaries,
    ).as_dict()
    retained_decision = _read_json(artifact_paths["decision"])
    retained_evidence = _read_json(artifact_paths["proposed_evidence"])
    if retained_decision != reproduced:
        raise ObservationReportError(
            f"{observation_id}: retained decision does not reproduce"
        )
    if retained_evidence != reproduced["proposed_evidence_record"]:
        raise ObservationReportError(
            f"{observation_id}: retained proposed evidence does not reproduce"
        )
    if observation["request"]["sha256"] != reproduced["request_sha256"]:
        raise ObservationReportError(
            f"{observation_id}: request digest does not match the decision"
        )
    evidence = reproduced["proposed_evidence_record"]
    expected_request_metadata = {
        "request_id": minimized_identifier(reproduced["request_id"]),
        "parameters_digest": minimized_parameters_digest(
            evidence["request"]["parameters_digest"]
        ),
    }
    for field, expected in expected_request_metadata.items():
        if observation["request"][field] != expected:
            raise ObservationReportError(
                f"{observation_id}: request {field} does not match the decision"
            )
    for field in (
        "authorized_goal_id",
        "actor_id",
        "capability_id",
        "action",
        "resource_id",
    ):
        if observation["action"][field] != minimized_identifier(
            evidence["action"][field]
        ):
            raise ObservationReportError(
                f"{observation_id}: action {field} does not match the decision"
            )
    if observation["policy"]["source_sha256"] != reproduced["policy"][
        "source_sha256"
    ]:
        raise ObservationReportError(
            f"{observation_id}: policy source digest does not match the decision"
        )
    for field in ("bundle_id", "bundle_version", "schema_version"):
        if observation["policy"][field] != reproduced["policy"][field]:
            raise ObservationReportError(
                f"{observation_id}: policy {field} does not match the decision"
            )
    expected_decision_metadata = {
        "decision_id": reproduced["decision_id"],
        "disposition": reproduced["disposition"],
        "reason_codes": [item["code"] for item in reproduced["reasons"]],
        "cited_control_ids": sorted(
            {item["control_id"] for item in reproduced["cited_controls"]}
        ),
        "approval_requirement_ids": [
            item["approval_id"] for item in reproduced["approval_requirements"]
        ],
    }
    for field, expected in expected_decision_metadata.items():
        if observation["decision"][field] != expected:
            raise ObservationReportError(
                f"{observation_id}: decision {field} does not match the artifact"
            )
    if observation["proposed_evidence"]["evidence_id"] != retained_evidence[
        "evidence_id"
    ]:
        raise ObservationReportError(
            f"{observation_id}: proposed-evidence metadata does not match the artifact"
        )
    if observation["schema_version"] == "0.2":
        if observation["request"]["valid"] == bool(request_issues):
            raise ObservationReportError(
                f"{observation_id}: request validity flag does not match validation"
            )
        if request_issues and (
            reproduced["disposition"] != "deny"
            or reproduced["approval_requirements"]
        ):
            raise ObservationReportError(
                f"{observation_id}: invalid request did not fail closed"
            )
    elif request_issues:
        raise ObservationReportError(
            f"{observation_id}: legacy v0.1 recorder could not retain invalid requests"
        )
    return request, not request_issues


def report_observations(
    *,
    output_dir: Path,
    trusted_identity_boundaries: Iterable[str],
) -> Dict[str, Any]:
    """Verify one local observation set and return deterministic metrics."""

    root = output_dir.resolve()
    rows = _load_index(root)
    rows_by_id: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        observation_id = row.get("observation_id")
        if not isinstance(observation_id, str):
            raise ObservationReportError("Index row has no valid observation_id")
        if observation_id in rows_by_id:
            raise ObservationReportError(
                f"Duplicate observation_id in index: {observation_id}"
            )
        rows_by_id[observation_id] = row

    observation_dirs = {
        path.name
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith("observation.")
    }
    if observation_dirs != set(rows_by_id):
        missing_rows = sorted(observation_dirs - set(rows_by_id))
        missing_dirs = sorted(set(rows_by_id) - observation_dirs)
        raise ObservationReportError(
            "Observation index and directory set differ: "
            f"missing_rows={missing_rows}, missing_directories={missing_dirs}"
        )

    verified: List[Tuple[Dict[str, Any], Dict[str, Any], bool]] = []
    boundaries = tuple(trusted_identity_boundaries)
    for observation_id in sorted(rows_by_id):
        observation_path = root / observation_id / "observation.json"
        file_observation = _read_json(observation_path)
        if file_observation != rows_by_id[observation_id]:
            raise ObservationReportError(
                f"{observation_id}: observation file does not equal its index row"
            )
        request, request_valid = _verify_observation(
            root, rows_by_id[observation_id], boundaries
        )
        verified.append((rows_by_id[observation_id], request, request_valid))

    total = len(verified)
    schema_versions = Counter(item[0]["schema_version"] for item in verified)
    material_flags: List[bool] = []
    explicit_materiality = 0
    legacy_materiality = 0
    activity_ids = set()
    friction_counts: Counter[str] = Counter()
    usefulness_counts: Counter[str] = Counter()
    timestamp_samples = 0
    timestamp_anomalies = 0
    invalid_requests = 0

    for observation, _, request_valid in verified:
        if observation["schema_version"] == "0.2":
            material_flags.append(observation["material"])
            explicit_materiality += 1
            activity_ids.add(observation["activity_id"])
            friction_counts.update(observation["friction_codes"])
            usefulness_counts[observation["decision_usefulness"]] += 1
            if observation["action_reported_at"] is not None:
                timestamp_samples += 1
                if _timestamp(observation["action_reported_at"]) > _timestamp(
                    observation["recorded_at"]
                ):
                    timestamp_anomalies += 1
        else:
            material_flags.append(
                observation["action"]["capability_id"]
                in LEGACY_MATERIAL_CAPABILITIES
            )
            legacy_materiality += 1
            activity_ids.add(observation["observation_id"])
            if observation["friction_code"] != "none":
                friction_counts[observation["friction_code"]] += 1
        if not request_valid:
            invalid_requests += 1

    material_count = sum(material_flags)
    safely_mapped_material = sum(
        material
        and observation["mapping_confidence"] in {"exact", "bounded"}
        for material, (observation, _, _) in zip(material_flags, verified)
    )
    agreement = sum(item[0]["agreement"] == "match" for item in verified)
    false_allows = sum(
        observation["decision"]["disposition"] == "allow"
        and observation["maintainer_expected_disposition"]
        in {"deny", "require_approval"}
        for observation, _, _ in verified
    )
    false_blocks = sum(
        observation["decision"]["disposition"] in {"deny", "require_approval"}
        and observation["maintainer_expected_disposition"] == "allow"
        for observation, _, _ in verified
    )
    approval_load = sum(
        item[0]["decision"]["disposition"] == "require_approval"
        for item in verified
    )
    unmapped = sum(
        item[0]["mapping_confidence"] == "unmapped" for item in verified
    )
    normalization_values = [
        item[0]["normalization_duration_ms"] for item in verified
    ]

    return {
        "schema_version": "0.1",
        "verified": True,
        "observations": {
            "count": total,
            "logical_activity_count": len(activity_ids),
            "schema_versions": dict(sorted(schema_versions.items())),
            "materiality": {
                "explicit_v0.2": explicit_materiality,
                "inferred_legacy_v0.1": legacy_materiality,
            },
        },
        "metrics": {
            "material_actions": _ratio(material_count, total),
            "mapping_coverage": _ratio(safely_mapped_material, material_count),
            "decision_agreement": _ratio(agreement, total),
            "false_allows": _ratio(false_allows, total),
            "false_blocks": _ratio(false_blocks, total),
            "approval_load": _ratio(approval_load, total),
            "unmapped_rate": _ratio(unmapped, total),
            "evidence_completeness": _ratio(total, total),
            "invalid_requests": _ratio(invalid_requests, total),
            "normalization_effort": {
                "sample_count": len(normalization_values),
                "median_ms": median(normalization_values)
                if normalization_values
                else None,
            },
            "decision_usefulness": {
                "denominator": sum(usefulness_counts.values()),
                "counts": dict(sorted(usefulness_counts.items())),
            },
            "friction_codes": {
                "denominator": total,
                "counts": dict(sorted(friction_counts.items())),
            },
            "timestamp_order_anomalies": _ratio(
                timestamp_anomalies, timestamp_samples
            ),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify and summarize local Dogfood 0 observations"
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--trusted-identity-boundary",
        required=True,
        action="append",
        dest="trusted_identity_boundaries",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = report_observations(
            output_dir=args.output_dir,
            trusted_identity_boundaries=args.trusted_identity_boundaries,
        )
    except (ObservationReportError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
