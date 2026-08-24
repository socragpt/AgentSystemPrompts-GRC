"""Record minimized Dogfood 0 shadow observations without enforcing actions."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from agent_governance import (
    ActionRequestError,
    PolicyBundleError,
    evaluate_action,
    load_action_request,
    load_policy_bundle,
    normalize_action_request,
    validate_action_request,
    validate_policy_bundle,
)
from agent_governance.policy import normalize_policy_bundle


SCHEMA_PATHS = {
    "0.1": Path(__file__).with_name("observation-v0.1.schema.json"),
    "0.2": Path(__file__).with_name("observation.schema.json"),
}
DISPOSITIONS = ("allow", "deny", "require_approval")
MAPPING_CONFIDENCE = ("exact", "bounded", "ambiguous", "unmapped")
FRICTION_CODES = (
    "approval-unverified",
    "goal-assumption",
    "identity-assumption",
    "normalization-ambiguous",
    "request-construction",
    "selector-too-broad",
    "unmapped-action",
)
DECISION_USEFULNESS = ("useful", "not_useful", "unknown")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_PARAMETERS_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def _pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def minimized_identifier(value: Any) -> Optional[str]:
    """Return a schema-safe identifier or ``None`` for invalid request data."""

    if isinstance(value, str) and _IDENTIFIER_PATTERN.fullmatch(value):
        return value
    return None


def minimized_parameters_digest(value: Any) -> Optional[str]:
    """Return a schema-safe parameter digest or ``None`` for invalid input."""

    if isinstance(value, str) and _PARAMETERS_DIGEST_PATTERN.fullmatch(value):
        return value
    return None


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _resolve_local_ref(root: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Unsupported observation schema reference: {ref}")
    value: Any = root
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Unresolved observation schema reference: {ref}")
        value = value[part]
    if not isinstance(value, dict):
        raise ValueError(f"Observation schema reference is not an object: {ref}")
    return value


def _schema_errors(
    value: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str = "/",
) -> List[str]:
    if "$ref" in schema:
        return _schema_errors(value, _resolve_local_ref(root, schema["$ref"]), root, path)

    errors: List[str] = []
    if "allOf" in schema:
        for item in schema["allOf"]:
            errors.extend(_schema_errors(value, item, root, path))
    if "if" in schema:
        condition_matches = not _schema_errors(value, schema["if"], root, path)
        branch = schema.get("then") if condition_matches else schema.get("else")
        if isinstance(branch, dict):
            errors.extend(_schema_errors(value, branch, root, path))
    if "oneOf" in schema:
        branch_results = [
            _schema_errors(value, item, root, path) for item in schema["oneOf"]
        ]
        if sum(not result for result in branch_results) != 1:
            errors.append(f"{path}: expected exactly one matching schema")

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is not in the allowed enumeration")

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = (
            expected_type if isinstance(expected_type, list) else [expected_type]
        )
        if not any(_json_type_matches(value, item) for item in expected_types):
            errors.append(f"{path}: expected type {expected_type!r}")
            return errors

    if isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                errors.append(f"{path}: missing required field {field!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for field in sorted(set(value) - set(properties)):
                errors.append(f"{path}: unknown field {field!r}")
        for field, field_schema in properties.items():
            if field in value:
                child_path = f"/{field}" if path == "/" else f"{path}/{field}"
                errors.extend(
                    _schema_errors(value[field], field_schema, root, child_path)
                )

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: expected at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems"):
            canonical = [_compact_json(item) for item in value]
            if len(canonical) != len(set(canonical)):
                errors.append(f"{path}: array items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _schema_errors(item, item_schema, root, f"{path}/{index}")
                )

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string is too long")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: string does not match the required pattern")

    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: integer is below the minimum")
    return errors


def load_observation_schema(
    path: Optional[Path] = None, *, version: str = "0.2"
) -> Dict[str, Any]:
    """Load one supported local Dogfood 0 observation schema."""

    schema_path = path or SCHEMA_PATHS.get(version)
    if schema_path is None:
        raise ValueError(f"Unsupported observation schema_version: {version!r}")
    value = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Observation schema root must be an object")
    return value


def validate_observation(
    observation: Any, schema: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Validate one observation with the schema features used by Dogfood 0."""

    if schema is not None:
        active_schema = schema
    elif isinstance(observation, dict):
        active_schema = load_observation_schema(
            version=str(observation.get("schema_version", ""))
        )
    else:
        active_schema = load_observation_schema()
    return sorted(_schema_errors(observation, active_schema, active_schema))


def _artifact_ref(observation_id: str, name: str) -> str:
    return f"{observation_id}/artifacts/{name}.json"


def _write_new(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _recording_time(clock: Optional[Callable[[], datetime]]) -> str:
    value = clock() if clock is not None else datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Recorder clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def record_observation(
    *,
    policy_path: Path,
    request_path: Path,
    output_dir: Path,
    observation_id: str,
    activity_id: str,
    action_reported_at: Optional[str],
    trusted_identity_boundaries: Iterable[str],
    maintainer_expected_disposition: str,
    approval_requested: bool,
    approval_received: bool,
    action_occurred: bool,
    material: bool,
    decision_usefulness: str,
    normalization_duration_ms: int,
    mapping_confidence: str,
    friction_codes: Iterable[str],
    clock: Optional[Callable[[], datetime]] = None,
) -> Path:
    """Create one local shadow record and append its minimized JSONL index row."""

    if approval_received and not approval_requested:
        raise ValueError("An observed approval cannot be received before it is requested")
    if maintainer_expected_disposition not in DISPOSITIONS:
        raise ValueError("Unsupported maintainer expected disposition")
    if mapping_confidence not in MAPPING_CONFIDENCE:
        raise ValueError("Unsupported mapping confidence")
    if decision_usefulness not in DECISION_USEFULNESS:
        raise ValueError("Unsupported decision usefulness")
    normalized_friction_codes = sorted(set(friction_codes))
    if any(code not in FRICTION_CODES for code in normalized_friction_codes):
        raise ValueError("Unsupported friction code")
    if normalization_duration_ms < 0:
        raise ValueError("normalization_duration_ms must not be negative")

    policy = load_policy_bundle(str(policy_path))
    policy_issues = validate_policy_bundle(policy)
    if policy_issues:
        raise PolicyBundleError(policy_issues)
    request = load_action_request(str(request_path))
    request_issues = validate_action_request(request)
    if any(issue.code == "schema.unknown_field" for issue in request_issues):
        raise ValueError(
            "Invalid requests with unknown fields are not retained because the "
            "fields are outside the minimized Action Request contract"
        )

    result = evaluate_action(
        policy,
        request,
        trusted_identity_boundaries=trusted_identity_boundaries,
    )
    result_dict = result.as_dict()
    evidence = result_dict["proposed_evidence_record"]
    if request_issues and (
        result_dict["disposition"] != "deny"
        or result_dict["approval_requirements"]
    ):
        raise ValueError("Invalid Action Requests must fail closed without approval")

    retained_request = (
        request if request_issues else normalize_action_request(request)
    )
    normalized_policy = normalize_policy_bundle(policy)
    request_text = _compact_json(retained_request)
    policy_text = _pretty_json(normalized_policy)
    decision_text = result.to_json()
    evidence_text = _pretty_json(evidence)
    request_sha256 = _sha256_text(request_text)
    policy_sha256 = _sha256_text(policy_text)
    decision_sha256 = _sha256_text(decision_text)
    evidence_sha256 = _sha256_text(evidence_text)

    if policy_sha256 != result_dict["policy"]["source_sha256"]:
        raise ValueError("Retained policy digest does not match the decision")

    reason_codes = [item["code"] for item in result_dict["reasons"]]
    cited_control_ids = sorted(
        {item["control_id"] for item in result_dict["cited_controls"]}
    )
    approval_requirement_ids = [
        item["approval_id"] for item in result_dict["approval_requirements"]
    ]
    observation = {
        "schema_version": "0.2",
        "observation_id": observation_id,
        "activity_id": activity_id,
        "recorded_at": _recording_time(clock),
        "action_reported_at": action_reported_at,
        "mode": "shadow",
        "enforced": False,
        "request": {
            "artifact_ref": _artifact_ref(observation_id, "request"),
            "sha256": result_dict["request_sha256"],
            "artifact_sha256": request_sha256,
            "request_id": minimized_identifier(result_dict["request_id"]),
            "parameters_digest": minimized_parameters_digest(
                evidence["request"]["parameters_digest"]
            ),
            "valid": not request_issues,
        },
        "action": {
            "authorized_goal_id": minimized_identifier(
                evidence["action"]["authorized_goal_id"]
            ),
            "actor_id": minimized_identifier(evidence["action"]["actor_id"]),
            "capability_id": minimized_identifier(
                evidence["action"]["capability_id"]
            ),
            "action": minimized_identifier(evidence["action"]["action"]),
            "resource_id": minimized_identifier(
                evidence["action"]["resource_id"]
            ),
        },
        "policy": {
            "artifact_ref": _artifact_ref(observation_id, "policy"),
            "sha256": policy_sha256,
            "bundle_id": result_dict["policy"]["bundle_id"],
            "bundle_version": result_dict["policy"]["bundle_version"],
            "schema_version": result_dict["policy"]["schema_version"],
            "source_sha256": result_dict["policy"]["source_sha256"],
        },
        "decision": {
            "artifact_ref": _artifact_ref(observation_id, "decision"),
            "sha256": decision_sha256,
            "decision_id": result_dict["decision_id"],
            "disposition": result_dict["disposition"],
            "reason_codes": reason_codes,
            "cited_control_ids": cited_control_ids,
            "approval_requirement_ids": approval_requirement_ids,
        },
        "proposed_evidence": {
            "artifact_ref": _artifact_ref(observation_id, "proposed-evidence"),
            "sha256": evidence_sha256,
            "evidence_id": evidence["evidence_id"],
            "proposal_only": True,
        },
        "maintainer_expected_disposition": maintainer_expected_disposition,
        "agreement": (
            "match"
            if result_dict["disposition"] == maintainer_expected_disposition
            else "mismatch"
        ),
        "out_of_band_approval": {
            "requested": approval_requested,
            "received": approval_received,
        },
        "action_occurred": action_occurred,
        "material": material,
        "decision_usefulness": decision_usefulness,
        "normalization_duration_ms": normalization_duration_ms,
        "mapping_confidence": mapping_confidence,
        "friction_codes": normalized_friction_codes,
    }
    observation_errors = validate_observation(observation)
    if observation_errors:
        raise ValueError("Invalid observation: " + "; ".join(observation_errors))

    destination = output_dir / observation_id
    if destination.exists():
        raise FileExistsError(f"Observation already exists: {destination}")
    artifacts = destination / "artifacts"
    artifacts.mkdir(parents=True)
    _write_new(artifacts / "request.json", request_text)
    _write_new(artifacts / "policy.json", policy_text)
    _write_new(artifacts / "decision.json", decision_text)
    _write_new(artifacts / "proposed-evidence.json", evidence_text)
    observation_path = destination / "observation.json"
    _write_new(observation_path, _pretty_json(observation))

    index_path = output_dir / "observations.jsonl"
    with index_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_compact_json(observation) + "\n")
    return observation_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record one non-enforcing Dogfood 0 shadow observation"
    )
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--observation-id", required=True)
    parser.add_argument("--activity-id", required=True)
    parser.add_argument("--action-reported-at")
    parser.add_argument(
        "--trusted-identity-boundary",
        required=True,
        action="append",
        dest="trusted_identity_boundaries",
    )
    parser.add_argument(
        "--expected-disposition", required=True, choices=DISPOSITIONS
    )
    parser.add_argument("--approval-requested", action="store_true")
    parser.add_argument("--approval-received", action="store_true")
    parser.add_argument("--action-occurred", required=True, choices=("yes", "no"))
    materiality = parser.add_mutually_exclusive_group(required=True)
    materiality.add_argument("--material", action="store_true")
    materiality.add_argument("--non-material", action="store_true")
    parser.add_argument(
        "--decision-usefulness", required=True, choices=DECISION_USEFULNESS
    )
    parser.add_argument("--normalization-duration-ms", required=True, type=int)
    parser.add_argument(
        "--mapping-confidence", required=True, choices=MAPPING_CONFIDENCE
    )
    parser.add_argument(
        "--friction-code", action="append", default=[], choices=FRICTION_CODES
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        path = record_observation(
            policy_path=args.policy,
            request_path=args.request,
            output_dir=args.output_dir,
            observation_id=args.observation_id,
            activity_id=args.activity_id,
            action_reported_at=args.action_reported_at,
            trusted_identity_boundaries=args.trusted_identity_boundaries,
            maintainer_expected_disposition=args.expected_disposition,
            approval_requested=args.approval_requested,
            approval_received=args.approval_received,
            action_occurred=args.action_occurred == "yes",
            material=args.material,
            decision_usefulness=args.decision_usefulness,
            normalization_duration_ms=args.normalization_duration_ms,
            mapping_confidence=args.mapping_confidence,
            friction_codes=args.friction_code,
        )
    except (ActionRequestError, PolicyBundleError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Recorded non-enforcing shadow observation: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
