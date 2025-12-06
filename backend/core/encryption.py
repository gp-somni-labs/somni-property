"""
Somni Property Manager - Encryption Service

Provides encryption/decryption for sensitive data like SSH keys and HA tokens
"""

import os
import bcrypt
from cryptography.fernet import Fernet


class EncryptionService:
    """
    Handles encryption and hashing of sensitive data

    Uses:
    - Fernet (symmetric encryption) for SSH keys
    - Bcrypt (hashing) for HA tokens
    """

    def __init__(self):
        # Get encryption key from environment variable
        # In production, this should be stored securely (e.g., Kubernetes Secret)
        encryption_key = os.getenv('ENCRYPTION_KEY')

        if not encryption_key:
            # Generate a key for development
            # WARNING: This is insecure for production!
            encryption_key = Fernet.generate_key().decode()
            print(f"WARNING: No ENCRYPTION_KEY env var set. Using generated key: {encryption_key}")

        self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using Fernet symmetric encryption

        Args:
            plaintext: String to encrypt (e.g., SSH private key)

        Returns:
            Encrypted string (base64 encoded)
        """
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext using Fernet symmetric encryption

        Args:
            ciphertext: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext
        """
        return self.fernet.decrypt(ciphertext.encode()).decode()

    def hash_token(self, token: str) -> str:
        """
        Hash token using bcrypt

        Args:
            token: Token to hash (e.g., HA long-lived access token)

        Returns:
            Bcrypt hash
        """
        return bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()

    def verify_token(self, token: str, token_hash: str) -> bool:
        """
        Verify token against bcrypt hash

        Args:
            token: Token to verify
            token_hash: Bcrypt hash to check against

        Returns:
            True if token matches hash, False otherwise
        """
        return bcrypt.checkpw(token.encode(), token_hash.encode())


# Convenience functions for module-level access
_encryption_service = None

def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def decrypt_value(ciphertext: str) -> str:
    """
    Convenience function to decrypt a value

    Args:
        ciphertext: Encrypted string (base64 encoded)

    Returns:
        Decrypted plaintext
    """
    return get_encryption_service().decrypt(ciphertext)


def encrypt_value(plaintext: str) -> str:
    """
    Convenience function to encrypt a value

    Args:
        plaintext: String to encrypt

    Returns:
        Encrypted string (base64 encoded)
    """
    return get_encryption_service().encrypt(plaintext)
