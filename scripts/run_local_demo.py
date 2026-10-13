#!/usr/bin/env python3
"""Exercise DICOM ingress and forwarding on loopback with synthetic CT fixtures."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pydicom
from pynetdicom import AE, StoragePresentationContexts, VerificationPresentationContexts, evt


def run() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("dicom_ingress", root / "docker/central-router/router.py")
    router = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(router)
    received = []

    def receive_store(event):
        received.append(str(event.dataset.SOPInstanceUID))
        return 0x0000

    sink_ae = AE(ae_title="CENTRAL_PACS")
    sink_ae.supported_contexts = StoragePresentationContexts
    sink = sink_ae.start_server(("127.0.0.1", 0), block=False,
                                evt_handlers=[(evt.EVT_C_STORE, receive_store)])
    ingress = None
    association = None
    try:
        router.DOWNSTREAM_HOST = "127.0.0.1"
        router.DOWNSTREAM_PORT = sink.server_address[1]
        router.AUTHORIZED_AETS = {"CT_SCANNER_01"}
        ingress_ae = AE(ae_title="CENTRAL_ROUTER")
        ingress_ae.supported_contexts = StoragePresentationContexts + VerificationPresentationContexts
        ingress = ingress_ae.start_server(
            ("127.0.0.1", 0), block=False,
            evt_handlers=[(evt.EVT_C_ECHO, router.handle_echo), (evt.EVT_C_STORE, router.handle_store)],
        )
        client = AE(ae_title="CT_SCANNER_01")
        client.requested_contexts = StoragePresentationContexts + VerificationPresentationContexts
        association = client.associate("127.0.0.1", ingress.server_address[1], ae_title="CENTRAL_ROUTER")
        if not association.is_established:
            raise RuntimeError("Ingress association failed")
        status = association.send_c_echo()
        if not status or status.Status != 0x0000:
            raise RuntimeError("Registered C-ECHO failed")
        print("PASS: registered calling AE receives C-ECHO success")

        expected = []
        for path in sorted((root / "sample_studies").glob("*.dcm")):
            dataset = pydicom.dcmread(path)
            expected.append(str(dataset.SOPInstanceUID))
            status = association.send_c_store(dataset)
            if not status or status.Status != 0x0000:
                raise RuntimeError(f"C-STORE failed: {path.name}")
        association.release()
        association = None
        if not expected or received != expected:
            raise RuntimeError("Receiver identifiers do not match the input instances")
        print(f"PASS: forward {len(expected)} CT instances and verify receiver identifiers")

        unknown = AE(ae_title="UNREGISTERED_AE")
        unknown.requested_contexts = StoragePresentationContexts + VerificationPresentationContexts
        association = unknown.associate("127.0.0.1", ingress.server_address[1], ae_title="CENTRAL_ROUTER")
        if not association.is_established:
            raise RuntimeError("Unable to exercise unregistered AE status handling")
        echo = association.send_c_echo()
        store = association.send_c_store(pydicom.dcmread(root / "sample_studies/ct_slice_001.dcm"))
        if not echo or echo.Status == 0x0000 or not store or store.Status == 0x0000:
            raise RuntimeError("Unregistered calling AE was accepted")
        if received != expected:
            raise RuntimeError("Unregistered calling AE reached the receiver")
        print("PASS: reject unregistered AE C-ECHO and C-STORE without forwarding")
    finally:
        if association is not None and association.is_established:
            association.release()
        if ingress is not None:
            ingress.shutdown()
        sink.shutdown()


if __name__ == "__main__":
    run()
