package identity.lifecycle_test

import future.keywords.in
import data.identity.lifecycle

test_onboard_allowed_for_hr_admin_with_managed_device {
    input := {
        "request_type": "ONBOARD",
        "caller_roles": ["hr_admin"],
        "target_role": "security_engineer",
        "context": {
            "device_trust": "managed",
            "risk_level": "low"
        }
    }
    lifecycle.allow with input as input
}

test_onboard_denied_for_privileged_role_with_high_risk {
    input := {
        "request_type": "ONBOARD",
        "caller_roles": ["hr_admin"],
        "target_role": "security_engineer",
        "context": {
            "device_trust": "managed",
            "risk_level": "high"
        }
    }
    not lifecycle.allow with input as input
}

test_onboard_denied_for_unauthorized_requester {
    input := {
        "request_type": "ONBOARD",
        "caller_roles": ["intern"],
        "target_role": "engineer",
        "context": {
            "device_trust": "managed",
            "risk_level": "low"
        }
    }
    not lifecycle.allow with input as input
}

test_role_change_allowed_for_identity_admin {
    input := {
        "request_type": "ROLE_CHANGE",
        "caller_roles": ["identity_admin"],
        "target_role": "cloud_admin",
        "context": {
            "device_trust": "managed",
            "risk_level": "low"
        }
    }
    lifecycle.allow with input as input
}

test_role_change_denied_for_standard_manager {
    input := {
        "request_type": "ROLE_CHANGE",
        "caller_roles": ["manager"],
        "target_role": "cloud_admin",
        "context": {
            "device_trust": "managed",
            "risk_level": "low"
        }
    }
    not lifecycle.allow with input as input
}

test_offboard_allowed_for_secops {
    input := {
        "request_type": "OFFBOARD",
        "caller_roles": ["secops"],
        "target_role": "any",
        "context": {
            "device_trust": "untrusted",
            "risk_level": "high"
        }
    }
    lifecycle.allow with input as input
}
