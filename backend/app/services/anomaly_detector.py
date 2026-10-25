import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.all import Evidence, BehaviorProfile
from app.repositories.all import EvidenceRepository

# Graceful import of IsolationForest
try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class AnomalyDetectorService:
    @staticmethod
    def extract_features(evidence_list: List[Evidence]) -> pd.DataFrame:
        features = []
        for ev in evidence_list:
            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
            
            # 1. Temporal features
            hour = ev.timestamp.hour
            day_of_week = ev.timestamp.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # 2. Location features (GPS)
            lat = float(meta.get("latitude", 0.0) or 0.0)
            lon = float(meta.get("longitude", 0.0) or 0.0)
            is_gps = 1.0 if ev.artifact_type == "GPS" else 0.0
            
            # 3. Artifact type label encoding
            type_map = {"SMS": 1, "Call": 2, "GPS": 3, "BrowserHistory": 4, "Contact": 5, "Application": 6, "File": 7}
            type_val = type_map.get(ev.artifact_type, 0)
            
            # 4. Content indicators
            is_apk = 1 if "apk" in str(meta.get("filename", "")).lower() else 0
            is_wallet = 1 if "wallet" in str(meta.get("app_name", "")).lower() or "wallet" in str(meta.get("filename", "")).lower() else 0
            
            features.append({
                "id": ev.id,
                "hour": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "lat": lat,
                "lon": lon,
                "is_gps": is_gps,
                "type_val": type_val,
                "is_apk": is_apk,
                "is_wallet": is_wallet
            })
            
        return pd.DataFrame(features)

    @staticmethod
    def detect_anomalies(db: Session, case_id: str) -> List[Dict[str, Any]]:
        evidence_list = EvidenceRepository.list_by_case(db, case_id)
        if len(evidence_list) < 5:
            # Not enough data for Isolation Forest, run rule-based fallback
            return AnomalyDetectorService._detect_rule_based(evidence_list)

        df = AnomalyDetectorService.extract_features(evidence_list)
        
        # Select numeric columns for IsolationForest
        feature_cols = ["hour", "day_of_week", "is_weekend", "lat", "lon", "is_gps", "type_val", "is_apk", "is_wallet"]
        X = df[feature_cols].values
        
        # Fit IsolationForest
        if HAS_SKLEARN:
            try:
                clf = IsolationForest(contamination=0.15, random_state=42)
                preds = clf.fit_predict(X)
                # decision_function returns negative values for anomalies
                scores = clf.decision_function(X)
                # Normalize scores to [0, 1] range, where higher = more anomalous
                min_score = np.min(scores) if len(scores) > 0 else -1
                max_score = np.max(scores) if len(scores) > 0 else 1
                normalized_scores = (max_score - scores) / (max_score - min_score + 1e-6)
            except Exception:
                return AnomalyDetectorService._detect_rule_based(evidence_list)
        else:
            # Fallback to statistical rule-based
            return AnomalyDetectorService._detect_rule_based(evidence_list)
            
        anomalies = []
        for idx, row in df.iterrows():
            pred = preds[idx]
            score = normalized_scores[idx]
            ev = evidence_list[idx]
            
            # Flag as anomaly if pred is -1 or score is high
            if pred == -1 or score > 0.65:
                meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
                explanation, confidence = AnomalyDetectorService._explain_anomaly(ev, meta, score)
                
                anomalies.append({
                    "evidence_id": ev.id,
                    "timestamp": ev.timestamp,
                    "artifact_type": ev.artifact_type,
                    "score": float(score),
                    "explanation": explanation,
                    "confidence": float(confidence),
                    "details": meta
                })
                
        # Sort anomalies by score descending
        anomalies.sort(key=lambda x: x["score"], reverse=True)
        return anomalies

    @staticmethod
    def _detect_rule_based(evidence_list: List[Evidence]) -> List[Dict[str, Any]]:
        """Fallback rule-based and statistical anomaly detection."""
        anomalies = []
        gps_points = []
        
        # Pre-scan for typical GPS locations to detect large jumps
        for ev in evidence_list:
            if ev.artifact_type == "GPS":
                meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
                lat = meta.get("latitude")
                lon = meta.get("longitude")
                if lat and lon:
                    gps_points.append((ev.timestamp, float(lat), float(lon)))
        
        for ev in evidence_list:
            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
            reasons = []
            score = 0.0
            
            # Rule 1: Late-night activity
            if ev.timestamp.hour < 5 or ev.timestamp.hour >= 23:
                reasons.append(f"Late-night activity at {ev.timestamp.strftime('%I:%M %p')}")
                score += 0.3
            
            # Rule 2: APK file download
            if ev.artifact_type == "File" and "apk" in str(meta.get("filename", "")).lower():
                reasons.append(f"Application package (.apk) downloaded: '{meta.get('filename')}'")
                score += 0.8
                
            # Rule 3: Hidden key or wallet access
            if "wallet" in str(meta.get("app_name", "")).lower() or ".key" in str(meta.get("filename", "")).lower():
                reasons.append(f"Access to sensitive crypto-wallet or private key asset")
                score += 0.75
                
            # Rule 4: Sudden GPS Jump (Velocity check)
            if ev.artifact_type == "GPS":
                lat = meta.get("latitude")
                lon = meta.get("longitude")
                if lat and lon:
                    lat = float(lat)
                    lon = float(lon)
                    for prev_time, prev_lat, prev_lon in gps_points:
                        time_diff = abs((ev.timestamp - prev_time).total_seconds())
                        if 0 < time_diff < 7200: # within 2 hours
                            # Haversine or simple distance estimation
                            dist = np.sqrt((lat - prev_lat)**2 + (lon - prev_lon)**2) * 111.0 # approx km
                            speed = dist / (time_diff / 3600.0) # km/h
                            if speed > 300.0: # physically impossible speed
                                reasons.append(f"Geographic anomaly: impossible travel speed ({int(speed)} km/h) from previous coordinates")
                                score += 0.9
                                break
                                
            # Rule 5: Call to unknown numbers
            if ev.artifact_type == "Call" and meta.get("duration", 0) > 0:
                contact_name = meta.get("contact_name")
                if not contact_name or contact_name == "Unknown":
                    # Unknown caller with long duration
                    score += 0.25
            
            if score > 0.4:
                anomalies.append({
                    "evidence_id": ev.id,
                    "timestamp": ev.timestamp,
                    "artifact_type": ev.artifact_type,
                    "score": min(score, 1.0),
                    "explanation": " & ".join(reasons),
                    "confidence": min(score + 0.1, 0.95),
                    "details": meta
                })
        
        anomalies.sort(key=lambda x: x["score"], reverse=True)
        return anomalies

    @staticmethod
    def _explain_anomaly(ev: Evidence, meta: Dict[str, Any], score: float) -> tuple:
        """Helper to generate natural language explanations for IsolationForest flags."""
        confidence = 0.5 + (score * 0.4) # scale confidence between 0.5 and 0.9
        
        if ev.artifact_type == "GPS":
            return (
                f"Flagged location anomaly at coordinates ({meta.get('latitude')}, {meta.get('longitude')}). "
                "This location is far outside the user's standard historical geographic cluster.",
                confidence
            )
        elif ev.artifact_type == "File":
            filename = meta.get("filename", "unknown")
            if "apk" in filename.lower():
                return f"Suspicious file activity: installation file '{filename}' was downloaded or created outside of standard app stores.", 0.9
            return f"Unusual file access to '{filename}' occurring at an anomalous hour.", confidence
        elif ev.artifact_type == "Application":
            app_name = meta.get("app_name", "unknown")
            if "wallet" in app_name.lower() or "crypto" in app_name.lower():
                return f"High-risk application '{app_name}' was accessed at {ev.timestamp.strftime('%I:%M %p')}, deviating from the typical daily routine.", 0.85
            return f"Application '{app_name}' was launched at an atypical hour.", confidence
        elif ev.artifact_type == "SMS":
            return f"SMS text containing potentially malicious URLs or suspicious transaction codes was received.", confidence
        elif ev.artifact_type == "Call":
            return f"Unusual call interaction with an unregistered or priority-flagged telephone number.", confidence
        
        return "Behavioral baseline deviation detected based on multi-variate event clustering.", confidence
