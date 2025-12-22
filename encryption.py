"""Encryption helpers for MyJournal.

This module derives a Fernet-compatible key from a user password and
provides simple helpers to encrypt/decrypt text and binary data.
"""

import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken

class EncryptionManager:
    """Manage symmetric encryption derived from a password.

    Create an instance with the user's master password and a salt. The
    instance exposes convenience methods for encrypting/decrypting
    both text and raw bytes.
    """
    ITERATIONS = 200000

    def __init__(self, password: str, salt: bytes):
        """Derive a key from ``password`` and ``salt`` and prepare Fernet.

        ``salt`` should be saved alongside the encrypted data so the key
        can be reproduced when the user logs back in.
        """
        self.key = self._derive_key(password, salt)
        self.fernet = Fernet(self.key)

    @staticmethod
    def _derive_key(password: str, salt: bytes):
        """Derive a 32-byte key from a password and salt (PBKDF2-HMAC-SHA256).

        The result is urlsafe-base64 encoded to be compatible with Fernet.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=EncryptionManager.ITERATIONS,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

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