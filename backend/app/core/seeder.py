import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.all import User, Case, Evidence, ThreatIndicator
from app.core.security import get_password_hash
from app.repositories.all import UserRepository, CaseRepository, EvidenceRepository

SEED_CASE_TITLE = "Case #2026-089A: Phishing & Wallet Takeover"

SEED_USER_EMAILS = {
    "investigator@aimcr.gov",
    "admin@aimcr.gov",
    "auditor@aimcr.gov",
}


def seed_database(db: Session):
    seed_occurred = False

    # 0. Seed Threat Indicators (idempotent: checked by type+value pairs)
    if not db.query(ThreatIndicator).first():
        threats = [
            ThreatIndicator(
                indicator_type="phone_number",
                value="+18005550199",
                threat_name="Phishing SMS Sender",
                severity="High",
                description="Known sender of banking credential phishing messages."
            ),
            ThreatIndicator(
                indicator_type="domain",
                value="secure-auth-bank.net",
                threat_name="Phishing Domain",
                severity="Critical",
                description="Malicious domain impersonating a secure banking portal."
            ),
            ThreatIndicator(
                indicator_type="url",
                value="http://secure-auth-bank.net/login",
                threat_name="Suspicious URL",
                severity="Critical",
                description="Direct URL hosting a credential harvesting form."
            ),
            ThreatIndicator(
                indicator_type="package_name",
                value="com.crypto.wallet",
                threat_name="Malicious Package",
                severity="High",
                description="Package associated with unauthorized crypto-assets transfer."
            ),
            ThreatIndicator(
                indicator_type="hash",
                value="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a13",
                threat_name="bank_update.apk hash",
                severity="Critical",
                description="SHA-256 hash of malicious banking update package."
            )
        ]
        db.add_all(threats)
        db.commit()
        seed_occurred = True

    # 1. Seed Users (idempotent: skip already-existing emails)
    seeded_users = {}
    for email in SEED_USER_EMAILS:
        user = db.query(User).filter(User.email == email).first()
        if user:
            seeded_users[email] = user
            continue

        if email == "investigator@aimcr.gov":
            user = User(
                name="Lead Investigator John",
                email=email,
                password_hash=get_password_hash("password123"),
                role="Investigator"
            )
        elif email == "admin@aimcr.gov":
            user = User(
                name="System Admin",
                email=email,
                password_hash=get_password_hash("admin123"),
                role="Admin"
            )
        elif email == "auditor@aimcr.gov":
            user = User(
                name="Compliance Auditor",
                email=email,
                password_hash=get_password_hash("auditor123"),
                role="Auditor"
            )

        db.add(user)
        db.flush()  # get the ID without committing yet
        seeded_users[email] = user
        seed_occurred = True

    if seed_occurred:
        db.commit()

    # All three seed users are guaranteed to be in seeded_users after the loop above
    investigator = seeded_users["investigator@aimcr.gov"]

    # 2. Seed the default case (idempotent: checked by title)
    case = db.query(Case).filter(Case.title == SEED_CASE_TITLE).first()
    if not case:
        case = Case(
            title=SEED_CASE_TITLE,
            description="Investigation into mobile phishing link, malicious package download (.apk), and unauthorized crypto-wallet drainage on device.",
            status="Active",
            investigator_id=investigator.id
        )
        db.add(case)
        db.commit()
        seed_occurred = True

    # 3. Seed Evidence (idempotent: checked by case + known hashes)
    seeded_hashes = {
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a11",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a12",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a13",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a14",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a15",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a16",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a17",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a18",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a19",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a20",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a21",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a22",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a23",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a24",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a25",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a26",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a27",
        "5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a28",
    }

    # Find which seeded hashes already exist in evidence for this case
    existing_hashes = set()
    if case:
        existing_evidence = db.query(Evidence.hash).filter(
            Evidence.case_id == case.id,
            Evidence.hash.in_(seeded_hashes)
        ).all()
        existing_hashes = {row[0] for row in existing_evidence}

    missing_hashes = seeded_hashes - existing_hashes

    if missing_hashes:
        base_time = datetime.now() - timedelta(hours=4)

        evidence_map = {}

        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a11"] = Evidence(
            case_id=case.id, artifact_type="SMS", source="SMS_Backup_2026.xml",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a11",
            timestamp=base_time,
            metadata_json=json.dumps({"phone_number": "+18005550199", "contact_name": "Unknown", "message": "CRITICAL: Your bank account is suspended. Verify immediately at http://secure-auth-bank.net/login"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a12"] = Evidence(
            case_id=case.id, artifact_type="BrowserHistory", source="Chrome_History.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a12",
            timestamp=base_time + timedelta(minutes=1, seconds=30),
            metadata_json=json.dumps({"url": "http://secure-auth-bank.net/login", "title": "Secure Bank Authentication Portal", "visit_count": 1, "typed_count": 0})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a13"] = Evidence(
            case_id=case.id, artifact_type="File", source="Downloads_Index.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a13",
            timestamp=base_time + timedelta(minutes=2),
            metadata_json=json.dumps({"filename": "bank_update.png", "filepath": "/sdcard/Downloads/bank_update.png", "filesize": 1420590, "permission": "rw-r--r--", "mime_type": "application/vnd.android.package-archive", "magic_bytes": "504B0304"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a14"] = Evidence(
            case_id=case.id, artifact_type="Application", source="App_Usage_Stats.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a14",
            timestamp=base_time + timedelta(minutes=3),
            metadata_json=json.dumps({"app_name": "com.android.settings", "class_name": "com.android.settings.Settings$AppInfoDashboardActivity", "duration_ms": 12400})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a15"] = Evidence(
            case_id=case.id, artifact_type="Application", source="App_Usage_Stats.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a15",
            timestamp=base_time + timedelta(minutes=6),
            metadata_json=json.dumps({"app_name": "com.bank.mobileapp", "class_name": "com.bank.mobileapp.MainActivity", "duration_ms": 45000})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a16"] = Evidence(
            case_id=case.id, artifact_type="SMS", source="SMS_Backup_2026.xml",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a16",
            timestamp=base_time + timedelta(minutes=6, seconds=30),
            metadata_json=json.dumps({"phone_number": "+18005550100", "contact_name": "Bank Alerts", "message": "Your OTP code for transfer of $5,000.00 is 882910. NEVER share this code with anyone."})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a17"] = Evidence(
            case_id=case.id, artifact_type="GPS", source="Location_History.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a17",
            timestamp=base_time - timedelta(minutes=10),
            metadata_json=json.dumps({"latitude": "40.7128", "longitude": "-74.0060", "accuracy": 15.0})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a18"] = Evidence(
            case_id=case.id, artifact_type="GPS", source="Location_History.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a18",
            timestamp=base_time + timedelta(hours=2),
            metadata_json=json.dumps({"latitude": "40.7130", "longitude": "-74.0058", "accuracy": 10.0})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a19"] = Evidence(
            case_id=case.id, artifact_type="GPS", source="Location_History.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a19",
            timestamp=base_time + timedelta(hours=2, minutes=1),
            metadata_json=json.dumps({"latitude": "34.0522", "longitude": "-118.2437", "accuracy": 20.0})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a20"] = Evidence(
            case_id=case.id, artifact_type="Application", source="App_Usage_Stats.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a20",
            timestamp=base_time + timedelta(hours=3, minutes=30),
            metadata_json=json.dumps({"app_name": "com.crypto.wallet", "class_name": "com.crypto.wallet.UnlockActivity", "duration_ms": 15600})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a21"] = Evidence(
            case_id=case.id, artifact_type="File", source="Downloads_Index.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a21",
            timestamp=base_time + timedelta(hours=3, minutes=32),
            metadata_json=json.dumps({"filename": ".wallet_backup.key", "filepath": "/sdcard/Documents/Keys/.wallet_backup.key", "filesize": 256, "permission": "r--------"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a22"] = Evidence(
            case_id=case.id, artifact_type="Contact", source="Contacts.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a22",
            timestamp=base_time - timedelta(days=5),
            metadata_json=json.dumps({"name": "Mom", "phone_number": "+12125550110", "email": "mom@family.org"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a23"] = Evidence(
            case_id=case.id, artifact_type="Contact", source="Contacts.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a23",
            timestamp=base_time - timedelta(days=5),
            metadata_json=json.dumps({"name": "Office Partner", "phone_number": "+12125550120", "email": "partner@firm.com"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a24"] = Evidence(
            case_id=case.id, artifact_type="SMS", source="SMS_Backup_2026.xml",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a24",
            timestamp=base_time - timedelta(hours=1),
            metadata_json=json.dumps({"phone_number": "+12125550110", "contact_name": "Mom", "message": "Hey honey, call me when you can!"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a25"] = Evidence(
            case_id=case.id, artifact_type="SMS", source="SMS_Backup_2026.xml",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a25",
            timestamp=base_time - timedelta(hours=1, minutes=30),
            metadata_json=json.dumps({"phone_number": "+12125550120", "contact_name": "Office Partner", "message": "Sent over the weekly brief report."})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a26"] = Evidence(
            case_id=case.id, artifact_type="File", source="FileSystem.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a26",
            timestamp=base_time + timedelta(hours=3, minutes=35),
            metadata_json=json.dumps({"filename": "confidential_transfers.xlsx", "filepath": "/sdcard/Documents/confidential_transfers.xlsx", "filesize": 10240, "created_time": (base_time + timedelta(hours=3, minutes=35)).isoformat(), "modified_time": "1970-01-01T00:00:00Z"})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a27"] = Evidence(
            case_id=case.id, artifact_type="File", source="FileSystem.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a27",
            timestamp=base_time + timedelta(hours=3, minutes=40),
            metadata_json=json.dumps({"filename": "incognito_history.db", "filepath": "/sdcard/data/com.android.chrome/app_chrome/incognito_history.db", "filesize": 0, "is_sqlite": True, "tables": []})
        )
        evidence_map["5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a28"] = Evidence(
            case_id=case.id, artifact_type="Application", source="App_Usage_Stats.db",
            hash="5a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a1b3c5e8d7f2a28",
            timestamp=base_time - timedelta(hours=1),
            metadata_json=json.dumps({"app_name": "com.piriform.ccleaner", "class_name": "com.piriform.ccleaner.MainActivity", "duration_ms": 32000})
        )

        new_evidence = [evidence_map[h] for h in sorted(missing_hashes)]
        db.add_all(new_evidence)
        db.commit()
        seed_occurred = True

    if seed_occurred:
        print("Database seeding completed.")
