import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

settings = get_settings()

# Constants for key derivation
_SALT_LENGTH = 16
_ITERATIONS = 100000  # NIST recommended minimum


def _derive_key(password: bytes, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password))


def encrypt_data(data: str) -> str:
    """
    Encrypt string data using AES-256 with proper key derivation.
    Salt is prepended to the encrypted data for decryption.
    """
    salt = os.urandom(_SALT_LENGTH)
    key = _derive_key(settings.ENCRYPTION_KEY.encode(), salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    # Prepend salt to encrypted data
    combined = salt + encrypted
    return base64.urlsafe_b64encode(combined).decode()


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt string data using AES-256 with proper key derivation.
    Extracts salt from the beginning of the encrypted data.
    """
    try:
        combined = base64.urlsafe_b64decode(encrypted_data.encode())
        salt = combined[:_SALT_LENGTH]
        encrypted = combined[_SALT_LENGTH:]
        key = _derive_key(settings.ENCRYPTION_KEY.encode(), salt)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted).decode()
    except Exception:
        # Fallback for data encrypted with old method (no salt)
        return _decrypt_legacy(encrypted_data)


def _decrypt_legacy(encrypted_data: str) -> str:
    """Decrypt data encrypted with the old method (no PBKDF2, padded key)."""
    key = settings.ENCRYPTION_KEY.encode()
    if len(key) < 32:
        key = key.ljust(32, b'0')
    elif len(key) > 32:
        key = key[:32]
    key_b64 = base64.urlsafe_b64encode(key)
    fernet = Fernet(key_b64)
    return fernet.decrypt(encrypted_data.encode()).decode()


def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt bytes using AES-256 with proper key derivation."""
    salt = os.urandom(_SALT_LENGTH)
    key = _derive_key(settings.ENCRYPTION_KEY.encode(), salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)
    return salt + encrypted


def decrypt_bytes(encrypted_data: bytes) -> bytes:
    """Decrypt bytes using AES-256 with proper key derivation."""
    try:
        salt = encrypted_data[:_SALT_LENGTH]
        encrypted = encrypted_data[_SALT_LENGTH:]
        key = _derive_key(settings.ENCRYPTION_KEY.encode(), salt)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted)
    except Exception:
        # Fallback for data encrypted with old method
        return _decrypt_bytes_legacy(encrypted_data)


def _decrypt_bytes_legacy(encrypted_data: bytes) -> bytes:
    """Decrypt bytes encrypted with the old method."""
    key = settings.ENCRYPTION_KEY.encode()
    if len(key) < 32:
        key = key.ljust(32, b'0')
    elif len(key) > 32:
        key = key[:32]
    key_b64 = base64.urlsafe_b64encode(key)
    fernet = Fernet(key_b64)
    return fernet.decrypt(encrypted_data)


# Aliases for backwards compatibility
encrypt_value = encrypt_data
decrypt_value = decrypt_data
