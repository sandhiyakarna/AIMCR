# backend/modules/device_acquisition/parser_router.py

import os
from typing import List, Dict, Any, Tuple
from modules.device_acquisition.artifact_registry import ParserRegistry
from modules.device_acquisition.artifact_detector import ArtifactDetector
import modules.device_acquisition.parser_factory

class ParserRouter:
    @staticmethod
    def route_and_parse(file_path: str) -> Tuple[str, str, List[Dict[str, Any]]]:
        """Routes file to correct parser, runs validation, and parses content.
        Returns:
            Tuple[detected_format, artifact_type, list_of_records]
        """
        fmt, artifact_type = ArtifactDetector.detect(file_path)
        
        parsers = ParserRegistry.get_parsers()
        matched_parser = None
        
        # 1. Try to find a specific parser that validates this file by name/heuristic
        for parser in parsers:
            if parser.priority <= 1:
                continue
            ext = os.path.splitext(file_path)[1].lower()
            if ext in parser.supported_extensions or "*" in parser.supported_extensions:
                try:
                    if parser.validate(file_path):
                        matched_parser = parser
                        break
                except Exception:
                    pass
        
        # 2. If no specific parser validated it, match based on detected artifact_type
        if not matched_parser:
            for parser in parsers:
                if parser.priority <= 1:
                    continue
                if parser.artifact_type == artifact_type:
                    if parser.__class__.__name__ == "MediaMetadataParser":
                        if not parser.validate(file_path):
                            continue
                    matched_parser = parser
                    break
                    
        # 3. Fallback to generic SQLiteDatabaseParser if format is SQLite
        if not matched_parser and fmt == "SQLite":
            for parser in parsers:
                if parser.artifact_type == "SQLiteDatabase":
                    matched_parser = parser
                    break
            
        # 4. Fallback to generic FileMetadataParser
        if not matched_parser:
            for parser in parsers:
                if parser.priority == 1: # FileMetadataParser
                    matched_parser = parser
                    break
                    
        records = []
        if matched_parser:
            try:
                records = matched_parser.parse(file_path)
                # Override artifact_type if matched a specific parser
                artifact_type = matched_parser.artifact_type
            except Exception as e:
                # Log parser failure gracefully
                print(f"Parser {matched_parser.__class__.__name__} failed: {e}")
        else:
            artifact_type = "Unsupported"

        return fmt, artifact_type, records
