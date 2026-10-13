#!/usr/bin/env python3
"""
Master Teleradiology Integration Test Suite Orchestrator
Executes the comprehensive suite of tests defined in the validation matrix,
captures timing, logs status, and outputs a formatted sign-off report.
"""

import os
import sys
import time
import subprocess
import argparse

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

class TestReport:
    def __init__(self):
        self.results = []

    def record(self, test_id, title, status, duration, notes=""):
        self.results.append({
            "id": test_id,
            "title": title,
            "status": status,
            "duration": duration,
            "notes": notes
        })

    def print_summary(self):
        print(f"\n{BOLD}{CYAN}{'='*85}")
        print(f"       MASTER TELERADIOLOGY INTEGRATION TEST EXECUTION SUMMARY")
        print(f"{'='*85}{RESET}")
        print(f"{BOLD}{'Test ID':<10} | {'Test Title':<35} | {'Status':<10} | {'Duration':<10} | Notes{RESET}")
        print("-" * 85)
        
        passed = 0
        for r in self.results:
            status_color = GREEN if r['status'] == "PASS" else (RED if r['status'] == "FAIL" else YELLOW)
            print(f"{r['id']:<10} | {r['title']:<35} | {status_color}{r['status']:<10}{RESET} | {r['duration']:<10} | {r['notes']}")
            if r['status'] == "PASS":
                passed += 1

        print("-" * 85)
        total = len(self.results)
        print(f"{BOLD}Total Tests: {total} | Passed: {passed} | Failed: {total - passed}{RESET}\n")

def run_command(cmd, description):
    print(f"\n{BOLD}[*] Executing: {description}...{RESET}")
    start = time.perf_counter()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    elapsed = time.perf_counter() - start
    print(res.stdout)
    return res.returncode == 0, f"{elapsed:.2f}s", res.stdout

def main():
    parser = argparse.ArgumentParser(description="Master Integration Test Runner")
    parser.add_argument("--target-host", default="10.200.20.50", help="Central PACS IP")
    parser.add_argument("--target-port", type=int, default=4242, help="Central PACS Port")
    parser.add_argument("--called-aet", default="CENTRAL_PACS", help="Called AET")
    parser.add_argument("--calling-aet", default="CT_SCANNER_01", help="Calling AET")
    parser.add_argument("--skip-network-check", action="store_true", help="Skip preflight network check")
    args = parser.parse_args()

    report = TestReport()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(base_dir, "scripts")
    sample_dir = os.path.join(base_dir, "sample_studies")

    gen_cmd = [
        sys.executable,
        os.path.join(scripts_dir, "generate_synthetic_dicom.py"),
        "--output-dir", sample_dir,
        "--slices", "3"
    ]
    ok, dur, _ = run_command(gen_cmd, "Create synthetic DICOM datasets")
    report.record("SETUP-01", "Synthetic DICOM Generation", "PASS" if ok else "FAIL", dur)

    if not args.skip_network_check:
        net_cmd = [
            sys.executable,
            os.path.join(scripts_dir, "network_preflight_check.py"),
            "--target-ip", args.target_host
        ]
        ok, dur, out = run_command(net_cmd, "Run network reachability checks")
        report.record("TC-01", "Network Reachability & Port Audit", "PASS" if ok else "FAIL", dur)
    else:
        report.record("TC-01", "Network Reachability & Port Audit", "SKIPPED", "0.00s")

    echo_cmd = [
        sys.executable,
        os.path.join(scripts_dir, "dicom_verification_client.py"),
        "--action", "echo",
        "--target-host", args.target_host,
        "--target-port", str(args.target_port),
        "--called-aet", args.called_aet,
        "--calling-aet", args.calling_aet
    ]
    ok, dur, _ = run_command(echo_cmd, f"Run C-ECHO against {args.called_aet}")
    report.record("TC-06", "DICOM C-ECHO Ping Verification", "PASS" if ok else "FAIL", dur)

    sample_file = os.path.join(sample_dir, "ct_slice_001.dcm")
    if os.path.exists(sample_file):
        store_cmd = [
            sys.executable,
            os.path.join(scripts_dir, "dicom_verification_client.py"),
            "--action", "store",
            "--file", sample_file,
            "--target-host", args.target_host,
            "--target-port", str(args.target_port),
            "--called-aet", args.called_aet,
            "--calling-aet", args.calling_aet
        ]
        ok, dur, _ = run_command(store_cmd, "Transfer one DICOM instance")
        report.record("TC-07", "Single Image C-STORE Push", "PASS" if ok else "FAIL", dur)

    batch_cmd = [
        sys.executable,
        os.path.join(scripts_dir, "dicom_verification_client.py"),
        "--action", "store_batch",
        "--dir", sample_dir,
        "--target-host", args.target_host,
        "--target-port", str(args.target_port),
        "--called-aet", args.called_aet,
        "--calling-aet", args.calling_aet
    ]
    ok, dur, _ = run_command(batch_cmd, "Transfer the DICOM series")
    report.record("TC-08", "Multi-Slice Exam C-STORE Transfer", "PASS" if ok else "FAIL", dur)

    reject_cmd = [
        sys.executable,
        os.path.join(scripts_dir, "dicom_verification_client.py"),
        "--action", "echo",
        "--target-host", args.target_host,
        "--target-port", str(args.target_port),
        "--called-aet", args.called_aet,
        "--calling-aet", "UNKNOWN_MODALITY"
    ]
    ok, dur, out = run_command(reject_cmd, "Verify unauthorized AE-title rejection")
    is_expected_rejection = not ok and ("Association REJECTED" in out or "C-ECHO Failed with status" in out)
    report.record("TC-13", "Unauthorized AET Rejection (Security)", "PASS" if is_expected_rejection else "FAIL", dur, "Rejected as expected")

    report.print_summary()
    return 1 if any(result["status"] == "FAIL" for result in report.results) else 0

if __name__ == "__main__":
    sys.exit(main())
