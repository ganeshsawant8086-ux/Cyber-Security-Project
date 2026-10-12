"""Mock Directory Adapter simulating Google Workspace / Microsoft Entra ID."""

from typing import Any, Dict, List
from src.adapters.base import DownstreamSystemAdapter
from src.core.logging import get_logger

logger = get_logger("adapter.directory")


class MockDirectoryAdapter(DownstreamSystemAdapter):
    """Simulates directory provisioning (e.g., Google Workspace Admin SDK / MS Graph)."""

    def system_name(self) -> str:
        return "directory_service"

    async def provision_user(
        self, user_email: str, full_name: str, department: str, entitlements: List[str]
    ) -> Dict[str, Any]:
        logger.info(f"[MOCK DIRECTORY] Provisioning primary corporate account for {user_email} in orgUnit /{department}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "PROVISION",
            "account_created": user_email,
            "org_unit": f"/{department}",
            "groups_joined": [e for e in entitlements if "group" in e or "team" in e],
        }

    async def deprovision_user(self, user_email: str) -> Dict[str, Any]:
        logger.info(f"[MOCK DIRECTORY] Suspending user account {user_email} and invalidating sessions")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "SUSPEND_AND_DEPROVISION",
            "account_suspended": user_email,
            "sessions_revoked": True,
        }

    async def update_entitlements(
        self, user_email: str, added_entitlements: List[str], removed_entitlements: List[str]
    ) -> Dict[str, Any]:
        logger.info(
            f"[MOCK DIRECTORY] Updating groups for {user_email}: added={added_entitlements}, removed={removed_entitlements}"
        )
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "UPDATE_GROUPS",
            "added": added_entitlements,
            "removed": removed_entitlements,
        }
