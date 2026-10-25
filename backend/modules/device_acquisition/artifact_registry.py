# backend/modules/device_acquisition/artifact_registry.py

from typing import Dict, List, Any
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @property
    @abstractmethod
    def artifact_type(self) -> str:
        """Name of the forensic artifact category (e.g. Contact, SMS, Call)."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions this parser handles (e.g. ['.csv', '.json'])."""
        pass

    @property
    def priority(self) -> int:
        """Priority rating. Higher runs first."""
        return 1

    @abstractmethod
    def validate(self, file_path: str) -> bool:
        """Validate if this file matches the rules for this parser (e.g. checking schema/headers)."""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse file content and return list of forensic records. Each record should contain timestamp and metadata."""
        pass

class ParserRegistry:
    _parsers: List[BaseParser] = []

    @classmethod
    def register(cls, parser: BaseParser):
        """Register a parser instance."""
        cls._parsers.append(parser)
        # Sort by priority desc
        cls._parsers.sort(key=lambda p: p.priority, reverse=True)

    @classmethod
    def get_parsers(cls) -> List[BaseParser]:
        """Return all registered parsers."""
        return cls._parsers
