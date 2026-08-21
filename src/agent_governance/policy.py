"""Validate and deterministically compile Policy Bundle v0.1 documents."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SEMVER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


@dataclass(frozen=True)
class ValidationIssue:
    """A stable, machine-readable policy validation error."""

    code: str
    path: str
    message: str
    related_path: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None

    def as_dict(self) -> Dict[str, Any]:
        """Return the issue without empty optional fields."""

        result: Dict[str, Any] = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.related_path is not None:
            result["related_path"] = self.related_path
        if self.line is not None:
            result["line"] = self.line
        if self.column is not None:
            result["column"] = self.column
        return result


class PolicyBundleError(ValueError):
    """Raised when a policy bundle cannot be loaded or validated."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(_sorted_issues(issues))
        message = self.issues[0].message if self.issues else "Invalid policy bundle"
        super().__init__(message)


@dataclass(frozen=True)
class CompiledPolicy:
    """The two deterministic artifacts produced by a successful compile."""

    agent_policy: str
    decision_data: str


def _sorted_issues(issues: Iterable[ValidationIssue]) -> List[ValidationIssue]:
    return sorted(issues, key=lambda item: (item.path, item.code, item.message))


def _pointer(base: str, value: object) -> str:
    escaped = str(value).replace("~", "~0").replace("/", "~1")
    return f"{base}/{escaped}" if base else f"/{escaped}"


class _ShapeValidator:
    """Small, explicit validator for the normative v0.1 document shape."""

    def __init__(self) -> None:
        self.issues: List[ValidationIssue] = []

    def issue(self, code: str, path: str, message: str) -> None:
        self.issues.append(ValidationIssue(code, path or "/", message))

    def obj(
        self,
        value: Any,
        path: str,
        required: Set[str],
        allowed: Set[str],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(value, dict):
            self.issue("schema.type", path, "Expected an object")
            return None
        for field in sorted(required - set(value)):
            self.issue(
                "schema.required",
                path or "/",
                f"Missing required field '{field}'",
            )
        for field in sorted(set(value) - allowed):
            self.issue(
                "schema.unknown_field",
                _pointer(path, field),
                f"Unknown field '{field}'",
            )
        return value

    def array(
        self, value: Any, path: str, minimum: int = 0
    ) -> Optional[List[Any]]:
        if not isinstance(value, list):
            self.issue("schema.type", path, "Expected an array")
            return None
        if len(value) < minimum:
            self.issue(
                "schema.min_items",
                path,
                f"Expected at least {minimum} item(s)",
            )
        return value

    def text(self, value: Any, path: str, maximum: int) -> None:
        if not isinstance(value, str):
            self.issue("schema.type", path, "Expected a string")
        elif not value.strip():
            self.issue("schema.min_length", path, "String must not be empty")
        elif len(value) > maximum:
            self.issue(
                "schema.max_length", path, f"String exceeds {maximum} characters"
            )

    def identifier(self, value: Any, path: str) -> None:
        if not isinstance(value, str):
            self.issue("schema.type", path, "Expected an identifier string")
        elif not 3 <= len(value) <= 128 or not _ID_PATTERN.fullmatch(value):
            self.issue("schema.pattern", path, f"Invalid identifier '{value}'")

    def choice(self, value: Any, path: str, choices: Set[str]) -> None:
        if not isinstance(value, str) or value not in choices:
            expected = ", ".join(sorted(choices))
            self.issue("schema.enum", path, f"Expected one of: {expected}")

    def integer(
        self, value: Any, path: str, minimum: int, maximum: Optional[int] = None
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            self.issue("schema.type", path, "Expected an integer")
            return
        if value < minimum or (maximum is not None and value > maximum):
            range_text = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
            self.issue("schema.range", path, f"Expected integer {range_text}")

    def boolean(self, value: Any, path: str) -> None:
        if not isinstance(value, bool):
            self.issue("schema.type", path, "Expected a boolean")

    def timestamp(self, value: Any, path: str) -> None:
        if not isinstance(value, str) or not _parse_timestamp(value):
            self.issue(
                "schema.format",
                path,
                "Expected a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form",
            )

    def semver(self, value: Any, path: str) -> None:
        if not isinstance(value, str) or not _SEMVER_PATTERN.fullmatch(value):
            self.issue("schema.pattern", path, "Expected a semantic version X.Y.Z")

    def id_list(self, value: Any, path: str, minimum: int = 1) -> None:
        items = self.array(value, path, minimum)
        if items is None:
            return
        seen: Set[str] = set()
        for index, item in enumerate(items):
            item_path = _pointer(path, index)
            self.identifier(item, item_path)
            if isinstance(item, str):
                if item in seen:
                    self.issue("schema.unique_items", item_path, f"Duplicate value '{item}'")
                seen.add(item)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not _TIMESTAMP_PATTERN.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _validate_provenance(validator: _ShapeValidator, value: Any, path: str) -> None:
    fields = {"source_uri", "revision", "authored_by", "approved_by"}
    item = validator.obj(value, path, fields, fields)
    if item is None:
        return
    if "source_uri" in item:
        validator.text(item["source_uri"], _pointer(path, "source_uri"), 2048)
        if isinstance(item["source_uri"], str) and ":" not in item["source_uri"]:
            validator.issue("schema.format", _pointer(path, "source_uri"), "Expected a URI")
    if "revision" in item:
        validator.text(item["revision"], _pointer(path, "revision"), 128)
    for field in ("authored_by", "approved_by"):
        if field in item:
            validator.id_list(item[field], _pointer(path, field))


def _validate_selector(validator: _ShapeValidator, value: Any, path: str) -> None:
    item = validator.obj(value, path, set(), {"any", "actor_ids", "role_ids"})
    if item is None:
        return
    if set(item) == {"any"}:
        if item["any"] is not True:
            validator.issue("schema.const", _pointer(path, "any"), "Expected true")
        return
    if not item or "any" in item:
        validator.issue(
            "schema.one_of",
            path,
            "Use either {'any': true} or actor_ids/role_ids",
        )
        return
    for field in ("actor_ids", "role_ids"):
        if field in item:
            validator.id_list(item[field], _pointer(path, field))


def _validate_constraints(validator: _ShapeValidator, value: Any, path: str) -> None:
    allowed = {
        "max_cost",
        "max_duration_seconds",
        "max_action_count",
        "max_delegation_depth",
        "allowed_data_classifications",
        "require_reversible",
    }
    item = validator.obj(value, path, set(), allowed)
    if item is None:
        return
    if not item:
        validator.issue("schema.min_properties", path, "Constraints must not be empty")
    if "max_cost" in item:
        cost_path = _pointer(path, "max_cost")
        cost_fields = {"amount_minor", "currency"}
        cost = validator.obj(item["max_cost"], cost_path, cost_fields, cost_fields)
        if cost is not None:
            if "amount_minor" in cost:
                validator.integer(cost["amount_minor"], _pointer(cost_path, "amount_minor"), 0)
            if "currency" in cost:
                currency = cost["currency"]
                if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
                    validator.issue("schema.pattern", _pointer(cost_path, "currency"), "Expected an ISO-style three-letter currency")
    for field in ("max_duration_seconds", "max_action_count"):
        if field in item:
            validator.integer(item[field], _pointer(path, field), 1)
    if "max_delegation_depth" in item:
        validator.integer(item["max_delegation_depth"], _pointer(path, "max_delegation_depth"), 0, 16)
    if "require_reversible" in item:
        validator.boolean(item["require_reversible"], _pointer(path, "require_reversible"))
    if "allowed_data_classifications" in item:
        field_path = _pointer(path, "allowed_data_classifications")
        values = validator.array(item["allowed_data_classifications"], field_path, 1)
        if values is not None:
            seen: Set[str] = set()
            for index, value_item in enumerate(values):
                value_path = _pointer(field_path, index)
                validator.choice(value_item, value_path, {"public", "internal", "confidential", "restricted"})
                if isinstance(value_item, str) and value_item in seen:
                    validator.issue("schema.unique_items", value_path, f"Duplicate value '{value_item}'")
                if isinstance(value_item, str):
                    seen.add(value_item)


def _validate_shape(bundle: Any) -> List[ValidationIssue]:
    validator = _ShapeValidator()
    top_fields = {
        "schema_version",
        "bundle",
        "actors",
        "roles",
        "resources",
        "capabilities",
        "policies",
        "approvals",
        "delegations",
        "exceptions",
    }
    root = validator.obj(bundle, "", top_fields, top_fields)
    if root is None:
        return validator.issues

    if "schema_version" in root and root["schema_version"] != "0.1":
        validator.issue("schema.const", "/schema_version", "Expected schema_version '0.1'")

    bundle_fields = {
        "id", "version", "title", "owner_actor_id", "effective_at", "review_at",
        "default_effect", "provenance",
    }
    if "bundle" in root:
        item = validator.obj(root["bundle"], "/bundle", bundle_fields, bundle_fields)
        if item is not None:
            if "id" in item:
                validator.identifier(item["id"], "/bundle/id")
            if "version" in item:
                validator.semver(item["version"], "/bundle/version")
            if "title" in item:
                validator.text(item["title"], "/bundle/title", 160)
            if "owner_actor_id" in item:
                validator.identifier(item["owner_actor_id"], "/bundle/owner_actor_id")
            for field in ("effective_at", "review_at"):
                if field in item:
                    validator.timestamp(item[field], _pointer("/bundle", field))
            if "default_effect" in item and item["default_effect"] != "deny":
                validator.issue("schema.const", "/bundle/default_effect", "Expected fail-closed default 'deny'")
            if "provenance" in item:
                _validate_provenance(validator, item["provenance"], "/bundle/provenance")

    entity_specs = {
        "actors": (1, {"id", "kind", "display_name", "roles"}),
        "roles": (1, {"id", "description", "capabilities"}),
        "resources": (1, {"id", "kind", "description", "classification"}),
        "capabilities": (1, {"id", "action", "resource_id", "description"}),
        "approvals": (0, {"id", "description", "approver_role_ids", "quorum", "separation_of_duties", "expires_after_seconds", "bind_to"}),
        "delegations": (0, {"id", "from_actor_id", "to_actor_id", "capability_ids", "valid_from", "valid_until", "max_depth"}),
        "exceptions": (0, {"id", "control_id", "subjects", "capability_ids", "replacement_effect", "approval_id", "valid_from", "valid_until", "reason", "approved_by", "approved_at", "evidence_ref"}),
    }
    required_specs = {
        "actors": {"id", "kind", "display_name", "roles"},
        "roles": {"id", "description", "capabilities"},
        "resources": {"id", "kind", "description"},
        "capabilities": {"id", "action", "resource_id", "description"},
        "approvals": {"id", "description", "approver_role_ids", "quorum", "separation_of_duties", "expires_after_seconds", "bind_to"},
        "delegations": {"id", "from_actor_id", "to_actor_id", "capability_ids", "valid_from", "valid_until", "max_depth"},
        "exceptions": {"id", "control_id", "subjects", "capability_ids", "replacement_effect", "valid_from", "valid_until", "reason", "approved_by", "approved_at", "evidence_ref"},
    }
    for collection, (minimum, allowed) in entity_specs.items():
        if collection not in root:
            continue
        values = validator.array(root[collection], f"/{collection}", minimum)
        if values is None:
            continue
        for index, value in enumerate(values):
            path = f"/{collection}/{index}"
            item = validator.obj(value, path, required_specs[collection], allowed)
            if item is None:
                continue
            if "id" in item:
                validator.identifier(item["id"], _pointer(path, "id"))

            if collection == "actors":
                if "kind" in item:
                    validator.choice(item["kind"], _pointer(path, "kind"), {"human", "agent", "service"})
                if "display_name" in item:
                    validator.text(item["display_name"], _pointer(path, "display_name"), 160)
                if "roles" in item:
                    validator.id_list(item["roles"], _pointer(path, "roles"), 0)
            elif collection == "roles":
                if "description" in item:
                    validator.text(item["description"], _pointer(path, "description"), 500)
                if "capabilities" in item:
                    validator.id_list(item["capabilities"], _pointer(path, "capabilities"), 0)
            elif collection == "resources":
                if "kind" in item:
                    validator.choice(item["kind"], _pointer(path, "kind"), {"tool", "data", "channel", "service"})
                if "description" in item:
                    validator.text(item["description"], _pointer(path, "description"), 500)
                if item.get("kind") == "data" and "classification" not in item:
                    validator.issue("schema.required", path, "Data resources require 'classification'")
                if item.get("kind") != "data" and "classification" in item:
                    validator.issue("schema.not", _pointer(path, "classification"), "Only data resources may declare a classification")
                if "classification" in item:
                    validator.choice(item["classification"], _pointer(path, "classification"), {"public", "internal", "confidential", "restricted"})
            elif collection == "capabilities":
                if "action" in item:
                    validator.identifier(item["action"], _pointer(path, "action"))
                if "resource_id" in item:
                    validator.identifier(item["resource_id"], _pointer(path, "resource_id"))
                if "description" in item:
                    validator.text(item["description"], _pointer(path, "description"), 500)
            elif collection == "approvals":
                if "description" in item:
                    validator.text(item["description"], _pointer(path, "description"), 500)
                if "approver_role_ids" in item:
                    validator.id_list(item["approver_role_ids"], _pointer(path, "approver_role_ids"))
                if "quorum" in item:
                    validator.integer(item["quorum"], _pointer(path, "quorum"), 1)
                if "separation_of_duties" in item:
                    validator.boolean(item["separation_of_duties"], _pointer(path, "separation_of_duties"))
                if "expires_after_seconds" in item:
                    validator.integer(item["expires_after_seconds"], _pointer(path, "expires_after_seconds"), 1)
                if "bind_to" in item:
                    values_list = validator.array(item["bind_to"], _pointer(path, "bind_to"), 1)
                    if values_list is not None:
                        for value_index, bind_value in enumerate(values_list):
                            validator.choice(bind_value, _pointer(_pointer(path, "bind_to"), value_index), {"subject", "capability", "resource", "parameters_digest"})
                        if len(values_list) != len(set(value for value in values_list if isinstance(value, str))):
                            validator.issue("schema.unique_items", _pointer(path, "bind_to"), "Approval bindings must be unique")
            elif collection == "delegations":
                for field in ("from_actor_id", "to_actor_id"):
                    if field in item:
                        validator.identifier(item[field], _pointer(path, field))
                if "capability_ids" in item:
                    validator.id_list(item["capability_ids"], _pointer(path, "capability_ids"))
                for field in ("valid_from", "valid_until"):
                    if field in item:
                        validator.timestamp(item[field], _pointer(path, field))
                if "max_depth" in item:
                    validator.integer(item["max_depth"], _pointer(path, "max_depth"), 0, 16)
            elif collection == "exceptions":
                if "control_id" in item:
                    validator.identifier(item["control_id"], _pointer(path, "control_id"))
                if "subjects" in item:
                    _validate_selector(validator, item["subjects"], _pointer(path, "subjects"))
                if "capability_ids" in item:
                    validator.id_list(item["capability_ids"], _pointer(path, "capability_ids"))
                if "replacement_effect" in item:
                    validator.choice(item["replacement_effect"], _pointer(path, "replacement_effect"), {"allow", "require_approval"})
                    if item["replacement_effect"] == "require_approval" and "approval_id" not in item:
                        validator.issue("schema.required", path, "A require_approval exception needs 'approval_id'")
                    if item["replacement_effect"] == "allow" and "approval_id" in item:
                        validator.issue("schema.not", _pointer(path, "approval_id"), "An allow exception must not declare approval_id")
                if "approval_id" in item:
                    validator.identifier(item["approval_id"], _pointer(path, "approval_id"))
                for field in ("valid_from", "valid_until", "approved_at"):
                    if field in item:
                        validator.timestamp(item[field], _pointer(path, field))
                for field, maximum in (("reason", 1000), ("evidence_ref", 500)):
                    if field in item:
                        validator.text(item[field], _pointer(path, field), maximum)
                if "approved_by" in item:
                    validator.id_list(item["approved_by"], _pointer(path, "approved_by"))

    if "policies" in root:
        policies = validator.array(root["policies"], "/policies", 1)
        if policies is not None:
            policy_required = {"id", "version", "title", "precedence", "owner_actor_id", "effective_at", "review_at", "provenance", "controls"}
            for policy_index, value in enumerate(policies):
                path = f"/policies/{policy_index}"
                item = validator.obj(value, path, policy_required, policy_required)
                if item is None:
                    continue
                if "id" in item:
                    validator.identifier(item["id"], _pointer(path, "id"))
                if "version" in item:
                    validator.semver(item["version"], _pointer(path, "version"))
                if "title" in item:
                    validator.text(item["title"], _pointer(path, "title"), 160)
                if "precedence" in item:
                    validator.integer(item["precedence"], _pointer(path, "precedence"), 0, 10000)
                if "owner_actor_id" in item:
                    validator.identifier(item["owner_actor_id"], _pointer(path, "owner_actor_id"))
                for field in ("effective_at", "review_at"):
                    if field in item:
                        validator.timestamp(item[field], _pointer(path, field))
                if "provenance" in item:
                    _validate_provenance(validator, item["provenance"], _pointer(path, "provenance"))
                controls = validator.array(item.get("controls"), _pointer(path, "controls"), 1) if "controls" in item else None
                if controls is None:
                    continue
                control_required = {"id", "description", "subjects", "capability_ids", "effect", "evidence_fields"}
                control_allowed = control_required | {"approval_id", "constraints"}
                for control_index, value_control in enumerate(controls):
                    control_path = f"{path}/controls/{control_index}"
                    control = validator.obj(value_control, control_path, control_required, control_allowed)
                    if control is None:
                        continue
                    if "id" in control:
                        validator.identifier(control["id"], _pointer(control_path, "id"))
                    if "description" in control:
                        validator.text(control["description"], _pointer(control_path, "description"), 500)
                    if "subjects" in control:
                        _validate_selector(validator, control["subjects"], _pointer(control_path, "subjects"))
                    if "capability_ids" in control:
                        validator.id_list(control["capability_ids"], _pointer(control_path, "capability_ids"))
                    if "effect" in control:
                        validator.choice(control["effect"], _pointer(control_path, "effect"), {"allow", "deny", "require_approval"})
                        if control["effect"] == "require_approval" and "approval_id" not in control:
                            validator.issue("schema.required", control_path, "A require_approval control needs 'approval_id'")
                        if control["effect"] != "require_approval" and "approval_id" in control:
                            validator.issue("schema.not", _pointer(control_path, "approval_id"), "Only require_approval controls may declare approval_id")
                    if "approval_id" in control:
                        validator.identifier(control["approval_id"], _pointer(control_path, "approval_id"))
                    if "constraints" in control:
                        _validate_constraints(validator, control["constraints"], _pointer(control_path, "constraints"))
                    if "evidence_fields" in control:
                        evidence_path = _pointer(control_path, "evidence_fields")
                        evidence = validator.array(control["evidence_fields"], evidence_path, 1)
                        allowed_evidence = {"request", "actor", "capability", "resource", "parameters_digest", "matched_controls", "policy_version", "disposition", "approval", "execution_outcome"}
                        if evidence is not None:
                            for evidence_index, field in enumerate(evidence):
                                validator.choice(field, _pointer(evidence_path, evidence_index), allowed_evidence)
                            if len(evidence) != len(set(field for field in evidence if isinstance(field, str))):
                                validator.issue("schema.unique_items", evidence_path, "Evidence fields must be unique")
    return validator.issues


def _objects(bundle: Dict[str, Any], collection: str) -> List[Dict[str, Any]]:
    value = bundle.get(collection, [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_set(value: Any) -> Set[str]:
    return (
        {item for item in value if isinstance(item, str)}
        if isinstance(value, list)
        else set()
    )


def _reference_issue(path: str, kind: str, identifier: Any, related: str) -> ValidationIssue:
    return ValidationIssue(
        "reference.not_found",
        path,
        f"Unknown {kind} id '{identifier}'",
        related,
    )


def _validate_semantics(bundle: Dict[str, Any]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    collections = {
        name: _objects(bundle, name)
        for name in ("actors", "roles", "resources", "capabilities", "policies", "approvals", "delegations", "exceptions")
    }

    id_paths: Dict[str, str] = {}
    typed: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for name, items in collections.items():
        typed[name] = {}
        for index, item in enumerate(items):
            identifier = item.get("id")
            path = f"/{name}/{index}/id"
            if isinstance(identifier, str):
                if identifier in id_paths:
                    issues.append(ValidationIssue("id.duplicate", path, f"Duplicate id '{identifier}'", id_paths[identifier]))
                else:
                    id_paths[identifier] = path
                typed[name].setdefault(identifier, item)

    controls: Dict[str, Dict[str, Any]] = {}
    control_paths: Dict[str, str] = {}
    control_policies: Dict[str, Dict[str, Any]] = {}
    for policy_index, policy in enumerate(collections["policies"]):
        policy_controls = policy.get("controls", [])
        if not isinstance(policy_controls, list):
            continue
        for control_index, control in enumerate(policy_controls):
            if not isinstance(control, dict):
                continue
            identifier = control.get("id")
            path = f"/policies/{policy_index}/controls/{control_index}/id"
            if isinstance(identifier, str):
                if identifier in id_paths:
                    issues.append(ValidationIssue("id.duplicate", path, f"Duplicate id '{identifier}'", id_paths[identifier]))
                else:
                    id_paths[identifier] = path
                controls.setdefault(identifier, control)
                control_paths.setdefault(identifier, path.rsplit("/", 1)[0])
                control_policies.setdefault(identifier, policy)

    bundle_item = bundle.get("bundle") if isinstance(bundle.get("bundle"), dict) else {}
    bundle_id = bundle_item.get("id")
    if isinstance(bundle_id, str):
        if bundle_id in id_paths:
            issues.append(ValidationIssue("id.duplicate", "/bundle/id", f"Duplicate id '{bundle_id}'", id_paths[bundle_id]))
        else:
            id_paths[bundle_id] = "/bundle/id"

    def require_ref(path: str, kind: str, identifier: Any, collection: str) -> None:
        if isinstance(identifier, str) and identifier not in typed[collection]:
            issues.append(_reference_issue(path, kind, identifier, f"/{collection}"))

    require_ref("/bundle/owner_actor_id", "actor", bundle_item.get("owner_actor_id"), "actors")
    provenance = bundle_item.get("provenance", {})
    if isinstance(provenance, dict):
        for field in ("authored_by", "approved_by"):
            values = provenance.get(field, [])
            if isinstance(values, list):
                for index, identifier in enumerate(values):
                    require_ref(f"/bundle/provenance/{field}/{index}", "actor", identifier, "actors")

    for index, actor in enumerate(collections["actors"]):
        for ref_index, identifier in enumerate(actor.get("roles", []) if isinstance(actor.get("roles"), list) else []):
            require_ref(f"/actors/{index}/roles/{ref_index}", "role", identifier, "roles")
    for index, role in enumerate(collections["roles"]):
        for ref_index, identifier in enumerate(role.get("capabilities", []) if isinstance(role.get("capabilities"), list) else []):
            require_ref(f"/roles/{index}/capabilities/{ref_index}", "capability", identifier, "capabilities")
    for index, capability in enumerate(collections["capabilities"]):
        require_ref(f"/capabilities/{index}/resource_id", "resource", capability.get("resource_id"), "resources")

    for policy_index, policy in enumerate(collections["policies"]):
        base = f"/policies/{policy_index}"
        require_ref(f"{base}/owner_actor_id", "actor", policy.get("owner_actor_id"), "actors")
        policy_provenance = policy.get("provenance", {})
        if isinstance(policy_provenance, dict):
            for field in ("authored_by", "approved_by"):
                values = policy_provenance.get(field, [])
                if isinstance(values, list):
                    for index, identifier in enumerate(values):
                        require_ref(f"{base}/provenance/{field}/{index}", "actor", identifier, "actors")
        policy_controls = policy.get("controls", [])
        if isinstance(policy_controls, list):
            for control_index, control in enumerate(policy_controls):
                if not isinstance(control, dict):
                    continue
                control_base = f"{base}/controls/{control_index}"
                selector = control.get("subjects", {})
                if isinstance(selector, dict):
                    for field, kind, target in (("actor_ids", "actor", "actors"), ("role_ids", "role", "roles")):
                        values = selector.get(field, [])
                        if isinstance(values, list):
                            for index, identifier in enumerate(values):
                                require_ref(f"{control_base}/subjects/{field}/{index}", kind, identifier, target)
                capabilities = control.get("capability_ids", [])
                if isinstance(capabilities, list):
                    for index, identifier in enumerate(capabilities):
                        require_ref(f"{control_base}/capability_ids/{index}", "capability", identifier, "capabilities")
                if "approval_id" in control:
                    require_ref(f"{control_base}/approval_id", "approval", control.get("approval_id"), "approvals")

    for approval_index, approval in enumerate(collections["approvals"]):
        eligible_roles = approval.get("approver_role_ids", [])
        if isinstance(eligible_roles, list):
            for index, identifier in enumerate(eligible_roles):
                require_ref(f"/approvals/{approval_index}/approver_role_ids/{index}", "role", identifier, "roles")
            eligible_actor_roles = _string_set(eligible_roles)
            eligible_actors = [
                actor
                for actor in collections["actors"]
                if _string_set(actor.get("roles")) & eligible_actor_roles
            ]
            quorum = approval.get("quorum")
            if isinstance(quorum, int) and not isinstance(quorum, bool) and quorum > len(eligible_actors):
                issues.append(ValidationIssue("approval.invalid", f"/approvals/{approval_index}/quorum", f"Quorum {quorum} exceeds {len(eligible_actors)} eligible actor(s)", f"/approvals/{approval_index}/approver_role_ids"))

    for delegation_index, delegation in enumerate(collections["delegations"]):
        base = f"/delegations/{delegation_index}"
        for field in ("from_actor_id", "to_actor_id"):
            require_ref(f"{base}/{field}", "actor", delegation.get(field), "actors")
        values = delegation.get("capability_ids", [])
        if isinstance(values, list):
            for index, identifier in enumerate(values):
                require_ref(f"{base}/capability_ids/{index}", "capability", identifier, "capabilities")

    for exception_index, exception in enumerate(collections["exceptions"]):
        base = f"/exceptions/{exception_index}"
        control_id = exception.get("control_id")
        if isinstance(control_id, str) and control_id not in controls:
            issues.append(_reference_issue(f"{base}/control_id", "control", control_id, "/policies"))
        selector = exception.get("subjects", {})
        if isinstance(selector, dict):
            for field, kind, target in (("actor_ids", "actor", "actors"), ("role_ids", "role", "roles")):
                values = selector.get(field, [])
                if isinstance(values, list):
                    for index, identifier in enumerate(values):
                        require_ref(f"{base}/subjects/{field}/{index}", kind, identifier, target)
        values = exception.get("capability_ids", [])
        if isinstance(values, list):
            for index, identifier in enumerate(values):
                require_ref(f"{base}/capability_ids/{index}", "capability", identifier, "capabilities")
        if "approval_id" in exception:
            require_ref(f"{base}/approval_id", "approval", exception.get("approval_id"), "approvals")
        approved_by = exception.get("approved_by", [])
        if isinstance(approved_by, list):
            for index, identifier in enumerate(approved_by):
                require_ref(f"{base}/approved_by/{index}", "actor", identifier, "actors")

    bundle_start = _parse_timestamp(bundle_item.get("effective_at"))
    bundle_end = _parse_timestamp(bundle_item.get("review_at"))
    if bundle_start and bundle_end and bundle_end <= bundle_start:
        issues.append(ValidationIssue("lifecycle.invalid", "/bundle/review_at", "Bundle review_at must be later than effective_at", "/bundle/effective_at"))
    for policy_index, policy in enumerate(collections["policies"]):
        start = _parse_timestamp(policy.get("effective_at"))
        end = _parse_timestamp(policy.get("review_at"))
        if start and end and end <= start:
            issues.append(ValidationIssue("lifecycle.invalid", f"/policies/{policy_index}/review_at", "Policy review_at must be later than effective_at", f"/policies/{policy_index}/effective_at"))
        if start and bundle_start and start < bundle_start:
            issues.append(ValidationIssue("lifecycle.invalid", f"/policies/{policy_index}/effective_at", "Policy lifecycle starts before the bundle", "/bundle/effective_at"))
        if end and bundle_end and end > bundle_end:
            issues.append(ValidationIssue("lifecycle.invalid", f"/policies/{policy_index}/review_at", "Policy lifecycle extends beyond the bundle", "/bundle/review_at"))
    for collection_name in ("delegations", "exceptions"):
        for index, item in enumerate(collections[collection_name]):
            start = _parse_timestamp(item.get("valid_from"))
            end = _parse_timestamp(item.get("valid_until"))
            if start and end and end <= start:
                issues.append(ValidationIssue("lifecycle.invalid", f"/{collection_name}/{index}/valid_until", "valid_until must be later than valid_from", f"/{collection_name}/{index}/valid_from"))
            if start and bundle_start and start < bundle_start:
                issues.append(ValidationIssue("lifecycle.invalid", f"/{collection_name}/{index}/valid_from", f"{collection_name[:-1].title()} starts before the bundle", "/bundle/effective_at"))
            if end and bundle_end and end > bundle_end:
                issues.append(ValidationIssue("lifecycle.invalid", f"/{collection_name}/{index}/valid_until", f"{collection_name[:-1].title()} extends beyond the bundle", "/bundle/review_at"))
            if collection_name == "exceptions":
                approved_at = _parse_timestamp(item.get("approved_at"))
                if approved_at and start and approved_at > start:
                    issues.append(ValidationIssue("lifecycle.invalid", f"/exceptions/{index}/approved_at", "approved_at must not be later than valid_from", f"/exceptions/{index}/valid_from"))

    issues.extend(_delegation_issues(bundle, typed))

    effect_rank = {"allow": 0, "require_approval": 1, "deny": 2}
    for exception_index, exception in enumerate(collections["exceptions"]):
        base = f"/exceptions/{exception_index}"
        control_id = exception.get("control_id")
        control = controls.get(control_id) if isinstance(control_id, str) else None
        if control is None:
            continue
        exception_caps = _string_set(exception.get("capability_ids"))
        control_caps = _string_set(control.get("capability_ids"))
        if not exception_caps.issubset(control_caps):
            issues.append(ValidationIssue("exception.scope", f"{base}/capability_ids", "Exception capabilities must be a subset of the referenced control", f"{control_paths[control_id]}/capability_ids"))
        exception_subjects = exception.get("subjects", {})
        control_subjects = control.get("subjects", {})
        if isinstance(exception_subjects, dict) and isinstance(control_subjects, dict):
            if exception_subjects.get("any") is True:
                issues.append(ValidationIssue("exception.scope", f"{base}/subjects", "An exception must select a narrower subject scope", f"{control_paths[control_id]}/subjects"))
            elif control_subjects.get("any") is not True:
                for field in ("actor_ids", "role_ids"):
                    selected = _string_set(exception_subjects.get(field))
                    governed = _string_set(control_subjects.get(field))
                    if not selected.issubset(governed):
                        issues.append(ValidationIssue("exception.scope", f"{base}/subjects/{field}", "Exception subjects must be a subset of the referenced control", f"{control_paths[control_id]}/subjects/{field}"))
        original = control.get("effect")
        replacement = exception.get("replacement_effect")
        if (
            isinstance(original, str)
            and isinstance(replacement, str)
            and original in effect_rank
            and replacement in effect_rank
            and effect_rank[replacement] >= effect_rank[original]
        ):
            issues.append(ValidationIssue("exception.scope", f"{base}/replacement_effect", "Exception replacement must be less restrictive than the control effect", f"{control_paths[control_id]}/effect"))
        policy = control_policies.get(control_id)
        if policy:
            policy_start = _parse_timestamp(policy.get("effective_at"))
            policy_end = _parse_timestamp(policy.get("review_at"))
            start = _parse_timestamp(exception.get("valid_from"))
            end = _parse_timestamp(exception.get("valid_until"))
            if start and policy_start and start < policy_start:
                issues.append(ValidationIssue("lifecycle.invalid", f"{base}/valid_from", "Exception starts before its policy", f"{control_paths[control_id].split('/controls/')[0]}/effective_at"))
            if end and policy_end and end > policy_end:
                issues.append(ValidationIssue("lifecycle.invalid", f"{base}/valid_until", "Exception extends beyond its policy", f"{control_paths[control_id].split('/controls/')[0]}/review_at"))
    return issues


def _delegation_issues(bundle: Dict[str, Any], typed: Dict[str, Dict[str, Dict[str, Any]]]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    delegations = _objects(bundle, "delegations")
    actor_ids = set(typed["actors"])
    capability_ids = set(typed["capabilities"])

    edges: Dict[str, List[Tuple[str, int]]] = {}
    for index, delegation in enumerate(delegations):
        source = delegation.get("from_actor_id")
        target = delegation.get("to_actor_id")
        if (
            isinstance(source, str)
            and isinstance(target, str)
            and source in actor_ids
            and target in actor_ids
        ):
            edges.setdefault(source, []).append((target, index))
    state: Dict[str, int] = {}
    stack: List[str] = []
    cycle_edges: Set[int] = set()

    def visit(actor: str) -> None:
        state[actor] = 1
        stack.append(actor)
        for target, edge_index in edges.get(actor, []):
            if state.get(target, 0) == 0:
                visit(target)
            elif state.get(target) == 1:
                cycle_start = stack.index(target)
                cycle_nodes = stack[cycle_start:] + [target]
                for left, right in zip(cycle_nodes, cycle_nodes[1:]):
                    for candidate, candidate_index in edges.get(left, []):
                        if candidate == right:
                            cycle_edges.add(candidate_index)
        stack.pop()
        state[actor] = 2

    for actor in sorted(actor_ids):
        if state.get(actor, 0) == 0:
            visit(actor)
    for index in sorted(cycle_edges):
        issues.append(ValidationIssue("delegation.cycle", f"/delegations/{index}", "Delegation graph must be acyclic"))

    role_caps: Dict[str, Set[str]] = {
        role_id: _string_set(role.get("capabilities")) & capability_ids
        for role_id, role in typed["roles"].items()
    }
    grants: Dict[Tuple[str, str], List[Tuple[Optional[datetime], Optional[datetime], int]]] = {}
    for actor_id, actor in typed["actors"].items():
        roles = actor.get("roles", []) if isinstance(actor.get("roles"), list) else []
        for role_id in (value for value in roles if isinstance(value, str)):
            for capability in role_caps.get(role_id, set()):
                grants.setdefault((actor_id, capability), []).append((None, None, 17))

    pending: Set[Tuple[int, int]] = set()
    for delegation_index, delegation in enumerate(delegations):
        caps = delegation.get("capability_ids", [])
        if isinstance(caps, list):
            pending.update((delegation_index, cap_index) for cap_index in range(len(caps)))

    def contains(grant: Tuple[Optional[datetime], Optional[datetime], int], start: Optional[datetime], end: Optional[datetime], depth: Any) -> bool:
        grant_start, grant_end, grant_depth = grant
        if start is None or end is None or not isinstance(depth, int) or isinstance(depth, bool):
            return False
        return (grant_start is None or grant_start <= start) and (grant_end is None or grant_end >= end) and grant_depth >= depth + 1

    progressed = True
    while pending and progressed:
        progressed = False
        for delegation_index, cap_index in sorted(pending):
            delegation = delegations[delegation_index]
            caps = delegation.get("capability_ids", [])
            if not isinstance(caps, list) or cap_index >= len(caps):
                pending.remove((delegation_index, cap_index))
                continue
            capability = caps[cap_index]
            source = delegation.get("from_actor_id")
            target = delegation.get("to_actor_id")
            start = _parse_timestamp(delegation.get("valid_from"))
            end = _parse_timestamp(delegation.get("valid_until"))
            depth = delegation.get("max_depth")
            if (
                not isinstance(capability, str)
                or not isinstance(source, str)
                or not isinstance(target, str)
                or capability not in capability_ids
                or source not in actor_ids
                or target not in actor_ids
            ):
                pending.remove((delegation_index, cap_index))
                continue
            if any(contains(grant, start, end, depth) for grant in grants.get((source, capability), [])):
                grants.setdefault((target, capability), []).append((start, end, depth))
                pending.remove((delegation_index, cap_index))
                progressed = True

    for delegation_index, cap_index in sorted(pending):
        delegation = delegations[delegation_index]
        caps = delegation.get("capability_ids", [])
        if not isinstance(caps, list) or cap_index >= len(caps):
            continue
        capability = caps[cap_index]
        if not isinstance(capability, str) or capability not in capability_ids:
            continue
        source = delegation.get("from_actor_id")
        if not isinstance(source, str) or source not in actor_ids:
            continue
        issues.append(ValidationIssue("delegation.escalation", f"/delegations/{delegation_index}/capability_ids/{cap_index}", f"Actor '{source}' cannot delegate capability '{capability}' within the requested depth and validity window", f"/delegations/{delegation_index}/from_actor_id"))
    return issues


def validate_policy_bundle(bundle: Any) -> List[ValidationIssue]:
    """Return all deterministic shape and semantic errors for a v0.1 bundle."""

    shape_issues = _validate_shape(bundle)
    semantic_issues = _validate_semantics(bundle) if isinstance(bundle, dict) else []
    return _sorted_issues(shape_issues + semantic_issues)


def load_policy_bundle(path: str) -> Dict[str, Any]:
    """Load a UTF-8 JSON policy bundle or raise ``PolicyBundleError``."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PolicyBundleError([ValidationIssue("json.read", "/", f"Unable to read {source}: {exc}")]) from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolicyBundleError([ValidationIssue("json.syntax", "/", exc.msg, line=exc.lineno, column=exc.colno)]) from exc
    if not isinstance(value, dict):
        raise PolicyBundleError([ValidationIssue("schema.type", "/", "Policy bundle root must be an object")])
    return value


def _sort_strings(value: Any) -> Any:
    return sorted(value) if isinstance(value, list) else value


def normalize_policy_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep-copied canonical representation of an already valid bundle."""

    result = deepcopy(bundle)
    if isinstance(result.get("bundle"), dict) and isinstance(result["bundle"].get("provenance"), dict):
        for field in ("authored_by", "approved_by"):
            result["bundle"]["provenance"][field] = _sort_strings(result["bundle"]["provenance"].get(field))
    for actor in result.get("actors", []):
        actor["roles"] = _sort_strings(actor.get("roles"))
    for role in result.get("roles", []):
        role["capabilities"] = _sort_strings(role.get("capabilities"))
    for policy in result.get("policies", []):
        if isinstance(policy.get("provenance"), dict):
            for field in ("authored_by", "approved_by"):
                policy["provenance"][field] = _sort_strings(policy["provenance"].get(field))
        for control in policy.get("controls", []):
            control["capability_ids"] = _sort_strings(control.get("capability_ids"))
            control["evidence_fields"] = _sort_strings(control.get("evidence_fields"))
            if isinstance(control.get("subjects"), dict):
                for field in ("actor_ids", "role_ids"):
                    if field in control["subjects"]:
                        control["subjects"][field] = _sort_strings(control["subjects"][field])
            constraints = control.get("constraints")
            if isinstance(constraints, dict) and "allowed_data_classifications" in constraints:
                constraints["allowed_data_classifications"] = _sort_strings(constraints["allowed_data_classifications"])
        policy["controls"] = sorted(policy.get("controls", []), key=lambda item: item["id"])
    for approval in result.get("approvals", []):
        approval["approver_role_ids"] = _sort_strings(approval.get("approver_role_ids"))
        approval["bind_to"] = _sort_strings(approval.get("bind_to"))
    for delegation in result.get("delegations", []):
        delegation["capability_ids"] = _sort_strings(delegation.get("capability_ids"))
    for exception in result.get("exceptions", []):
        exception["capability_ids"] = _sort_strings(exception.get("capability_ids"))
        exception["approved_by"] = _sort_strings(exception.get("approved_by"))
        if isinstance(exception.get("subjects"), dict):
            for field in ("actor_ids", "role_ids"):
                if field in exception["subjects"]:
                    exception["subjects"][field] = _sort_strings(exception["subjects"][field])

    for collection in ("actors", "roles", "resources", "capabilities", "approvals", "delegations", "exceptions"):
        result[collection] = sorted(result.get(collection, []), key=lambda item: item["id"])
    result["policies"] = sorted(result.get("policies", []), key=lambda item: (-item["precedence"], item["id"]))
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _one_line(value: Any) -> str:
    return " ".join(str(value).split())


def _selector_text(selector: Dict[str, Any]) -> str:
    if selector.get("any") is True:
        return "any actor"
    parts = []
    if selector.get("actor_ids"):
        parts.append("actors=" + ",".join(selector["actor_ids"]))
    if selector.get("role_ids"):
        parts.append("roles=" + ",".join(selector["role_ids"]))
    return "; ".join(parts)


def _render_agent_policy(bundle: Dict[str, Any], source_sha256: str) -> str:
    metadata = bundle["bundle"]
    lines = [
        "AI Agent Governance Policy",
        "==========================",
        f"Bundle: {metadata['id']} v{metadata['version']} — {_one_line(metadata['title'])}",
        f"Lifecycle: {metadata['effective_at']} through {metadata['review_at']}",
        f"Source SHA-256: {source_sha256}",
        "",
        "FAIL-CLOSED RULE",
        "No actor may exercise a capability unless the governance graph establishes authority and the highest-precedence applicable controls permit it. Missing, stale, conflicting, or ambiguous authority is denied.",
        "",
        "ACTORS AND BASELINE ROLES",
    ]
    for actor in bundle["actors"]:
        lines.append(f"- {actor['id']} ({actor['kind']}; {_one_line(actor['display_name'])}): roles={','.join(actor['roles']) or 'none'}")
    lines.extend(["", "ROLES AND BASELINE CAPABILITIES"])
    for role in bundle["roles"]:
        lines.append(
            f"- {role['id']}: capabilities={','.join(role['capabilities']) or 'none'}"
        )
    lines.extend(["", "RESOURCES"])
    for resource in bundle["resources"]:
        classification = (
            f"; classification={resource['classification']}"
            if resource.get("classification")
            else ""
        )
        lines.append(
            f"- {resource['id']} ({resource['kind']}{classification}): "
            f"{_one_line(resource['description'])}"
        )
    lines.extend(["", "CAPABILITIES"])
    for capability in bundle["capabilities"]:
        lines.append(f"- {capability['id']}: {capability['action']} on {capability['resource_id']} — {_one_line(capability['description'])}")
    lines.extend(["", "POLICIES AND CONTROLS"])
    for policy in bundle["policies"]:
        lines.append(f"- {policy['id']} v{policy['version']} (precedence {policy['precedence']}): {_one_line(policy['title'])}")
        for control in policy["controls"]:
            detail = f"  - {control['id']}: effect={control['effect']}; subjects={_selector_text(control['subjects'])}; capabilities={','.join(control['capability_ids'])}"
            if control.get("approval_id"):
                detail += f"; approval={control['approval_id']}"
            if control.get("constraints"):
                detail += "; constraints=" + json.dumps(control["constraints"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            lines.append(detail)
    lines.extend(["", "APPROVALS"])
    if bundle["approvals"]:
        for approval in bundle["approvals"]:
            lines.append(f"- {approval['id']}: roles={','.join(approval['approver_role_ids'])}; quorum={approval['quorum']}; separation_of_duties={str(approval['separation_of_duties']).lower()}; expires_after_seconds={approval['expires_after_seconds']}; bind_to={','.join(approval['bind_to'])}")
    else:
        lines.append("- none")
    lines.extend(["", "DELEGATIONS"])
    if bundle["delegations"]:
        for delegation in bundle["delegations"]:
            lines.append(f"- {delegation['id']}: {delegation['from_actor_id']} -> {delegation['to_actor_id']}; capabilities={','.join(delegation['capability_ids'])}; valid={delegation['valid_from']}..{delegation['valid_until']}; additional_depth={delegation['max_depth']}")
    else:
        lines.append("- none")
    lines.extend(["", "EXCEPTIONS"])
    if bundle["exceptions"]:
        for exception in bundle["exceptions"]:
            detail = f"- {exception['id']}: replaces {exception['control_id']} with {exception['replacement_effect']}; subjects={_selector_text(exception['subjects'])}; capabilities={','.join(exception['capability_ids'])}; valid={exception['valid_from']}..{exception['valid_until']}"
            if exception.get("approval_id"):
                detail += f"; approval={exception['approval_id']}"
            lines.append(detail)
    else:
        lines.append("- none")
    lines.extend([
        "",
        "ENFORCEMENT BOUNDARY",
        "This compiled document is policy data, not an authorization decision or security boundary. A runtime enforcement layer must resolve identity, applicability, approvals, constraints, expiry, and evidence before tool dispatch.",
    ])
    return "\n".join(lines) + "\n"


def compile_policy_bundle(bundle: Dict[str, Any]) -> CompiledPolicy:
    """Validate and compile a bundle into stable text and JSON artifacts."""

    issues = validate_policy_bundle(bundle)
    if issues:
        raise PolicyBundleError(issues)
    normalized = normalize_policy_bundle(bundle)
    source_json = _canonical_json(normalized)
    source_sha256 = _digest(source_json)
    agent_policy = _render_agent_policy(normalized, source_sha256)
    decision = deepcopy(normalized)
    decision["compilation"] = {
        "agent_policy_sha256": _digest(agent_policy),
        "source_sha256": source_sha256,
    }
    decision["resolution"] = {
        "default_effect": "deny",
        "effect_order": ["deny", "require_approval", "allow"],
        "policy_precedence": "higher_integer_first",
        "unresolved_authority": "deny",
    }
    return CompiledPolicy(agent_policy=agent_policy, decision_data=_canonical_json(decision))


def write_compiled_policy(bundle: Dict[str, Any], output_dir: str) -> Tuple[Path, Path]:
    """Compile and atomically replace both artifacts in ``output_dir``."""

    compiled = compile_policy_bundle(bundle)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    targets = (
        (destination / "agent-policy.txt", compiled.agent_policy),
        (destination / "decision-data.json", compiled.decision_data),
    )
    written: List[Path] = []
    temporary: List[Path] = []
    try:
        for target, content in targets:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=str(destination), prefix=f".{target.name}.", delete=False) as handle:
                handle.write(content)
                temporary.append(Path(handle.name))
        for (target, _), temp_path in zip(targets, temporary):
            temp_path.replace(target)
            written.append(target)
    finally:
        for temp_path in temporary:
            if temp_path.exists():
                temp_path.unlink()
    return written[0], written[1]


def validation_result(issues: Iterable[ValidationIssue]) -> Dict[str, Any]:
    """Return the stable JSON validation envelope documented by v0.1."""

    sorted_issues = _sorted_issues(issues)
    return {"valid": not sorted_issues, "errors": [issue.as_dict() for issue in sorted_issues]}
