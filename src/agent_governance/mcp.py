"""Deterministic MCP tool-call normalization and non-enforcing shadow evaluation."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .approval import verify_approval_grant
from .decision import (
    ParameterEncodingError,
    canonical_parameters_digest,
    evaluate_action,
    validate_action_request,
)
from .policy import PolicyBundleError, ValidationIssue, load_policy_bundle


MCP_CALL_PROPOSAL_SCHEMA_VERSION = "0.1"
MCP_ADAPTER_MAPPING_SCHEMA_VERSION = "0.1"
MCP_NORMALIZATION_RESULT_SCHEMA_VERSION = "0.1"
MCP_SHADOW_RESULT_SCHEMA_VERSION = "0.1"
MCP_SHADOW_EVIDENCE_SCHEMA_VERSION = "0.1"

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_SEMVER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
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


@dataclass(frozen=True)
class MCPNormalizationResult:
    """Immutable normalization contract returned for every MCP proposal outcome."""

    _json: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "MCPNormalizationResult":
        return cls(_contract_json(value))

    def as_dict(self) -> Dict[str, Any]:
        return json.loads(self._json)

    def to_json(self) -> str:
        return self._json

    @property
    def outcome(self) -> str:
        return self.as_dict()["outcome"]

    @property
    def action_request(self) -> Optional[Dict[str, Any]]:
        return self.as_dict()["action_request"]


@dataclass(frozen=True)
class MCPShadowResult:
    """Immutable proposal-only MCP shadow envelope returned by the SDK."""

    _json: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "MCPShadowResult":
        return cls(_contract_json(value))

    def as_dict(self) -> Dict[str, Any]:
        return json.loads(self._json)

    def to_json(self) -> str:
        return self._json

    @property
    def outcome(self) -> str:
        return self.as_dict()["outcome"]

    @property
    def disposition(self) -> Optional[str]:
        decision = self.as_dict()["decision_result"]
        return decision["disposition"] if isinstance(decision, dict) else None

    @property
    def proposed_evidence_record(self) -> Dict[str, Any]:
        return self.as_dict()["proposed_evidence_record"]


class MCPContractError(ValueError):
    """Raised when an MCP proposal or mapping cannot be loaded."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(_sorted_issues(issues))
        message = self.issues[0].message if self.issues else "Invalid MCP contract"
        super().__init__(message)


def _contract_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _safe_json_value(value: Any) -> Any:
    """Return a deterministic digest input even for malformed SDK values."""

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


def _sha256(value: Any) -> str:
    encoded = _canonical_json(_safe_json_value(value)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sorted_issues(issues: Iterable[ValidationIssue]) -> List[ValidationIssue]:
    return sorted(issues, key=lambda item: (item.path, item.code, item.message))


def _sorted_reasons(reasons: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (deepcopy(reason) for reason in reasons),
        key=lambda item: (item.get("path", ""), item["code"], item["message"]),
    )


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


def _issue(
    issues: List[ValidationIssue], code: str, path: str, message: str,
    related_path: Optional[str] = None,
) -> None:
    issues.append(ValidationIssue(code, path or "/", message, related_path))


def _reason(code: str, message: str, path: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        result["path"] = path
    return result


def _validate_object(
    issues: List[ValidationIssue],
    value: Any,
    path: str,
    required: Set[str],
    allowed: Set[str],
    prefix: str,
) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        _issue(issues, f"{prefix}.schema.type", path, "Expected an object")
        return None
    for field in sorted(required - set(value)):
        _issue(
            issues,
            f"{prefix}.schema.required",
            path or "/",
            f"Missing required field '{field}'",
        )
    for field in sorted(set(value) - allowed, key=str):
        _issue(
            issues,
            f"{prefix}.schema.unknown_field",
            _pointer(path, field),
            f"Unknown field '{field}'",
        )
    return value


def _validate_identifier(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    if not isinstance(value, str):
        _issue(issues, f"{prefix}.schema.type", path, "Expected an identifier string")
    elif not 3 <= len(value) <= 128 or not _ID_PATTERN.fullmatch(value):
        _issue(issues, f"{prefix}.schema.pattern", path, f"Invalid identifier '{value}'")


def _validate_tool_name(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    if not isinstance(value, str):
        _issue(issues, f"{prefix}.schema.type", path, "Expected a tool-name string")
    elif not 1 <= len(value) <= 128 or not _TOOL_NAME_PATTERN.fullmatch(value):
        _issue(
            issues,
            f"{prefix}.schema.pattern",
            path,
            "Expected a 1..128 character MCP tool name using letters, digits, '.', '_', or '-'",
        )


def _validate_timestamp(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    if _parse_timestamp(value) is None:
        _issue(
            issues,
            f"{prefix}.schema.format",
            path,
            "Expected a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form",
        )


def _validate_integer(
    issues: List[ValidationIssue],
    value: Any,
    path: str,
    prefix: str,
    minimum: int,
    maximum: Optional[int] = None,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _issue(issues, f"{prefix}.schema.type", path, "Expected an integer")
        return
    if value < minimum or (maximum is not None and value > maximum):
        expected = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        _issue(issues, f"{prefix}.schema.range", path, f"Expected integer {expected}")


def _validate_constraints(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    fields = {
        "max_cost",
        "max_duration_seconds",
        "max_action_count",
        "max_delegation_depth",
    }
    constraints = _validate_object(issues, value, path, fields, fields, prefix)
    if constraints is None:
        return
    if "max_cost" in constraints:
        cost_fields = {"amount_minor", "currency"}
        cost = _validate_object(
            issues,
            constraints["max_cost"],
            f"{path}/max_cost",
            cost_fields,
            cost_fields,
            prefix,
        )
        if cost is not None:
            if "amount_minor" in cost:
                _validate_integer(
                    issues, cost["amount_minor"], f"{path}/max_cost/amount_minor", prefix, 0
                )
            if "currency" in cost:
                currency = cost["currency"]
                if not isinstance(currency, str) or not _CURRENCY_PATTERN.fullmatch(currency):
                    _issue(
                        issues,
                        f"{prefix}.schema.pattern",
                        f"{path}/max_cost/currency",
                        "Expected an ISO-style three-letter currency",
                    )
    for field in ("max_duration_seconds", "max_action_count"):
        if field in constraints:
            _validate_integer(issues, constraints[field], f"{path}/{field}", prefix, 1)
    if "max_delegation_depth" in constraints:
        _validate_integer(
            issues,
            constraints["max_delegation_depth"],
            f"{path}/max_delegation_depth",
            prefix,
            0,
            16,
        )


def _validate_principal(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    principal_fields = {"actor_id", "authentication"}
    principal = _validate_object(
        issues, value, path, principal_fields, principal_fields, prefix
    )
    if principal is None:
        return
    if "actor_id" in principal:
        _validate_identifier(issues, principal["actor_id"], f"{path}/actor_id", prefix)
    auth_fields = {
        "trust_boundary_id",
        "assertion_id",
        "authenticated_at",
        "expires_at",
    }
    if "authentication" not in principal:
        return
    authentication = _validate_object(
        issues,
        principal["authentication"],
        f"{path}/authentication",
        auth_fields,
        auth_fields,
        prefix,
    )
    if authentication is None:
        return
    for field in ("trust_boundary_id", "assertion_id"):
        if field in authentication:
            _validate_identifier(
                issues, authentication[field], f"{path}/authentication/{field}", prefix
            )
    for field in ("authenticated_at", "expires_at"):
        if field in authentication:
            _validate_timestamp(
                issues, authentication[field], f"{path}/authentication/{field}", prefix
            )
    authenticated_at = _parse_timestamp(authentication.get("authenticated_at"))
    expires_at = _parse_timestamp(authentication.get("expires_at"))
    if authenticated_at and expires_at and expires_at <= authenticated_at:
        _issue(
            issues,
            f"{prefix}.authentication.lifecycle_invalid",
            f"{path}/authentication/expires_at",
            "expires_at must be later than authenticated_at",
        )


def validate_mcp_call_proposal(proposal: Any) -> List[ValidationIssue]:
    """Return sorted shape errors for MCP Call Proposal v0.1."""

    prefix = "mcp.proposal"
    issues: List[ValidationIssue] = []
    required = {
        "schema_version",
        "proposal_id",
        "server_id",
        "tool_name",
        "arguments",
        "principal",
        "actor_id",
        "authorized_goal_id",
        "requested_at",
    }
    allowed = required | {"annotations", "requested_constraints"}
    root = _validate_object(issues, proposal, "", required, allowed, prefix)
    if root is None:
        return _sorted_issues(issues)
    if "schema_version" in root and root["schema_version"] != MCP_CALL_PROPOSAL_SCHEMA_VERSION:
        _issue(
            issues,
            f"{prefix}.schema_version.unsupported",
            "/schema_version",
            f"Expected schema_version '{MCP_CALL_PROPOSAL_SCHEMA_VERSION}'",
        )
    for field in ("proposal_id", "server_id", "actor_id", "authorized_goal_id"):
        if field in root:
            _validate_identifier(issues, root[field], f"/{field}", prefix)
    if "tool_name" in root:
        _validate_tool_name(issues, root["tool_name"], "/tool_name", prefix)
    if "arguments" in root and not isinstance(root["arguments"], dict):
        _issue(issues, f"{prefix}.schema.type", "/arguments", "Expected an object")
    if "annotations" in root and not isinstance(root["annotations"], dict):
        _issue(issues, f"{prefix}.schema.type", "/annotations", "Expected an object")
    if "principal" in root:
        _validate_principal(issues, root["principal"], "/principal", prefix)
    if "requested_at" in root:
        _validate_timestamp(issues, root["requested_at"], "/requested_at", prefix)
    if "requested_constraints" in root:
        _validate_constraints(
            issues, root["requested_constraints"], "/requested_constraints", prefix
        )
    return _sorted_issues(issues)


def _validate_string_array(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    if not isinstance(value, list):
        _issue(issues, f"{prefix}.schema.type", path, "Expected an array")
        return
    if not value:
        _issue(issues, f"{prefix}.schema.min_items", path, "Expected at least one item")
        return
    seen: Set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}/{index}"
        _validate_identifier(issues, item, item_path, prefix)
        if isinstance(item, str) and item in seen:
            _issue(issues, f"{prefix}.schema.unique_items", item_path, f"Duplicate value '{item}'")
        elif isinstance(item, str):
            seen.add(item)


def _validate_provenance(
    issues: List[ValidationIssue], value: Any, path: str, prefix: str
) -> None:
    fields = {"source_uri", "revision", "authored_by", "approved_by"}
    provenance = _validate_object(issues, value, path, fields, fields, prefix)
    if provenance is None:
        return
    if "source_uri" in provenance:
        source_uri = provenance["source_uri"]
        if not isinstance(source_uri, str) or not source_uri or ":" not in source_uri:
            _issue(issues, f"{prefix}.schema.format", f"{path}/source_uri", "Expected a non-empty URI")
    if "revision" in provenance:
        revision = provenance["revision"]
        if not isinstance(revision, str):
            _issue(issues, f"{prefix}.schema.type", f"{path}/revision", "Expected a string")
        elif not 1 <= len(revision) <= 128:
            _issue(issues, f"{prefix}.schema.range", f"{path}/revision", "Expected 1..128 characters")
    for field in ("authored_by", "approved_by"):
        if field in provenance:
            _validate_string_array(issues, provenance[field], f"{path}/{field}", prefix)


def validate_mcp_adapter_mapping(mapping: Any) -> List[ValidationIssue]:
    """Return sorted shape and semantic errors for MCP Adapter Mapping v0.1."""

    prefix = "mcp.mapping"
    issues: List[ValidationIssue] = []
    root_fields = {"schema_version", "mapping", "entries"}
    root = _validate_object(issues, mapping, "", root_fields, root_fields, prefix)
    if root is None:
        return _sorted_issues(issues)
    if "schema_version" in root and root["schema_version"] != MCP_ADAPTER_MAPPING_SCHEMA_VERSION:
        _issue(
            issues,
            f"{prefix}.schema_version.unsupported",
            "/schema_version",
            f"Expected schema_version '{MCP_ADAPTER_MAPPING_SCHEMA_VERSION}'",
        )
    metadata_fields = {
        "id",
        "version",
        "title",
        "effective_at",
        "review_at",
        "provenance",
    }
    metadata = None
    if "mapping" in root:
        metadata = _validate_object(
            issues,
            root["mapping"],
            "/mapping",
            metadata_fields,
            metadata_fields,
            prefix,
        )
    if metadata is not None:
        if "id" in metadata:
            _validate_identifier(issues, metadata["id"], "/mapping/id", prefix)
        if "version" in metadata:
            version = metadata["version"]
            if not isinstance(version, str) or not _SEMVER_PATTERN.fullmatch(version):
                _issue(issues, f"{prefix}.schema.pattern", "/mapping/version", "Expected semantic version x.y.z")
        if "title" in metadata:
            title = metadata["title"]
            if not isinstance(title, str):
                _issue(issues, f"{prefix}.schema.type", "/mapping/title", "Expected a string")
            elif not 1 <= len(title) <= 160:
                _issue(issues, f"{prefix}.schema.range", "/mapping/title", "Expected 1..160 characters")
        for field in ("effective_at", "review_at"):
            if field in metadata:
                _validate_timestamp(issues, metadata[field], f"/mapping/{field}", prefix)
        effective_at = _parse_timestamp(metadata.get("effective_at"))
        review_at = _parse_timestamp(metadata.get("review_at"))
        if effective_at and review_at and review_at <= effective_at:
            _issue(
                issues,
                f"{prefix}.lifecycle_invalid",
                "/mapping/review_at",
                "review_at must be later than effective_at",
            )
        if "provenance" in metadata:
            _validate_provenance(
                issues, metadata["provenance"], "/mapping/provenance", prefix
            )

    entries = root.get("entries")
    if not isinstance(entries, list):
        if "entries" in root:
            _issue(issues, f"{prefix}.schema.type", "/entries", "Expected an array")
        return _sorted_issues(issues)
    if not entries:
        _issue(issues, f"{prefix}.schema.min_items", "/entries", "Expected at least one mapping entry")
    entry_required = {
        "server_id",
        "tool_name",
        "capability_id",
        "resource_id",
        "action",
        "channel_id",
        "data_classification",
        "expected_side_effects",
        "reversible",
    }
    entry_allowed = entry_required | {"requested_constraints"}
    seen: Dict[Tuple[str, str], int] = {}
    for index, value in enumerate(entries):
        path = f"/entries/{index}"
        entry = _validate_object(
            issues, value, path, entry_required, entry_allowed, prefix
        )
        if entry is None:
            continue
        for field in ("server_id", "capability_id", "resource_id", "action"):
            if field in entry:
                _validate_identifier(issues, entry[field], f"{path}/{field}", prefix)
        if "tool_name" in entry:
            _validate_tool_name(issues, entry["tool_name"], f"{path}/tool_name", prefix)
        if "channel_id" in entry and entry["channel_id"] is not None:
            _validate_identifier(issues, entry["channel_id"], f"{path}/channel_id", prefix)
        if "data_classification" in entry:
            classification = entry["data_classification"]
            if not isinstance(classification, str) or classification not in _DATA_CLASSIFICATIONS:
                _issue(
                    issues,
                    f"{prefix}.schema.enum",
                    f"{path}/data_classification",
                    "Expected one of: confidential, internal, public, restricted",
                )
        if "expected_side_effects" in entry:
            effects = entry["expected_side_effects"]
            if not isinstance(effects, list):
                _issue(issues, f"{prefix}.schema.type", f"{path}/expected_side_effects", "Expected an array")
            elif not effects:
                _issue(issues, f"{prefix}.schema.min_items", f"{path}/expected_side_effects", "Expected at least one side effect")
            else:
                effect_seen: Set[str] = set()
                for effect_index, effect in enumerate(effects):
                    effect_path = f"{path}/expected_side_effects/{effect_index}"
                    if not isinstance(effect, str) or effect not in _SIDE_EFFECTS:
                        _issue(issues, f"{prefix}.schema.enum", effect_path, "Unsupported expected side effect")
                    elif effect in effect_seen:
                        _issue(issues, f"{prefix}.schema.unique_items", effect_path, f"Duplicate value '{effect}'")
                    else:
                        effect_seen.add(effect)
        if "reversible" in entry and not isinstance(entry["reversible"], bool):
            _issue(issues, f"{prefix}.schema.type", f"{path}/reversible", "Expected a boolean")
        if "requested_constraints" in entry:
            _validate_constraints(
                issues, entry["requested_constraints"], f"{path}/requested_constraints", prefix
            )
        server_id = entry.get("server_id")
        tool_name = entry.get("tool_name")
        if isinstance(server_id, str) and isinstance(tool_name, str):
            key = (server_id, tool_name)
            if key in seen:
                _issue(
                    issues,
                    f"{prefix}.ambiguous_key",
                    path,
                    f"Duplicate mapping key ({server_id!r}, {tool_name!r})",
                    related_path=f"/entries/{seen[key]}",
                )
            else:
                seen[key] = index
    return _sorted_issues(issues)


def _load_json(path: str, prefix: str) -> Tuple[Any, Sequence[ValidationIssue]]:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return None, (ValidationIssue(f"{prefix}.json.read", "/", f"Unable to read {source}: {exc}"),)
    try:
        return json.loads(text), ()
    except json.JSONDecodeError as exc:
        return None, (
            ValidationIssue(
                f"{prefix}.json.syntax",
                "/",
                exc.msg,
                line=exc.lineno,
                column=exc.colno,
            ),
        )


def load_mcp_call_proposal(path: str) -> Dict[str, Any]:
    """Load a UTF-8 MCP call proposal or raise ``MCPContractError``."""

    value, issues = _load_json(path, "mcp.proposal")
    if issues:
        raise MCPContractError(issues)
    if not isinstance(value, dict):
        raise MCPContractError(
            [ValidationIssue("mcp.proposal.schema.type", "/", "Proposal root must be an object")]
        )
    return value


def load_mcp_adapter_mapping(path: str) -> Dict[str, Any]:
    """Load a UTF-8 MCP adapter mapping or raise ``MCPContractError``."""

    value, issues = _load_json(path, "mcp.mapping")
    if issues:
        raise MCPContractError(issues)
    if not isinstance(value, dict):
        raise MCPContractError(
            [ValidationIssue("mcp.mapping.schema.type", "/", "Mapping root must be an object")]
        )
    return value


def normalize_mcp_adapter_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Return a canonical copy of a valid MCP Adapter Mapping v0.1."""

    result = deepcopy(mapping)
    metadata = result.get("mapping")
    if isinstance(metadata, dict):
        provenance = metadata.get("provenance")
        if isinstance(provenance, dict):
            for field in ("authored_by", "approved_by"):
                if isinstance(provenance.get(field), list):
                    provenance[field] = sorted(provenance[field])
    entries = result.get("entries")
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("expected_side_effects"), list):
                entry["expected_side_effects"] = sorted(entry["expected_side_effects"])
        result["entries"] = sorted(
            entries,
            key=lambda item: (
                item.get("server_id", "") if isinstance(item, dict) else "",
                item.get("tool_name", "") if isinstance(item, dict) else "",
            ),
        )
    return result


def _summary_string(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _proposal_summary(proposal: Any) -> Dict[str, Any]:
    proposal_id = proposal.get("proposal_id") if isinstance(proposal, dict) else None
    return {
        "proposal_id": _summary_string(proposal_id),
        "proposal_sha256": _sha256(proposal),
    }


def _mapping_summary(mapping: Any, valid: bool) -> Dict[str, Any]:
    metadata = mapping.get("mapping", {}) if isinstance(mapping, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    digest_input = normalize_mcp_adapter_mapping(mapping) if valid and isinstance(mapping, dict) else mapping
    return {
        "mapping_id": _summary_string(metadata.get("id")),
        "mapping_version": _summary_string(metadata.get("version")),
        "mapping_sha256": _sha256(digest_input),
    }


def _issues_as_reasons(issues: Iterable[ValidationIssue]) -> List[Dict[str, Any]]:
    return [_reason(issue.code, issue.message, issue.path) for issue in _sorted_issues(issues)]


def _build_normalization_result(
    proposal: Any,
    mapping: Any,
    *,
    mapping_valid: bool,
    outcome: str,
    reasons: Sequence[Dict[str, Any]],
    action_request: Optional[Dict[str, Any]],
) -> MCPNormalizationResult:
    normalized_reasons = _sorted_reasons(reasons)
    core = {
        "outcome": outcome,
        "proposal_only": True,
        "reasons": normalized_reasons,
        "proposal": _proposal_summary(proposal),
        "mapping": _mapping_summary(mapping, mapping_valid),
        "action_request": deepcopy(action_request),
    }
    normalization_id = "mcp-normalization." + _sha256(core)
    return MCPNormalizationResult.from_dict(
        {
            "schema_version": MCP_NORMALIZATION_RESULT_SCHEMA_VERSION,
            "normalization_id": normalization_id,
            **core,
        }
    )


def _normalization_rejection(
    proposal: Any,
    mapping: Any,
    code: str,
    message: str,
    path: str,
) -> MCPNormalizationResult:
    return _build_normalization_result(
        proposal,
        mapping,
        mapping_valid=True,
        outcome="rejected",
        reasons=[_reason(code, message, path)],
        action_request=None,
    )


def _normalize_mcp_call(
    proposal: Any,
    mapping: Any,
    *,
    proposal_input_issues: Iterable[ValidationIssue] = (),
    mapping_input_issues: Iterable[ValidationIssue] = (),
) -> MCPNormalizationResult:
    proposal_issues = list(proposal_input_issues)
    if not proposal_issues:
        proposal_issues = validate_mcp_call_proposal(proposal)
    mapping_issues = list(mapping_input_issues)
    if not mapping_issues:
        mapping_issues = validate_mcp_adapter_mapping(mapping)
    if proposal_issues or mapping_issues:
        return _build_normalization_result(
            proposal,
            mapping,
            mapping_valid=not mapping_issues,
            outcome="invalid_input",
            reasons=_issues_as_reasons([*proposal_issues, *mapping_issues]),
            action_request=None,
        )

    assert isinstance(proposal, dict)
    assert isinstance(mapping, dict)
    requested_at = _parse_timestamp(proposal["requested_at"])
    effective_at = _parse_timestamp(mapping["mapping"]["effective_at"])
    review_at = _parse_timestamp(mapping["mapping"]["review_at"])
    assert requested_at is not None
    assert effective_at is not None
    assert review_at is not None
    if requested_at < effective_at:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.mapping.not_effective",
            "Mapping is not effective at requested_at",
            "/requested_at",
        )
    if requested_at >= review_at:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.mapping.stale",
            "Mapping is stale at requested_at",
            "/requested_at",
        )

    entries = mapping["entries"]
    server_matches = [entry for entry in entries if entry["server_id"] == proposal["server_id"]]
    if not server_matches:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.mapping.unknown_server",
            f"Unknown caller-assigned server_id '{proposal['server_id']}'",
            "/server_id",
        )
    matches = [entry for entry in server_matches if entry["tool_name"] == proposal["tool_name"]]
    if not matches:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.mapping.unmapped_tool",
            f"No mapping for tool_name '{proposal['tool_name']}' on server_id '{proposal['server_id']}'",
            "/tool_name",
        )
    if len(matches) != 1:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.mapping.ambiguous_key",
            "More than one mapping entry matches the exact server_id and tool_name",
            "/tool_name",
        )
    entry = matches[0]

    try:
        parameters_digest = canonical_parameters_digest(proposal["arguments"])
    except ParameterEncodingError as exc:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.arguments.uncanonicalizable",
            str(exc),
            "/arguments",
        )

    proposal_constraints = proposal.get("requested_constraints")
    mapping_constraints = entry.get("requested_constraints")
    if proposal_constraints is None and mapping_constraints is None:
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.context.missing_constraints",
            "requested_constraints must come from the proposal or matched mapping entry",
            "/requested_constraints",
        )
    if (
        proposal_constraints is not None
        and mapping_constraints is not None
        and proposal_constraints != mapping_constraints
    ):
        return _normalization_rejection(
            proposal,
            mapping,
            "mcp.context.constraints_conflict",
            "Proposal and mapping requested_constraints must be exactly equal when both are present",
            "/requested_constraints",
        )
    requested_constraints = (
        proposal_constraints if proposal_constraints is not None else mapping_constraints
    )

    request_source = {
        key: deepcopy(value)
        for key, value in proposal.items()
        if key != "annotations"
    }
    request_id = "request.mcp." + _sha256(request_source)
    action_request = {
        "schema_version": "0.1",
        "request_id": request_id,
        "principal": deepcopy(proposal["principal"]),
        "authorized_goal_id": proposal["authorized_goal_id"],
        "actor_id": proposal["actor_id"],
        "capability_id": entry["capability_id"],
        "action": entry["action"],
        "resource_id": entry["resource_id"],
        "parameters_digest": parameters_digest,
        "requested_at": proposal["requested_at"],
        "context": {
            "channel_id": entry["channel_id"],
            "data_classification": entry["data_classification"],
            "expected_side_effects": sorted(entry["expected_side_effects"]),
            "reversible": entry["reversible"],
            "requested_constraints": deepcopy(requested_constraints),
        },
    }
    request_issues = validate_action_request(action_request)
    if request_issues:
        reasons = [
            _reason(
                f"mcp.action_request.{issue.code}",
                issue.message,
                "/action_request" + (issue.path if issue.path != "/" else ""),
            )
            for issue in request_issues
        ]
        return _build_normalization_result(
            proposal,
            mapping,
            mapping_valid=True,
            outcome="rejected",
            reasons=reasons,
            action_request=None,
        )
    return _build_normalization_result(
        proposal,
        mapping,
        mapping_valid=True,
        outcome="normalized",
        reasons=[_reason("mcp.normalization.succeeded", "Proposal normalized to Action Request v0.1")],
        action_request=action_request,
    )


def normalize_mcp_call(proposal: Any, mapping: Any) -> MCPNormalizationResult:
    """Normalize one MCP proposal without I/O, policy evaluation, or dispatch."""

    return _normalize_mcp_call(proposal, mapping)


def normalize_mcp_call_files(mapping_path: str, proposal_path: str) -> MCPNormalizationResult:
    """Load mapping and proposal JSON and return a contract for every outcome."""

    mapping, mapping_issues = _load_json(mapping_path, "mcp.mapping")
    proposal, proposal_issues = _load_json(proposal_path, "mcp.proposal")
    return _normalize_mcp_call(
        proposal,
        mapping,
        proposal_input_issues=proposal_issues,
        mapping_input_issues=mapping_issues,
    )


def _build_shadow_result(
    normalization: MCPNormalizationResult,
    *,
    outcome: str,
    reasons: Sequence[Dict[str, Any]],
    decision_result: Optional[Dict[str, Any]],
    approval_verification_result: Optional[Dict[str, Any]],
) -> MCPShadowResult:
    normalization_data = normalization.as_dict()
    action_request = normalization_data["action_request"]
    normalized_reasons = _sorted_reasons(reasons)
    normalization_summary = {
        "normalization_id": normalization_data["normalization_id"],
        "outcome": normalization_data["outcome"],
        "reasons": deepcopy(normalization_data["reasons"]),
    }
    core = {
        "outcome": outcome,
        "mode": "shadow",
        "proposal_only": True,
        "reasons": normalized_reasons,
        "proposal": deepcopy(normalization_data["proposal"]),
        "mapping": deepcopy(normalization_data["mapping"]),
        "normalization": normalization_summary,
        "action_request": deepcopy(action_request),
        "decision_result": deepcopy(decision_result),
        "approval_verification_result": deepcopy(approval_verification_result),
    }
    shadow_result_id = "mcp-shadow." + _sha256(core)
    request_summary = {
        "request_id": action_request.get("request_id") if isinstance(action_request, dict) else None,
        "request_sha256": (
            decision_result.get("request_sha256")
            if isinstance(decision_result, dict)
            else (_sha256(action_request) if isinstance(action_request, dict) else None)
        ),
        "parameters_digest": (
            action_request.get("parameters_digest") if isinstance(action_request, dict) else None
        ),
    }
    decision_summary = {
        "decision_id": decision_result.get("decision_id") if isinstance(decision_result, dict) else None,
        "disposition": decision_result.get("disposition") if isinstance(decision_result, dict) else None,
    }
    verification_summary = None
    if isinstance(approval_verification_result, dict):
        verification_summary = {
            "verification_id": approval_verification_result.get("verification_id"),
            "outcome": approval_verification_result.get("outcome"),
        }
    evidence_core = {
        "record_type": "proposed_mcp_shadow",
        "mode": "shadow",
        "proposal_only": True,
        "shadow_result_id": shadow_result_id,
        "proposal": deepcopy(normalization_data["proposal"]),
        "mapping": deepcopy(normalization_data["mapping"]),
        "normalization": {
            "normalization_id": normalization_data["normalization_id"],
            "outcome": normalization_data["outcome"],
            "reason_codes": [reason["code"] for reason in normalization_data["reasons"]],
        },
        "request": request_summary,
        "decision": decision_summary,
        "approval_verification": verification_summary,
    }
    evidence_id = "evidence." + _sha256(evidence_core)
    evidence = {
        "schema_version": MCP_SHADOW_EVIDENCE_SCHEMA_VERSION,
        "evidence_id": evidence_id,
        **evidence_core,
    }
    return MCPShadowResult.from_dict(
        {
            "schema_version": MCP_SHADOW_RESULT_SCHEMA_VERSION,
            "shadow_result_id": shadow_result_id,
            **core,
            "proposed_evidence_record": evidence,
        }
    )


def _shadow_from_normalization(
    policy: Any,
    normalization: MCPNormalizationResult,
    *,
    trusted_identity_boundaries: Iterable[str],
    grant: Any = None,
    verification_state: Any = None,
) -> MCPShadowResult:
    if normalization.outcome != "normalized":
        outcome = (
            "invalid_input"
            if normalization.outcome == "invalid_input"
            else "normalization_rejected"
        )
        return _build_shadow_result(
            normalization,
            outcome=outcome,
            reasons=normalization.as_dict()["reasons"],
            decision_result=None,
            approval_verification_result=None,
        )
    action_request = normalization.action_request
    assert action_request is not None
    decision = evaluate_action(
        policy,
        action_request,
        trusted_identity_boundaries=trusted_identity_boundaries,
    )
    decision_data = decision.as_dict()
    if (grant is None) != (verification_state is None):
        return _build_shadow_result(
            normalization,
            outcome="invalid_input",
            reasons=[
                _reason(
                    "mcp.approval.context_incomplete",
                    "grant and verification_state must be supplied together",
                    "/approval_verification_result",
                )
            ],
            decision_result=decision_data,
            approval_verification_result=None,
        )
    verification_data = None
    reasons = [_reason("mcp.shadow.evaluated", "Shared evaluator result embedded without dispatch")]
    if grant is not None and verification_state is not None:
        verification_data = verify_approval_grant(
            policy,
            action_request,
            decision,
            grant,
            verification_state,
        ).as_dict()
        reasons.append(
            _reason(
                "mcp.shadow.approval_verification_embedded",
                "Shared approval verification result embedded without changing disposition",
            )
        )
    return _build_shadow_result(
        normalization,
        outcome="evaluated",
        reasons=reasons,
        decision_result=decision_data,
        approval_verification_result=verification_data,
    )


def evaluate_mcp_shadow(
    policy: Any,
    mapping: Any,
    proposal: Any,
    *,
    trusted_identity_boundaries: Iterable[str] = (),
    grant: Any = None,
    verification_state: Any = None,
) -> MCPShadowResult:
    """Normalize and evaluate an MCP proposal without I/O, enforcement, or dispatch."""

    normalization = normalize_mcp_call(proposal, mapping)
    return _shadow_from_normalization(
        policy,
        normalization,
        trusted_identity_boundaries=trusted_identity_boundaries,
        grant=grant,
        verification_state=verification_state,
    )


def evaluate_mcp_shadow_files(
    policy_path: str,
    mapping_path: str,
    proposal_path: str,
    *,
    trusted_identity_boundaries: Iterable[str] = (),
    grant_path: Optional[str] = None,
    state_path: Optional[str] = None,
) -> MCPShadowResult:
    """Load shadow inputs and return a proposal-only envelope for every outcome."""

    normalization = normalize_mcp_call_files(mapping_path, proposal_path)
    if normalization.outcome != "normalized":
        return _shadow_from_normalization(
            None,
            normalization,
            trusted_identity_boundaries=trusted_identity_boundaries,
        )
    try:
        policy = load_policy_bundle(policy_path)
    except PolicyBundleError as exc:
        return _build_shadow_result(
            normalization,
            outcome="invalid_input",
            reasons=[
                _reason(f"mcp.policy.{issue.code}", issue.message, issue.path)
                for issue in exc.issues
            ],
            decision_result=None,
            approval_verification_result=None,
        )
    if (grant_path is None) != (state_path is None):
        return _shadow_from_normalization(
            policy,
            normalization,
            trusted_identity_boundaries=trusted_identity_boundaries,
            grant={} if grant_path is not None else None,
            verification_state={} if state_path is not None else None,
        )
    grant = None
    state = None
    if grant_path is not None and state_path is not None:
        grant, grant_issues = _load_json(grant_path, "mcp.grant")
        state, state_issues = _load_json(state_path, "mcp.state")
        if grant_issues or state_issues:
            decision = evaluate_action(
                policy,
                normalization.action_request,
                trusted_identity_boundaries=trusted_identity_boundaries,
            )
            return _build_shadow_result(
                normalization,
                outcome="invalid_input",
                reasons=_issues_as_reasons([*grant_issues, *state_issues]),
                decision_result=decision.as_dict(),
                approval_verification_result=None,
            )
    return _shadow_from_normalization(
        policy,
        normalization,
        trusted_identity_boundaries=trusted_identity_boundaries,
        grant=grant,
        verification_state=state,
    )
