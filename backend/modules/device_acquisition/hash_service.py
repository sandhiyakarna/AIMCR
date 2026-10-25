# backend/modules/device_acquisition/hash_service.py

import hashlib

class HashService:
    @staticmethod
    def calculate_sha256_bytes(data: bytes) -> str:
        """Calculate SHA-256 for bytes in memory."""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(data)
        return sha256_hash.hexdigest()

    @staticmethod
    def calculate_sha256_file(file_path: str, block_size: int = 65536) -> str:
        """Calculate SHA-256 for a file on disk, streaming to avoid memory overhead."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(block_size), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            # Fallback to empty hash if error reading
            return hashlib.sha256(str(e).encode("utf-8")).hexdigest()
