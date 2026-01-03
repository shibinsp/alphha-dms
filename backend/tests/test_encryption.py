import pytest
import os

# Set test environment variables
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-bytes!!"

from app.utils.encryption import encrypt_data, decrypt_data, encrypt_bytes, decrypt_bytes


class TestEncryption:
    """Test encryption utilities."""

    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption."""
        original = "Hello, World! This is a test message."
        encrypted = encrypt_data(original)

        # Encrypted should be different from original
        assert encrypted != original

        # Decryption should return original
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_empty_string(self):
        """Test encryption of empty string."""
        original = ""
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_unicode(self):
        """Test encryption of unicode characters."""
        original = "Hello, World!"
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_bytes(self):
        """Test bytes encryption and decryption."""
        original = b"Binary data \x00\x01\x02\x03"
        encrypted = encrypt_bytes(original)

        # Encrypted should be different
        assert encrypted != original

        # Decryption should return original
        decrypted = decrypt_bytes(encrypted)
        assert decrypted == original

    def test_different_encryptions_differ(self):
        """Test that same data produces different ciphertexts (due to random salt)."""
        original = "Same message"
        encrypted1 = encrypt_data(original)
        encrypted2 = encrypt_data(original)

        # Different salts should produce different ciphertexts
        assert encrypted1 != encrypted2

        # Both should decrypt to same original
        assert decrypt_data(encrypted1) == original
        assert decrypt_data(encrypted2) == original

    def test_long_data(self):
        """Test encryption of large data."""
        original = "A" * 100000  # 100KB of data
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        assert decrypted == original
