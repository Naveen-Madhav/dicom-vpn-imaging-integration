# DICOM handoff and operating procedure

## Before activation

- Confirm peer identities, certificate or PSK ownership, traffic selectors, and change approval.
- Confirm the AE registry, routing destinations, storage capacity, and retention policy.
- Verify that management ports are reachable only from the approved administration network.
- Run the validation matrix and attach the results to the change record.

## Daily checks

Review IKE and child-SA state, Orthanc health, storage utilization, failed C-STORE counts, and routing destinations. Alert on repeated association rejection, store failure, or unexpected calling AE titles.

## Incident handling

Record the UTC timestamp, source AE title, destination, SOP instance UID, and the first failing boundary. Preserve gateway, router, and PACS logs before restarting a service. If the path is unavailable, leave the instance at the source modality or use the approved store-and-forward process; do not copy patient data into ad hoc locations.

## Recovery

After restoring a gateway or PACS, verify the tunnel, C-ECHO, one representative C-STORE, and destination fan-out. Reconcile any queued instances against the PACS index before closing the incident.
