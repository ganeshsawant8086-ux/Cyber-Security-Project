"""Unit tests for OPA policy decision logic and context-aware evaluation."""

import pytest
from src.services.policy_client import policy_client


@pytest.mark.asyncio
async def test_lifecycle_onboard_allowed_for_hr_admin_with_managed_device():
    """HR admin onboarding an engineer from managed device with low risk must be allowed."""
    input_data = {
        "request_type": "ONBOARD",
        "caller_roles": ["hr_admin"],
        "target_role": "security_engineer",
        "context": {
            "device_trust": "managed",
            "risk_level": "low",
        },
    }
    decision = await policy_client.evaluate_lifecycle(input_data)
    assert decision["allow"] is True
    assert "approved" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_lifecycle_onboard_denied_when_risk_high_for_privileged_role():
    """Privileged role onboard request from high-risk context must be denied."""
    input_data = {
        "request_type": "ONBOARD",
        "caller_roles": ["hr_admin"],
        "target_role": "security_engineer",
        "context": {
            "device_trust": "managed",
            "risk_level": "high",
        },
    }
    decision = await policy_client.evaluate_lifecycle(input_data)
    assert decision["allow"] is False
    assert "risk too high" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_lifecycle_role_change_denied_for_non_identity_admin():
    """Role changes require identity_admin role."""
    input_data = {
        "request_type": "ROLE_CHANGE",
        "caller_roles": ["manager"],
        "target_role": "cloud_admin",
        "context": {"device_trust": "managed", "risk_level": "low"},
    }
    decision = await policy_client.evaluate_lifecycle(input_data)
    assert decision["allow"] is False
    assert "identity_admin" in decision["reason"]


@pytest.mark.asyncio
async def test_access_policy_contractor_blocked_from_cloud_infra():
    """Contractors are strictly denied access to cloud infrastructure."""
    input_data = {
        "subject": {"id": "usr-eve", "roles": ["contractor", "engineer"]},
        "action": "read",
        "resource": {"type": "cloud_infra", "sensitivity": "medium"},
        "context": {"device_trust": "managed", "risk_level": "low"},
    }
    decision = await policy_client.evaluate_access(input_data)
    assert decision["allow"] is False
    assert "contractor" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_access_policy_untrusted_device_blocked_from_admin_action():
    """Untrusted devices cannot perform write/admin actions."""
    input_data = {
        "subject": {"id": "usr-alice", "roles": ["security_engineer"]},
        "action": "write",
        "resource": {"type": "cloud_infra", "sensitivity": "high"},
        "context": {"device_trust": "untrusted", "risk_level": "low"},
    }
    decision = await policy_client.evaluate_access(input_data)
    assert decision["allow"] is False
    assert "untrusted device" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_access_policy_security_engineer_allowed_with_clean_posture():
    """Security engineer with managed device and low risk is authorized."""
    input_data = {
        "subject": {"id": "usr-alice", "roles": ["security_engineer"]},
        "action": "read",
        "resource": {"type": "cloud_infra", "sensitivity": "critical"},
        "context": {"device_trust": "managed", "risk_level": "low"},
    }
    decision = await policy_client.evaluate_access(input_data)
    assert decision["allow"] is True
