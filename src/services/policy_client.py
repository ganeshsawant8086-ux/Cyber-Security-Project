"""Open Policy Agent (OPA) Client with Resilient Fallback Evaluator.

Connects to OPA's HTTP REST API (`/v1/data/...`).
Includes a python-based fallback policy evaluator so tests and demos run seamlessly
even when the external OPA container is not actively running.
"""

from typing import Any, Dict
import httpx
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("policy_client")


class PolicyClient:
    """Client for querying OPA Policy Decision Point (PDP)."""

    def __init__(self, opa_url: str = settings.OPA_URL):
        self.opa_url = opa_url.rstrip("/")
        self.timeout = settings.OPA_TIMEOUT_SECONDS

    async def evaluate_lifecycle(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Query identity.lifecycle OPA policy."""
        url = f"{self.opa_url}/v1/data/identity/lifecycle"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json={"input": input_data})
                if response.status_code == 200:
                    result = response.json().get("result", {})
                    allow = result.get("allow", False)
                    reason = result.get("reason", "Decision returned from OPA")
                    return {"allow": allow, "reason": reason, "engine": "opa_remote"}
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"OPA service unreachable ({str(exc)}). Using local PEP policy evaluator fallback.")

        # Local fallback evaluation logic mirroring Rego policy
        return self._evaluate_lifecycle_locally(input_data)

    async def evaluate_access(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Query identity.authz OPA policy."""
        url = f"{self.opa_url}/v1/data/identity/authz"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json={"input": input_data})
                if response.status_code == 200:
                    result = response.json().get("result", {})
                    allow = result.get("allow", False)
                    reason = result.get("reason", "Decision returned from OPA")
                    return {"allow": allow, "reason": reason, "engine": "opa_remote"}
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"OPA service unreachable ({str(exc)}). Using local PEP policy evaluator fallback.")

        return self._evaluate_access_locally(input_data)

    def _evaluate_lifecycle_locally(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        """Python mirror of policies/lifecycle_policy.rego."""
        req_type = inp.get("request_type")
        caller_roles = inp.get("caller_roles", [])
        target_role = inp.get("target_role", "")
        context = inp.get("context", {})
        device_trust = context.get("device_trust", "untrusted")
        risk_level = context.get("risk_level", "high")

        privileged_roles = {"security_engineer", "cloud_admin", "secops", "infrastructure_admin"}
        is_privileged = target_role in privileged_roles

        if req_type == "ONBOARD":
            authorized = any(r in ["hr_admin", "identity_admin", "manager", "admin"] for r in caller_roles)
            if not authorized:
                return {"allow": False, "reason": "Denial: Requester unauthorized to trigger onboarding", "engine": "local_fallback"}

            if is_privileged:
                compliant = (device_trust == "managed" and risk_level == "low")
            else:
                compliant = (device_trust in ["managed", "compliant"] and risk_level in ["low", "medium"])

            if not compliant:
                return {"allow": False, "reason": "Denial: Context security risk too high or device unmanaged for privileged role", "engine": "local_fallback"}

            return {"allow": True, "reason": "Onboarding request approved", "engine": "local_fallback"}

        elif req_type == "ROLE_CHANGE":
            if "identity_admin" not in caller_roles and "admin" not in caller_roles:
                return {"allow": False, "reason": "Denial: Role changes require identity_admin permissions", "engine": "local_fallback"}
            return {"allow": True, "reason": "Role change approved", "engine": "local_fallback"}

        elif req_type == "OFFBOARD":
            can_offboard = any(r in ["hr_admin", "secops", "identity_admin", "admin"] for r in caller_roles)
            if not can_offboard:
                return {"allow": False, "reason": "Denial: Offboarding must be submitted by hr_admin, secops, or identity_admin", "engine": "local_fallback"}
            return {"allow": True, "reason": "Offboarding request approved for immediate deprovisioning", "engine": "local_fallback"}

        return {"allow": False, "reason": "Default deny: unknown lifecycle operation", "engine": "local_fallback"}

    def _evaluate_access_locally(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        """Python mirror of policies/access_policy.rego."""
        subject = inp.get("subject", {})
        action = inp.get("action", "")
        resource = inp.get("resource", {})
        context = inp.get("context", {})

        roles = subject.get("roles", [])
        device_trust = context.get("device_trust", "untrusted")
        risk_level = context.get("risk_level", "high")
        res_type = resource.get("type", "")
        sensitivity = resource.get("sensitivity", "medium")

        # Rule 1: Contractor blocked from cloud_infra
        if "contractor" in roles and res_type in ["cloud_infra", "kms_keys", "production_db"]:
            return {
                "allow": False,
                "reason": "Access denied: contractors are restricted from accessing production cloud infrastructure",
                "engine": "local_fallback",
            }

        # Rule 2: Untrusted device blocked from write/admin
        if device_trust == "untrusted" and action in ["write", "delete", "admin", "provision"]:
            return {
                "allow": False,
                "reason": "Access denied: write or administrative actions are forbidden from untrusted devices",
                "engine": "local_fallback",
            }

        # Rule 3: Risk check
        if sensitivity == "critical":
            if not (risk_level == "low" and device_trust == "managed"):
                return {
                    "allow": False,
                    "reason": "Access denied: risk level too high for requested resource sensitivity",
                    "engine": "local_fallback",
                }
        elif sensitivity in ["medium", "high"]:
            if risk_level not in ["low", "medium"]:
                return {
                    "allow": False,
                    "reason": "Access denied: risk level too high for requested resource sensitivity",
                    "engine": "local_fallback",
                }

        # Rule 4: Action by role
        if "admin" in roles:
            return {"allow": True, "reason": "Access granted: authorized subject with acceptable risk posture", "engine": "local_fallback"}

        if "security_engineer" in roles and res_type in ["cloud_infra", "security_logs", "kms_keys"]:
            return {"allow": True, "reason": "Access granted: authorized subject with acceptable risk posture", "engine": "local_fallback"}

        if "engineer" in roles and action in ["read", "write"] and sensitivity in ["low", "medium"]:
            return {"allow": True, "reason": "Access granted: authorized subject with acceptable risk posture", "engine": "local_fallback"}

        if action == "read" and sensitivity == "low" and device_trust in ["managed", "compliant"]:
            return {"allow": True, "reason": "Access granted: authorized subject with acceptable risk posture", "engine": "local_fallback"}

        return {
            "allow": False,
            "reason": "Access denied: subject lacks requisite role or department for action on resource",
            "engine": "local_fallback",
        }


policy_client = PolicyClient()
