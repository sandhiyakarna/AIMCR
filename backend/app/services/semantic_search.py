import json
import math
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.all import Evidence
from app.repositories.all import EvidenceRepository

# Attempt loading sentence_transformers and faiss
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False

class SemanticSearchService:
    _model = None
    _index_cache = {}  # case_id -> {"evidence_hash": hash, "index": faiss_index, "evidence_list": list}

    @classmethod
    def get_model(cls):
        if not HAS_SEMANTIC:
            return None
        if cls._model is None:
            try:
                # Load small 120MB CPU-friendly model
                cls._model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                return None
        return cls._model

    @staticmethod
    def get_evidence_description(ev: Evidence) -> str:
        meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
        timestamp_str = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        if ev.artifact_type == "SMS":
            return f"SMS message ID {ev.id} from {meta.get('phone_number', 'unknown')} at {timestamp_str}: '{meta.get('message', '')}'"
        elif ev.artifact_type == "Call":
            return f"Phone call log ID {ev.id} with {meta.get('contact_name', 'Unknown')} ({meta.get('phone_number', 'unknown')}) at {timestamp_str}, lasting {meta.get('duration', 0)} seconds, status {meta.get('status', 'unknown')}"
        elif ev.artifact_type == "BrowserHistory":
            return f"Chrome browser history log ID {ev.id} visiting URL '{meta.get('url', '')}' (Title: '{meta.get('title', '')}') at {timestamp_str}"
        elif ev.artifact_type == "GPS":
            return f"GPS location record ID {ev.id} at latitude {meta.get('latitude', '')}, longitude {meta.get('longitude', '')} at {timestamp_str}"
        elif ev.artifact_type == "Contact":
            return f"Contact book entry ID {ev.id}: name '{meta.get('name', '')}', phone number '{meta.get('phone_number', '')}' created at {timestamp_str}"
        elif ev.artifact_type == "Application":
            return f"Application run event ID {ev.id}: opened app package '{meta.get('app_name', '')}' at {timestamp_str}"
        elif ev.artifact_type == "File":
            return f"File modification log ID {ev.id}: file '{meta.get('filename', '')}' in directory '{meta.get('filepath', '')}', size {meta.get('filesize', 0)} bytes, modified at {timestamp_str}"
        
        return f"Forensic artifact ID {ev.id} of type {ev.artifact_type} at {timestamp_str}"

    @staticmethod
    def search(db: Session, case_id: str, query: str, top_k: int = 5) -> List[Tuple[Evidence, float]]:
        evidence_list = EvidenceRepository.list_by_case(db, case_id)
        if not evidence_list:
            return []

        # If packages are available, run true semantic vector search
        model = SemanticSearchService.get_model()
        if HAS_SEMANTIC and model is not None:
            try:
                import hashlib
                # Calculate current evidence state hash
                hasher = hashlib.sha256()
                for ev in evidence_list:
                    hasher.update(f"{ev.id}:{ev.hash}".encode('utf-8'))
                current_hash = hasher.hexdigest()
                
                cached = SemanticSearchService._index_cache.get(case_id)
                if cached and cached.get("evidence_hash") == current_hash:
                    # Cache hit! Reuse the FAISS index and ordered list
                    index = cached["index"]
                    cached_evidence = cached["evidence_list"]
                else:
                    # Cache miss or stale. Build index.
                    descriptions = [SemanticSearchService.get_evidence_description(ev) for ev in evidence_list]
                    doc_embeddings = model.encode(descriptions, show_progress_bar=False)
                    doc_embeddings = np.array(doc_embeddings).astype('float32')
                    dimension = doc_embeddings.shape[1]
                    
                    index = faiss.IndexFlatL2(dimension)
                    index.add(doc_embeddings)
                    
                    # Update cache
                    SemanticSearchService._index_cache[case_id] = {
                        "evidence_hash": current_hash,
                        "index": index,
                        "evidence_list": evidence_list
                    }
                    cached_evidence = evidence_list
                
                query_embedding = model.encode([query], show_progress_bar=False)
                query_embedding = np.array(query_embedding).astype('float32')
                
                # Search
                distances, indices = index.search(query_embedding, min(top_k, len(cached_evidence)))
                
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx != -1:
                        # Convert distance to a similarity score (0 to 1)
                        similarity = float(1.0 / (1.0 + distances[0][i]))
                        results.append((cached_evidence[idx], similarity))
                return results
            except Exception:
                pass  # Fallback to TF-IDF if FAISS/Transformers fail at runtime

        # Fallback: TF-IDF based keyword search in pure Python
        return SemanticSearchService._fallback_tfidf_search(evidence_list, query, top_k)

    @staticmethod
    def _fallback_tfidf_search(evidence_list: List[Evidence], query: str, top_k: int) -> List[Tuple[Evidence, float]]:
        """A simple, pure-Python TF-IDF similarity search as a robust fallback."""
        query_tokens = query.lower().split()
        if not query_tokens:
            return [(ev, 0.0) for ev in evidence_list[:top_k]]

        docs = []
        doc_tokens = []
        for ev in evidence_list:
            desc = SemanticSearchService.get_evidence_description(ev).lower()
            docs.append(ev)
            doc_tokens.append(desc.split())

        # Calculate IDF for each query token
        N = len(docs)
        idfs = {}
        for token in query_tokens:
            df = sum(1 for tokens in doc_tokens if token in tokens)
            idfs[token] = math.log((N + 1) / (df + 1)) + 1.0

        scores = []
        for idx, tokens in enumerate(doc_tokens):
            # Calculate similarity score based on term match and IDF weight
            score = 0.0
            for token in query_tokens:
                tf = tokens.count(token)
                if tf > 0:
                    score += tf * idfs[token]
            
            # Simple length normalization
            if len(tokens) > 0:
                score = score / math.sqrt(len(tokens))
            
            scores.append((docs[idx], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Normalize scores to 0-1 range
        max_score = scores[0][1] if scores else 0.0
        normalized_results = []
        for doc, raw_score in scores[:top_k]:
            sim = raw_score / max_score if max_score > 0 else 0.0
            normalized_results.append((doc, sim))
            
        return normalized_results
