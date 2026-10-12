"""Abstract Base Class for Downstream Target System Provisioning Adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DownstreamSystemAdapter(ABC):
    """Interface implemented by integrations to target systems (e.g. AWS SSO, Google Workspace, Okta).

    ARCHITECTURE NOTE:
    In this demo portfolio project, all adapters are mock implementations.
    In a production system, these adapters would call target system SCIM 2.0 endpoints,
    Google Workspace Directory API, AWS IAM Identity Center API, or Okta API.
    """

    @abstractmethod
    def system_name(self) -> str:
        """Name of the target system."""
        pass

    @abstractmethod
    async def provision_user(
        self, user_email: str, full_name: str, department: str, entitlements: List[str]
    ) -> Dict[str, Any]:
        """Create identity and grant requested entitlements in target system."""
        pass

    @abstractmethod
    async def deprovision_user(self, user_email: str) -> Dict[str, Any]:
        """Revoke all access and suspend/remove identity from target system."""
        pass

    @abstractmethod
    async def update_entitlements(
        self, user_email: str, added_entitlements: List[str], removed_entitlements: List[str]
    ) -> Dict[str, Any]:
        """Modify entitlements for an existing user."""
        pass
