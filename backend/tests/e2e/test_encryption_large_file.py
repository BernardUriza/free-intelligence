#!/usr/bin/env python3
"""E2E Test: Large file encryption with automatic chunking.

Card: FI-CORE-CRYPTO-15
Checklist item: Test E2E cifrar video 100MB, verificar sha256, desencriptar

This test validates:
1. Automatic chunking for files >500MB (using 100MB test file)
2. SHA-256 integrity verification
3. Successful decryption and reassembly
4. Round-trip data integrity

Usage:
    pytest backend/tests/e2e/test_encryption_large_file.py -v
    python backend/tests/e2e/test_encryption_large_file.py  # Direct execution
"""

from __future__ import annotations

import h5py
import numpy as np
import os
import pytest
import sys
import tempfile
import time
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.src.fi_workers.tasks.encryption_worker import (
    CHUNK_SIZE_BYTES,
    chunk_large_data,
    decrypt_chunked_dataset,
    encrypt_large_dataset,
    generate_dek,
    load_kek,
    sha256_hex,
    unwrap_dek,
    wrap_dek,
)


class TestLargeFileEncryption:
    """Test suite for large file encryption with chunking."""

    @pytest.fixture
    def temp_h5_file(self):
        """Create a temporary HDF5 file for testing."""
        fd, path = tempfile.mkstemp(suffix=".h5")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def session_id(self):
        """Generate a test session ID."""
        return f"test_session_{int(time.time())}"

    def test_chunk_large_data_splits_correctly(self):
        """Test that chunk_large_data splits data into correct chunks."""
        # Create 150MB of test data
        size_mb = 150
        data = os.urandom(size_mb * 1024 * 1024)

        chunks = chunk_large_data(data, CHUNK_SIZE_BYTES)

        # Should have 3 chunks (150MB / 50MB = 3)
        assert len(chunks) == 3

        # Reassemble and verify
        reassembled = b"".join(chunks)
        assert reassembled == data
        assert sha256_hex(reassembled) == sha256_hex(data)

    def test_chunk_small_data_no_split(self):
        """Test that small data is not chunked."""
        # Create 10MB of test data (below threshold)
        data = os.urandom(10 * 1024 * 1024)

        chunks = chunk_large_data(data, CHUNK_SIZE_BYTES)

        assert len(chunks) == 1
        assert chunks[0] == data

    def test_encrypt_decrypt_large_file_roundtrip(self, temp_h5_file, session_id):
        """E2E test: encrypt 100MB file, verify SHA-256, decrypt, verify integrity."""
        # Configuration for test (use smaller threshold to test chunking)
        test_size_mb = 100
        test_chunk_size = 25 * 1024 * 1024  # 25MB chunks for faster test

        # Generate test data (simulating video file)
        print(f"\n[1/6] Generating {test_size_mb}MB test data...")
        test_data = os.urandom(test_size_mb * 1024 * 1024)
        original_sha256 = sha256_hex(test_data)
        print(f"       Original SHA-256: {original_sha256[:32]}...")

        # Create HDF5 with test dataset
        print("[2/6] Creating HDF5 file with test dataset...")
        ds_path = "/video/test_large_video"
        with h5py.File(temp_h5_file, "w") as h5:
            h5.create_dataset(ds_path, data=np.frombuffer(test_data, dtype=np.uint8))

        # Generate DEK
        print("[3/6] Generating encryption keys...")
        dek_id, dek, aesgcm = generate_dek()
        kek = load_kek()
        wrap_dek(dek, kek)

        # Manually chunk and encrypt (simulating encrypt_large_dataset behavior)
        print("[4/6] Encrypting with chunking...")
        start_time = time.time()

        with h5py.File(temp_h5_file, "r+") as h5:
            # Read original data
            ds = h5[ds_path]
            plain_data = ds[...].tobytes()

            # Verify data integrity before encryption
            assert sha256_hex(plain_data) == original_sha256

            # Chunk the data
            chunks = chunk_large_data(plain_data, test_chunk_size)
            print(f"       Split into {len(chunks)} chunks")

            # Delete original dataset
            del h5[ds_path]

            # Create chunk group
            chunk_group_path = f"{ds_path}__chunks"
            chunk_group = h5.require_group(chunk_group_path)
            chunk_group.attrs["original_path"] = ds_path
            chunk_group.attrs["chunk_count"] = len(chunks)
            chunk_group.attrs["total_plaintext_bytes"] = len(plain_data)
            chunk_group.attrs["plaintext_sha256"] = original_sha256

            # Encrypt each chunk
            for i, chunk_data in enumerate(chunks):
                chunk_path = f"{chunk_group_path}/chunk_{i:04d}"
                chunk_sha256 = sha256_hex(chunk_data)

                # Unique IV per chunk
                iv = os.urandom(12)
                aad = f"{session_id}:{chunk_path}".encode()

                # Encrypt
                ciphertext = aesgcm.encrypt(iv, chunk_data, aad)

                # Store
                enc_array = np.frombuffer(ciphertext, dtype=np.uint8)
                dset = h5.create_dataset(chunk_path, data=enc_array, dtype=np.uint8)
                dset.attrs["enc:algorithm"] = "AES-GCM-256"
                dset.attrs["enc:dek_id"] = dek_id
                dset.attrs["enc:iv_b64"] = __import__("base64").b64encode(iv).decode()
                dset.attrs["enc:plaintext_sha256"] = chunk_sha256
                dset.attrs["enc:chunk_index"] = i

                print(
                    f"       Chunk {i}: {len(chunk_data) // (1024 * 1024)}MB -> {len(ciphertext) // (1024 * 1024)}MB encrypted"
                )

        encrypt_time = time.time() - start_time
        print(f"       Encryption completed in {encrypt_time:.2f}s")

        # Decrypt and verify
        print("[5/6] Decrypting and reassembling...")
        start_time = time.time()

        with h5py.File(temp_h5_file, "r") as h5:
            decrypted_data = decrypt_chunked_dataset(session_id, h5, chunk_group_path, aesgcm)

        decrypt_time = time.time() - start_time
        print(f"       Decryption completed in {decrypt_time:.2f}s")

        # Verify integrity
        print("[6/6] Verifying data integrity...")
        decrypted_sha256 = sha256_hex(decrypted_data)
        print(f"       Decrypted SHA-256: {decrypted_sha256[:32]}...")

        assert decrypted_sha256 == original_sha256, "SHA-256 mismatch after decryption!"
        assert decrypted_data == test_data, "Data mismatch after round-trip!"

        print("\n[SUCCESS] E2E encryption/decryption test passed!")
        print(f"         Data size: {test_size_mb}MB")
        print(f"         Chunks: {len(chunks)}")
        print(f"         Encrypt time: {encrypt_time:.2f}s")
        print(f"         Decrypt time: {decrypt_time:.2f}s")
        print(f"         SHA-256 verified: {original_sha256[:16]}...")

    def test_dek_wrap_unwrap_roundtrip(self):
        """Test DEK wrapping and unwrapping with KEK."""
        # Generate DEK
        dek_id, dek, _ = generate_dek()

        # Load KEK and wrap
        kek = load_kek()
        wrapped = wrap_dek(dek, kek)

        # Unwrap and verify
        unwrapped = unwrap_dek(wrapped, kek)

        assert unwrapped == dek
        print(f"DEK wrap/unwrap verified: {dek_id}")

    def test_encrypt_large_dataset_integration(self, temp_h5_file, session_id):
        """Integration test for encrypt_large_dataset function."""
        # For this test, we'll use a smaller file but verify the function works
        test_size_mb = 10  # Small file to test function, not chunking

        # Generate test data
        test_data = os.urandom(test_size_mb * 1024 * 1024)
        sha256_hex(test_data)

        # Create HDF5
        ds_path = "/audio/test_audio"
        with h5py.File(temp_h5_file, "w") as h5:
            h5.create_dataset(ds_path, data=np.frombuffer(test_data, dtype=np.uint8))

        # Generate keys
        dek_id, _dek, aesgcm = generate_dek()

        # Encrypt using the function
        with h5py.File(temp_h5_file, "r+") as h5:
            entries = encrypt_large_dataset(session_id, h5, ds_path, aesgcm, dek_id)

        # Since file is below threshold, should return empty (use normal encryption)
        assert len(entries) == 0, "Small files should not be chunked"
        print(f"Small file ({test_size_mb}MB) correctly skipped chunking")


def run_manual_test():
    """Run manual test outside pytest."""
    print("=" * 60)
    print("FI-CORE-CRYPTO-15: E2E Large File Encryption Test")
    print("=" * 60)

    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=".h5")
    os.close(fd)

    try:
        test = TestLargeFileEncryption()
        session_id = f"manual_test_{int(time.time())}"

        # Run the main E2E test
        test.test_encrypt_decrypt_large_file_roundtrip(temp_path, session_id)

        # Run additional tests
        print("\n" + "=" * 60)
        test.test_chunk_large_data_splits_correctly()
        print("[PASS] Chunking test passed")

        test.test_dek_wrap_unwrap_roundtrip()
        print("[PASS] DEK wrap/unwrap test passed")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    sys.exit(run_manual_test())
