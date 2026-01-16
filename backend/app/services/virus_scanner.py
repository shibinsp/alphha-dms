"""Virus Scanning Service using ClamAV"""
import socket
import struct
from typing import Tuple, Optional
from io import BytesIO

from app.core.config import settings


class VirusScanResult:
    def __init__(self, is_clean: bool, threat_name: Optional[str] = None, error: Optional[str] = None):
        self.is_clean = is_clean
        self.threat_name = threat_name
        self.error = error


class ClamAVScanner:
    """ClamAV virus scanner client."""
    
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.CLAMAV_HOST
        self.port = port or settings.CLAMAV_PORT
    
    def _send_command(self, command: bytes, data: bytes = None) -> str:
        """Send command to ClamAV daemon."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(30)
                sock.connect((self.host, self.port))
                
                if data:
                    # INSTREAM command for scanning data
                    sock.send(b"zINSTREAM\0")
                    
                    # Send data in chunks
                    stream = BytesIO(data)
                    while True:
                        chunk = stream.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        sock.send(struct.pack("!I", len(chunk)))
                        sock.send(chunk)
                    
                    # Send zero-length chunk to indicate end
                    sock.send(struct.pack("!I", 0))
                else:
                    sock.send(command)
                
                # Receive response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\0" in response:
                        break
                
                return response.decode("utf-8").strip("\0").strip()
        
        except socket.timeout:
            return "ERROR: Connection timeout"
        except ConnectionRefusedError:
            return "ERROR: ClamAV not available"
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def ping(self) -> bool:
        """Check if ClamAV is running."""
        response = self._send_command(b"zPING\0")
        return response == "PONG"
    
    def version(self) -> str:
        """Get ClamAV version."""
        return self._send_command(b"zVERSION\0")
    
    def scan_bytes(self, data: bytes) -> VirusScanResult:
        """Scan bytes for viruses."""
        if not settings.VIRUS_SCAN_ENABLED:
            return VirusScanResult(is_clean=True)
        
        response = self._send_command(b"", data)
        
        if response.startswith("ERROR"):
            return VirusScanResult(is_clean=False, error=response)
        
        # Parse response: "stream: OK" or "stream: VirusName FOUND"
        if "OK" in response:
            return VirusScanResult(is_clean=True)
        elif "FOUND" in response:
            # Extract virus name
            parts = response.split(":")
            if len(parts) >= 2:
                threat = parts[1].replace("FOUND", "").strip()
                return VirusScanResult(is_clean=False, threat_name=threat)
            return VirusScanResult(is_clean=False, threat_name="Unknown threat")
        else:
            return VirusScanResult(is_clean=False, error=f"Unexpected response: {response}")
    
    def scan_file(self, file_path: str) -> VirusScanResult:
        """Scan a file for viruses."""
        try:
            with open(file_path, "rb") as f:
                return self.scan_bytes(f.read())
        except Exception as e:
            return VirusScanResult(is_clean=False, error=str(e))


# Singleton scanner instance
_scanner: Optional[ClamAVScanner] = None


def get_scanner() -> ClamAVScanner:
    """Get or create scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = ClamAVScanner()
    return _scanner


def scan_file_content(content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Scan file content for viruses.
    Returns (is_clean, error_or_threat_name)
    """
    if not settings.VIRUS_SCAN_ENABLED:
        return True, None
    
    scanner = get_scanner()
    result = scanner.scan_bytes(content)
    
    if result.error:
        # Log error but allow upload if scanner unavailable
        print(f"Virus scan error: {result.error}")
        return True, f"Warning: {result.error}"
    
    if not result.is_clean:
        return False, result.threat_name
    
    return True, None
