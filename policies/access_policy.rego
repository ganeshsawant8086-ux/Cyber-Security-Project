package identity.authz

import future.keywords.in

default allow := false
default reason := "Default deny: unauthorized access attempt"

# Allow access if all security constraints pass
allow {
    not is_contractor_blocked
    not is_untrusted_device_blocked
    is_action_authorized
    is_risk_acceptable
}

# Determine reason dynamically
reason := "Access granted: authorized subject with acceptable risk posture" {
    allow
}

reason := "Access denied: contractors are restricted from accessing production cloud infrastructure" {
    is_contractor_blocked
}

reason := "Access denied: write or administrative actions are forbidden from untrusted devices" {
    not is_contractor_blocked
    is_untrusted_device_blocked
}

reason := "Access denied: risk level too high for requested resource sensitivity" {
    not is_contractor_blocked
    not is_untrusted_device_blocked
    not is_risk_acceptable
}

reason := "Access denied: subject lacks requisite role or department for action on resource" {
    not is_contractor_blocked
    not is_untrusted_device_blocked
    is_risk_acceptable
    not is_action_authorized
}

# --- Enforcement Rules ---

# Rule 1: Contractor boundary defense
is_contractor_blocked {
    "contractor" in input.subject.roles
    input.resource.type in ["cloud_infra", "kms_keys", "production_db"]
}

# Rule 2: Untrusted device restrictions
is_untrusted_device_blocked {
    input.context.device_trust == "untrusted"
    input.action in ["write", "delete", "admin", "provision"]
}

# Rule 3: Risk level assessment
is_risk_acceptable {
    input.resource.sensitivity == "critical"
    input.context.risk_level == "low"
    input.context.device_trust == "managed"
}

is_risk_acceptable {
    input.resource.sensitivity in ["medium", "high"]
    input.context.risk_level in ["low", "medium"]
}

is_risk_acceptable {
    input.resource.sensitivity == "low"
    input.context.risk_level in ["low", "medium", "high"]
}

# Rule 4: Action authorization by role
is_action_authorized {
    # Admins can perform any action
    "admin" in input.subject.roles
}

is_action_authorized {
    # Security Engineers have broad access to cloud infra and security logs
    "security_engineer" in input.subject.roles
    input.resource.type in ["cloud_infra", "security_logs", "kms_keys"]
}

is_action_authorized {
    # Engineers have read/write access to dev and medium/low sensitivity resources
    "engineer" in input.subject.roles
    input.action in ["read", "write"]
    input.resource.sensitivity in ["low", "medium"]
}

is_action_authorized {
    # Anyone can read low-sensitivity internal resources if device is compliant
    input.action == "read"
    input.resource.sensitivity == "low"
    input.context.device_trust in ["managed", "compliant"]
}
