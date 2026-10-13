# DICOM operations runbook

## Start with the boundary

1. Confirm the target address and port from the deployment record.
2. Check the local route and the child-SA selectors.
3. Check the TCP handshake before investigating DICOM negotiation.
4. Capture one association only after the preceding checks pass.

## Symptom guide

| Symptom | Likely boundary | Action |
| --- | --- | --- |
| no route to host | local route or selector | inspect ip route and swanctl --list-sas |
| TCP timeout | firewall or unavailable peer | inspect forward counters and listener state |
| association rejected | AE title or called title | compare both titles with the registry |
| echo succeeds, store stalls | MTU or downstream PACS | run DF ping and inspect router logs |
| router returns 0xC000 | PACS association unavailable | verify PACS address, port, and route |
| router returns 0xA700 | PACS rejected dataset | inspect SOP class, transfer syntax, and PACS log |

Do not disable the firewall or authorization checks to make a transfer pass. Capture the failing association, preserve timestamps, and change one boundary at a time.

