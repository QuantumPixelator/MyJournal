"""Encryption helpers for MyJournal.

This module derives a Fernet-compatible key from a user password and
provides simple helpers to encrypt/decrypt text and binary data.
"""

import os
import base64
import argon2
from cryptography.fernet import Fernet, InvalidToken

class EncryptionManager:
    """Manage symmetric encryption derived from a password.

    Create an instance with the user's master password and a salt. The
    instance exposes convenience methods for encrypting/decrypting
    both text and raw bytes.
    """

    def __init__(self, password: str, salt: bytes):
        """Derive a key from ``password`` and ``salt`` and prepare Fernet.

        ``salt`` should be saved alongside the encrypted data so the key
        can be reproduced when the user logs back in.
        """
        self.key = self._derive_key(password, salt)
        self.fernet = Fernet(self.key)

    @staticmethod
    def _derive_key(password: str, salt: bytes):
        """Derive a 32-byte key from a password and salt using Argon2id.

        The result is urlsafe-base64 encoded to be compatible with Fernet.
        """
        raw_key = argon2.low_level.hash_secret_raw(
            secret=password.encode(),
            salt=salt,
            time_cost=3,
            memory_cost=65536,  # 64 MiB
            parallelism=4,
            hash_len=32,
            type=argon2.Type.ID
        )
        return base64.urlsafe_b64encode(raw_key)

    @staticmethod
    def generate_salt() -> bytes:
        """Return a new 16-byte cryptographically secure salt."""
        return os.urandom(16)

    def encrypt_text(self, text: str) -> bytes:
        """Encrypt a UTF-8 text string and return the token bytes."""
        return self.fernet.encrypt(text.encode("utf-8"))

    def decrypt_text(self, token: bytes) -> str:
        """Decrypt token bytes and return the decoded UTF-8 string."""
        return self.fernet.decrypt(token).decode("utf-8")

    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt arbitrary bytes and return the token bytes."""
        return self.fernet.encrypt(data)

    def decrypt_data(self, token: bytes) -> bytes:
        """Decrypt token bytes and return the original bytes."""
        return self.fernet.decrypt(token)