#!/usr/bin/env python3
"""
Synthetic DICOM Dataset Generator for Teleradiology Testing
Generates standards-compliant synthetic DICOM files (CT, MRI, Digital Radiography)
with realistic tag hierarchies, valid transfer syntaxes, and geometric pixel arrays.
Contains ZERO Protected Health Information (PHI).

Supports both pure standard-library binary DICOM generation (no external packages required)
and advanced pydicom/numpy generation when installed.
"""

import os
import sys
import struct
import datetime
import argparse

try:
    import pydicom
    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.uid import (
        ExplicitVRLittleEndian,
        ImplicitVRLittleEndian,
        CTImageStorage,
        MRImageStorage,
        CRImageStorage,
        generate_uid
    )
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def simple_uid():
    import uuid
    return f"2.25.{uuid.uuid4().int}"

def encode_dicom_element(group, element, vr, value_bytes):
    """Encodes an Explicit VR Little Endian DICOM element."""
    tag = struct.pack("<HH", group, element)
    vr_bytes = vr.encode("ascii")
    if vr in ["OB", "OW", "OF", "SQ", "UT", "UN"]:
        reserved = b"\x00\x00"
        length = struct.pack("<I", len(value_bytes))
        return tag + vr_bytes + reserved + length + value_bytes
    else:
        if len(value_bytes) % 2 != 0:
            value_bytes += b" " if vr not in ["UI", "OB"] else b"\x00"
        length = struct.pack("<H", len(value_bytes))
        return tag + vr_bytes + length + value_bytes

def write_pure_dicom_file(filepath, modality, slice_index, total_slices, study_uid, series_uid, is_stat):
    """Generates a valid DICOM Part 10 file using pure Python struct/bytes."""
    sop_uid = simple_uid()
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d").encode("ascii")
    time_str = now.strftime("%H%M%S").encode("ascii")

    sop_class_uid = b"1.2.840.10008.5.1.4.1.1.2" if modality == "CT" else (
        b"1.2.840.10008.5.1.4.1.1.4" if modality == "MR" else b"1.2.840.10008.5.1.4.1.1.1"
    )

    meta_elements = [
        encode_dicom_element(0x0002, 0x0001, "OB", b"\x00\x01"),
        encode_dicom_element(0x0002, 0x0002, "UI", sop_class_uid),
        encode_dicom_element(0x0002, 0x0003, "UI", sop_uid.encode("ascii")),
        encode_dicom_element(0x0002, 0x0010, "UI", b"1.2.840.10008.1.2.1"),
        encode_dicom_element(0x0002, 0x0012, "UI", b"1.2.826.0.1.3680043.9.7133.1.1"),
        encode_dicom_element(0x0002, 0x0013, "SH", b"TELERAD_SIM_2026")
    ]
    meta_payload = b"".join(meta_elements)
    meta_header = encode_dicom_element(0x0002, 0x0000, "UL", struct.pack("<I", len(meta_payload)))

    rows = 256
    cols = 256
    pixel_data = bytearray(rows * cols * 2)
    center = rows // 2
    r_sq = (rows // 3) ** 2
    inner_sq = (rows // 6) ** 2
    base_val = (slice_index * 20) % 250
    idx = 0
    for r in range(rows):
        dy_sq = (r - center) ** 2
        for c in range(cols):
            d_sq = dy_sq + (c - center) ** 2
            val = base_val
            if d_sq < inner_sq:
                val += 1200
            elif d_sq < r_sq:
                val += 700
            pixel_data[idx] = val & 0xFF
            pixel_data[idx + 1] = (val >> 8) & 0xFF
            idx += 2

    study_desc = f"{'STAT ' if is_stat else ''}ROUTINE {modality} CLINICAL EXAM".encode("ascii")

    dataset_elements = [
        encode_dicom_element(0x0008, 0x0016, "UI", sop_class_uid),
        encode_dicom_element(0x0008, 0x0018, "UI", sop_uid.encode("ascii")),
        encode_dicom_element(0x0008, 0x0020, "DA", date_str),
        encode_dicom_element(0x0008, 0x0030, "TM", time_str),
        encode_dicom_element(0x0008, 0x0050, "SH", f"ACC-{now.strftime('%Y%m%d')}-{modality}".encode("ascii")),
        encode_dicom_element(0x0008, 0x0060, "CS", modality.encode("ascii")),
        encode_dicom_element(0x0008, 0x1030, "LO", study_desc),
        encode_dicom_element(0x0010, 0x0010, "PN", f"SYNTHETIC^{modality}^PATIENT".encode("ascii")),
        encode_dicom_element(0x0010, 0x0020, "LO", f"SIM-{modality}-99401".encode("ascii")),
        encode_dicom_element(0x0010, 0x0030, "DA", b"19800101"),
        encode_dicom_element(0x0010, 0x0040, "CS", b"O"),
        encode_dicom_element(0x0020, 0x000D, "UI", study_uid.encode("ascii")),
        encode_dicom_element(0x0020, 0x000E, "UI", series_uid.encode("ascii")),
        encode_dicom_element(0x0020, 0x0011, "IS", str(1).encode("ascii")),
        encode_dicom_element(0x0020, 0x0013, "IS", str(slice_index).encode("ascii")),
        encode_dicom_element(0x0028, 0x0002, "US", struct.pack("<H", 1)),
        encode_dicom_element(0x0028, 0x0004, "CS", b"MONOCHROME2"),
        encode_dicom_element(0x0028, 0x0010, "US", struct.pack("<H", rows)),
        encode_dicom_element(0x0028, 0x0011, "US", struct.pack("<H", cols)),
        encode_dicom_element(0x0028, 0x0100, "US", struct.pack("<H", 16)),
        encode_dicom_element(0x0028, 0x0101, "US", struct.pack("<H", 12)),
        encode_dicom_element(0x0028, 0x0102, "US", struct.pack("<H", 11)),
        encode_dicom_element(0x0028, 0x0103, "US", struct.pack("<H", 0)),
        encode_dicom_element(0x7FE0, 0x0010, "OW", bytes(pixel_data))
    ]

    with open(filepath, "wb") as f:
        f.write(b"\x00" * 128)
        f.write(b"DICM")
        f.write(meta_header)
        f.write(meta_payload)
        for elem in dataset_elements:
            f.write(elem)

def create_pydicom_dataset(modality, slice_index, total_slices, study_uid, series_uid, is_stat):
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    sop_class_map = {"CT": CTImageStorage, "MR": MRImageStorage, "CR": CRImageStorage}
    sop_class = sop_class_map.get(modality.upper(), CTImageStorage)
    sop_instance_uid = generate_uid()

    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 200
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = sop_class
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.9.7133.1.1"
    file_meta.ImplementationVersionName = "TELERAD_SIM_2026"

    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.PatientName = f"SYNTHETIC^{modality}^PATIENT"
    ds.PatientID = f"SIM-{modality}-99401"
    ds.PatientBirthDate = "19800101"
    ds.PatientSex = "O"

    ds.StudyDate = date_str
    ds.StudyTime = time_str
    ds.AccessionNumber = f"ACC-{date_str}-{modality}"
    ds.ReferringPhysicianName = "DR^REFERRING^SIM"
    ds.StudyDescription = f"{'STAT ' if is_stat else ''}ROUTINE {modality} CLINICAL EXAM"
    ds.SeriesDescription = f"{modality} AXIAL 2.5MM SLICE {slice_index}"
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyID = "STUDY-001"
    ds.SeriesNumber = 1
    ds.InstanceNumber = slice_index

    ds.Modality = modality.upper()
    ds.SOPClassUID = sop_class
    ds.SOPInstanceUID = sop_instance_uid

    rows, cols = 512, 512
    ds.Rows = rows
    ds.Columns = cols
    ds.PixelSpacing = [0.75, 0.75]
    ds.SliceThickness = 2.5
    ds.ImagePositionPatient = [0.0, 0.0, float(slice_index * 2.5)]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]

    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0

    if HAS_NUMPY:
        y, x = np.ogrid[:rows, :cols]
        center_y, center_x = rows // 2, cols // 2
        dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        radius = rows // 3
        pixel_array = np.zeros((rows, cols), dtype=np.uint16)
        pixel_array[dist < radius] = 800
        pixel_array[dist < (radius // 2)] = 1400
        pixel_array += (slice_index * 10) % 200
        ds.PixelData = pixel_array.tobytes()
    else:
        ds.PixelData = bytes(rows * cols * 2)

    return ds

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic DICOM datasets for teleradiology testing.")
    parser.add_argument("--output-dir", default="./sample_studies", help="Directory to save DICOM files")
    parser.add_argument("--modality", default="CT", choices=["CT", "MR", "CR"], help="Imaging Modality")
    parser.add_argument("--slices", type=int, default=5, help="Number of slices to generate")
    parser.add_argument("--stat", action="store_true", help="Mark study as STAT / Emergency")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    study_uid = generate_uid() if HAS_PYDICOM else simple_uid()
    series_uid = generate_uid() if HAS_PYDICOM else simple_uid()

    engine = "pydicom" if HAS_PYDICOM else "Pure-Python Binary Encoder (Standard Library)"
    print(f"[*] Generating {args.slices} synthetic {args.modality} instances using [{engine}]...")
    print(f"    StudyInstanceUID:  {study_uid}")
    print(f"    SeriesInstanceUID: {series_uid}")
    print(f"    Priority Flag:     {'STAT' if args.stat else 'ROUTINE'}")

    for i in range(1, args.slices + 1):
        file_name = os.path.join(args.output_dir, f"{args.modality.lower()}_slice_{i:03d}.dcm")
        if HAS_PYDICOM:
            ds = create_pydicom_dataset(args.modality, i, args.slices, study_uid, series_uid, args.stat)
            ds.save_as(file_name, write_like_original=False)
        else:
            write_pure_dicom_file(file_name, args.modality, i, args.slices, study_uid, series_uid, args.stat)

    print(f"[+] Wrote {args.slices} DICOM instances to '{args.output_dir}'.")

if __name__ == "__main__":
    main()
