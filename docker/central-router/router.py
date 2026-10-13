#!/usr/bin/env python3
"""DICOM ingress service with AE-title authorization and PACS forwarding."""

from __future__ import annotations

import logging
import os
from typing import Set

from pydicom.dataset import Dataset
from pynetdicom import AE, StoragePresentationContexts, VerificationPresentationContexts, evt

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("dicom-ingress")

ROUTER_AET = os.getenv("ROUTER_AET", "CENTRAL_ROUTER")
ROUTER_PORT = int(os.getenv("ROUTER_PORT", "11112"))
DOWNSTREAM_AET = os.getenv("DOWNSTREAM_PACS_AET", "CENTRAL_PACS")
DOWNSTREAM_HOST = os.getenv("DOWNSTREAM_PACS_IP", "10.200.20.50")
DOWNSTREAM_PORT = int(os.getenv("DOWNSTREAM_PACS_PORT", "4242"))
AUTHORIZED_AETS: Set[str] = {
    value.strip()
    for value in os.getenv(
        "AUTHORIZED_CALLING_AETS",
        "CT_SCANNER_01,MR_SCANNER_01,XR_ROOM_01,EDGE_DICOM_GW,RAD_DESK_01",
    ).split(",")
    if value.strip()
}


def is_authorized(event: evt.Event) -> bool:
    calling_aet = event.assoc.requestor.ae_title.strip()
    if calling_aet not in AUTHORIZED_AETS:
        logger.warning("Rejected operation from unauthorized AE title %s", calling_aet)
        return False
    return True


def handle_echo(event: evt.Event) -> int:
    return 0x0000 if is_authorized(event) else 0xC000


def handle_store(event: evt.Event) -> int:
    if not is_authorized(event):
        return 0xC000

    dataset: Dataset = event.dataset
    dataset.file_meta = event.file_meta
    sop_instance_uid = getattr(dataset, "SOPInstanceUID", "unknown")
    logger.info(
        "C-STORE from %s modality=%s sop_instance=%s",
        event.assoc.requestor.ae_title.strip(),
        getattr(dataset, "Modality", "unknown"),
        sop_instance_uid,
    )

    forward_ae = AE(ae_title=ROUTER_AET)
    forward_ae.requested_contexts = StoragePresentationContexts
    association = forward_ae.associate(DOWNSTREAM_HOST, DOWNSTREAM_PORT, ae_title=DOWNSTREAM_AET)
    if not association.is_established:
        logger.error("Unable to associate with PACS %s:%d", DOWNSTREAM_HOST, DOWNSTREAM_PORT)
        return 0xC000

    try:
        status = association.send_c_store(dataset)
        if status and status.Status == 0x0000:
            logger.info("Forwarded SOP instance %s to %s", sop_instance_uid, DOWNSTREAM_AET)
            return 0x0000
        logger.error("PACS rejected SOP instance %s with status %s", sop_instance_uid, status)
        return 0xA700
    finally:
        association.release()


def main() -> None:
    logger.info("Starting DICOM ingress on %s:%d", ROUTER_AET, ROUTER_PORT)
    logger.info("PACS destination %s@%s:%d", DOWNSTREAM_AET, DOWNSTREAM_HOST, DOWNSTREAM_PORT)
    ae = AE(ae_title=ROUTER_AET)
    ae.supported_contexts = StoragePresentationContexts + VerificationPresentationContexts
    ae.maximum_pdu_size = 65536
    ae.start_server(
        ("", ROUTER_PORT),
        block=True,
        evt_handlers=[(evt.EVT_C_ECHO, handle_echo), (evt.EVT_C_STORE, handle_store)],
    )


if __name__ == "__main__":
    main()
