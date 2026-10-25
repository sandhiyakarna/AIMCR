# backend/modules/device_acquisition/device_detector.py

from typing import List, Dict, Any
from modules.device_acquisition.adb_manager import ADBManager

class DeviceDetector:
    @staticmethod
    def get_connected_devices() -> List[Dict[str, Any]]:
        """List all connected devices, retrieving detailed metadata properties for each device."""
        devices = ADBManager.list_devices()
        detailed_devices = []
        for dev in devices:
            device_id = dev["id"]
            model = dev["model"]
            status = dev["status"]
            dev_type = dev["type"]
            
            info = {}
            if status == "device":
                info = ADBManager.get_device_info(device_id)
                
            detailed_devices.append({
                "id": device_id,
                "model": model,
                "status": "Connected" if status == "device" else "Unauthorized" if status == "unauthorized" else status,
                "type": dev_type,
                "brand": info.get("ro.product.brand", "Unknown"),
                "os_version": info.get("ro.build.version.release", "Unknown"),
                "serial": info.get("ro.serialno", "Unknown"),
                "encrypted": info.get("ro.crypto.state", "Unknown") == "encrypted",
                "bootloader_locked": info.get("ro.boot.flash.locked", "1") == "1"
            })
        return detailed_devices
