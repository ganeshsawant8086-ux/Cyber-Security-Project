"""Mock SaaS Adapter simulating Slack and Okta app assignments."""

from typing import Any, Dict, List
from src.adapters.base import DownstreamSystemAdapter
from src.core.logging import get_logger

logger = get_logger("adapter.saas")


class MockSaaSAdapter(DownstreamSystemAdapter):
    """Simulates SaaS application access provisioning (Slack workspace, Salesforce, Jira)."""

    def system_name(self) -> str:
        return "saas_apps"

    async def provision_user(
        self, user_email: str, full_name: str, department: str, entitlements: List[str]
    ) -> Dict[str, Any]:
        saas_entitlements = [e for e in entitlements if "slack" in e or "jira" in e or "github" in e]
        logger.info(f"[MOCK SAAS] Inviting {user_email} to SaaS apps: {saas_entitlements}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "PROVISION_SAAS",
            "user_email": user_email,
            "apps": saas_entitlements,
        }

    async def deprovision_user(self, user_email: str) -> Dict[str, Any]:
        logger.info(f"[MOCK SAAS] Deactivating account and terminating active sessions for {user_email}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "DEACTIVATE_SAAS_ACCOUNTS",
            "user_email": user_email,
            "status": "REVOKED",
        }

    async def update_entitlements(
        self, user_email: str, added_entitlements: List[str], removed_entitlements: List[str]
    ) -> Dict[str, Any]:
        logger.info(f"[MOCK SAAS] Updating SaaS licenses for {user_email}")
        return {
            "status": "SUCCESS",
            "system": self.system_name(),
            "action": "UPDATE_SAAS_LICENSES",
            "added": added_entitlements,
            "removed": removed_entitlements,
        }
