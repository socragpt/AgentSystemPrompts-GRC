"""Deterministic, side-effect-free Policy Bundle v0.1 action decisions."""

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .policy import (
    PolicyBundleError,
    ValidationIssue,
    compile_policy_bundle,
    load_policy_bundle,
    validate_policy_bundle,
)


ACTION_REQUEST_SCHEMA_VERSION = "0.1"
DECISION_RESULT_SCHEMA_VERSION = "0.1"
EVIDENCE_RECORD_SCHEMA_VERSION = "0.1"

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_DATA_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}
_SIDE_EFFECTS = {
    "create",
    "delete",
    "delegate",
    "external_communication",
    "read",
    "spend",
    "update",
}
_EFFECT_RANK = {"allow": 0, "require_approval": 1, "deny": 2}


@dataclass(frozen=True)
class DecisionResult:
    """Immutable serialized decision-result contract returned by the SDK."""

    _json: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "DecisionResult":
        return cls(_contract_json(value))

    def as_dict(self) -> Dict[str, Any]:
        """Return a fresh JSON-compatible decision object."""

        return json.loads(self._json)

    def to_json(self) -> str:
        """Return canonical, human-readable JSON with one trailing newline."""

        return self._json

    @property
    def disposition(self) -> str:
        return self.as_dict()["disposition"]

    @property
    def decision_id(self) -> str:
        return self.as_dict()["decision_id"]

    @property
    def proposed_evidence_record(self) -> Dict[str, Any]:
        return self.as_dict()["proposed_evidence_record"]


class ActionRequestError(ValueError):
    """Raised when a serialized action request cannot be loaded."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(_sorted_issues(issues))
        message = self.issues[0].message if self.issues else "Invalid action request"
        super().__init__(message)


class ParameterEncodingError(ValueError):
    """Raised when parameters cannot use the v0.1 canonical JSON subset."""


def _sorted_issues(issues: Iterable[ValidationIssue]) -> List[ValidationIssue]:
    return sorted(issues, key=lambda item: (item.path, item.code, item.message))


def _pointer(base: str, value: object) -> str:
    escaped = str(value).replace("~", "~0").replace("/", "~1")
    return f"{base}/{escaped}" if base else f"/{escaped}"


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not _TIMESTAMP_PATTERN.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _contract_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _safe_json_value(value: Any) -> Any:
    """Create a deterministic digest input even for malformed SDK values."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return {"unsupported_number": repr(value)}
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value]
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            safe_key = key if isinstance(key, str) else f"unsupported-key:{type(key).__name__}:{key}"
            result[safe_key] = _safe_json_value(value[key])
        return result
    value_type = type(value)
    return {"unsupported_type": f"{value_type.__module__}.{value_type.__qualname__}"}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _input_digest(value: Any) -> str:
    return _sha256_text(_canonical_json(_safe_json_value(value)))


def _canonical_parameter_value(value: Any, path: str = "") -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, list):
        return [
            _canonical_parameter_value(item, f"{path}/{index}")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ParameterEncodingError(
                f"Parameter object keys must be strings at {path or '/'}"
            )
        return {
            key: _canonical_parameter_value(value[key], _pointer(path, key))
            for key in sorted(value)
        }
    raise ParameterEncodingError(
        f"Unsupported parameter type '{type(value).__name__}' at {path or '/'}; "
        "v0.1 permits null, booleans, integers, strings, arrays, and objects"
    )


def canonical_parameters_digest(parameters: Any) -> str:
    """Return the v0.1 canonical SHA-256 binding for JSON-like parameters."""

    normalized = _canonical_parameter_value(parameters)
    return "sha256:" + _sha256_text(_canonical_json(normalized))


def _issue(
    issues: List[ValidationIssue], code: str, path: str, message: str
) -> None:
    issues.append(ValidationIssue(code, path or "/", message))


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


def _validate_positive_integer(
    issues: List[ValidationIssue],
    value: Any,
    path: str,
    minimum: int,
    maximum: Optional[int] = None,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _issue(issues, "schema.type", path, "Expected an integer")
        return
    if value < minimum or (maximum is not None and value > maximum):
        range_text = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        _issue(issues, "schema.range", path, f"Expected integer {range_text}")


def validate_action_request(request: Any) -> List[ValidationIssue]:
    """Return deterministic shape errors for Action Request v0.1."""

    issues: List[ValidationIssue] = []
    top_fields = {
        "schema_version",
        "request_id",
        "principal",
        "authorized_goal_id",
        "actor_id",
        "capability_id",
        "action",
        "resource_id",
        "parameters_digest",
        "requested_at",
        "context",
    }
    root = _validate_object(issues, request, "", top_fields, top_fields)
    if root is None:
        return _sorted_issues(issues)

    if "schema_version" in root and root["schema_version"] != ACTION_REQUEST_SCHEMA_VERSION:
        _issue(
            issues,
            "schema_version.unsupported",
            "/schema_version",
            f"Expected schema_version '{ACTION_REQUEST_SCHEMA_VERSION}'",
        )
    for field in (
        "request_id",
        "authorized_goal_id",
        "actor_id",
        "capability_id",
        "action",
        "resource_id",
    ):
        if field in root:
            _validate_identifier(issues, root[field], f"/{field}")
    if "parameters_digest" in root:
        digest = root["parameters_digest"]
        if not isinstance(digest, str) or not _DIGEST_PATTERN.fullmatch(digest):
            _issue(
                issues,
                "schema.format",
                "/parameters_digest",
                "Expected a lowercase sha256:<64-hex-character> digest",
            )
    if "requested_at" in root:
        _validate_timestamp(issues, root["requested_at"], "/requested_at")

    principal_fields = {"actor_id", "authentication"}
    if "principal" in root:
        principal = _validate_object(
            issues, root["principal"], "/principal", principal_fields, principal_fields
        )
        if principal is not None:
            if "actor_id" in principal:
                _validate_identifier(issues, principal["actor_id"], "/principal/actor_id")
            auth_fields = {
                "trust_boundary_id",
                "assertion_id",
                "authenticated_at",
                "expires_at",
            }
            if "authentication" in principal:
                authentication = _validate_object(
                    issues,
                    principal["authentication"],
                    "/principal/authentication",
                    auth_fields,
                    auth_fields,
                )
                if authentication is not None:
                    for field in ("trust_boundary_id", "assertion_id"):
                        if field in authentication:
                            _validate_identifier(
                                issues,
                                authentication[field],
                                f"/principal/authentication/{field}",
                            )
                    for field in ("authenticated_at", "expires_at"):
                        if field in authentication:
                            _validate_timestamp(
                                issues,
                                authentication[field],
                                f"/principal/authentication/{field}",
                            )
                    authenticated_at = _parse_timestamp(authentication.get("authenticated_at"))
                    expires_at = _parse_timestamp(authentication.get("expires_at"))
                    if authenticated_at and expires_at and expires_at <= authenticated_at:
                        _issue(
                            issues,
                            "authentication.lifecycle_invalid",
                            "/principal/authentication/expires_at",
                            "expires_at must be later than authenticated_at",
                        )

    context_fields = {
        "channel_id",
        "data_classification",
        "expected_side_effects",
        "reversible",
        "requested_constraints",
    }
    if "context" in root:
        context = _validate_object(
            issues, root["context"], "/context", context_fields, context_fields
        )
        if context is not None:
            if "channel_id" in context and context["channel_id"] is not None:
                _validate_identifier(issues, context["channel_id"], "/context/channel_id")
            if "data_classification" in context:
                classification = context["data_classification"]
                if not isinstance(classification, str) or classification not in _DATA_CLASSIFICATIONS:
                    _issue(
                        issues,
                        "schema.enum",
                        "/context/data_classification",
                        "Expected one of: confidential, internal, public, restricted",
                    )
            if "expected_side_effects" in context:
                effects = context["expected_side_effects"]
                if not isinstance(effects, list):
                    _issue(
                        issues,
                        "schema.type",
                        "/context/expected_side_effects",
                        "Expected an array",
                    )
                elif not effects:
                    _issue(
                        issues,
                        "schema.min_items",
                        "/context/expected_side_effects",
                        "Expected at least one side effect",
                    )
                else:
                    seen: Set[str] = set()
                    for index, effect in enumerate(effects):
                        effect_path = f"/context/expected_side_effects/{index}"
                        if not isinstance(effect, str) or effect not in _SIDE_EFFECTS:
                            _issue(
                                issues,
                                "schema.enum",
                                effect_path,
                                "Unsupported expected side effect",
                            )
                        elif effect in seen:
                            _issue(
                                issues,
                                "schema.unique_items",
                                effect_path,
                                f"Duplicate value '{effect}'",
                            )
                        else:
                            seen.add(effect)
            if "reversible" in context and not isinstance(context["reversible"], bool):
                _issue(issues, "schema.type", "/context/reversible", "Expected a boolean")

            constraint_fields = {
                "max_cost",
                "max_duration_seconds",
                "max_action_count",
                "max_delegation_depth",
            }
            if "requested_constraints" in context:
                constraints = _validate_object(
                    issues,
                    context["requested_constraints"],
                    "/context/requested_constraints",
                    constraint_fields,
                    constraint_fields,
                )
                if constraints is not None:
                    if "max_cost" in constraints:
                        cost_fields = {"amount_minor", "currency"}
                        cost = _validate_object(
                            issues,
                            constraints["max_cost"],
                            "/context/requested_constraints/max_cost",
                            cost_fields,
                            cost_fields,
                        )
                        if cost is not None:
                            if "amount_minor" in cost:
                                _validate_positive_integer(
                                    issues,
                                    cost["amount_minor"],
                                    "/context/requested_constraints/max_cost/amount_minor",
                                    0,
                                )
                            if "currency" in cost:
                                currency = cost["currency"]
                                if not isinstance(currency, str) or not _CURRENCY_PATTERN.fullmatch(currency):
                                    _issue(
                                        issues,
                                        "schema.pattern",
                                        "/context/requested_constraints/max_cost/currency",
                                        "Expected an ISO-style three-letter currency",
                                    )
                    for field in ("max_duration_seconds", "max_action_count"):
                        if field in constraints:
                            _validate_positive_integer(
                                issues,
                                constraints[field],
                                f"/context/requested_constraints/{field}",
                                1,
                            )
                    if "max_delegation_depth" in constraints:
                        _validate_positive_integer(
                            issues,
                            constraints["max_delegation_depth"],
                            "/context/requested_constraints/max_delegation_depth",
                            0,
                            16,
                        )
    return _sorted_issues(issues)


def load_action_request(path: str) -> Dict[str, Any]:
    """Load a UTF-8 JSON action request or raise ``ActionRequestError``."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ActionRequestError(
            [ValidationIssue("json.read", "/", f"Unable to read {source}: {exc}")]
        ) from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ActionRequestError(
            [
                ValidationIssue(
                    "json.syntax",
                    "/",
                    exc.msg,
                    line=exc.lineno,
                    column=exc.colno,
                )
            ]
        ) from exc
    if not isinstance(value, dict):
        raise ActionRequestError(
            [ValidationIssue("schema.type", "/", "Action request root must be an object")]
        )
    return value


def normalize_action_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return a canonical copy of an already valid Action Request v0.1."""

    result = deepcopy(request)
    effects = result.get("context", {}).get("expected_side_effects")
    if isinstance(effects, list):
        result["context"]["expected_side_effects"] = sorted(effects)
    return result


def _reason(code: str, message: str, path: Optional[str] = None) -> Dict[str, Any]:
    value: Dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        value["path"] = path
    return value


def _validation_reasons(
    prefix: str, issues: Iterable[ValidationIssue]
) -> List[Dict[str, Any]]:
    result = []
    for issue in _sorted_issues(issues):
        code = issue.code
        if issue.path == "/schema_version":
            code = "schema_version.unsupported"
        result.append(_reason(f"{prefix}.{code}", issue.message, issue.path))
    return result


def _policy_provenance(policy: Any, valid_policy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metadata = policy.get("bundle", {}) if isinstance(policy, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    source_sha256 = _input_digest(policy)
    schema_version = policy.get("schema_version") if isinstance(policy, dict) else None
    if valid_policy is not None:
        compiled_data = json.loads(compile_policy_bundle(valid_policy).decision_data)
        source_sha256 = compiled_data["compilation"]["source_sha256"]
        schema_version = compiled_data["schema_version"]
        metadata = compiled_data["bundle"]
    return {
        "bundle_id": metadata.get("id") if isinstance(metadata.get("id"), str) else None,
        "bundle_version": metadata.get("version") if isinstance(metadata.get("version"), str) else None,
        "schema_version": schema_version if isinstance(schema_version, str) else None,
        "source_sha256": source_sha256,
    }


def _extract_request_context(request: Any) -> Dict[str, Any]:
    root = request if isinstance(request, dict) else {}
    principal = root.get("principal") if isinstance(root.get("principal"), dict) else {}
    authentication = (
        principal.get("authentication")
        if isinstance(principal.get("authentication"), dict)
        else {}
    )

    def string(mapping: Dict[str, Any], field: str) -> Optional[str]:
        value = mapping.get(field)
        return value if isinstance(value, str) else None

    return {
        "request_id": string(root, "request_id"),
        "requested_at": string(root, "requested_at"),
        "parameters_digest": string(root, "parameters_digest"),
        "principal_actor_id": string(principal, "actor_id"),
        "trust_boundary_id": string(authentication, "trust_boundary_id"),
        "assertion_id": string(authentication, "assertion_id"),
        "authorized_goal_id": string(root, "authorized_goal_id"),
        "actor_id": string(root, "actor_id"),
        "capability_id": string(root, "capability_id"),
        "action": string(root, "action"),
        "resource_id": string(root, "resource_id"),
    }


def _subject_matches(
    selector: Dict[str, Any], actor_id: str, actor_roles: Set[str]
) -> bool:
    if selector.get("any") is True:
        return True
    return actor_id in set(selector.get("actor_ids", [])) or bool(
        actor_roles & set(selector.get("role_ids", []))
    )


def _authority_path(
    policy: Dict[str, Any],
    principal_actor_id: str,
    actor_id: str,
    capability_id: str,
    requested_at: datetime,
) -> Tuple[Optional[Tuple[str, ...]], int, bool]:
    actors = {item["id"]: item for item in policy["actors"]}
    roles = {item["id"]: item for item in policy["roles"]}
    principal = actors[principal_actor_id]
    principal_capabilities: Set[str] = set()
    for role_id in principal["roles"]:
        principal_capabilities.update(roles[role_id]["capabilities"])
    if capability_id not in principal_capabilities:
        return None, 0, False
    if principal_actor_id == actor_id:
        return (), 16, False

    delegations = sorted(policy["delegations"], key=lambda item: item["id"])
    queue: Deque[Tuple[str, int, Tuple[str, ...]]] = deque(
        [(principal_actor_id, 17, ())]
    )
    best_remaining: Dict[str, int] = {principal_actor_id: 17}
    saw_inactive = False
    while queue:
        current, remaining, path = queue.popleft()
        for delegation in delegations:
            if delegation["from_actor_id"] != current:
                continue
            if capability_id not in delegation["capability_ids"]:
                continue
            start = _parse_timestamp(delegation["valid_from"])
            end = _parse_timestamp(delegation["valid_until"])
            if start is None or end is None or not (start <= requested_at < end):
                if delegation["to_actor_id"] == actor_id:
                    saw_inactive = True
                continue
            next_remaining = delegation["max_depth"]
            if remaining < 1 or next_remaining > remaining - 1:
                continue
            target = delegation["to_actor_id"]
            next_path = path + (delegation["id"],)
            if target == actor_id:
                return next_path, next_remaining, saw_inactive
            if best_remaining.get(target, -1) >= next_remaining:
                continue
            best_remaining[target] = next_remaining
            queue.append((target, next_remaining, next_path))
    return None, 0, saw_inactive


def _control_citation(
    policy: Dict[str, Any],
    control: Dict[str, Any],
    effective_effect: str,
    exception_id: Optional[str],
) -> Dict[str, Any]:
    return {
        "policy_id": policy["id"],
        "policy_version": policy["version"],
        "precedence": policy["precedence"],
        "control_id": control["id"],
        "control_effect": control["effect"],
        "effective_effect": effective_effect,
        "exception_id": exception_id,
    }


def _combine_constraints(
    request: Dict[str, Any],
    controls: Sequence[Dict[str, Any]],
    authority_remaining_depth: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    context = request["context"]
    requested = context["requested_constraints"]
    requested_cost = requested["max_cost"]
    currency = requested_cost["currency"]
    cost_amount = requested_cost["amount_minor"]
    max_duration = requested["max_duration_seconds"]
    max_action_count = requested["max_action_count"]
    max_delegation_depth = min(
        requested["max_delegation_depth"], authority_remaining_depth
    )
    allowed_classifications: Optional[Set[str]] = None
    require_reversible = False
    reasons: List[Dict[str, Any]] = []

    for control in controls:
        constraints = control.get("constraints", {})
        if "max_cost" in constraints:
            policy_cost = constraints["max_cost"]
            if policy_cost["currency"] != currency:
                reasons.append(
                    _reason(
                        "constraint.cost_currency_conflict",
                        "Requested and policy cost bounds use different currencies",
                        "/context/requested_constraints/max_cost/currency",
                    )
                )
            else:
                cost_amount = min(cost_amount, policy_cost["amount_minor"])
        if "max_duration_seconds" in constraints:
            max_duration = min(max_duration, constraints["max_duration_seconds"])
        if "max_action_count" in constraints:
            max_action_count = min(max_action_count, constraints["max_action_count"])
        if "max_delegation_depth" in constraints:
            max_delegation_depth = min(
                max_delegation_depth, constraints["max_delegation_depth"]
            )
        if "allowed_data_classifications" in constraints:
            values = set(constraints["allowed_data_classifications"])
            allowed_classifications = (
                values
                if allowed_classifications is None
                else allowed_classifications & values
            )
        require_reversible = require_reversible or constraints.get(
            "require_reversible", False
        )

    requested_classification = context["data_classification"]
    if (
        allowed_classifications is not None
        and requested_classification not in allowed_classifications
    ):
        reasons.append(
            _reason(
                "constraint.data_classification_denied",
                f"Data classification '{requested_classification}' is outside the effective control scope",
                "/context/data_classification",
            )
        )
        effective_classifications: List[str] = sorted(allowed_classifications)
    else:
        effective_classifications = [requested_classification]
    if require_reversible and not context["reversible"]:
        reasons.append(
            _reason(
                "constraint.reversibility_required",
                "The applicable controls require a reversible action",
                "/context/reversible",
            )
        )

    effective = {
        "max_cost": {"amount_minor": cost_amount, "currency": currency},
        "max_duration_seconds": max_duration,
        "max_action_count": max_action_count,
        "max_delegation_depth": max_delegation_depth,
        "allowed_data_classifications": effective_classifications,
        "require_reversible": require_reversible,
    }
    return effective, reasons


def _approval_requirements(
    policy: Dict[str, Any], approval_ids: Iterable[str]
) -> List[Dict[str, Any]]:
    approvals = {item["id"]: item for item in policy["approvals"]}
    result = []
    for approval_id in sorted(set(approval_ids)):
        approval = approvals[approval_id]
        result.append(
            {
                "approval_id": approval_id,
                "approver_role_ids": sorted(approval["approver_role_ids"]),
                "quorum": approval["quorum"],
                "separation_of_duties": approval["separation_of_duties"],
                "expires_after_seconds": approval["expires_after_seconds"],
                "bind_to": sorted(approval["bind_to"]),
            }
        )
    return result


def _build_result(
    *,
    request: Any,
    request_sha256: str,
    disposition: str,
    reasons: Sequence[Dict[str, Any]],
    cited_controls: Sequence[Dict[str, Any]],
    effective_constraints: Dict[str, Any],
    approval_requirements: Sequence[Dict[str, Any]],
    policy_provenance: Dict[str, Any],
    delegation_path: Sequence[str],
    valid_until: Optional[str],
) -> DecisionResult:
    request_context = _extract_request_context(request)
    authority = {
        "principal_actor_id": request_context["principal_actor_id"],
        "acting_actor_id": request_context["actor_id"],
        "authorized_goal_id": request_context["authorized_goal_id"],
        "delegation_path": list(delegation_path),
    }
    normalized_citations = sorted(
        (deepcopy(item) for item in cited_controls),
        key=lambda item: (
            -item["precedence"],
            item["policy_id"],
            item["control_id"],
            item["exception_id"] or "",
        ),
    )
    normalized_approvals = sorted(
        (deepcopy(item) for item in approval_requirements),
        key=lambda item: item["approval_id"],
    )
    decision_core = {
        "request_sha256": request_sha256,
        "disposition": disposition,
        "reasons": list(reasons),
        "cited_controls": normalized_citations,
        "effective_constraints": deepcopy(effective_constraints),
        "approval_requirements": normalized_approvals,
        "valid_until": valid_until,
        "policy": deepcopy(policy_provenance),
        "authority": authority,
    }
    decision_id = "decision." + _sha256_text(_canonical_json(decision_core))
    reason_codes = list(dict.fromkeys(item["code"] for item in reasons))
    evidence_core = {
        "record_type": "proposed_decision",
        "proposal_only": True,
        "request": {
            "request_id": request_context["request_id"],
            "request_sha256": request_sha256,
            "requested_at": request_context["requested_at"],
            "parameters_digest": request_context["parameters_digest"],
        },
        "principal": {
            "actor_id": request_context["principal_actor_id"],
            "trust_boundary_id": request_context["trust_boundary_id"],
            "assertion_id": request_context["assertion_id"],
        },
        "action": {
            "authorized_goal_id": request_context["authorized_goal_id"],
            "actor_id": request_context["actor_id"],
            "capability_id": request_context["capability_id"],
            "action": request_context["action"],
            "resource_id": request_context["resource_id"],
        },
        "policy": deepcopy(policy_provenance),
        "decision": {
            "decision_id": decision_id,
            "disposition": disposition,
            "valid_until": valid_until,
            "reason_codes": reason_codes,
            "cited_control_ids": sorted(
                {item["control_id"] for item in normalized_citations}
            ),
            "effective_constraints": deepcopy(effective_constraints),
            "approval_requirement_ids": [
                item["approval_id"] for item in normalized_approvals
            ],
        },
    }
    evidence_id = "evidence." + _sha256_text(_canonical_json(evidence_core))
    evidence = {
        "schema_version": EVIDENCE_RECORD_SCHEMA_VERSION,
        "evidence_id": evidence_id,
        **evidence_core,
    }
    payload = {
        "schema_version": DECISION_RESULT_SCHEMA_VERSION,
        "decision_id": decision_id,
        "request_id": request_context["request_id"],
        **decision_core,
        "proposed_evidence_record": evidence,
    }
    return DecisionResult.from_dict(payload)


def _evaluate_action(
    policy: Any,
    request: Any,
    *,
    trusted_identity_boundaries: Iterable[str],
    policy_input_issues: Iterable[ValidationIssue] = (),
    request_input_issues: Iterable[ValidationIssue] = (),
) -> DecisionResult:
    raw_request_sha256 = _input_digest(request)
    request_issues = list(request_input_issues)
    if not request_issues:
        request_issues = validate_action_request(request)
    policy_issues = list(policy_input_issues)
    if not policy_issues:
        policy_issues = validate_policy_bundle(policy)
    valid_policy = policy if not policy_issues and isinstance(policy, dict) else None
    provenance = _policy_provenance(policy, valid_policy)
    if request_issues or policy_issues:
        reasons = _validation_reasons("request", request_issues)
        reasons.extend(_validation_reasons("policy", policy_issues))
        return _build_result(
            request=request,
            request_sha256=raw_request_sha256,
            disposition="deny",
            reasons=reasons,
            cited_controls=(),
            effective_constraints={},
            approval_requirements=(),
            policy_provenance=provenance,
            delegation_path=(),
            valid_until=None,
        )

    assert isinstance(policy, dict)
    assert isinstance(request, dict)
    normalized_request = normalize_action_request(request)
    request_sha256 = _input_digest(normalized_request)
    compiled = json.loads(compile_policy_bundle(policy).decision_data)
    context = normalized_request["context"]
    principal = normalized_request["principal"]
    authentication = principal["authentication"]
    requested_at = _parse_timestamp(normalized_request["requested_at"])
    authenticated_at = _parse_timestamp(authentication["authenticated_at"])
    authentication_expires_at = _parse_timestamp(authentication["expires_at"])
    assert requested_at is not None
    assert authenticated_at is not None
    assert authentication_expires_at is not None

    def finish(
        disposition: str,
        reasons: Sequence[Dict[str, Any]],
        cited_controls: Sequence[Dict[str, Any]] = (),
        effective_constraints: Optional[Dict[str, Any]] = None,
        approval_requirements: Sequence[Dict[str, Any]] = (),
        delegation_path: Sequence[str] = (),
        valid_until: Optional[str] = None,
    ) -> DecisionResult:
        return _build_result(
            request=normalized_request,
            request_sha256=request_sha256,
            disposition=disposition,
            reasons=reasons,
            cited_controls=cited_controls,
            effective_constraints=effective_constraints or {},
            approval_requirements=approval_requirements,
            policy_provenance=provenance,
            delegation_path=delegation_path,
            valid_until=valid_until,
        )

    trusted = {
        boundary
        for boundary in trusted_identity_boundaries
        if isinstance(boundary, str)
    }
    if authentication["trust_boundary_id"] not in trusted:
        return finish(
            "deny",
            [
                _reason(
                    "identity.boundary_untrusted",
                    f"Identity boundary '{authentication['trust_boundary_id']}' is not trusted for this evaluation",
                    "/principal/authentication/trust_boundary_id",
                )
            ],
        )
    if requested_at < authenticated_at:
        return finish(
            "deny",
            [
                _reason(
                    "identity.assertion_not_yet_valid",
                    "The identity assertion was authenticated after the requested action time",
                    "/principal/authentication/authenticated_at",
                )
            ],
        )
    if requested_at >= authentication_expires_at:
        return finish(
            "deny",
            [
                _reason(
                    "identity.assertion_expired",
                    "The identity assertion is expired at the requested action time",
                    "/principal/authentication/expires_at",
                )
            ],
        )

    bundle_start = _parse_timestamp(compiled["bundle"]["effective_at"])
    bundle_end = _parse_timestamp(compiled["bundle"]["review_at"])
    assert bundle_start is not None and bundle_end is not None
    if requested_at < bundle_start:
        return finish(
            "deny",
            [
                _reason(
                    "policy.not_yet_effective",
                    "The policy bundle is not effective at the requested action time",
                    "/bundle/effective_at",
                )
            ],
        )
    if requested_at >= bundle_end:
        return finish(
            "deny",
            [
                _reason(
                    "policy.stale",
                    "The policy bundle reached review_at before the requested action time",
                    "/bundle/review_at",
                )
            ],
        )

    actors = {item["id"]: item for item in compiled["actors"]}
    roles = {item["id"]: item for item in compiled["roles"]}
    resources = {item["id"]: item for item in compiled["resources"]}
    capabilities = {item["id"]: item for item in compiled["capabilities"]}
    principal_id = principal["actor_id"]
    actor_id = normalized_request["actor_id"]
    capability_id = normalized_request["capability_id"]
    if principal_id not in actors:
        return finish(
            "deny",
            [
                _reason(
                    "authority.principal_not_found",
                    f"Principal actor '{principal_id}' is not defined by the policy",
                    "/principal/actor_id",
                )
            ],
        )
    if actor_id not in actors:
        return finish(
            "deny",
            [
                _reason(
                    "authority.actor_not_found",
                    f"Acting actor '{actor_id}' is not defined by the policy",
                    "/actor_id",
                )
            ],
        )
    if capability_id not in capabilities:
        return finish(
            "deny",
            [
                _reason(
                    "authority.capability_not_found",
                    f"Capability '{capability_id}' is not defined by the policy",
                    "/capability_id",
                )
            ],
        )
    capability = capabilities[capability_id]
    if normalized_request["action"] != capability["action"]:
        return finish(
            "deny",
            [
                _reason(
                    "request.capability_action_mismatch",
                    "The requested action does not match the named capability",
                    "/action",
                )
            ],
        )
    if normalized_request["resource_id"] != capability["resource_id"]:
        return finish(
            "deny",
            [
                _reason(
                    "request.capability_resource_mismatch",
                    "The concrete resource does not match the named capability",
                    "/resource_id",
                )
            ],
        )
    resource = resources[capability["resource_id"]]
    if resource.get("kind") == "data" and resource.get("classification") != context["data_classification"]:
        return finish(
            "deny",
            [
                _reason(
                    "request.resource_classification_mismatch",
                    "The requested data classification does not match the governed resource",
                    "/context/data_classification",
                )
            ],
        )
    channel_id = context["channel_id"]
    if resource["kind"] == "channel" and channel_id != resource["id"]:
        return finish(
            "deny",
            [
                _reason(
                    "request.channel_required",
                    "A channel capability must name its governed channel as channel_id",
                    "/context/channel_id",
                )
            ],
        )
    if channel_id is not None and resource["kind"] != "channel":
        return finish(
            "deny",
            [
                _reason(
                    "request.channel_unsupported",
                    "Policy Bundle v0.1 cannot authorize a separate channel for this capability",
                    "/context/channel_id",
                )
            ],
        )

    path, remaining_depth, saw_inactive = _authority_path(
        compiled, principal_id, actor_id, capability_id, requested_at
    )
    if path is None:
        reason_code = (
            "authority.delegation_inactive" if saw_inactive else "authority.not_granted"
        )
        message = (
            "A matching delegation exists but is not active at the requested action time"
            if saw_inactive
            else "No current role and delegation path grants this principal authority for the acting actor and capability"
        )
        return finish("deny", [_reason(reason_code, message)])

    actor_roles = set(actors[actor_id]["roles"])
    applicable: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    active: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    inactive: List[Tuple[Dict[str, Any], Dict[str, Any], str]] = []
    for policy_item in compiled["policies"]:
        policy_start = _parse_timestamp(policy_item["effective_at"])
        policy_end = _parse_timestamp(policy_item["review_at"])
        assert policy_start is not None and policy_end is not None
        for control in policy_item["controls"]:
            if capability_id not in control["capability_ids"]:
                continue
            if not _subject_matches(control["subjects"], actor_id, actor_roles):
                continue
            applicable.append((policy_item, control))
            if policy_start <= requested_at < policy_end:
                active.append((policy_item, control))
            else:
                state = "not_yet_effective" if requested_at < policy_start else "stale"
                inactive.append((policy_item, control, state))
    if not applicable:
        return finish(
            "deny",
            [
                _reason(
                    "control.not_applicable",
                    "No policy control applies to the acting actor and capability",
                )
            ],
            delegation_path=path,
        )

    highest_active = max((item[0]["precedence"] for item in active), default=-1)
    blocking_inactive = [
        item for item in inactive if item[0]["precedence"] >= highest_active
    ]
    if blocking_inactive:
        reasons = []
        citations = []
        for policy_item, control, state in sorted(
            blocking_inactive,
            key=lambda item: (-item[0]["precedence"], item[0]["id"], item[1]["id"]),
        ):
            code = f"policy.{state}"
            reasons.append(
                _reason(
                    code,
                    f"Applicable policy '{policy_item['id']}' is {state.replace('_', ' ')} at the requested action time",
                )
            )
            citations.append(
                _control_citation(policy_item, control, control["effect"], None)
            )
        return finish(
            "deny", reasons, citations, delegation_path=path
        )

    selected = [item for item in active if item[0]["precedence"] == highest_active]
    cited_controls: List[Dict[str, Any]] = []
    effective_controls: List[Dict[str, Any]] = []
    effective_effects: List[str] = []
    approval_ids: List[str] = []
    reasons: List[Dict[str, Any]] = []
    exception_conflict = False
    for policy_item, control in selected:
        matching_exceptions = []
        inactive_exceptions = []
        for exception in compiled["exceptions"]:
            if exception["control_id"] != control["id"]:
                continue
            if capability_id not in exception["capability_ids"]:
                continue
            if not _subject_matches(exception["subjects"], actor_id, actor_roles):
                continue
            start = _parse_timestamp(exception["valid_from"])
            end = _parse_timestamp(exception["valid_until"])
            assert start is not None and end is not None
            if start <= requested_at < end:
                matching_exceptions.append(exception)
            else:
                inactive_exceptions.append(exception)
        if len(matching_exceptions) > 1:
            exception_conflict = True
            reasons.append(
                _reason(
                    "exception.conflict",
                    f"Multiple active exceptions match control '{control['id']}'",
                )
            )
            effective_effect = control["effect"]
            exception_id = None
            approval_id = control.get("approval_id")
        elif matching_exceptions:
            exception = matching_exceptions[0]
            effective_effect = exception["replacement_effect"]
            exception_id = exception["id"]
            approval_id = exception.get("approval_id")
            reasons.append(
                _reason(
                    "exception.applied",
                    f"Active exception '{exception_id}' replaces control '{control['id']}' with {effective_effect}",
                )
            )
        else:
            effective_effect = control["effect"]
            exception_id = None
            approval_id = control.get("approval_id")
            for exception in sorted(inactive_exceptions, key=lambda item: item["id"]):
                reasons.append(
                    _reason(
                        "exception.inactive",
                        f"Exception '{exception['id']}' is not active at the requested action time",
                    )
                )
        cited_controls.append(
            _control_citation(policy_item, control, effective_effect, exception_id)
        )
        effective_controls.append(control)
        effective_effects.append(effective_effect)
        if effective_effect == "require_approval" and approval_id:
            approval_ids.append(approval_id)

    effective_constraints, constraint_reasons = _combine_constraints(
        normalized_request, effective_controls, remaining_depth
    )
    reasons.extend(constraint_reasons)
    resolved_effect = max(
        effective_effects, key=lambda effect: _EFFECT_RANK[effect]
    )
    if len(set(effective_effects)) > 1:
        reasons.append(
            _reason(
                "control.restrictive_precedence",
                f"Equal-precedence controls resolve to the most restrictive effect: {resolved_effect}",
            )
        )
    if exception_conflict or constraint_reasons:
        disposition = "deny"
        approval_requirements: Sequence[Dict[str, Any]] = ()
    else:
        disposition = resolved_effect
        approval_requirements = (
            _approval_requirements(compiled, approval_ids)
            if disposition == "require_approval"
            else ()
        )
    reasons.append(
        _reason(
            f"control.{resolved_effect}",
            f"The highest-precedence applicable controls resolve to {resolved_effect}",
        )
    )
    decision_valid_until: Optional[str] = None
    if disposition != "deny":
        expiry_values = [
            authentication["expires_at"],
            compiled["bundle"]["review_at"],
        ]
        delegations_by_id = {item["id"]: item for item in compiled["delegations"]}
        expiry_values.extend(
            delegations_by_id[delegation_id]["valid_until"]
            for delegation_id in path
        )
        expiry_values.extend(policy_item["review_at"] for policy_item, _ in selected)
        exceptions_by_id = {item["id"]: item for item in compiled["exceptions"]}
        expiry_values.extend(
            exceptions_by_id[item["exception_id"]]["valid_until"]
            for item in cited_controls
            if item["exception_id"] is not None
        )
        decision_valid_until = min(expiry_values)
    return finish(
        disposition,
        reasons,
        cited_controls,
        effective_constraints,
        approval_requirements,
        delegation_path=path,
        valid_until=decision_valid_until,
    )


def evaluate_action(
    policy: Any,
    request: Any,
    *,
    trusted_identity_boundaries: Iterable[str] = (),
) -> DecisionResult:
    """Evaluate one normalized request without I/O, dispatch, approval, or mutation."""

    return _evaluate_action(
        policy,
        request,
        trusted_identity_boundaries=trusted_identity_boundaries,
    )


def evaluate_action_files(
    policy_path: str,
    request_path: str,
    *,
    trusted_identity_boundaries: Iterable[str] = (),
) -> DecisionResult:
    """Load two JSON files and return a fail-closed decision for every outcome."""

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
    return _evaluate_action(
        policy,
        request,
        trusted_identity_boundaries=trusted_identity_boundaries,
        policy_input_issues=policy_issues,
        request_input_issues=request_issues,
    )
