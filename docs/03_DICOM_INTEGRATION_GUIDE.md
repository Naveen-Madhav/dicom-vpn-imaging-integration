# DICOM integration guide

## Application entities

| AE title | Address | Port | Role |
| --- | --- | --- | --- |
| CT_SCANNER_01 | 10.100.10.21 | 11112 | remote modality |
| CENTRAL_ROUTER | 10.200.20.10 | 11112 | authorized ingress |
| CENTRAL_PACS | 10.200.20.50 | 4242 | storage SCP |

The router accepts calling AE titles from its AUTHORIZED_CALLING_AETS environment variable. The same title must be registered in the PACS modality table when direct PACS associations are allowed.

## DIMSE behavior

- C-ECHO verifies association negotiation and authorization.
- C-STORE forwards the received dataset over a separate association to PACS.
- A failed downstream association returns 0xC000; a failed downstream store returns 0xA700.
- The client releases associations after each operation and reports transfer timing.
- Batch transfers reuse one association and return failure when any instance is rejected.

## Dataset requirements

Stored instances require Patient ID, SOP Class UID, SOP Instance UID, modality, and a valid file meta header. The included datasets contain synthetic identifiers and must not be replaced with production patient data in source control. Orthanc rejects unknown SOP classes and keeps storage synchronous for an unambiguous C-STORE result.

## Routing

Orthanc sends studies containing STAT, TRAUMA, STROKE, or EMERGENCY in the study description to RAD_DESK_01. Every stored instance is also sent to CORP_VNA. Review the Lua routing script and CSV policy together when changing destinations.

