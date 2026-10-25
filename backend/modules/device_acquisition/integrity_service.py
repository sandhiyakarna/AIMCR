# backend/modules/device_acquisition/integrity_service.py

import os
import sqlite3
import zipfile
import tarfile
import gzip
from typing import Tuple

class IntegrityService:
    # Magic bytes mappings
    SIGNATURES = {
        "SQLite": [b"SQLite format 3\x00"],
        "PNG": [b"\x89PNG\r\n\x1a\n"],
        "JPEG": [b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"\xff\xd8\xff\xe2", b"\xff\xd8\xff\xe8", b"\xff\xd8\xff"],
        "PDF": [b"%PDF-"],
        "ZIP": [b"PK\x03\x04"],
        "GZIP": [b"\x1f\x8b"]
    }

    @staticmethod
    def verify_magic_bytes(file_path: str, expected_type: str) -> bool:
        """Verify file starts with correct magic bytes if we know the signature for expected_type."""
        if expected_type not in IntegrityService.SIGNATURES:
            return True # No signature checker for this type, assume valid
        
        signatures = IntegrityService.SIGNATURES[expected_type]
        max_len = max(len(s) for s in signatures)
        try:
            with open(file_path, "rb") as f:
                header = f.read(max_len)
            
            for sig in signatures:
                if header.startswith(sig):
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def check_sqlite_integrity(file_path: str) -> Tuple[bool, str]:
        """Verify SQLite database integrity."""
        conn = None
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            if result and result[0] == "ok":
                return True, "Integrity OK"
            return False, f"Integrity failed: {result}"
        except Exception as e:
            return False, f"SQLite error: {str(e)}"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def check_archive_integrity(file_path: str, file_type: str) -> Tuple[bool, str]:
        """Verify ZIP, TAR or GZIP file integrity."""
        try:
            if file_type == "ZIP":
                if not zipfile.is_zipfile(file_path):
                    return False, "Not a valid ZIP file"
                with zipfile.ZipFile(file_path) as z:
                    bad_file = z.testzip()
                    if bad_file:
                        return False, f"Corrupted file in ZIP: {bad_file}"
                return True, "ZIP Integrity OK"
            elif file_type == "TAR":
                if not tarfile.is_tarfile(file_path):
                    return False, "Not a valid TAR file"
                with tarfile.open(file_path) as t:
                    t.getnames()
                return True, "TAR Integrity OK"
            elif file_type == "GZIP":
                with gzip.open(file_path, 'rb') as g:
                    g.read(1024)
                return True, "GZIP Integrity OK"
            return True, "Not an archive"
        except Exception as e:
            return False, f"Archive extraction error: {str(e)}"

    @staticmethod
    def validate_file(file_path: str, expected_type: str) -> Tuple[bool, str]:
        """Full file validation checking size, magic bytes and internal integrity."""
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check size (limit to 50MB for single upload files)
        size = os.path.getsize(file_path)
        if size > 50 * 1024 * 1024:
            return False, "File exceeds maximum allowed size (50MB)"
            
        # Verify magic bytes
        if expected_type in ["SQLite", "PNG", "JPEG", "PDF", "ZIP", "GZIP"]:
            if not IntegrityService.verify_magic_bytes(file_path, expected_type):
                return False, f"File signature mismatch. Expected {expected_type}."

        # Verify internal integrity for databases/archives
        if expected_type == "SQLite":
            return IntegrityService.check_sqlite_integrity(file_path)
        elif expected_type in ["ZIP", "TAR", "GZIP"]:
            return IntegrityService.check_archive_integrity(file_path, expected_type)

        return True, "Validated"
