#!/usr/bin/env python3
"""
DICOM verification and transfer client.
Runs C-ECHO, C-STORE, and C-FIND over TCP and reports operation timing.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

try:
    import pydicom
    from pydicom.dataset import Dataset
    from pynetdicom import AE, StoragePresentationContexts
    from pynetdicom.sop_class import (
        Verification,
        StudyRootQueryRetrieveInformationModelFind
    )
except ImportError:
    print("[!] pydicom and pynetdicom are required. Install via: pip install pydicom pynetdicom")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DICOM_CLIENT")

def run_c_echo(target_host, target_port, calling_aet, called_aet, pdu_size=65536):
    """Executes a DICOM Verification (C-ECHO) transaction."""
    logger.info(f"Initiating C-ECHO: CallingAET=[{calling_aet}] -> Target=[{called_aet}@{target_host}:{target_port}]")
    
    ae = AE(ae_title=calling_aet)
    ae.add_requested_context(Verification)
    ae.maximum_pdu_size = pdu_size

    start_time = time.perf_counter()
    assoc = ae.associate(target_host, target_port, ae_title=called_aet)
    
    if assoc.is_established:
        negotiation_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"[+] Association Accepted (A-ASSOCIATE-AC) in {negotiation_time:.2f} ms.")
        logger.info(f"    Negotiated Max PDU: {assoc.acceptor.maximum_length} Bytes")
        
        echo_start = time.perf_counter()
        status = assoc.send_c_echo()
        echo_rtt = (time.perf_counter() - echo_start) * 1000
        
        assoc.release()
        
        if status and status.Status == 0x0000:
            logger.info(f"[+] C-ECHO Verification SUCCESSFUL. Status: 0x0000 (Success). Echo RTT: {echo_rtt:.2f} ms.")
            return True
        else:
            logger.error(f"[-] C-ECHO Failed with status: {status}")
            return False
    elif assoc.is_rejected:
        logger.error(f"[-] Association REJECTED by peer (A-ASSOCIATE-RJ).")
        return False
    elif assoc.is_aborted:
        logger.error("[-] Association ABORTED by peer (A-ABORT).")
        return False
    else:
        logger.error(f"[-] TCP Connection failed to {target_host}:{target_port}. Host down or port blocked.")
        return False

def run_c_store_single(target_host, target_port, calling_aet, called_aet, file_path, pdu_size=65536):
    """Transmits a single DICOM file via C-STORE."""
    path = Path(file_path)
    if not path.is_file():
        logger.error(f"[-] File not found: {file_path}")
        return False

    ds = pydicom.dcmread(str(path))
    file_size_kb = path.stat().st_size / 1024.0

    logger.info(f"Sending C-STORE: {path.name} ({file_size_kb:.1f} KB) -> [{called_aet}@{target_host}:{target_port}]")
    logger.info(f"    PatientID: {getattr(ds, 'PatientID', 'N/A')}, Modality: {getattr(ds, 'Modality', 'N/A')}")
    logger.info(f"    SOPInstanceUID: {ds.SOPInstanceUID}")

    ae = AE(ae_title=calling_aet)
    ae.requested_contexts = StoragePresentationContexts
    ae.maximum_pdu_size = pdu_size

    assoc = ae.associate(target_host, target_port, ae_title=called_aet)
    if assoc.is_established:
        start_transfer = time.perf_counter()
        status = assoc.send_c_store(ds)
        elapsed = time.perf_counter() - start_transfer
        assoc.release()

        if status and status.Status == 0x0000:
            throughput_mbps = (file_size_kb * 8 / 1024) / max(elapsed, 0.001)
            logger.info(f"[+] C-STORE SUCCESS: 0x0000. Transferred in {elapsed:.3f}s ({throughput_mbps:.2f} Mbps).")
            return True
        else:
            logger.error(f"[-] C-STORE Rejected by peer. Status: {status}")
            return False
    else:
        logger.error(f"[-] Association failed to [{called_aet}@{target_host}:{target_port}].")
        return False

def run_c_store_batch(target_host, target_port, calling_aet, called_aet, directory, pdu_size=65536):
    """Transmits all DICOM files in a directory over a single association."""
    dir_path = Path(directory)
    dcm_files = list(dir_path.glob("*.dcm"))
    if not dcm_files:
        logger.error(f"[-] No .dcm files found in {directory}")
        return False

    total_bytes = sum(f.stat().st_size for f in dcm_files)
    logger.info(f"Batch C-STORE: {len(dcm_files)} files ({total_bytes / (1024*1024):.2f} MB) -> [{called_aet}@{target_host}:{target_port}]")

    ae = AE(ae_title=calling_aet)
    ae.requested_contexts = StoragePresentationContexts
    ae.maximum_pdu_size = pdu_size

    assoc = ae.associate(target_host, target_port, ae_title=called_aet)
    if not assoc.is_established:
        logger.error("[-] Failed to establish association for batch transfer.")
        return False

    success_count = 0
    start_batch = time.perf_counter()

    for idx, f in enumerate(dcm_files, 1):
        try:
            ds = pydicom.dcmread(str(f))
            status = assoc.send_c_store(ds)
            if status and status.Status == 0x0000:
                success_count += 1
            else:
                logger.warning(f"[-] Slice {f.name} rejected. Status: {status}")
        except Exception as e:
            logger.error(f"[-] Error transferring {f.name}: {e}")

    elapsed_total = time.perf_counter() - start_batch
    assoc.release()

    overall_throughput_mbps = (total_bytes * 8 / (1024 * 1024)) / max(elapsed_total, 0.001)
    logger.info(f"[+] Batch Transfer Complete: {success_count}/{len(dcm_files)} instances stored.")
    logger.info(f"    Elapsed: {elapsed_total:.2f}s | Throughput: {overall_throughput_mbps:.2f} Mbps")
    return success_count == len(dcm_files)

def run_c_find(target_host, target_port, calling_aet, called_aet, patient_id="*"):
    """Queries studies via Study Root Query/Retrieve C-FIND."""
    logger.info(f"Querying Studies (C-FIND): PatientID=[{patient_id}] -> [{called_aet}@{target_host}:{target_port}]")
    ae = AE(ae_title=calling_aet)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

    ds = Dataset()
    ds.QueryRetrieveLevel = "STUDY"
    ds.PatientID = patient_id
    ds.PatientName = ""
    ds.StudyInstanceUID = ""
    ds.StudyDate = ""
    ds.StudyDescription = ""
    ds.ModalitiesInStudy = ""

    assoc = ae.associate(target_host, target_port, ae_title=called_aet)
    if assoc.is_established:
        responses = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
        count = 0
        for (status, identifier) in responses:
            if status and status.Status in (0xFF00, 0xFF01): # Pending responses
                count += 1
                logger.info(f"    Match #{count}: PatientID=[{identifier.get('PatientID', '')}], "
                            f"Desc=[{identifier.get('StudyDescription', '')}], "
                            f"StudyUID=[{identifier.get('StudyInstanceUID', '')}]")
        assoc.release()
        logger.info(f"[+] C-FIND Complete. Found {count} matching study records.")
        return True
    else:
        logger.error("[-] Association failed for C-FIND.")
        return False

def main():
    parser = argparse.ArgumentParser(description="DICOM Verification, C-STORE, and Query Client")
    parser.add_argument("--action", required=True, choices=["echo", "store", "store_batch", "find"], help="Action to perform")
    parser.add_argument("--target-host", default="10.200.20.50", help="Target PACS or Router IP/Hostname")
    parser.add_argument("--target-port", type=int, default=4242, help="Target DICOM Port (e.g. 4242 or 11112)")
    parser.add_argument("--called-aet", default="CENTRAL_PACS", help="Called Application Entity Title")
    parser.add_argument("--calling-aet", default="CT_SCANNER_01", help="Calling Application Entity Title")
    parser.add_argument("--file", help="Path to single .dcm file for C-STORE")
    parser.add_argument("--dir", help="Path to directory containing .dcm files for batch C-STORE")
    parser.add_argument("--pdu-size", type=int, default=65536, help="Maximum PDU length (bytes)")
    parser.add_argument("--patient-id", default="*", help="PatientID filter for C-FIND")
    args = parser.parse_args()

    if args.action == "echo":
        success = run_c_echo(args.target_host, args.target_port, args.calling_aet, args.called_aet, args.pdu_size)
    elif args.action == "store":
        if not args.file:
            print("[!] Error: --file argument required for store action.")
            sys.exit(1)
        success = run_c_store_single(args.target_host, args.target_port, args.calling_aet, args.called_aet, args.file, args.pdu_size)
    elif args.action == "store_batch":
        if not args.dir:
            print("[!] Error: --dir argument required for store_batch action.")
            sys.exit(1)
        success = run_c_store_batch(args.target_host, args.target_port, args.calling_aet, args.called_aet, args.dir, args.pdu_size)
    elif args.action == "find":
        success = run_c_find(args.target_host, args.target_port, args.calling_aet, args.called_aet, args.patient_id)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
