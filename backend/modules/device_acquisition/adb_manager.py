# backend/modules/device_acquisition/adb_manager.py

import os
import json
import subprocess
import shutil
from typing import List, Dict, Any, Optional

class ADBManager:
    @staticmethod
    def is_adb_available() -> bool:
        """Check if adb CLI tool is installed and in system PATH."""
        return shutil.which("adb") is not None

    @classmethod
    def list_devices(cls) -> List[Dict[str, str]]:
        """List connected Android devices. If none or ADB missing, fallback to mock devices."""
        devices = []
        if cls.is_adb_available():
            try:
                res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
                lines = res.stdout.strip().split("\n")
                for line in lines[1:]: # Skip "List of devices attached"
                    if line.strip() and "\t" in line:
                        parts = line.split("\t")
                        device_id = parts[0]
                        status = parts[1]
                        
                        # Try to get model property
                        model = cls.get_device_model(device_id)
                        devices.append({
                            "id": device_id,
                            "model": model,
                            "status": status,
                            "type": "physical"
                        })
            except Exception:
                pass
                
        # Mock fallback for demonstration / testing / sandbox environment
        if not devices:
            devices.append({
                "id": "pixel_6_mock_001",
                "model": "Pixel 6 Pro (Forensic Mock)",
                "status": "device",
                "type": "emulated"
            })
            devices.append({
                "id": "samsung_s22_mock_002",
                "model": "Galaxy S22 Ultra (Forensic Mock)",
                "status": "unauthorized",
                "type": "emulated"
            })
            
        return devices

    @classmethod
    def get_device_model(cls, device_id: str) -> str:
        """Retrieve the device model name via adb shell getprop."""
        try:
            res = subprocess.run(
                ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"],
                capture_output=True, text=True, timeout=2
            )
            model = res.stdout.strip()
            if model:
                return model
        except Exception:
            pass
        return "Android Device"

    @classmethod
    def get_device_info(cls, device_id: str) -> Dict[str, str]:
        """Fetch all key-value hardware and OS system properties."""
        info = {}
        if device_id.endswith("_mock_001") or device_id.endswith("_mock_002"):
            # Emulated mock properties
            is_authorized = "unauthorized" not in device_id
            info = {
                "ro.product.model": "Pixel 6 Pro" if "pixel_6" in device_id else "Galaxy S22 Ultra",
                "ro.product.brand": "Google" if "pixel_6" in device_id else "Samsung",
                "ro.build.version.release": "13.0",
                "ro.build.version.sdk": "33",
                "ro.serialno": "FA59A120984" if "pixel_6" in device_id else "S22U920831",
                "ro.product.cpu.abi": "arm64-v8a",
                "ro.product.manufacturer": "Google" if "pixel_6" in device_id else "Samsung",
                "ro.build.fingerprint": "google/raven/raven:13/TQ1A.230205.002/9525287:user/release-keys",
                "ro.boot.flash.locked": "1",
                "ro.crypto.state": "encrypted",
                "ro.secure": "1",
                "adb_status": "Authorized" if is_authorized else "Unauthorized"
            }
        else:
            # Physical device extraction
            properties = [
                "ro.product.model", "ro.product.brand", "ro.build.version.release",
                "ro.build.version.sdk", "ro.serialno", "ro.product.cpu.abi",
                "ro.product.manufacturer", "ro.build.fingerprint", "ro.crypto.state"
            ]
            for prop in properties:
                try:
                    res = subprocess.run(
                        ["adb", "-s", device_id, "shell", "getprop", prop],
                        capture_output=True, text=True, timeout=1.5
                    )
                    info[prop] = res.stdout.strip()
                except Exception:
                    info[prop] = "Unknown"
            info["adb_status"] = "Authorized"
            
        return info

    @classmethod
    def scan_accessible_artifacts(cls, device_id: str) -> List[str]:
        """Scan standard device partitions and list available file paths for acquisition."""
        if device_id.endswith("_mock_001") or device_id.endswith("_mock_002"):
            # Mock files
            return [
                "/sdcard/forensics/contacts.csv",
                "/sdcard/forensics/sms_backup.json",
                "/sdcard/forensics/calls.csv",
                "/sdcard/forensics/gps_route.xml",
                "/sdcard/forensics/wifi_connections.json",
                "/sdcard/forensics/installed_packages.json",
                "/sdcard/forensics/device_properties.txt",
                "/sdcard/dcim/camera/IMG_20260720_1950.jpg",
                "/sdcard/dcim/camera/VID_20260720_1230.mp4",
                "/sdcard/download/evidence_log.txt",
                "/sdcard/download/corrupt_signature.png"
            ]
            
        # Physical device files scanning
        file_list = []
        try:
            # Look in typical directories for artifacts
            search_cmd = "find /sdcard/ -type f -maxdepth 3 \\( -name \"*.csv\" -o -name \"*.json\" -o -name \"*.xml\" -o -name \"*.db\" -o -name \"*.log\" -o -name \"*.txt\" -o -name \"*.jpg\" -o -name \"*.png\" -o -name \"*.mp4\" \\)"
            res = subprocess.run(
                ["adb", "-s", device_id, "shell", search_cmd],
                capture_output=True, text=True, timeout=5
            )
            for line in res.stdout.strip().split("\n"):
                if line.strip() and not line.startswith("find:"):
                    file_list.append(line.strip())
        except Exception:
            pass
        return file_list

    @classmethod
    def acquire_file(cls, device_id: str, remote_path: str, local_path: str) -> bool:
        """Copy file from device using adb pull or write mock data if emulated device."""
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        if device_id.endswith("_mock_001") or device_id.endswith("_mock_002"):
            filename = os.path.basename(remote_path)
            # Write synthetic forensic evidence to destination file
            try:
                if filename == "contacts.csv":
                    content = (
                        "first_name,last_name,phone,email\n"
                        "John,Doe,+15550011,john.doe@gmail.com\n"
                        "Jane,Smith,+15550022,jane.smith@yahoo.com\n"
                        "Robert,Johnson,+15550033,robert.j@work.com\n"
                    )
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                elif filename == "sms_backup.json":
                    content = [
                        {"sender": "+15550011", "recipient": "Me", "body": "Hey, meet at the library tonight", "timestamp": "2026-07-20T14:30:00"},
                        {"sender": "Me", "recipient": "+15550011", "body": "Understood, bringing the drive", "timestamp": "2026-07-20T14:32:00"},
                        {"sender": "+15550022", "recipient": "Me", "body": "Did you access the server? Code is 9982", "timestamp": "2026-07-20T15:10:00"}
                    ]
                    with open(local_path, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2)
                elif filename == "calls.csv":
                    content = (
                        "caller,duration,type,timestamp\n"
                        "+15550033,180,incoming,2026-07-20T09:12:00\n"
                        "+15550011,45,outgoing,2026-07-20T13:40:00\n"
                        "+15559999,0,missed,2026-07-20T17:15:00\n"
                    )
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                elif filename == "gps_route.xml":
                    content = (
                        "<?xml version='1.0' encoding='UTF-8'?>\n"
                        "<gpx version='1.1' creator='Mock Mobile GPS'>\n"
                        "  <wpt lat='34.0522' lon='-118.2437'>\n"
                        "    <time>2026-07-20T18:00:00Z</time>\n"
                        "    <name>LA Downtown</name>\n"
                        "  </wpt>\n"
                        "  <wpt lat='34.0407' lon='-118.2684'>\n"
                        "    <time>2026-07-20T18:15:00Z</time>\n"
                        "    <name>Crypto Arena</name>\n"
                        "  </wpt>\n"
                        "</gpx>\n"
                    )
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                elif filename == "wifi_connections.json":
                    content = [
                        {"ssid": "Target_Corp_WiFi", "bssid": "00:14:22:01:23:45", "security": "WPA2-Enterprise", "last_connected": "2026-07-20T10:00:00"},
                        {"ssid": "Home_Network_5G", "bssid": "c8:3a:35:88:99:aa", "security": "WPA3", "last_connected": "2026-07-20T19:40:00"}
                    ]
                    with open(local_path, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2)
                elif filename == "installed_packages.json":
                    content = [
                        {"app_name": "Signal", "package_name": "org.thoughtcrime.securesms", "version": "6.12.3", "install_time": "2026-07-01T12:00:00"},
                        {"app_name": "Tor Browser", "package_name": "org.torproject.torbrowser", "version": "12.5.1", "install_time": "2026-07-15T18:22:00"},
                        {"app_name": "Telegram", "package_name": "org.telegram.messenger", "version": "9.4.0", "install_time": "2026-07-10T11:00:00"}
                    ]
                    with open(local_path, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2)
                elif filename == "device_properties.txt":
                    content = (
                        "ro.product.model=Pixel 6 Pro\n"
                        "ro.build.version.release=13.0\n"
                        "ro.serialno=FA59A120984\n"
                    )
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                elif filename == "IMG_20260720_1950.jpg":
                    # Synthetic JPEG: valid magic bytes and SOF0 marker for 1920x1080 dimensions
                    header = (
                        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00"
                        b"\xff\xe1\x00\x1eExif\x00\x00II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                        b"\xff\xc0\x00\x11\x08\x04\x38\x07\x80\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01" # Height 1080 (0x0438), Width 1920 (0x0780)
                        b"\xff\xd9"
                    )
                    with open(local_path, "wb") as f:
                        f.write(header)
                elif filename == "VID_20260720_1230.mp4":
                    # Synthetic MP4 with mvhd and tkhd atoms
                    # ftyp box
                    ftyp = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
                    # moov container
                    moov_header = b"\x00\x00\x00\x70moov"
                    # mvhd box (duration = 60s at timescale = 1000)
                    mvhd = b"\x00\x00\x00\x68mvhd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\xea\x60\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02"
                    with open(local_path, "wb") as f:
                        f.write(ftyp + moov_header + mvhd)
                elif filename == "evidence_log.txt":
                    content = "2026-07-20 19:40:12 System starting up\n2026-07-20 19:45:00 USB Debugging authorized by host computer\n"
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                elif filename == "corrupt_signature.png":
                    # Extension is PNG, but magic bytes are garbage (will trigger validation error)
                    with open(local_path, "wb") as f:
                        f.write(b"NOT_A_PNG_FILE_SIGNATURE_TRICKY_FORENSICS_CORRUPTION")
                else:
                    # Catch-all empty text file
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write("Forensic target extracted")
                return True
            except Exception:
                return False
        else:
            # Physical pull execution
            try:
                res = subprocess.run(["adb", "-s", device_id, "pull", remote_path, local_path], capture_output=True, text=True, timeout=10)
                return res.returncode == 0
            except Exception:
                return False
