# Network and VPN specification

## Address plan

| Segment | CIDR | Gateway |
| --- | --- | --- |
| Remote clinical LAN | 10.100.10.0/24 | 10.100.10.1 |
| Underlay transit | 198.51.100.0/24 | 198.51.100.254 |
| Central data center LAN | 10.200.20.0/24 | 10.200.20.1 |

Remote and central peers use IKEv2 with AES-256-GCM, SHA-384 PRF, and elliptic-curve or MODP-3072 key exchange. The profiles include rekeying and dead-peer detection. The PSK is not stored in this repository; the container entrypoint reads VPN_PSK and creates the runtime credential with restrictive permissions.

## Traffic selectors

    remote local_ts:   10.100.10.0/24
    remote remote_ts:  10.200.20.0/24
    central local_ts:  10.200.20.0/24
    central remote_ts: 10.100.10.0/24

Permitted application paths are DICOM TCP 11112 to the central ingress router, DICOM TCP 4242 to PACS, DICOMweb TCP 8042 where explicitly required, and ICMP for reachability monitoring. The firewall policy denies other forwarded traffic.

## Operating requirements

- Keep the VPN credential in a secret manager or an equivalent protected runtime environment.
- Confirm both peers use the same selectors and proposals before enabling traffic.
- Test the path MTU with the DF bit set after every underlay change.
- Monitor IKE and child-SA age, rekeys, packet counters, and retransmits.
- Review logs for unexpected source addresses and AE titles.

