# DICOM Imaging Connectivity and Secure VPN Integration

A two-site imaging integration lab that pairs DICOM storage and forwarding with an IPsec VPN network design.

## Sample output

Output excerpt from `python scripts/run_local_demo.py` using Python 3.11. This checks the loopback DICOM path.

```text
PASS: registered calling AE receives C-ECHO success
PASS: forward 3 CT instances and verify receiver identifiers
PASS: reject unregistered AE C-ECHO and C-STORE without forwarding
```

## Integration problem

Remote imaging systems need to deliver studies to a central PACS without exposing imaging services to an untrusted network. A TCP connection alone does not establish that the calling application entity is permitted, the transfer syntax is supported, or PACS has accepted the instance. This project separates those checks so a failed transfer can be traced to the network, DICOM ingress, or storage boundary.

## Architecture and data flow

```text
Remote modality          Remote VPN       Central VPN       DICOM ingress       Orthanc PACS
CT_SCANNER_01 ----------> strongSwan ======> strongSwan -----> CENTRAL_ROUTER ----> CENTRAL_PACS
10.100.10.21              198.51.100.2       198.51.100.1       :11112               :4242
                         IKEv2 / IPsec ESP
```

Five Docker service definitions represent a simulated modality, two strongSwan gateways, a Python ingress router, and Orthanc. The router handles C-ECHO and C-STORE, checks calling AE titles, and forwards datasets over a separate association. It returns a failure status if the downstream association or store fails.

The network reference includes traffic selectors, IKE/ESP proposals, iptables and nftables policies, and TCP MSS settings. These are lab configurations. `10.100.10.0/24` and `10.200.20.0/24` are Docker LANs; `198.51.100.0/24` is an example transit network, not a real site address.

Orthanc's Lua policy attempts to forward every stored instance to `CORP_VNA`. Descriptions containing STAT, TRAUMA, STROKE, or EMERGENCY also go to `RAD_DESK_01`. These destinations are configuration examples and are not started by Compose. The CSV routing table is a design reference; the Python router does not read it.

## Components and standards

| Component | Purpose |
| --- | --- |
| `docker/central-router/router.py` | DICOM ingress and downstream status handling |
| `config/dicom/` | PACS settings, AE registry, Lua forwarding, and reference routing table |
| `config/vpn/` and `config/firewall/` | VPN and network policy examples |
| `scripts/dicom_verification_client.py` | C-ECHO, single and batch C-STORE, and C-FIND client |
| `scripts/generate_synthetic_dicom.py` | Synthetic CT, MR, and CR file creation |
| `scripts/network_preflight_check.py` | ICMP, path-MTU, TCP, and local strongSwan checks |
| `scripts/master_test_runner.py` | Deployment checks and an execution report |
| `diagrams/` and `config/wireshark/` | Protocol diagrams and packet-analysis references |

The implementation uses Python 3.11, pydicom, pynetdicom, Orthanc, strongSwan, Docker Compose, and Linux networking tools. Standards represented in the code and configuration include DICOM Part 10, DIMSE over TCP, CT/MR/CR Storage SOP classes, Explicit VR Little Endian, IKEv2, and IPsec ESP. DCMTK configuration is provided as a reference.

## Quickstart: run the DICOM path locally

From this repository's root, with Python 3.11 or later:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/run_local_demo.py
```

The demo starts the actual ingress handlers and a temporary storage SCP on loopback. It checks C-ECHO, forwards the three included CT instances, verifies their SOP instance identifiers at the receiver, and checks an unregistered calling AE. Both listeners shut down when finished. This exercises DICOM transport and forwarding; it does not establish a VPN or run Orthanc.

Create additional synthetic files without changing the checked-in samples:

```bash
python scripts/generate_synthetic_dicom.py --output-dir generated_studies --modality CT --slices 3
python scripts/dicom_verification_client.py --help
```

NumPy is optional for the generator's geometric pixel pattern. The generator also has a standard-library binary writer when pydicom is unavailable.

## Explore the VPN deployment reference

The container lab requires Docker Compose and Linux kernel support for IPsec and privileged networking. Supply a local-only key before starting it:

```bash
read -r -s -p "Lab VPN pre-shared key: " VPN_PSK
export VPN_PSK
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
```

The gateways write the supplied key to runtime files with restrictive permissions. No key is committed. Orthanc's host ports are bound to loopback. Network checks require routes to the lab subnets; Docker Desktop does not generally expose container addresses directly to the host.

Read the [architecture](docs/01_ARCHITECTURE_AND_DESIGN.md), [VPN specification](docs/02_NETWORK_AND_VPN_SPECIFICATION.md), [DICOM guide](docs/03_DICOM_INTEGRATION_GUIDE.md), and [validation matrix](docs/04_TEST_PROCEDURES_AND_VALIDATION_MATRIX.md). The [troubleshooting runbook](docs/05_TROUBLESHOOTING_RUNBOOK_AND_DECISION_TREES.md) and [handoff procedure](docs/06_POST_IMPLEMENTATION_HANDOFF_AND_SOP.md) describe operational checks.

## Sample data

`sample_studies/` contains three synthetic CT instances with `SYNTHETIC^CT^PATIENT` and `SIM-CT-99401` identifiers and programmatically created pixel data. They contain no patient data. These are transport fixtures, not diagnostic images or proof of complete modality IOD conformance. Keep real imaging data, runtime exports, and captures outside source control.

## Honest Scope and Limitations

- This is an integration reference and local DICOM demonstration. It does not claim a clinical deployment, measured business outcome, or regulatory certification.
- The full Docker VPN path has not been validated here. Gateway scripts combine `ipsec` and `swanctl` configuration paths, generated swanctl secrets are not included by the supplied profiles, firewall rules assume interface names, and central services do not apply their `DEFAULT_GATEWAY` variables. Review these boundaries on a Linux lab host before expecting end-to-end VPN delivery.
- AE-title checks are an application allowlist, not cryptographic identity verification. VPN profiles use a runtime PSK; certificate provisioning and key rotation are outside the implementation.
- The ingress router supports C-ECHO and C-STORE. C-FIND is available in the client for a compatible PACS, but the router has no query/retrieve handler. C-MOVE, RIS workflows, and modality worklist are not implemented.
- VNA/radiology fan-out, CSV compression actions, durable ingress retries, high availability, and production monitoring are not demonstrated by the local demo.
- The deployment test runner covers a subset of the validation matrix. A skipped or unavailable strongSwan check is not evidence that a tunnel is established.

## Author and license

Naveen Madhav | [LinkedIn](https://linkedin.com/in/naveenmadhav)

Licensed under the [MIT License](LICENSE).

**AI assistance:** I defined the project concept, requirements, and validation rule priorities based on my healthcare integration experience. AI coding assistants helped with planning, design exploration, implementation, debugging, testing, and documentation. I take responsibility for reviewing the project, checking its claims, and deciding what to submit.
