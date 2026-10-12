"""Integration tests for all REST API endpoints and end-to-end flows."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_and_readiness_probes(client: AsyncClient):
    """Verify health and readiness probes return 200 OK."""
    health_res = await client.get("/healthz")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "UP"

    ready_res = await client.get("/readyz")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "READY"


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Verify OWASP recommended security headers are enforced."""
    res = await client.get("/healthz")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in res.headers
    assert "Content-Security-Policy" in res.headers


@pytest.mark.asyncio
async def test_auth_token_minting_and_inspection(client: AsyncClient):
    """Verify demo token generation and cryptographic inspection."""
    mint_res = await client.post(
        "/api/v1/auth/token",
        json={
            "subject": "usr-demo-alice",
            "email": "alice@example.com",
            "roles": ["engineer", "secops"],
            "department": "Security",
        },
    )
    assert mint_res.status_code == 200
    token = mint_res.json()["access_token"]
    assert token is not None

    # Inspect token
    inspect_res = await client.post("/api/v1/auth/inspect", json={"token": token})
    assert inspect_res.status_code == 200
    inspect_data = inspect_res.json()
    assert inspect_data["valid"] is True
    assert inspect_data["subject"] == "usr-demo-alice"
    assert "secops" in inspect_data["roles"]


@pytest.mark.asyncio
async def test_lifecycle_onboarding_flow(client: AsyncClient, hr_admin_token: str):
    """Verify ServiceNow onboarding ticket ingestion, OPA check, and PubSub event generation."""
    headers = {"Authorization": f"Bearer {hr_admin_token}", "X-Correlation-ID": "corr-test-onboard-01"}
    ticket = {
        "ticket_id": "REQ-SNOW-9001",
        "request_type": "ONBOARD",
        "requester_email": "alice.hr@example.com",
        "target_user_email": "new.engineer@example.com",
        "target_user_full_name": "New Engineer",
        "department": "Engineering",
        "target_role": "engineer",
        "justification": "Approved hiring requisition",
        "requested_entitlements": ["slack:dev", "google_workspace:eng"],
        "context": {"device_trust": "managed", "risk_level": "low"},
    }

    res = await client.post("/api/v1/lifecycle/request", json=ticket, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert data["ticket_id"] == "REQ-SNOW-9001"
    assert data["policy_evaluation"]["allow"] is True

    # Check status endpoint
    status_res = await client.get("/api/v1/events/status/REQ-SNOW-9001", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_lifecycle_onboard_denied_when_unauthorized_caller(client: AsyncClient, engineer_token: str):
    """Verify an ordinary engineer attempting to trigger onboarding is denied by OPA policy."""
    headers = {"Authorization": f"Bearer {engineer_token}"}
    ticket = {
        "ticket_id": "REQ-SNOW-9002",
        "request_type": "ONBOARD",
        "requester_email": "charlie.eng@example.com",
        "target_user_email": "unauthorized.user@example.com",
        "target_user_full_name": "Unauthorized User",
        "department": "Finance",
        "target_role": "finance_analyst",
        "justification": "Attempting unauthorized onboard",
        "context": {"device_trust": "untrusted", "risk_level": "high"},
    }

    res = await client.post("/api/v1/lifecycle/request", json=ticket, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["policy_evaluation"]["allow"] is False


@pytest.mark.asyncio
async def test_policy_evaluation_endpoint(client: AsyncClient, engineer_token: str):
    """Verify context-aware ABAC evaluation endpoint."""
    headers = {"Authorization": f"Bearer {engineer_token}"}
    payload = {
        "subject": {"id": "usr-charlie", "email": "charlie@example.com", "roles": ["engineer"], "department": "Engineering"},
        "action": "read",
        "resource": {"type": "code_repo", "name": "backend-core", "sensitivity": "medium"},
        "context": {"device_trust": "managed", "risk_level": "low"},
    }

    res = await client.post("/api/v1/policies/evaluate", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["allow"] is True


@pytest.mark.asyncio
async def test_access_review_campaign_lifecycle(client: AsyncClient, identity_admin_token: str):
    """Verify creating an access review campaign and submitting a revocation decision."""
    headers = {"Authorization": f"Bearer {identity_admin_token}"}

    create_res = await client.post(
        "/api/v1/reviews/campaigns",
        json={"campaign_name": "Q4 Audit Review", "due_days": 10},
        headers=headers,
    )
    assert create_res.status_code == 201
    campaign = create_res.json()
    assert campaign["campaign_name"] == "Q4 Audit Review"

    list_res = await client.get("/api/v1/reviews/campaigns", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_simulate_security_anomaly_and_audit(client: AsyncClient, engineer_token: str):
    """Verify simulated security anomaly triggers alert and is written to audit trail."""
    headers = {"Authorization": f"Bearer {engineer_token}"}
    anomaly_req = {
        "anomaly_type": "IMPOSSIBLE_TRAVEL",
        "target_user_email": "flagged.user@example.com",
        "simulated_context": {
            "device_trust": "untrusted",
            "risk_level": "critical",
            "origin_geo": "TOR_EXIT_NODE",
        },
    }

    res = await client.post("/api/v1/anomalies/simulate", json=anomaly_req, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["policy_action_taken"] == "ACCESS_BLOCKED_AND_SESSION_FLAGGED"
    assert data["audit_event_logged"] is True

    # Verify audit query includes the anomaly alert
    audit_res = await client.get("/api/v1/audit?status=ALERT", headers=headers)
    assert audit_res.status_code == 200
    audit_events = audit_res.json()
    assert any("SECURITY_ANOMALY" in e["action"] for e in audit_events)
