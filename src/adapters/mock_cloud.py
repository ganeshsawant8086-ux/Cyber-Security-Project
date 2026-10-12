"""Mock Cloud Access Adapter simulating AWS IAM Identity Center and GCP IAM."""

from typing import Any, Dict, List
from src.adapters.base import DownstreamSystemAdapter
from src.core.logging import get_logger

logger = get_logger("adapter.cloud_iam")


class MockCloudAccessAdapter(DownstreamSystemAdapter):
    """Simulates cloud infrastructure privilege assignment (AWS SSO / GCP IAM)."""

    def system_name(self) -> str:
        return "cloud_iam"

    async def provision_user(
        self, user_email: str, full_name: str, department: str, entitlements: List[str]
    ) -> Dict[str, Any]:
        iam_roles = [e.split(":")[-1] for e in entitlements if "aws" in e or "gcp" in e or "cloud" in e]
        logger.info(f"[MOCK CLOUD IAM] Assigning permission sets to {user_email}: {iam_roles}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "ASSIGN_IAM_ROLES",
            "user_email": user_email,
            "assigned_roles": iam_roles,
        }

    async def deprovision_user(self, user_email: str) -> Dict[str, Any]:
        logger.info(f"[MOCK CLOUD IAM] Revoking all cloud IAM permission sets and temporary STS tokens for {user_email}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "REVOKE_ALL_CLOUD_IAM",
            "user_email": user_email,
            "roles_revoked": True,
            "active_tokens_invalidated": True,
        }

    async def update_entitlements(
        self, user_email: str, added_entitlements: List[str], removed_entitlements: List[str]
    ) -> Dict[str, Any]:
        logger.info(f"[MOCK CLOUD IAM] Syncing IAM roles for {user_email}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "SYNC_IAM_ROLES",
            "added_roles": added_entitlements,
            "removed_roles": removed_entitlements,
        }
