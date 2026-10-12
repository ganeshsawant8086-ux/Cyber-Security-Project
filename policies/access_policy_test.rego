package identity.authz_test

import future.keywords.in
import data.identity.authz

test_contractor_blocked_from_cloud_infra {
    input := {
        "subject": {"id": "usr-bob", "roles": ["contractor", "engineer"]},
        "action": "read",
        "resource": {"type": "cloud_infra", "sensitivity": "medium"},
        "context": {"device_trust": "managed", "risk_level": "low"}
    }
    not authz.allow with input as input
    authz.reason == "Access denied: contractors are restricted from accessing production cloud infrastructure" with input as input
}

test_untrusted_device_blocked_from_write {
    input := {
        "subject": {"id": "usr-alice", "roles": ["security_engineer"]},
        "action": "write",
        "resource": {"type": "cloud_infra", "sensitivity": "high"},
        "context": {"device_trust": "untrusted", "risk_level": "low"}
    }
    not authz.allow with input as input
    authz.reason == "Access denied: write or administrative actions are forbidden from untrusted devices" with input as input
}

test_critical_resource_denied_when_risk_high {
    input := {
        "subject": {"id": "usr-alice", "roles": ["security_engineer"]},
        "action": "read",
        "resource": {"type": "cloud_infra", "sensitivity": "critical"},
        "context": {"device_trust": "managed", "risk_level": "high"}
    }
    not authz.allow with input as input
}

test_security_engineer_allowed_critical_resource_when_posture_clean {
    input := {
        "subject": {"id": "usr-alice", "roles": ["security_engineer"]},
        "action": "read",
        "resource": {"type": "cloud_infra", "sensitivity": "critical"},
        "context": {"device_trust": "managed", "risk_level": "low"}
    }
    authz.allow with input as input
}

test_admin_allowed_full_access {
    input := {
        "subject": {"id": "admin-1", "roles": ["admin"]},
        "action": "admin",
        "resource": {"type": "kms_keys", "sensitivity": "critical"},
        "context": {"device_trust": "managed", "risk_level": "low"}
    }
    authz.allow with input as input
}
