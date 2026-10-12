package identity.lifecycle

import future.keywords.in

default allow := false
default reason := "Default deny: access does not meet policy criteria"

# Allow Onboarding if requester has authority and context satisfies security posture
allow {
    input.request_type == "ONBOARD"
    requester_is_authorized
    context_is_compliant
}

reason := "Onboarding request approved" {
    input.request_type == "ONBOARD"
    requester_is_authorized
    context_is_compliant
}

# Allow Role Change if requester is identity_admin and target role constraints pass
allow {
    input.request_type == "ROLE_CHANGE"
    requester_has_role("identity_admin")
    context_is_compliant
}

reason := "Role change approved" {
    input.request_type == "ROLE_CHANGE"
    requester_has_role("identity_admin")
    context_is_compliant
}

# Allow Offboarding immediately for security or HR
allow {
    input.request_type == "OFFBOARD"
    requester_can_offboard
}

reason := "Offboarding request approved for immediate deprovisioning" {
    input.request_type == "OFFBOARD"
    requester_can_offboard
}

# Denial reasons for debugging and audit transparency
reason := "Denial: Requester unauthorized to trigger onboarding" {
    input.request_type == "ONBOARD"
    not requester_is_authorized
}

reason := "Denial: Context security risk too high or device unmanaged for privileged role" {
    input.request_type == "ONBOARD"
    requester_is_authorized
    not context_is_compliant
}

reason := "Denial: Role changes require identity_admin permissions" {
    input.request_type == "ROLE_CHANGE"
    not requester_has_role("identity_admin")
}

reason := "Denial: Offboarding must be submitted by hr_admin, secops, or identity_admin" {
    input.request_type == "OFFBOARD"
    not requester_can_offboard
}

# --- Helper Rules ---

requester_has_role(role) {
    role in input.caller_roles
}

requester_is_authorized {
    allowed_roles := ["hr_admin", "identity_admin", "manager", "admin"]
    some role in input.caller_roles
    role in allowed_roles
}

requester_can_offboard {
    allowed_offboarders := ["hr_admin", "secops", "identity_admin", "admin"]
    some role in input.caller_roles
    role in allowed_offboarders
}

# Privileged roles require managed device posture and low risk level
is_privileged_role {
    privileged_roles := ["security_engineer", "cloud_admin", "secops", "infrastructure_admin"]
    input.target_role in privileged_roles
}

context_is_compliant {
    is_privileged_role
    input.context.device_trust == "managed"
    input.context.risk_level == "low"
}

context_is_compliant {
    not is_privileged_role
    input.context.device_trust in ["managed", "compliant"]
    input.context.risk_level in ["low", "medium"]
}
