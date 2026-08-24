"""Deterministic, side-effect-free Approval Grant v0.1 verification."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .decision import (
    ActionRequestError,
    DecisionResult,
    evaluate_action,
    load_action_request,
    normalize_action_request,
    validate_action_request,
)
from .policy import (
    PolicyBundleError,
    ValidationIssue,
    compile_policy_bundle,
    load_policy_bundle,
    validate_policy_bundle,
)


APPROVAL_GRANT_SCHEMA_VERSION = "0.1"
APPROVAL_VERIFICATION_STATE_SCHEMA_VERSION = "0.1"
APPROVAL_VERIFICATION_RESULT_SCHEMA_VERSION = "0.1"
APPROVAL_VERIFICATION_EVIDENCE_SCHEMA_VERSION = "0.1"

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PREFIXED_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_DECISION_ID_PATTERN = re.compile(r"^decision\.[0-9a-f]{64}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_DATA_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}


@dataclass(frozen=True)
class ApprovalVerificationResult:
    """Immutable Approval Verification Result v0.1 returned by the SDK."""

    _json: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "ApprovalVerificationResult":
        return cls(_contract_json(value))

    def as_dict(self) -> Dict[str, Any]:
        """Return a fresh JSON-compatible verification result."""

        return json.loads(self._json)

    def to_json(self) -> str:
        """Return canonical, human-readable JSON with one trailing newline."""

        return self._json

    @property
    def outcome(self) -> str:
        return self.as_dict()["outcome"]

    @property
    def verification_id(self) -> str:
        return self.as_dict()["verification_id"]

    @property
    def proposed_evidence_record(self) -> Dict[str, Any]:
        return self.as_dict()["proposed_evidence_record"]


class ApprovalGrantError(ValueError):
    """Raised when an approval contract file cannot be loaded."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(_sorted_issues(issues))
        message = self.issues[0].message if self.issues else "Invalid approval input"
        super().__init__(message)


def _sorted_issues(issues: Iterable[ValidationIssue]) -> List[ValidationIssue]:
    return sorted(issues, key=lambda item: (item.path, item.code, item.message))


def _pointer(base: str, value: object) -> str:
    escaped = str(value).replace("~", "~0").replace("/", "~1")
    return f"{base}/{escaped}" if base else f"/{escaped}"


def _contract_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _safe_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return {"unsupported_number": repr(value)}
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value]
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            safe_key = (
                key
                if isinstance(key, str)
                else f"unsupported-key:{type(key).__name__}:{key}"
            )
            result[safe_key] = _safe_json_value(value[key])
        return result
    value_type = type(value)
    return {"unsupported_type": f"{value_type.__module__}.{value_type.__qualname__}"}


def _input_digest(value: Any) -> str:
    serialized = _canonical_json(_safe_json_value(value))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not _TIMESTAMP_PATTERN.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _issue(
    issues: List[ValidationIssue], code: str, path: str, message: str
) -> None:
    issues.append(ValidationIssue(code, path or "/", message))


def _validate_object(
    issues: List[ValidationIssue],
    value: Any,
    path: str,
    required: Set[str],
    allowed: Set[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        _issue(issues, "schema.type", path or "/", "Expected an object")
        return None
    for field in sorted(required - set(value)):
        _issue(
            issues,
            "schema.required",
            path or "/",
            f"Missing required field '{field}'",
        )
    for field in sorted(set(value) - allowed, key=str):
        _issue(
            issues,
            "schema.unknown_field",
            _pointer(path, field),
            f"Unknown field '{field}'",
        )
    return value


def _validate_identifier(
    issues: List[ValidationIssue], value: Any, path: str
) -> None:
    if not isinstance(value, str):
        _issue(issues, "schema.type", path, "Expected an identifier string")
    elif not 3 <= len(value) <= 128 or not _ID_PATTERN.fullmatch(value):
        _issue(issues, "schema.pattern", path, f"Invalid identifier '{value}'")


def _validate_timestamp(
    issues: List[ValidationIssue], value: Any, path: str
) -> None:
    if _parse_timestamp(value) is None:
        _issue(
            issues,
            "schema.format",
            path,
            "Expected a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form",
        )


def _validate_digest(
    issues: List[ValidationIssue], value: Any, path: str, *, prefixed: bool
) -> None:
    pattern = _PREFIXED_SHA256_PATTERN if prefixed else _SHA256_PATTERN
    description = (
        "a lowercase sha256:<64-hex-character> digest"
        if prefixed
        else "a lowercase 64-hex-character SHA-256 digest"
    )
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _issue(issues, "schema.format", path, f"Expected {description}")


def _validate_identifier_array(
    issues: List[ValidationIssue],
    value: Any,
    path: str,
    *,
    minimum_items: int = 0,
) -> None:
    if not isinstance(value, list):
        _issue(issues, "schema.type", path, "Expected an array")
        return
    if len(value) < minimum_items:
        _issue(
            issues,
            "schema.min_items",
            path,
            f"Expected at least {minimum_items} item(s)",
        )
    seen: Set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}/{index}"
        _validate_identifier(issues, item, item_path)
        if isinstance(item, str):
            if item in seen:
                _issue(
                    issues,
                    "schema.unique_items",
                    item_path,
                    f"Duplicate value '{item}'",
                )
            seen.add(item)


def _validate_policy_provenance(
    issues: List[ValidationIssue], value: Any, path: str
) -> None:
    fields = {"bundle_id", "bundle_version", "schema_version", "source_sha256"}
    policy = _validate_object(issues, value, path, fields, fields)
    if policy is None:
        return
    if "bundle_id" in policy:
        _validate_identifier(issues, policy["bundle_id"], f"{path}/bundle_id")
    for field in ("bundle_version", "schema_version"):
        if field in policy and (
            not isinstance(policy[field], str) or not policy[field]
        ):
            _issue(
                issues,
                "schema.type",
                f"{path}/{field}",
                "Expected a non-empty string",
            )
    if "source_sha256" in policy:
        _validate_digest(
            issues,
            policy["source_sha256"],
            f"{path}/source_sha256",
            prefixed=False,
        )


def _validate_nonnegative_integer(
    issues: List[ValidationIssue], value: Any, path: str, *, minimum: int = 0
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _issue(issues, "schema.type", path, "Expected an integer")
    elif value < minimum:
        _issue(issues, "schema.range", path, f"Expected integer >= {minimum}")


def _validate_scope(issues: List[ValidationIssue], value: Any, path: str) -> None:
    fields = {
        "max_cost",
        "max_duration_seconds",
        "max_action_count",
        "max_delegation_depth",
        "allowed_data_classifications",
        "require_reversible",
    }
    scope = _validate_object(issues, value, path, fields, fields)
    if scope is None:
        return
    if "max_cost" in scope:
        cost_fields = {"amount_minor", "currency"}
        cost = _validate_object(
            issues, scope["max_cost"], f"{path}/max_cost", cost_fields, cost_fields
        )
        if cost is not None:
            if "amount_minor" in cost:
                _validate_nonnegative_integer(
                    issues, cost["amount_minor"], f"{path}/max_cost/amount_minor"
                )
            if "currency" in cost:
                currency = cost["currency"]
                if (
                    not isinstance(currency, str)
                    or not _CURRENCY_PATTERN.fullmatch(currency)
                ):
                    _issue(
                        issues,
                        "schema.pattern",
                        f"{path}/max_cost/currency",
                        "Expected an ISO-style three-letter currency",
                    )
    for field in ("max_duration_seconds", "max_action_count"):
        if field in scope:
            _validate_nonnegative_integer(
                issues, scope[field], f"{path}/{field}", minimum=1
            )
    if "max_delegation_depth" in scope:
        _validate_nonnegative_integer(
            issues, scope["max_delegation_depth"], f"{path}/max_delegation_depth"
        )
        depth = scope["max_delegation_depth"]
        if isinstance(depth, int) and not isinstance(depth, bool) and depth > 16:
            _issue(
                issues,
                "schema.range",
                f"{path}/max_delegation_depth",
                "Expected integer 0..16",
            )
    if "allowed_data_classifications" in scope:
        values = scope["allowed_data_classifications"]
        if not isinstance(values, list):
            _issue(
                issues,
                "schema.type",
                f"{path}/allowed_data_classifications",
                "Expected an array",
            )
        else:
            seen: Set[str] = set()
            for index, item in enumerate(values):
                item_path = f"{path}/allowed_data_classifications/{index}"
                if not isinstance(item, str) or item not in _DATA_CLASSIFICATIONS:
                    _issue(
                        issues,
                        "schema.enum",
                        item_path,
                        "Unsupported data classification",
                    )
                elif item in seen:
                    _issue(
                        issues,
                        "schema.unique_items",
                        item_path,
                        f"Duplicate value '{item}'",
                    )
                else:
                    seen.add(item)
    if "require_reversible" in scope and not isinstance(
        scope["require_reversible"], bool
    ):
        _issue(
            issues,
            "schema.type",
            f"{path}/require_reversible",
            "Expected a boolean",
        )


def validate_approval_grant(grant: Any) -> List[ValidationIssue]:
    """Return deterministic shape errors for Approval Grant v0.1."""

    issues: List[ValidationIssue] = []
    fields = {
        "schema_version",
        "grant_id",
        "approval_requirement_ids",
        "binding",
        "issued_at",
        "expires_at",
        "reuse_policy",
        "approvals",
    }
    root = _validate_object(issues, grant, "", fields, fields)
    if root is None:
        return _sorted_issues(issues)

    if "schema_version" in root and root["schema_version"] != APPROVAL_GRANT_SCHEMA_VERSION:
        _issue(
            issues,
            "schema_version.unsupported",
            "/schema_version",
            f"Expected schema_version '{APPROVAL_GRANT_SCHEMA_VERSION}'",
        )
    if "grant_id" in root:
        _validate_identifier(issues, root["grant_id"], "/grant_id")
    if "approval_requirement_ids" in root:
        _validate_identifier_array(
            issues,
            root["approval_requirement_ids"],
            "/approval_requirement_ids",
            minimum_items=1,
        )
    for field in ("issued_at", "expires_at"):
        if field in root:
            _validate_timestamp(issues, root[field], f"/{field}")
    issued_at = _parse_timestamp(root.get("issued_at"))
    expires_at = _parse_timestamp(root.get("expires_at"))
    if issued_at and expires_at and expires_at <= issued_at:
        _issue(
            issues,
            "lifecycle.invalid",
            "/expires_at",
            "expires_at must be later than issued_at",
        )
    if "reuse_policy" in root and root["reuse_policy"] != "single_use":
        _issue(
            issues,
            "schema.const",
            "/reuse_policy",
            "Approval Grant v0.1 requires reuse_policy 'single_use'",
        )

    binding_fields = {
        "request_id",
        "request_sha256",
        "decision_id",
        "decision_disposition",
        "subject_actor_id",
        "capability_id",
        "resource_id",
        "parameters_digest",
        "policy",
        "scope",
    }
    if "binding" in root:
        binding = _validate_object(
            issues, root["binding"], "/binding", binding_fields, binding_fields
        )
        if binding is not None:
            for field in (
                "request_id",
                "subject_actor_id",
                "capability_id",
                "resource_id",
            ):
                if field in binding:
                    _validate_identifier(issues, binding[field], f"/binding/{field}")
            if "request_sha256" in binding:
                _validate_digest(
                    issues,
                    binding["request_sha256"],
                    "/binding/request_sha256",
                    prefixed=False,
                )
            if "decision_id" in binding:
                decision_id = binding["decision_id"]
                if (
                    not isinstance(decision_id, str)
                    or not _DECISION_ID_PATTERN.fullmatch(decision_id)
                ):
                    _issue(
                        issues,
                        "schema.pattern",
                        "/binding/decision_id",
                        "Expected decision.<64-hex-character> identifier",
                    )
            if (
                "decision_disposition" in binding
                and binding["decision_disposition"] != "require_approval"
            ):
                _issue(
                    issues,
                    "schema.const",
                    "/binding/decision_disposition",
                    "Approval grants only bind require_approval decisions",
                )
            if "parameters_digest" in binding:
                _validate_digest(
                    issues,
                    binding["parameters_digest"],
                    "/binding/parameters_digest",
                    prefixed=True,
                )
            if "policy" in binding:
                _validate_policy_provenance(issues, binding["policy"], "/binding/policy")
            if "scope" in binding:
                _validate_scope(issues, binding["scope"], "/binding/scope")

    if "approvals" in root:
        approvals = root["approvals"]
        if not isinstance(approvals, list):
            _issue(issues, "schema.type", "/approvals", "Expected an array")
        else:
            for index, value in enumerate(approvals):
                path = f"/approvals/{index}"
                approval_fields = {
                    "approval_id",
                    "approver_actor_id",
                    "approved_at",
                    "identity",
                    "rationale",
                }
                approval = _validate_object(
                    issues, value, path, approval_fields, approval_fields
                )
                if approval is None:
                    continue
                for field in ("approval_id", "approver_actor_id"):
                    if field in approval:
                        _validate_identifier(
                            issues, approval[field], f"{path}/{field}"
                        )
                if "approved_at" in approval:
                    _validate_timestamp(
                        issues, approval["approved_at"], f"{path}/approved_at"
                    )
                identity_fields = {
                    "trust_boundary_id",
                    "assertion_id",
                    "authenticated_at",
                    "expires_at",
                }
                if "identity" in approval:
                    identity = _validate_object(
                        issues,
                        approval["identity"],
                        f"{path}/identity",
                        identity_fields,
                        identity_fields,
                    )
                    if identity is not None:
                        for field in ("trust_boundary_id", "assertion_id"):
                            if field in identity:
                                _validate_identifier(
                                    issues,
                                    identity[field],
                                    f"{path}/identity/{field}",
                                )
                        for field in ("authenticated_at", "expires_at"):
                            if field in identity:
                                _validate_timestamp(
                                    issues,
                                    identity[field],
                                    f"{path}/identity/{field}",
                                )
                        authenticated_at = _parse_timestamp(
                            identity.get("authenticated_at")
                        )
                        identity_expires_at = _parse_timestamp(identity.get("expires_at"))
                        if (
                            authenticated_at
                            and identity_expires_at
                            and identity_expires_at <= authenticated_at
                        ):
                            _issue(
                                issues,
                                "identity.lifecycle_invalid",
                                f"{path}/identity/expires_at",
                                "expires_at must be later than authenticated_at",
                            )
                rationale_fields = {"code", "reference"}
                if "rationale" in approval:
                    rationale = _validate_object(
                        issues,
                        approval["rationale"],
                        f"{path}/rationale",
                        rationale_fields,
                        rationale_fields,
                    )
                    if rationale is not None:
                        if "code" in rationale:
                            _validate_identifier(
                                issues, rationale["code"], f"{path}/rationale/code"
                            )
                        if "reference" in rationale:
                            reference = rationale["reference"]
                            if reference is not None and (
                                not isinstance(reference, str)
                                or not 1 <= len(reference) <= 512
                            ):
                                _issue(
                                    issues,
                                    "schema.type",
                                    f"{path}/rationale/reference",
                                    "Expected null or a string of 1..512 characters",
                                )
    return _sorted_issues(issues)


def validate_approval_verification_state(state: Any) -> List[ValidationIssue]:
    """Return deterministic shape errors for caller-supplied verification state."""

    issues: List[ValidationIssue] = []
    fields = {
        "schema_version",
        "verified_at",
        "trusted_request_identity_boundaries",
        "trusted_approver_identity_boundaries",
        "revoked_grant_ids",
        "consumed_grant_ids",
    }
    root = _validate_object(issues, state, "", fields, fields)
    if root is None:
        return _sorted_issues(issues)
    if (
        "schema_version" in root
        and root["schema_version"] != APPROVAL_VERIFICATION_STATE_SCHEMA_VERSION
    ):
        _issue(
            issues,
            "schema_version.unsupported",
            "/schema_version",
            f"Expected schema_version '{APPROVAL_VERIFICATION_STATE_SCHEMA_VERSION}'",
        )
    if "verified_at" in root:
        _validate_timestamp(issues, root["verified_at"], "/verified_at")
    for field in (
        "trusted_request_identity_boundaries",
        "trusted_approver_identity_boundaries",
        "revoked_grant_ids",
        "consumed_grant_ids",
    ):
        if field in root:
            _validate_identifier_array(issues, root[field], f"/{field}")
    return _sorted_issues(issues)


def _validate_decision_result(decision: Any) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    fields = {
        "schema_version",
        "decision_id",
        "request_id",
        "request_sha256",
        "disposition",
        "valid_until",
        "reasons",
        "cited_controls",
        "effective_constraints",
        "approval_requirements",
        "policy",
        "authority",
        "proposed_evidence_record",
    }
    root = _validate_object(issues, decision, "", fields, fields)
    if root is None:
        return _sorted_issues(issues)
    if "schema_version" in root and root["schema_version"] != "0.1":
        _issue(
            issues,
            "schema_version.unsupported",
            "/schema_version",
            "Expected Decision Result schema_version '0.1'",
        )
    if "decision_id" in root:
        value = root["decision_id"]
        if not isinstance(value, str) or not _DECISION_ID_PATTERN.fullmatch(value):
            _issue(
                issues,
                "schema.pattern",
                "/decision_id",
                "Expected decision.<64-hex-character> identifier",
            )
    if "request_id" in root and root["request_id"] is not None:
        _validate_identifier(issues, root["request_id"], "/request_id")
    if "request_sha256" in root:
        _validate_digest(
            issues, root["request_sha256"], "/request_sha256", prefixed=False
        )
    if "disposition" in root and root["disposition"] not in {
        "allow",
        "deny",
        "require_approval",
    }:
        _issue(
            issues,
            "schema.enum",
            "/disposition",
            "Expected allow, deny, or require_approval",
        )
    if "valid_until" in root and root["valid_until"] is not None:
        _validate_timestamp(issues, root["valid_until"], "/valid_until")
    for field in ("reasons", "cited_controls", "approval_requirements"):
        if field in root and not isinstance(root[field], list):
            _issue(issues, "schema.type", f"/{field}", "Expected an array")
    for field in (
        "effective_constraints",
        "policy",
        "authority",
        "proposed_evidence_record",
    ):
        if field in root and not isinstance(root[field], dict):
            _issue(issues, "schema.type", f"/{field}", "Expected an object")
    return _sorted_issues(issues)


def _load_json(path: str) -> Tuple[Any, Sequence[ValidationIssue]]:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return None, (
            ValidationIssue("json.read", "/", f"Unable to read {source}: {exc}"),
        )
    try:
        return json.loads(text), ()
    except json.JSONDecodeError as exc:
        return None, (
            ValidationIssue(
                "json.syntax",
                "/",
                exc.msg,
                line=exc.lineno,
                column=exc.colno,
            ),
        )


def load_approval_grant(path: str) -> Dict[str, Any]:
    """Load a UTF-8 JSON approval grant or raise ``ApprovalGrantError``."""

    value, issues = _load_json(path)
    if issues:
        raise ApprovalGrantError(issues)
    if not isinstance(value, dict):
        raise ApprovalGrantError(
            [ValidationIssue("schema.type", "/", "Approval grant root must be an object")]
        )
    return value


def load_approval_verification_state(path: str) -> Dict[str, Any]:
    """Load caller-supplied verification state or raise ``ApprovalGrantError``."""

    value, issues = _load_json(path)
    if issues:
        raise ApprovalGrantError(issues)
    if not isinstance(value, dict):
        raise ApprovalGrantError(
            [ValidationIssue("schema.type", "/", "Verification state root must be an object")]
        )
    return value


def _reason(code: str, message: str, path: Optional[str] = None) -> Dict[str, Any]:
    value: Dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        value["path"] = path
    return value


def _sorted_reasons(reasons: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (deepcopy(reason) for reason in reasons),
        key=lambda item: (item.get("path", ""), item["code"], item["message"]),
    )


def _validation_reasons(
    prefix: str, issues: Iterable[ValidationIssue]
) -> List[Dict[str, Any]]:
    return [
        _reason(f"{prefix}.{issue.code}", issue.message, issue.path)
        for issue in _sorted_issues(issues)
    ]


def _policy_provenance(policy: Any, valid: bool) -> Dict[str, Any]:
    raw_metadata = policy.get("bundle", {}) if isinstance(policy, dict) else {}
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    source_sha256 = _input_digest(policy)
    schema_version = policy.get("schema_version") if isinstance(policy, dict) else None
    if valid and isinstance(policy, dict):
        compiled = json.loads(compile_policy_bundle(policy).decision_data)
        metadata = compiled["bundle"]
        schema_version = compiled["schema_version"]
        source_sha256 = compiled["compilation"]["source_sha256"]
    return {
        "bundle_id": metadata.get("id") if isinstance(metadata.get("id"), str) else None,
        "bundle_version": (
            metadata.get("version") if isinstance(metadata.get("version"), str) else None
        ),
        "schema_version": schema_version if isinstance(schema_version, str) else None,
        "source_sha256": source_sha256,
    }


def _decision_dict(decision: Any) -> Any:
    if isinstance(decision, DecisionResult):
        return decision.as_dict()
    return deepcopy(decision)


def _string_or_none(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _timestamp_or_none(value: Any) -> Optional[str]:
    return value if _parse_timestamp(value) is not None else None


def _parameters_digest_or_none(value: Any) -> Optional[str]:
    if isinstance(value, str) and _PREFIXED_SHA256_PATTERN.fullmatch(value):
        return value
    return None


def _extract_approver_data(grant: Any) -> Tuple[List[str], List[str]]:
    actor_ids: Set[str] = set()
    rationale_codes: Set[str] = set()
    approvals = grant.get("approvals") if isinstance(grant, dict) else None
    if isinstance(approvals, list):
        for approval in approvals:
            if not isinstance(approval, dict):
                continue
            actor_id = approval.get("approver_actor_id")
            if isinstance(actor_id, str):
                actor_ids.add(actor_id)
            rationale = approval.get("rationale")
            if isinstance(rationale, dict) and isinstance(rationale.get("code"), str):
                rationale_codes.add(rationale["code"])
    return sorted(actor_ids), sorted(rationale_codes)


def _build_result(
    *,
    policy: Any,
    policy_valid: bool,
    request: Any,
    request_valid: bool,
    decision: Any,
    grant: Any,
    state: Any,
    outcome: str,
    reasons: Sequence[Dict[str, Any]],
    valid_until: Optional[str],
) -> ApprovalVerificationResult:
    policy_data = _policy_provenance(policy, policy_valid)
    normalized_request = (
        normalize_action_request(request)
        if request_valid and isinstance(request, dict)
        else request
    )
    request_sha256 = _input_digest(normalized_request)
    request_id = _string_or_none(
        request.get("request_id") if isinstance(request, dict) else None
    )
    request_parameters_digest = (
        request.get("parameters_digest") if isinstance(request, dict) else None
    )
    request_parameters_digest = _parameters_digest_or_none(request_parameters_digest)
    decision_id = _string_or_none(
        decision.get("decision_id") if isinstance(decision, dict) else None
    )
    raw_decision_disposition = (
        decision.get("disposition") if isinstance(decision, dict) else None
    )
    decision_disposition = (
        raw_decision_disposition
        if raw_decision_disposition in {"allow", "deny", "require_approval"}
        else None
    )
    grant_id = _string_or_none(
        grant.get("grant_id") if isinstance(grant, dict) else None
    )
    grant_sha256 = _input_digest(grant)
    verified_at = _timestamp_or_none(
        state.get("verified_at") if isinstance(state, dict) else None
    )
    requirement_ids = []
    if isinstance(decision, dict) and isinstance(decision.get("approval_requirements"), list):
        requirement_ids = sorted(
            {
                item["approval_id"]
                for item in decision["approval_requirements"]
                if isinstance(item, dict) and isinstance(item.get("approval_id"), str)
            }
        )
    approver_actor_ids, rationale_codes = _extract_approver_data(grant)
    normalized_reasons = _sorted_reasons(reasons)
    result_core = {
        "outcome": outcome,
        "valid_until": valid_until,
        "reasons": normalized_reasons,
        "grant": {"grant_id": grant_id, "grant_sha256": grant_sha256},
        "request": {"request_id": request_id, "request_sha256": request_sha256},
        "decision": {
            "decision_id": decision_id,
            "disposition": decision_disposition,
        },
        "policy": policy_data,
        "approval_requirement_ids": requirement_ids,
        "approver_actor_ids": approver_actor_ids,
        "verified_at": verified_at,
    }
    verification_id = "approval-verification." + hashlib.sha256(
        _canonical_json(result_core).encode("utf-8")
    ).hexdigest()
    evidence_core = {
        "record_type": "proposed_approval_verification",
        "proposal_only": True,
        "verification_id": verification_id,
        "grant": {"grant_id": grant_id, "grant_sha256": grant_sha256},
        "request": {
            "request_id": request_id,
            "request_sha256": request_sha256,
            "parameters_digest": request_parameters_digest,
        },
        "decision": {
            "decision_id": decision_id,
            "disposition": decision_disposition,
        },
        "policy": policy_data,
        "verification": {
            "outcome": outcome,
            "reason_codes": list(
                dict.fromkeys(item["code"] for item in normalized_reasons)
            ),
            "approval_requirement_ids": requirement_ids,
            "approver_actor_ids": approver_actor_ids,
            "rationale_codes": rationale_codes,
            "verified_at": verified_at,
            "valid_until": valid_until,
        },
    }
    evidence_id = "evidence." + hashlib.sha256(
        _canonical_json(evidence_core).encode("utf-8")
    ).hexdigest()
    evidence = {
        "schema_version": APPROVAL_VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "evidence_id": evidence_id,
        **evidence_core,
    }
    payload = {
        "schema_version": APPROVAL_VERIFICATION_RESULT_SCHEMA_VERSION,
        "verification_id": verification_id,
        **result_core,
        "proposed_evidence_record": evidence,
    }
    return ApprovalVerificationResult.from_dict(payload)


def _verify_approval_grant(
    policy: Any,
    request: Any,
    decision: Any,
    grant: Any,
    state: Any,
    *,
    policy_input_issues: Iterable[ValidationIssue] = (),
    request_input_issues: Iterable[ValidationIssue] = (),
    decision_input_issues: Iterable[ValidationIssue] = (),
    grant_input_issues: Iterable[ValidationIssue] = (),
    state_input_issues: Iterable[ValidationIssue] = (),
) -> ApprovalVerificationResult:
    decision_data = _decision_dict(decision)
    policy_issues = list(policy_input_issues)
    if not policy_issues:
        policy_issues = validate_policy_bundle(policy)
    request_issues = list(request_input_issues)
    if not request_issues:
        request_issues = validate_action_request(request)
    decision_issues = list(decision_input_issues)
    if not decision_issues:
        decision_issues = _validate_decision_result(decision_data)
    grant_issues = list(grant_input_issues)
    if not grant_issues:
        grant_issues = validate_approval_grant(grant)
    state_issues = list(state_input_issues)
    if not state_issues:
        state_issues = validate_approval_verification_state(state)
    reasons: List[Dict[str, Any]] = []
    reasons.extend(_validation_reasons("policy", policy_issues))
    reasons.extend(_validation_reasons("request", request_issues))
    reasons.extend(_validation_reasons("decision", decision_issues))
    reasons.extend(_validation_reasons("grant", grant_issues))
    reasons.extend(_validation_reasons("state", state_issues))
    policy_valid = not policy_issues and isinstance(policy, dict)
    request_valid = not request_issues and isinstance(request, dict)
    if reasons:
        return _build_result(
            policy=policy,
            policy_valid=policy_valid,
            request=request,
            request_valid=request_valid,
            decision=decision_data,
            grant=grant,
            state=state,
            outcome="not_satisfied",
            reasons=reasons,
            valid_until=None,
        )

    assert isinstance(policy, dict)
    assert isinstance(request, dict)
    assert isinstance(decision_data, dict)
    assert isinstance(grant, dict)
    assert isinstance(state, dict)
    trusted_request_boundaries = set(
        state["trusted_request_identity_boundaries"]
    )
    trusted_approver_boundaries = set(
        state["trusted_approver_identity_boundaries"]
    )
    expected = evaluate_action(
        policy,
        request,
        trusted_identity_boundaries=trusted_request_boundaries,
    ).as_dict()
    if decision_data != expected:
        reasons.append(
            _reason(
                "approval.decision_mismatch",
                "The supplied decision does not equal deterministic reevaluation of the request and policy",
                "/decision_id",
            )
        )
    if expected["disposition"] != "require_approval":
        reasons.append(
            _reason(
                "approval.decision_not_required",
                "Approval verification can satisfy only a require_approval decision",
                "/disposition",
            )
        )

    binding = grant["binding"]
    if binding["request_id"] != request["request_id"] or binding[
        "request_sha256"
    ] != expected["request_sha256"]:
        reasons.append(
            _reason(
                "approval.request_mismatch",
                "The grant is not bound to the exact request identity and digest",
                "/binding/request_sha256",
            )
        )
    if binding["decision_id"] != expected["decision_id"] or binding[
        "decision_disposition"
    ] != "require_approval":
        reasons.append(
            _reason(
                "approval.decision_mismatch",
                "The grant is not bound to the exact require_approval decision",
                "/binding/decision_id",
            )
        )
    if binding["subject_actor_id"] != request["actor_id"]:
        reasons.append(
            _reason(
                "approval.subject_mismatch",
                "The grant subject does not match the acting actor",
                "/binding/subject_actor_id",
            )
        )
    if binding["capability_id"] != request["capability_id"]:
        reasons.append(
            _reason(
                "approval.capability_mismatch",
                "The grant capability does not match the request",
                "/binding/capability_id",
            )
        )
    if binding["resource_id"] != request["resource_id"]:
        reasons.append(
            _reason(
                "approval.resource_mismatch",
                "The grant resource does not match the request",
                "/binding/resource_id",
            )
        )
    if binding["parameters_digest"] != request["parameters_digest"]:
        reasons.append(
            _reason(
                "approval.parameters_mismatch",
                "The grant parameter digest does not match the request",
                "/binding/parameters_digest",
            )
        )
    if binding["policy"] != expected["policy"]:
        reasons.append(
            _reason(
                "approval.policy_mismatch",
                "The grant policy identity or digest does not match the decision",
                "/binding/policy",
            )
        )
    if binding["scope"] != expected["effective_constraints"]:
        reasons.append(
            _reason(
                "approval.scope_mismatch",
                "The grant scope does not exactly match the decision constraints",
                "/binding/scope",
            )
        )

    requirements = {
        item["approval_id"]: item for item in expected["approval_requirements"]
    }
    required_ids = sorted(requirements)
    if sorted(grant["approval_requirement_ids"]) != required_ids:
        reasons.append(
            _reason(
                "approval.requirement_mismatch",
                "The grant approval requirements do not exactly match the decision",
                "/approval_requirement_ids",
            )
        )

    grant_id = grant["grant_id"]
    if grant_id in set(state["revoked_grant_ids"]):
        reasons.append(
            _reason(
                "approval.revoked",
                "The caller reports this approval grant as revoked",
                "/revoked_grant_ids",
            )
        )
    if grant_id in set(state["consumed_grant_ids"]):
        reasons.append(
            _reason(
                "approval.reused",
                "The caller reports this single-use approval grant as already consumed",
                "/consumed_grant_ids",
            )
        )

    verified_at = _parse_timestamp(state["verified_at"])
    issued_at = _parse_timestamp(grant["issued_at"])
    expires_at = _parse_timestamp(grant["expires_at"])
    requested_at = _parse_timestamp(request["requested_at"])
    decision_valid_until = _parse_timestamp(expected["valid_until"])
    assert verified_at and issued_at and expires_at and requested_at
    if verified_at < issued_at:
        reasons.append(
            _reason(
                "approval.not_yet_valid",
                "The grant was issued after the caller-supplied verification time",
                "/issued_at",
            )
        )
    if verified_at >= expires_at:
        reasons.append(
            _reason(
                "approval.expired",
                "The approval grant is expired at the caller-supplied verification time",
                "/expires_at",
            )
        )
    if issued_at < requested_at:
        reasons.append(
            _reason(
                "approval.issued_before_request",
                "The grant was issued before the exact request was proposed",
                "/issued_at",
            )
        )
    if decision_valid_until is None or verified_at >= decision_valid_until:
        reasons.append(
            _reason(
                "approval.decision_expired",
                "The bound decision is not current at verification time",
                "/decision/valid_until",
            )
        )
    if decision_valid_until is not None and expires_at > decision_valid_until:
        reasons.append(
            _reason(
                "approval.expiry_exceeds_decision",
                "The grant expires after the bound decision",
                "/expires_at",
            )
        )
    if requirements:
        rule_expiry = min(
            item["expires_after_seconds"] for item in requirements.values()
        )
        if expires_at > issued_at + timedelta(seconds=rule_expiry):
            reasons.append(
                _reason(
                    "approval.expiry_exceeds_rule",
                    "The grant expiry exceeds an applicable approval rule",
                    "/expires_at",
                )
            )

    actors = {item["id"]: item for item in policy["actors"]}
    eligible_votes: Dict[str, Set[str]] = {
        approval_id: set() for approval_id in requirements
    }
    seen_votes: Set[Tuple[str, str]] = set()
    for index, approval in enumerate(grant["approvals"]):
        path = f"/approvals/{index}"
        approval_id = approval["approval_id"]
        actor_id = approval["approver_actor_id"]
        vote_valid = True
        if approval_id not in requirements:
            reasons.append(
                _reason(
                    "approval.requirement_mismatch",
                    f"Approval entry references unexpected requirement '{approval_id}'",
                    f"{path}/approval_id",
                )
            )
            continue
        vote_key = (approval_id, actor_id)
        if vote_key in seen_votes:
            reasons.append(
                _reason(
                    "approval.duplicate_approver",
                    "An approver may count at most once toward one requirement",
                    f"{path}/approver_actor_id",
                )
            )
            vote_valid = False
        seen_votes.add(vote_key)
        requirement = requirements[approval_id]
        actor = actors.get(actor_id)
        actor_roles = set(actor["roles"]) if actor is not None else set()
        if actor is None or not actor_roles.intersection(
            requirement["approver_role_ids"]
        ):
            reasons.append(
                _reason(
                    "approval.approver_ineligible",
                    f"Actor '{actor_id}' does not hold an eligible approver role",
                    f"{path}/approver_actor_id",
                )
            )
            vote_valid = False
        if requirement["separation_of_duties"] and actor_id == request["actor_id"]:
            reasons.append(
                _reason(
                    "approval.self_approved",
                    "Separation of duties prohibits the acting actor from approving itself",
                    f"{path}/approver_actor_id",
                )
            )
            vote_valid = False
        identity = approval["identity"]
        if identity["trust_boundary_id"] not in trusted_approver_boundaries:
            reasons.append(
                _reason(
                    "approval.approver_untrusted",
                    "The approver identity boundary is not caller-trusted",
                    f"{path}/identity/trust_boundary_id",
                )
            )
            vote_valid = False
        approved_at = _parse_timestamp(approval["approved_at"])
        authenticated_at = _parse_timestamp(identity["authenticated_at"])
        identity_expires_at = _parse_timestamp(identity["expires_at"])
        assert approved_at and authenticated_at and identity_expires_at
        if not authenticated_at <= approved_at < identity_expires_at:
            reasons.append(
                _reason(
                    "approval.approver_assertion_stale",
                    "The approver assertion was not current when approval occurred",
                    f"{path}/approved_at",
                )
            )
            vote_valid = False
        if approved_at < requested_at:
            reasons.append(
                _reason(
                    "approval.approved_before_request",
                    "The approval predates the exact request",
                    f"{path}/approved_at",
                )
            )
            vote_valid = False
        if approved_at > issued_at:
            reasons.append(
                _reason(
                    "approval.approved_after_issue",
                    "The approval occurred after the grant was issued",
                    f"{path}/approved_at",
                )
            )
            vote_valid = False
        if vote_valid:
            eligible_votes[approval_id].add(actor_id)

    for approval_id, requirement in sorted(requirements.items()):
        actual = len(eligible_votes[approval_id])
        if actual < requirement["quorum"]:
            reasons.append(
                _reason(
                    "approval.insufficient_quorum",
                    f"Approval requirement '{approval_id}' needs quorum {requirement['quorum']} but has {actual} eligible approval(s)",
                    "/approvals",
                )
            )

    outcome = "satisfied" if not reasons else "not_satisfied"
    if outcome == "satisfied":
        reasons = [
            _reason(
                "approval.satisfied",
                "The exact-bound approval grant satisfies every approval requirement",
            )
        ]
    return _build_result(
        policy=policy,
        policy_valid=True,
        request=request,
        request_valid=True,
        decision=decision_data,
        grant=grant,
        state=state,
        outcome=outcome,
        reasons=reasons,
        valid_until=grant["expires_at"] if outcome == "satisfied" else None,
    )


def verify_approval_grant(
    policy: Any,
    request: Any,
    decision: Any,
    grant: Any,
    state: Any,
) -> ApprovalVerificationResult:
    """Verify one exact-bound grant without I/O, dispatch, or state mutation."""

    return _verify_approval_grant(policy, request, decision, grant, state)


def verify_approval_grant_files(
    policy_path: str,
    request_path: str,
    decision_path: str,
    grant_path: str,
    state_path: str,
) -> ApprovalVerificationResult:
    """Load verification inputs and return a fail-closed result for every outcome."""

    policy: Any = None
    request: Any = None
    policy_issues: Sequence[ValidationIssue] = ()
    request_issues: Sequence[ValidationIssue] = ()
    try:
        policy = load_policy_bundle(policy_path)
    except PolicyBundleError as exc:
        policy_issues = exc.issues
    try:
        request = load_action_request(request_path)
    except ActionRequestError as exc:
        request_issues = exc.issues
    decision, decision_issues = _load_json(decision_path)
    grant, grant_issues = _load_json(grant_path)
    state, state_issues = _load_json(state_path)
    return _verify_approval_grant(
        policy,
        request,
        decision,
        grant,
        state,
        policy_input_issues=policy_issues,
        request_input_issues=request_issues,
        decision_input_issues=decision_issues,
        grant_input_issues=grant_issues,
        state_input_issues=state_issues,
    )
