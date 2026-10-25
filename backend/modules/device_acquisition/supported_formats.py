# backend/modules/device_acquisition/supported_formats.py

SUPPORTED_EXTENSIONS = {
    # Text/Structured
    ".csv", ".json", ".xml", ".txt", ".log", ".html",
    # Documents
    ".pdf",
    # Databases
    ".db", ".sqlite", ".sqlite3",
    # Media (Images, Videos, Audio)
    ".jpg", ".jpeg", ".png", ".heic",
    ".mp4", ".avi", ".mov",
    ".mp3", ".wav", ".aac",
    # Archives
    ".zip", ".tar", ".gz", ".gzip"
}

MIME_TYPE_MAPPING = {
    "application/json": "JSON",
    "text/csv": "CSV",
    "text/plain": "TXT",
    "text/xml": "XML",
    "application/xml": "XML",
    "application/x-sqlite3": "SQLite",
    "application/vnd.sqlite3": "SQLite",
    "application/pdf": "PDF",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/heic": "HEIC",
    "video/mp4": "MP4",
    "video/x-msvideo": "AVI",
    "video/quicktime": "MOV",
    "audio/mpeg": "MP3",
    "audio/wav": "WAV",
    "audio/x-wav": "WAV",
    "audio/aac": "AAC",
    "application/zip": "ZIP",
    "application/x-tar": "TAR",
    "application/gzip": "GZIP",
    "application/x-gzip": "GZIP"
}

# Mapping of file names or common search terms to evidence types
FILENAME_TO_ARTIFACT_TYPE = {
    "contacts": "Contact",
    "contact": "Contact",
    "sms": "SMS",
    "message": "SMS",
    "messages": "SMS",
    "call": "Call",
    "calls": "Call",
    "calllog": "Call",
    "calllogs": "Call",
    "browser": "BrowserHistory",
    "history": "BrowserHistory",
    "chrome": "BrowserHistory",
    "gps": "GPS",
    "location": "GPS",
    "locations": "GPS",
    "gpx": "GPS",
    "app": "Application",
    "apps": "Application",
    "installed": "Application",
    "download": "File",
    "downloads": "File",
    "wifi": "WiFi",
    "bluetooth": "Bluetooth",
    "notification": "Notification",
    "notifications": "Notification",
    "device": "DeviceInformation",
    "device_info": "DeviceInformation",
    "timeline": "TimelineEvent",
    "system": "SystemLogs",
    "audit": "SystemLogs",
    "log": "SystemLogs",
    "logs": "SystemLogs"
}
