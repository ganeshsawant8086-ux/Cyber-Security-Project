// Identity Lifecycle & Access Orchestration Platform Frontend Logic

let currentToken = "";
let currentPersona = "alice_hr";

const PERSONAS = {
  alice_hr: {
    subject: "usr-alice-hr",
    email: "alice.hr@example.com",
    roles: ["hr_admin"],
    department: "Human Resources",
  },
  bob_identity: {
    subject: "usr-bob-secops",
    email: "bob.secops@example.com",
    roles: ["identity_admin", "secops"],
    department: "Cloud Security",
  },
  charlie_contractor: {
    subject: "usr-charlie-contractor",
    email: "charlie.contractor@example.com",
    roles: ["contractor", "engineer"],
    department: "External Contractors",
  },
  eve_engineer: {
    subject: "usr-eve-eng",
    email: "eve.eng@example.com",
    roles: ["engineer"],
    department: "Engineering",
  },
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  await checkHealth();
  await switchPersona();
  await loadAuditLogs();
});

// Tab Switcher
function showTab(tabName) {
  document.querySelectorAll(".tab-panel").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach((el) => el.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${tabName}`);
  if (targetTab) targetTab.classList.add("active");

  const btnIndex = {
    lifecycle: 0,
    policy: 1,
    anomalies: 2,
    audit: 3,
    tokens: 4,
    apidocs: 5,
  }[tabName];

  const btns = document.querySelectorAll(".tab-btn");
  if (btns[btnIndex]) btns[btnIndex].classList.add("active");

  if (tabName === "audit") {
    loadAuditLogs();
  }
}

// Check Health & Readiness
async function checkHealth() {
  try {
    const res = await fetch("/readyz");
    const data = await res.json();
    const pill = document.getElementById("system-status-pill");
    const text = document.getElementById("system-status-text");

    if (data.status === "READY") {
      pill.style.background = "rgba(16, 185, 129, 0.15)";
      pill.style.color = "#34d399";
      text.innerText = "System Active (All Probes Ready)";
    } else {
      pill.style.background = "rgba(245, 158, 11, 0.15)";
      pill.style.color = "#fbbf24";
      text.innerText = "Degraded State";
    }
  } catch (e) {
    document.getElementById("system-status-text").innerText = "Server Offline";
  }
}

// Switch Persona & Mint JWT
async function switchPersona() {
  const select = document.getElementById("persona-select");
  currentPersona = select.value;
  const config = PERSONAS[currentPersona];

  try {
    const res = await fetch("/api/v1/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await res.json();
    currentToken = data.access_token;

    // Update active token view
    document.getElementById("active-token-view").textContent = JSON.stringify(
      {
        active_persona: currentPersona,
        email: config.email,
        assigned_roles: config.roles,
        department: config.department,
        token_type: data.token_type,
        issuer: data.issuer,
        audience: data.audience,
        expires_in_seconds: data.expires_in,
        access_token_preview: currentToken.substring(0, 32) + "...[REDACTED]",
      },
      null,
      2
    );
  } catch (err) {
    console.error("Failed to mint token:", err);
  }
}

// Submit Lifecycle Ticket
async function submitLifecycleTicket(event) {
  event.preventDefault();
  const resultView = document.getElementById("lifecycle-result-view");
  resultView.textContent = "Ingesting ticket, evaluating OPA policies, and dispatching Pub/Sub events...";

  const ticketType = document.getElementById("ticket-type").value;
  const ticketId = document.getElementById("ticket-id").value;
  const targetEmail = document.getElementById("target-email").value;
  const targetRole = document.getElementById("target-role").value;
  const deviceTrust = document.getElementById("device-trust").value;
  const riskLevel = document.getElementById("risk-level").value;

  const payload = {
    ticket_id: ticketId,
    request_type: ticketType,
    requester_email: PERSONAS[currentPersona].email,
    target_user_email: targetEmail,
    target_user_full_name: targetEmail.split("@")[0].replace(".", " ").toUpperCase(),
    department: "Cloud Engineering",
    target_role: targetRole,
    justification: `Automated lifecycle submission for ${ticketType} operation`,
    requested_entitlements: [
      `cloud_iam:${targetRole}-admin`,
      "google_workspace:corp-team",
      "slack:engineering",
    ],
    context: {
      device_trust: deviceTrust,
      risk_level: riskLevel,
      ip_address: "192.168.1.100",
    },
  };

  try {
    const res = await fetch("/api/v1/lifecycle/request", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
        "X-Correlation-ID": `corr-web-${Date.now()}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    resultView.textContent = JSON.stringify(data, null, 2);
    // Refresh audit trail after ticket
    loadAuditLogs();
  } catch (err) {
    resultView.textContent = `Error: ${err.message}`;
  }
}

// Presets for Policy Evaluation
function loadPolicyPreset(preset) {
  if (preset === "contractor_kms") {
    document.getElementById("pol-subject-role").value = "contractor";
    document.getElementById("pol-action").value = "read";
    document.getElementById("pol-res-type").value = "cloud_infra";
    document.getElementById("pol-res-sens").value = "critical";
    document.getElementById("pol-device-trust").value = "managed";
    document.getElementById("pol-risk-level").value = "low";
  } else if (preset === "untrusted_admin") {
    document.getElementById("pol-subject-role").value = "security_engineer";
    document.getElementById("pol-action").value = "write";
    document.getElementById("pol-res-type").value = "cloud_infra";
    document.getElementById("pol-res-sens").value = "high";
    document.getElementById("pol-device-trust").value = "untrusted";
    document.getElementById("pol-risk-level").value = "low";
  } else if (preset === "secops_prod") {
    document.getElementById("pol-subject-role").value = "security_engineer";
    document.getElementById("pol-action").value = "read";
    document.getElementById("pol-res-type").value = "cloud_infra";
    document.getElementById("pol-res-sens").value = "critical";
    document.getElementById("pol-device-trust").value = "managed";
    document.getElementById("pol-risk-level").value = "low";
  }
}

// Evaluate OPA Policy
async function evaluatePolicy(event) {
  event.preventDefault();
  const resultView = document.getElementById("policy-result-view");
  resultView.textContent = "Querying Open Policy Agent (OPA)...";

  const payload = {
    subject: {
      id: "usr-evaluator-1",
      email: PERSONAS[currentPersona].email,
      roles: document.getElementById("pol-subject-role").value.split(",").map((s) => s.trim()),
      department: "Engineering",
    },
    action: document.getElementById("pol-action").value,
    resource: {
      type: document.getElementById("pol-res-type").value,
      name: "target-resource-id",
      sensitivity: document.getElementById("pol-res-sens").value,
    },
    context: {
      device_trust: document.getElementById("pol-device-trust").value,
      risk_level: document.getElementById("pol-risk-level").value,
    },
  };

  try {
    const res = await fetch("/api/v1/policies/evaluate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    resultView.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultView.textContent = `Error: ${err.message}`;
  }
}

// Simulate Anomaly
async function simulateAnomaly(anomalyType) {
  const resultView = document.getElementById("anomaly-result-view");
  resultView.textContent = `Simulating threat scenario: ${anomalyType}...`;

  const payload = {
    anomaly_type: anomalyType,
    target_user_email: "eve.compromised@example.com",
    simulated_context: {
      device_trust: "untrusted",
      risk_level: "critical",
      origin_geo: "TOR_EXIT_NODE_BUCHAREST",
    },
  };

  try {
    const res = await fetch("/api/v1/anomalies/simulate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    resultView.textContent = JSON.stringify(data, null, 2);
    loadAuditLogs();
  } catch (err) {
    resultView.textContent = `Error: ${err.message}`;
  }
}

// Load Audit Logs
async function loadAuditLogs() {
  const tbody = document.getElementById("audit-tbody");
  tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Fetching immutable audit trail...</td></tr>`;

  try {
    const res = await fetch("/api/v1/audit?limit=25", {
      headers: { Authorization: `Bearer ${currentToken}` },
    });
    const logs = await res.json();

    if (!logs.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No audit records found yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs
      .map((item) => {
        const badgeClass =
          item.status === "SUCCESS"
            ? "badge-success"
            : item.status === "ALERT"
            ? "badge-danger"
            : "badge-warning";

        const time = new Date(item.timestamp).toLocaleTimeString();
        return `
        <tr>
          <td><span style="color: var(--text-dim); font-size: 0.78rem;">${time}</span></td>
          <td><strong style="color: var(--cyan);">${item.actor}</strong></td>
          <td><code>${item.action}</code></td>
          <td><span style="color: var(--text-muted);">${item.resource_type}:${item.resource_id}</span></td>
          <td><span class="badge ${badgeClass}">${item.status}</span></td>
          <td><code style="font-size: 0.76rem; color: var(--text-dim);">${item.correlation_id}</code></td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: #ef4444; text-align: center;">Error fetching audit logs: ${err.message}</td></tr>`;
  }
}

// Mint Custom Token
async function mintCustomToken(event) {
  event.preventDefault();
  const subject = document.getElementById("custom-subject").value;
  const email = document.getElementById("custom-email").value;
  const roles = document
    .getElementById("custom-roles")
    .value.split(",")
    .map((s) => s.trim());

  const res = await fetch("/api/v1/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject, email, roles }),
  });
  const data = await res.json();

  const preview = document.getElementById("minted-token-view");
  preview.style.display = "block";
  preview.textContent = JSON.stringify(data, null, 2);
}
