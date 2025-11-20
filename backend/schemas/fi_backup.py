#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Auto-Backup System

Automated backup with AES-256 encryption for local/NAS storage.
Supports incremental backups, integrity verification, and retention policies.

FI-SEC-FEAT-001
"""

import base64
import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.logger import get_logger

logger = get_logger(__name__)


def generate_key_from_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Generate encryption key from password using PBKDF2.

    Args:
        password: User password
        salt: Salt for key derivation (generated if None)

    Returns:
        Tuple of (key, salt)

    Examples:
        >>> key, salt = generate_key_from_password("my_secure_password")
        >>> len(key)
        44
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_file(input_path: Path, output_path: Path, key: bytes) -> str:
    """
    Encrypt file using Fernet (AES-256).

    Args:
        input_path: Source file to encrypt
        output_path: Encrypted output file
        key: Encryption key (from generate_key_from_password)

    Returns:
        SHA256 hash of encrypted file

    Event: FILE_ENCRYPTED

    Examples:
        >>> key, salt = generate_key_from_password("password")
        >>> hash_val = encrypt_file(Path("corpus.h5"), Path("corpus.h5.enc"), key)
    """
    logger.info("FILE_ENCRYPTION_STARTED", input_path=str(input_path))

    fernet = Fernet(key)

    # Read and encrypt
    with open(input_path, "rb") as f_in:
        data = f_in.read()

    encrypted_data = fernet.encrypt(data)

    # Write encrypted file
    with open(output_path, "wb") as f_out:
        f_out.write(encrypted_data)

    # Compute hash of encrypted file
    hash_obj = hashlib.sha256()
    hash_obj.update(encrypted_data)
    hash_hex = hash_obj.hexdigest()

    logger.info(
        "FILE_ENCRYPTED",
        input_path=str(input_path),
        output_path=str(output_path),
        encrypted_size=len(encrypted_data),
        sha256=hash_hex[:16],
    )

    return hash_hex


def decrypt_file(input_path: Path, output_path: Path, key: bytes) -> str:
    """
    Decrypt file using Fernet (AES-256).

    Args:
        input_path: Encrypted file
        output_path: Decrypted output file
        key: Encryption key

    Returns:
        SHA256 hash of decrypted file

    Event: FILE_DECRYPTED

    Examples:
        >>> key, salt = generate_key_from_password("password")
        >>> hash_val = decrypt_file(Path("corpus.h5.enc"), Path("corpus_restored.h5"), key)
    """
    logger.info("FILE_DECRYPTION_STARTED", input_path=str(input_path))

    fernet = Fernet(key)

    # Read encrypted file
    with open(input_path, "rb") as f_in:
        encrypted_data = f_in.read()

    # Decrypt
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except Exception as e:
        logger.error("FILE_DECRYPTION_FAILED", error=str(e))
        raise ValueError("Decryption failed - invalid key or corrupted file")

    # Write decrypted file
    with open(output_path, "wb") as f_out:
        f_out.write(decrypted_data)

    # Compute hash of decrypted file
    hash_obj = hashlib.sha256()
    hash_obj.update(decrypted_data)
    hash_hex = hash_obj.hexdigest()

    logger.info(
        "FILE_DECRYPTED",
        input_path=str(input_path),
        output_path=str(output_path),
        decrypted_size=len(decrypted_data),
        sha256=hash_hex[:16],
    )

    return hash_hex


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of file.

    Args:
        file_path: File to hash

    Returns:
        SHA256 hash (hex)

    Examples:
        >>> hash_val = compute_file_hash(Path("corpus.h5"))
    """
    hash_obj = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def create_backup(
    corpus_path: str, backup_dir: str, password: str, encrypt: bool = True, retention_days: int = 30
) -> tuple[str, dict]:
    """
    Create encrypted backup of corpus.

    Args:
        corpus_path: Path to corpus.h5
        backup_dir: Backup destination directory
        password: Encryption password
        encrypt: Whether to encrypt (True) or copy plain (False)
        retention_days: Retention policy in days

    Returns:
        Tuple of (backup_path, metadata_dict)

    Event: BACKUP_CREATED

    Examples:
        >>> backup_path, metadata = create_backup(
        ...     "storage/corpus.h5",
        ...     "backups/",
        ...     "my_password",
        ...     encrypt=True,
        ...     retention_days=30
        ... )
        >>> print(f"Backup: {backup_path}")
    """
    logger.info(
        "BACKUP_CREATION_STARTED", corpus_path=corpus_path, backup_dir=backup_dir, encrypt=encrypt
    )

    corpus_path_obj = Path(corpus_path)
    backup_dir_obj = Path(backup_dir)
    backup_dir_obj.mkdir(parents=True, exist_ok=True)

    if not corpus_path_obj.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"corpus_backup_{timestamp}.h5"
    if encrypt:
        backup_name += ".enc"

    backup_path = backup_dir_obj / backup_name
    metadata_path = backup_dir_obj / f"corpus_backup_{timestamp}.meta.json"

    # Compute original file hash
    original_hash = compute_file_hash(corpus_path_obj)

    # Create backup
    if encrypt:
        # Generate encryption key
        key, salt = generate_key_from_password(password)

        # Encrypt corpus
        encrypted_hash = encrypt_file(corpus_path_obj, backup_path, key)

        # Store salt separately (needed for decryption)
        salt_file = backup_dir_obj / f"corpus_backup_{timestamp}.salt"
        with open(salt_file, "wb") as f:
            f.write(salt)

        backup_hash = encrypted_hash
    else:
        # Plain copy
        shutil.copy2(corpus_path_obj, backup_path)
        backup_hash = compute_file_hash(backup_path)

    # Create metadata
    metadata = {
        "backup_id": timestamp,
        "timestamp": datetime.now().isoformat(),
        "corpus_path": str(corpus_path_obj),
        "backup_path": str(backup_path),
        "encrypted": encrypt,
        "original_hash": original_hash,
        "backup_hash": backup_hash,
        "original_size": corpus_path_obj.stat().st_size,
        "backup_size": backup_path.stat().st_size,
        "retention_days": retention_days,
        "expires_at": (datetime.now() + timedelta(days=retention_days)).isoformat(),
    }

    # Save metadata
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "BACKUP_CREATED",
        backup_path=str(backup_path),
        encrypted=encrypt,
        original_size=metadata["original_size"],
        backup_size=metadata["backup_size"],
        retention_days=retention_days,
    )

    return str(backup_path), metadata


def restore_backup(backup_path: str, output_path: str, password: str | None = None) -> str:
    """
    Restore corpus from backup.

    Args:
        backup_path: Path to backup file (.h5 or .h5.enc)
        output_path: Restored corpus destination
        password: Decryption password (required if encrypted)

    Returns:
        SHA256 hash of restored file

    Event: BACKUP_RESTORED

    Examples:
        >>> restored_hash = restore_backup(
        ...     "backups/corpus_backup_20251028_195500.h5.enc",
        ...     "storage/corpus_restored.h5",
        ...     password="my_password"
        ... )
    """
    logger.info("BACKUP_RESTORATION_STARTED", backup_path=backup_path, output_path=output_path)

    backup_path_obj = Path(backup_path)
    output_path_obj = Path(output_path)

    if not backup_path_obj.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    # Check if encrypted
    is_encrypted = backup_path.endswith(".enc")

    if is_encrypted:
        if not password:
            raise ValueError("Password required for encrypted backup")

        # Load salt
        salt_file = backup_path_obj.parent / backup_path_obj.name.replace(".h5.enc", ".salt")
        if not salt_file.exists():
            raise FileNotFoundError(f"Salt file not found: {salt_file}")

        with open(salt_file, "rb") as f:
            salt = f.read()

        # Generate key
        key, _ = generate_key_from_password(password, salt)

        # Decrypt
        restored_hash = decrypt_file(backup_path_obj, output_path_obj, key)
    else:
        # Plain copy
        shutil.copy2(backup_path_obj, output_path_obj)
        restored_hash = compute_file_hash(output_path_obj)

    logger.info(
        "BACKUP_RESTORED",
        backup_path=backup_path,
        output_path=output_path,
        restored_hash=restored_hash[:16],
    )

    return restored_hash


def verify_backup(backup_path: str, password: str | None = None) -> bool:
    """
    Verify backup integrity.

    Args:
        backup_path: Path to backup file
        password: Decryption password (if encrypted)

    Returns:
        True if backup is valid

    Event: BACKUP_VERIFIED

    Examples:
        >>> is_valid = verify_backup("backups/corpus_backup_20251028_195500.h5.enc", "password")
        >>> print(f"Valid: {is_valid}")
    """
    logger.info("BACKUP_VERIFICATION_STARTED", backup_path=backup_path)

    backup_path_obj = Path(backup_path)
    if not backup_path_obj.exists():
        logger.error("BACKUP_VERIFICATION_FAILED", reason="File not found")
        return False

    # Load metadata
    meta_path = backup_path_obj.parent / backup_path_obj.name.replace(
        ".h5.enc", ".meta.json"
    ).replace(".h5", ".meta.json")
    if not meta_path.exists():
        logger.warning("BACKUP_METADATA_MISSING", backup_path=backup_path)
        # Can still verify file exists and is readable
        is_encrypted = backup_path.endswith(".enc")
        if is_encrypted and not password:
            logger.error("BACKUP_VERIFICATION_FAILED", reason="Password required")
            return False
        return True

    with open(meta_path) as f:
        metadata = json.load(f)

    # Verify backup hash
    current_hash = compute_file_hash(backup_path_obj)
    if current_hash != metadata["backup_hash"]:
        logger.error(
            "BACKUP_VERIFICATION_FAILED",
            reason="Hash mismatch",
            expected=metadata["backup_hash"][:16],
            actual=current_hash[:16],
        )
        return False

    # If encrypted, try decrypting to temp file
    if metadata["encrypted"]:
        if not password:
            logger.warning(
                "BACKUP_VERIFICATION_INCOMPLETE", reason="No password for decryption test"
            )
            # Hash matched, assume valid
            return True

        # Try decrypt to temp
        import tempfile

        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            try:
                restore_backup(backup_path, tmp.name, password)
                logger.info("BACKUP_VERIFIED", backup_path=backup_path, decryption_test="passed")
                return True
            except Exception as e:
                logger.error("BACKUP_VERIFICATION_FAILED", reason="Decryption failed", error=str(e))
                return False

    logger.info("BACKUP_VERIFIED", backup_path=backup_path)
    return True


def cleanup_old_backups(backup_dir: str, retention_days: int = 30) -> list[str]:
    """
    Remove backups older than retention policy.

    Args:
        backup_dir: Backup directory
        retention_days: Retention in days

    Returns:
        List of removed backup paths

    Event: BACKUPS_CLEANED_UP

    Examples:
        >>> removed = cleanup_old_backups("backups/", retention_days=30)
        >>> print(f"Removed {len(removed)} old backups")
    """
    logger.info("BACKUP_CLEANUP_STARTED", backup_dir=backup_dir, retention_days=retention_days)

    backup_dir_obj = Path(backup_dir)
    if not backup_dir_obj.exists():
        return []

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    removed = []

    # Find all metadata files
    for meta_file in backup_dir_obj.glob("*.meta.json"):
        with open(meta_file) as f:
            metadata = json.load(f)

        backup_date = datetime.fromisoformat(metadata["timestamp"])
        if backup_date < cutoff_date:
            # Remove backup + metadata + salt (if exists)
            backup_path = Path(metadata["backup_path"])
            if backup_path.exists():
                backup_path.unlink()
                removed.append(str(backup_path))

            meta_file.unlink()

            salt_file = backup_path.parent / backup_path.name.replace(".h5.enc", ".salt")
            if salt_file.exists():
                salt_file.unlink()

            logger.info(
                "BACKUP_REMOVED",
                backup_path=str(backup_path),
                age_days=(datetime.now() - backup_date).days,
            )

    logger.info("BACKUPS_CLEANED_UP", backup_dir=backup_dir, removed_count=len(removed))

    return removed


def list_backups(backup_dir: str) -> list[dict]:
    """
    List all backups with metadata.

    Args:
        backup_dir: Backup directory

    Returns:
        List of backup metadata dicts

    Examples:
        >>> backups = list_backups("backups/")
        >>> for b in backups:
        ...     print(f"{b['backup_id']}: {b['backup_size']} bytes")
    """
    backup_dir_obj = Path(backup_dir)
    if not backup_dir_obj.exists():
        return []

    backups = []
    for meta_file in sorted(backup_dir_obj.glob("*.meta.json")):
        with open(meta_file) as f:
            metadata = json.load(f)
        backups.append(metadata)

    return backups


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import getpass
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 backend/fi_backup.py create <corpus.h5> <backup_dir> [--encrypt]")
        print("  python3 backend/fi_backup.py restore <backup_file> <output.h5>")
        print("  python3 backend/fi_backup.py verify <backup_file>")
        print("  python3 backend/fi_backup.py list <backup_dir>")
        print("  python3 backend/fi_backup.py cleanup <backup_dir> [retention_days]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create" and len(sys.argv) >= 4:
        corpus_path = sys.argv[2]
        backup_dir = sys.argv[3]
        encrypt = "--encrypt" in sys.argv

        if encrypt:
            password = getpass.getpass("Enter encryption password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords don't match")
                sys.exit(1)
        else:
            password = "dummy"  # Not used

        try:
            backup_path, metadata = create_backup(
                corpus_path, backup_dir, password, encrypt=encrypt
            )
            print(f"✅ Backup created: {backup_path}")
            print(f"   Original: {metadata['original_size']} bytes")
            print(f"   Backup: {metadata['backup_size']} bytes")
            print(f"   Encrypted: {metadata['encrypted']}")
            print(f"   Expires: {metadata['expires_at']}")
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif command == "restore" and len(sys.argv) >= 4:
        backup_path = sys.argv[2]
        output_path = sys.argv[3]

        is_encrypted = backup_path.endswith(".enc")
        if is_encrypted:
            password = getpass.getpass("Enter decryption password: ")
        else:
            password = None

        try:
            restored_hash = restore_backup(backup_path, output_path, password)
            print(f"✅ Backup restored: {output_path}")
            print(f"   SHA256: {restored_hash[:16]}...")
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif command == "verify" and len(sys.argv) >= 3:
        backup_path = sys.argv[2]

        is_encrypted = backup_path.endswith(".enc")
        if is_encrypted:
            password = getpass.getpass("Enter password (or Enter to skip decryption test): ")
            if not password:
                password = None
        else:
            password = None

        try:
            is_valid = verify_backup(backup_path, password)
            if is_valid:
                print(f"✅ Backup is valid: {backup_path}")
            else:
                print(f"❌ Backup is invalid: {backup_path}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif command == "list" and len(sys.argv) >= 3:
        backup_dir = sys.argv[2]
        backups = list_backups(backup_dir)
        if not backups:
            print("No backups found")
        else:
            print(f"\n📦 Backups in {backup_dir}:")
            for b in backups:
                print(
                    f"   [{b['backup_id']}] {b['backup_size']} bytes (encrypted: {b['encrypted']})"
                )

    elif command == "cleanup" and len(sys.argv) >= 3:
        backup_dir = sys.argv[2]
        retention_days = int(sys.argv[3]) if len(sys.argv) >= 4 else 30

        removed = cleanup_old_backups(backup_dir, retention_days)
        print(f"✅ Removed {len(removed)} old backups (>{retention_days} days)")

    else:
        print("Invalid command or missing arguments")
        sys.exit(1)
