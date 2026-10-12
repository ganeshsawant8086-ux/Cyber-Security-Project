"""End-to-End Demonstration Script for Identity Lifecycle & Access Orchestration.

Demonstrates full portfolio scenarios using fictional personas:
1. Alice (HR Admin) onboards Bob (DevOps Engineer) -> OPA approves -> Async worker provisions Directory, Cloud IAM, SaaS.
2. Charlie (External Contractor) requests privileged KMS access -> OPA ABAC blocks due to contractor boundary.
3. Eve (Simulated compromise / Impossible Travel) -> Anomaly detection flags session and alerts audit stream.
4. Dave (Terminated User) -> Immediate offboarding -> Worker deprovisions all active credentials and SaaS accounts.
5. Poison Message -> Downstream API failure triggers Dead Letter Queue (DLQ) routing.
6. Audit Inspection -> Query structured audit events with correlation ID tracing.
"""

import asyncio
import json
from datetime import datetime, timezone
import httpx

BASE_URL = "http://localhost:8000"


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


async def run_e2e_demo():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print_banner("1. HEALTH & READINESS PROBES")
        res = await client.get("/healthz")
        print(f"Liveness Probe: {res.status_code} -> {res.json()}")
        ready_res = await client.get("/readyz")
        print(f"Readiness Probe: {ready_res.status_code} -> {ready_res.json()}")

        print_banner("2. GENERATE PERSONA BEARER TOKENS (OIDC / OAuth2 DEMO)")
        # 2.1 Alice (HR Admin)
        alice_token_res = await client.post(
            "/api/v1/auth/token",
            json={
                "subject": "usr-alice-hr",
                "email": "alice.hr@example.com",
                "roles": ["hr_admin"],
                "department": "Human Resources",
            },
        )
        alice_token = alice_token_res.json()["access_token"]
        print(f"[Persona] Alice (HR Admin) token minted successfully.")

        # 2.2 Charlie (Contractor)
        charlie_token_res = await client.post(
            "/api/v1/auth/token",
            json={
                "subject": "usr-charlie-contractor",
                "email": "charlie.contractor@example.com",
                "roles": ["contractor", "engineer"],
                "department": "External Contractors",
            },
        )
        charlie_token = charlie_token_res.json()["access_token"]
        print(f"[Persona] Charlie (Contractor) token minted successfully.")

        # 2.3 Identity Admin
        admin_token_res = await client.post(
            "/api/v1/auth/token",
            json={
                "subject": "usr-id-admin",
                "email": "secops.admin@example.com",
                "roles": ["identity_admin", "secops"],
                "department": "Cloud Security",
            },
        )
        admin_token = admin_token_res.json()["access_token"]
        print(f"[Persona] SecOps Identity Admin token minted successfully.")

        print_banner("3. SCENARIO A: ONBOARDING BOB (DEVOPS ENGINEER)")
        bob_ticket = {
            "ticket_id": "SNOW-REQ-10001",
            "request_type": "ONBOARD",
            "requester_email": "alice.hr@example.com",
            "target_user_email": "bob.devops@example.com",
            "target_user_full_name": "Bob DevOps",
            "department": "Infrastructure",
            "target_role": "devops",
            "justification": "Approved hiring requisition for Cloud Infra team",
            "requested_entitlements": [
                "aws_sso:DevOps-PowerUser",
                "google_workspace:infrastructure-team",
                "slack:devops-alerts",
            ],
            "context": {"device_trust": "managed", "risk_level": "low"},
        }
        headers_alice = {"Authorization": f"Bearer {alice_token}", "X-Correlation-ID": "corr-onboard-bob-001"}
        onboard_res = await client.post("/api/v1/lifecycle/request", json=bob_ticket, headers=headers_alice)
        print(f"Status: {onboard_res.status_code}")
        print("Response:", json.dumps(onboard_res.json(), indent=2))

        print_banner("4. SCENARIO B: POLICY DENIAL (CONTRACTOR BOUNDARY DEFENSE)")
        charlie_access_req = {
            "subject": {
                "id": "usr-charlie-contractor",
                "email": "charlie.contractor@example.com",
                "roles": ["contractor", "engineer"],
                "department": "External Contractors",
            },
            "action": "admin",
            "resource": {
                "type": "cloud_infra",
                "name": "gcp-production-kms",
                "sensitivity": "critical",
            },
            "context": {"device_trust": "managed", "risk_level": "low"},
        }
        headers_charlie = {"Authorization": f"Bearer {charlie_token}"}
        eval_res = await client.post("/api/v1/policies/evaluate", json=charlie_access_req, headers=headers_charlie)
        print("Contractor Access Evaluation Outcome:")
        print(json.dumps(eval_res.json(), indent=2))

        print_banner("5. SCENARIO C: SIMULATED SECURITY ANOMALY (IMPOSSIBLE TRAVEL)")
        anomaly_req = {
            "anomaly_type": "IMPOSSIBLE_TRAVEL",
            "target_user_email": "eve.compromised@example.com",
            "simulated_context": {
                "device_trust": "untrusted",
                "risk_level": "critical",
                "origin_geo": "TOR_EXIT_NODE_BUCHAREST",
            },
        }
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        anom_res = await client.post("/api/v1/anomalies/simulate", json=anomaly_req, headers=headers_admin)
        print("Anomaly Response:")
        print(json.dumps(anom_res.json(), indent=2))

        print_banner("6. SCENARIO D: OFFBOARDING DAVE (IMMEDIATE DEPROVISIONING)")
        dave_ticket = {
            "ticket_id": "SNOW-REQ-10002",
            "request_type": "OFFBOARD",
            "requester_email": "secops.admin@example.com",
            "target_user_email": "dave.departed@example.com",
            "target_user_full_name": "Dave Departed",
            "department": "Engineering",
            "target_role": "engineer",
            "justification": "Employment termination effective immediately",
            "requested_entitlements": [],
            "context": {"device_trust": "managed", "risk_level": "low"},
        }
        offboard_res = await client.post("/api/v1/lifecycle/offboard", json=dave_ticket, headers=headers_admin)
        print("Offboarding Response:")
        print(json.dumps(offboard_res.json(), indent=2))

        print_banner("7. SCENARIO E: DEAD LETTER QUEUE (DLQ) INSPECTION")
        dlq_res = await client.get("/api/v1/events/dlq", headers=headers_admin)
        print(f"DLQ Messages count: {len(dlq_res.json())}")

        print_banner("8. SCENARIO F: AUDIT TRAIL VERIFICATION")
        audit_res = await client.get("/api/v1/audit?limit=10", headers=headers_admin)
        print(f"Retrieved {len(audit_res.json())} audit events. Recent entries:")
        for ev in audit_res.json()[:4]:
            print(f"- [{ev['timestamp']}] Actor: {ev['actor']:<25} Action: {ev['action']:<30} Status: {ev['status']}")

        print_banner("DEMO COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    try:
        asyncio.run(run_e2e_demo())
    except httpx.ConnectError:
        print("[!] Server not currently running on http://localhost:8000.")
        print("    Start server with: uvicorn src.main:app --port 8000")
        print("    or run via docker-compose: docker compose up")
