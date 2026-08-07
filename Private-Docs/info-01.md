###########################################################
######################## **Section 1** ###################
##########################################################


Here is a comprehensive blueprint to engineer this into an open-source, enterprise-grade tool (e.g., **`EWS-Gateway`** or **`msgate`**).

---

## 1. Core Functionality & Capabilities

### Exchange & Protocol Support

* **Dual Backend Support:**
* **EWS (Exchange Web Services):** NTLM, Basic Auth, and Kerberos for on-premises Exchange (2013–2019).
* **Microsoft Graph API (Modern Auth):** OAuth2 Client Credentials flow for Microsoft 365 / Exchange Online environments.


* **Universal SMTP Protocol Translation:**
* Handles legacy and modern client auth formats seamlessly (`AUTH PLAIN`, `AUTH LOGIN`, `CRAM-MD5`, or Anonymous IP-whitelisted relaying).
* **Smart Auth Sanitizer:** Automatically cleans domain prefixes (e.g., handles `DOMAIN\user`, `user@domain`, or plain `user`) and normalizes auth payloads before passing them to Exchange.



### Resilience & Reliability

* **Asynchronous Queue & Retry Engine:**
* If Exchange EWS/Graph drops or rate-limits requests (e.g., HTTP 429/503), the gateway buffers messages in a local SQLite database and retries with exponential backoff instead of dropping alerts from Zabbix or monitoring services.


* **Smart Failure Fallback:**
* Define secondary SMTP/Exchange endpoints for failover.



### Diagnostics & Monitoring

* **Outbound Webhooks:**
* Send instant alerts to Slack, Discord, Microsoft Teams, or Zabbix if the Exchange connection fails or authentication errors spike.


* **Prometheus Metrics Endpoint (`/metrics`):**
* Expose real-time metrics for total processed emails, delivery latencies, authentication failures, and active SMTP connections.



---

## 2. Web UI & Visualization

### Look & Feel

* **Aesthetic:** Clean, dark-mode-first dashboard inspired by modern tools like Portainer, Nginx Proxy Manager, and Mailpit.
* **Layout:**
* **Sidebar:** Overview, Live Traffic, Message Logs, Relay Rules, Settings, System Health.
* **Header:** Quick status badges (EWS Status: *Healthy*, SMTP Port: *1025*, Queue: *0 pending*).



```
+-----------------------------------------------------------------------------------+
|  msgate Gateway | EWS: Connected (18ms) | SMTP: Port 1025 | Queue: 0  | [Dark] |
+-----------------------------------------------------------------------------------+
| [Sidebar]  |  [Dashboard Overview]                                                |
| - Stats    |  +-------------------+ +-------------------+ +--------------------+  |
| - Live Logs|  | Sent Today        | | Avg Latency       | | EWS Auth Errors    |  |
| - Inspector|  | 1,248             | | 142ms             | | 0 (Last 24h)     |  |
| - Testing  |  +-------------------+ +-------------------+ +--------------------+  |
| - Settings |                                                                      |
|            |  [Real-Time Traffic Stream] (WebSockets)                             |
|            |  15:02:11 [SMTP] CONNECT 127.0.0.1:48291                             |
|            |  15:02:11 [SMTP] AUTH PLAIN (Decoded: internal.wdc -> OK)           |
|            |  15:02:12 [EWS]  200 OK - Message Queued for Delivery (ID: 0x82A1)    |
+-----------------------------------------------------------------------------------+

```

### Interactive UI Tools

* **Live Protocol Inspector (WebSocket Stream):**
* Real-time terminal-style viewer showing active SMTP commands, decoded auth attempts, and exact raw EWS response XML/JSON payloads.


* **Built-in Diagnostic Test Suite:**
* **"Send Test Email" Wizard:** Form to test full end-to-end delivery with custom From/To/Subject/Body.
* **"Auth Simulator":** Input raw `AUTH PLAIN` or `AUTH LOGIN` base64 payloads to verify how the gateway parses and sanitizes credentials before hitting Exchange.


* **Interactive EWS Connection Validator:**
* One-click "Check Exchange Health" button that performs an `Autodiscover` or `GetFolder` call to verify credentials and SSL certificates instantly.



---

## 3. Technology Stack & Architecture

| Layer | Recommended Technology | Why it Fits |
| --- | --- | --- |
| **Language** | Python 3.11+ | Modern async features, native typing, lightweight deployment. |
| **SMTP Server** | `aiosmtpd` | Asynchronous, high-performance Python SMTP server daemon. |
| **Web Backend** | **FastAPI** | High-speed REST API & native WebSocket support for live log streaming. |
| **Frontend** | **HTMX + Alpine.js + Tailwind CSS** | Lightweight, responsive UI bundled directly inside the Python package with zero external Node/NPM build overhead at runtime. |
| **Exchange Client** | `exchangelib` (EWS) & `MSAL` (Graph) | Proven, robust libraries for handling NTLM/EWS XML and OAuth2 tokens. |
| **Storage & Queue** | **SQLite (WAL Mode)** | Zero-dependency, file-based persistence for storing settings, logs, and email retries. |

---

## 4. Installation & OS Compatibility

To make the tool simple to deploy across diverse server environments, support three primary distribution formats:

### Method A: Single-Line Systemd Installer (Linux Native)

A clean shell script that sets up a dedicated system user, isolated Python virtual environment, systemd unit file, and firewall rules:

```bash
curl -sSL https://raw.githubusercontent.com/your-org/msgate/main/install.sh | sudo bash

```

### Method B: Containerized (Docker & Docker Compose)

Provide pre-built multi-arch Docker images (`linux/amd64`, `linux/arm64`) hosted on GitHub Container Registry (GHCR):

```yaml
version: '3.8'
services:
  msgate:
    image: ghcr.io/your-username/msgate:latest
    container_name: msgate
    restart: unless-stopped
    ports:
      - "1025:1025"   # SMTP Port
      - "8080:8080"   # Web UI & REST API
    volumes:
      - ./data:/app/data
    environment:
      - MSGATE_EWS_URL=https://datacenter.wigner.mta.hu/EWS/Exchange.asmx

```

### Method C: Single-File Executable (PyInstaller)

* Compile the entire app (Python interpreter + dependencies + web UI assets) into a single executable binary (`msgate-linux-amd64`).
* Zero dependencies required on the target machine (no Python or `pip` needed).

---

## 5. Lifecycle Management & Production Readiness

### OS Update & Dependency Isolation

* **Virtual Environment / Binary Containment:** Python packages are completely isolated from system libraries (preventing breakage during OS upgrades like Debian 12 to 13 or Ubuntu updates).
* **Automated Data Migrations:** Built-in schema migration engine (via Alembic) that automatically upgrades the SQLite database when updating to newer app versions.

### Maintenance & Operations

* **Zero-Downtime Configuration Reloads:** Modifying settings in the Web UI triggers a hot-reload of EWS configurations without restarting the listening SMTP socket or dropping active client connections.
* **Encrypted Backups:** One-click JSON import/export of configuration settings, with sensitive Exchange passwords encrypted using AES-256 (derived from an optional secret key).
* **Automated Log Rotation:** Built-in log retention policy (e.g., keep logs for 7/14/30 days) to prevent disk exhaustion.

---

## Next Steps

To begin building the MVP (Minimum Viable Product):

1. **Phase 1:** Core SMTP-to-EWS proxy engine (`aiosmtpd` + `exchangelib` handling `AUTH PLAIN` cleanly).
2. **Phase 2:** FastAPI REST backend & configuration store.
3. **Phase 3:** Web UI layout & live WebSocket log stream.

###########################################################
######################## **Section 2** ###################
##########################################################
Here is the breakdown of your two points, including a direct assessment of whether this project is worth your time.

---

## 1. Monitoring & High Availability (HA)

### Application-Level Monitoring

**Yes, absolutely.** To make it production-ready for platforms like Zabbix, Nagios, or Datadog, the gateway should implement a standard health API:

* **`GET /healthz` (Liveness):** Returns HTTP `200` if the local SMTP socket and HTTP server are up.
* **`GET /readyz` (Readiness):** Returns HTTP `200` only if the app can successfully communicate with the downstream Exchange/EWS/Graph endpoint and write to its local database.
* **Zabbix Integration:** Zabbix can monitor the app via:
1. **HTTP Agent:** Polling `/healthz` or `/api/v1/status` (returning JSON with queue size, Exchange latency, error rates).
2. **Passive/Active Checks:** A dedicated Zabbix UserParameter or native REST API integration.
3. **Outbound Webhooks:** The app can push alerts *to* Zabbix or Teams/Slack whenever Exchange drops connections or auth fails repeatedly.



### Active-Passive HA Architecture

For enterprise reliability, you can run two nodes (**Node A - Active**, **Node B - Passive**):

* **Network Layer (Virtual IP):** Combine the app with **Keepalived (VRRP)** so a floating Virtual IP points to the active node. If Node A dies, Node B takes over the IP instantly.
* **Application Layer (Leader Election):**
* Both nodes listen for SMTP traffic, but only the Active node processes the outbound queue to Exchange.
* Node state (Active/Passive) is exposed via the API (`/api/v1/ha/status`).
* Database sync can use SQLite WAL over a shared volume or a simple primary/secondary replication hook.



---

## 2. API-First Concept

**Yes, API-First is the gold standard for modern infrastructure tools.**

If you build using **FastAPI**, you get an API-first architecture automatically:

* **Automatic OpenAPI/Swagger Docs:** Interactive documentation generated at `/docs`.
* **Headless Deployment (DevOps Automation):** Infrastructure-as-Code tools (Ansible, Terraform, CI/CD pipelines) can programmatically deploy the gateway, inject EWS/Graph credentials, and rotate passwords without ever clicking through a Web UI.
* **Decoupled Frontend:** The Web UI becomes a single-page app (SPA) or HTMX interface consuming the public REST endpoints.

---

## 3. Is It Really Worth Developing?

**Yes — and here is why it has long-term value, even beyond old Exchange servers.**

### The Problem in Modern Environments

Microsoft has aggressively disabled **Basic Authentication** (username/password over SMTP/EWS) across Microsoft 365 (Exchange Online) and is pushing everything toward **OAuth2 / Graph API**.

However, millions of production applications and hardware devices **cannot speak OAuth2 or Graph API**:

* Legacy ERP systems and custom enterprise software.
* Monitoring tools like Zabbix/Nagios scripts that expect standard SMTP auth.
* Network printers, scanners, and IoT appliances.

### Why This Tool Fills a Critical Market Gap

| Feature / Need | DavMail | Traditional Relays (Postfix) | **Your Modern App** |
| --- | --- | --- | --- |
| **Backend Support** | EWS (Java-heavy) | Standard SMTP only | **EWS + MS Graph API (OAuth2)** |
| **SMTP Auth Handling** | Strict / Fragile (`AUTH PLAIN` bugs) | Standard | **Smart Auth Sanitizer (Auto-cleans domain prefixes)** |
| **Interface & Observability** | Basic desktop GUI / raw logs | CLI / Config files | **Modern Web UI, WebSockets live stream, REST API** |
| **Resource Footprint** | High (Java Runtime) | Low (C) | **Low (Python Async / Dockerized)** |

### Summary

* **For On-Premise Exchange (EWS):** It solves immediate bugs (like DavMail's `AUTH PLAIN` domain parsing failure with Zabbix).
* **For Cloud / M365 (Graph API):** It serves as a **permanent bridge** translating standard SMTP from internal apps into modern Microsoft Graph API calls using OAuth2 Client Credentials.

It bridges legacy protocols to modern cloud APIs, making it a high-value open-source project.

---
###########################################################
######################## **Section 3** ###################
##########################################################

Here is the complete OpenAPI specification and Pydantic v2 data model architecture for **msgate** (our Python EWS/Graph SMTP gateway).

---

## 1. Core Data Models (`schemas.py`)

Defined using **Pydantic v2** for strict validation, settings management, and automated OpenAPI schema generation.

```python
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, EmailStr, ConfigDict
from datetime import datetime


class BackendType(str, Enum):
    EWS = "ews"
    GRAPH = "graph"


class AuthType(str, Enum):
    BASIC = "basic"
    NTLM = "ntlm"
    OAUTH2 = "oauth2"


class MessageStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    RETRAYING = "retrying"


# --- Configuration Models ---

class EWSConfig(BaseModel):
    server_url: HttpUrl = Field(..., example="https://exchange.domain.com/EWS/Exchange.asmx")
    auth_type: AuthType = Field(default=AuthType.NTLM, description="Authentication scheme")
    domain: Optional[str] = Field(default=None, example="WDC", description="Default Windows Domain")
    trust_self_signed: bool = Field(default=False, description="Bypass SSL verification")


class GraphConfig(BaseModel):
    tenant_id: str = Field(..., example="00000000-0000-0000-0000-000000000000")
    client_id: str = Field(..., example="11111111-1111-1111-1111-111111111111")
    client_secret: str = Field(..., description="Application Secret Value")
    scopes: List[str] = Field(default=["https://graph.microsoft.com/.default"])


class SMTPConfig(BaseModel):
    bind_address: str = Field(default="127.0.0.1", example="0.0.0.0")
    port: int = Field(default=1025, ge=1, le=65535)
    max_message_size_mb: int = Field(default=25, ge=1, le=100)
    allowed_ips: List[str] = Field(default=["127.0.0.1"], description="Whitelisted CIDR ranges for relaying")


class GatewayConfig(BaseModel):
    backend: BackendType = Field(default=BackendType.EWS)
    smtp: SMTPConfig
    ews: Optional[EWSConfig] = None
    graph: Optional[GraphConfig] = None
    default_sender: Optional[EmailStr] = Field(default=None, example="gateway@domain.com")
    
    model_config = ConfigDict(use_enum_values=True)


# --- Live Inspector & Message Tracking Models ---

class EmailMessageRequest(BaseModel):
    sender: EmailStr = Field(..., example="zabbix@domain.com")
    recipients: List[EmailStr] = Field(..., example=["admin@domain.com"])
    subject: str = Field(..., example="[PROBLEM] High CPU utilization")
    body: str = Field(..., example="CPU load exceeded 95% on server01")
    is_html: bool = Field(default=False)


class MessageRecord(BaseModel):
    id: str = Field(..., example="msg_984a1b2c")
    client_ip: str = Field(..., example="127.0.0.1")
    raw_auth_user: str = Field(..., example="WDC\\internal.wdc")
    sanitized_user: str = Field(..., example="internal.wdc")
    sender: EmailStr
    recipients: List[EmailStr]
    subject: str
    status: MessageStatus
    attempts: int = Field(default=0)
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- Health & Metrics Models ---

class HealthStatus(BaseModel):
    status: str = Field(..., example="healthy")
    smtp_server: bool = Field(..., example=True)
    exchange_backend: bool = Field(..., example=True)
    backend_latency_ms: float = Field(..., example=42.5)
    queue_pending: int = Field(..., example=0)


class HAModeStatus(BaseModel):
    node_id: str = Field(..., example="node-01")
    role: str = Field(..., example="active", description="'active' or 'passive'")
    vrrp_state: str = Field(..., example="MASTER")
    leader_node: str = Field(..., example="node-01")

```

---

## 2. API Endpoint Matrix

| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/healthz` | `GET` | Liveness | Basic HTTP process & socket status check |
| `/readyz` | `GET` | Readiness | Deep check verifying EWS/Graph connectivity |
| `/api/v1/config` | `GET` / `PUT` | System | Fetch or update runtime gateway settings |
| `/api/v1/queue` | `GET` | Management | List queued, retrying, or failed messages |
| `/api/v1/messages/test` | `POST` | Diagnostics | Send a test email directly via the API |
| `/api/v1/ha/status` | `GET` | HA Clustering | Get Active/Passive state and VRRP metadata |
| `/metrics` | `GET` | Monitoring | Prometheus-formatted metric exports |

---

## 3. OpenAPI 3.1 Specification (`openapi.yaml`)

```yaml
openapi: 3.1.0
info:
  title: msgate - EWS/Graph SMTP Gateway API
  description: High-availability REST API for managing, monitoring, and debugging the msgate SMTP Proxy.
  version: 1.0.0
paths:
  /healthz:
    get:
      summary: Liveness Probe
      operationId: getLiveness
      responses:
        '200':
          description: Service is running.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: { type: string, example: "ok" }

  /readyz:
    get:
      summary: Readiness Probe
      operationId: getReadiness
      responses:
        '200':
          description: Backend Exchange connection is healthy.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'
        '503':
          description: Exchange backend unreachable or degraded.

  /api/v1/config:
    get:
      summary: Get Gateway Configuration
      operationId: getConfig
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GatewayConfig'
    put:
      summary: Update Gateway Configuration
      operationId: updateConfig
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GatewayConfig'
      responses:
        '200':
          description: Configuration updated and reloaded.

  /api/v1/queue:
    get:
      summary: List Outbound Message Queue
      operationId: getQueue
      parameters:
        - name: status
          in: query
          required: false
          schema:
            type: string
            enum: [queued, retrying, failed, sent]
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/MessageRecord'

  /api/v1/messages/test:
    post:
      summary: Send Diagnostic Email
      operationId: sendTestEmail
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EmailMessageRequest'
      responses:
        '200':
          description: Message accepted and dispatched.
          content:
            application/json:
              schema:
                type: object
                properties:
                  message_id: { type: string, example: "msg_984a1b2c" }
                  status: { type: string, example: "sent" }

  /api/v1/ha/status:
    get:
      summary: Get Active/Passive HA Cluster Status
      operationId: getHAStatus
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HAModeStatus'

  /metrics:
    get:
      summary: Prometheus Metrics Endpoint
      operationId: getMetrics
      responses:
        '200':
          description: Prometheus formatted metric text output.
          content:
            text/plain:
              example: |
                # HELP msgate_processed_emails_total Total emails processed
                # TYPE msgate_processed_emails_total counter
                msgate_processed_emails_total{backend="ews",status="sent"} 1420
                msgate_processed_emails_total{backend="ews",status="failed"} 0

```



###########################################################
######################## **Section 4** ###################
##########################################################
