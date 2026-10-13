# DICOM/IPsec architecture

## Scope

The deployment connects a remote imaging subnet (10.100.10.0/24) to a central data-center subnet (10.200.20.0/24). DICOM traffic is carried through an IKEv2 tunnel between 198.51.100.2 and 198.51.100.1.

## Request path

    CT_SCANNER_01 -> remote gateway -> IPsec child SA -> central gateway
    -> CENTRAL_ROUTER:11112 -> CENTRAL_PACS:4242

The ingress router is the application authorization boundary. It accepts only registered calling AE titles, supports C-ECHO and C-STORE, and returns a failure status when PACS cannot accept an instance. The PACS configuration maintains the modality registry and forwards stored instances to the radiology workstation and VNA according to the routing policy.

## Network controls

- The gateways route only the two declared private subnets through the child SA.
- IKE uses UDP 500; NAT-T uses UDP 4500; ESP is permitted when the underlay is not translating.
- Firewall forward rules constrain source subnet, destination address, protocol, and port.
- TCP MSS is clamped to 1360 bytes on tunnel-bound SYN packets.
- Host-side management access is not part of the tunnel policy.

## Failure boundaries

| Boundary | Observable failure | Evidence |
| --- | --- | --- |
| Underlay | no IKE or TCP handshake | gateway and firewall counters |
| Child SA | route exists but protected traffic drops | swanctl --list-sas, policy counters |
| Ingress authorization | association or store rejected | router log and DICOM status |
| PACS forwarding | ingress accepts but downstream store fails | router status and PACS logs |
| MTU | echo works while large stores stall | DF ping and packet capture |

The design is suitable for a contained deployment reference. A real installation still needs certificate-based peer authentication, monitored storage capacity, centralized logs, and an approved change process.

