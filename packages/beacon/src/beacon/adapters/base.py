from abc import ABC, abstractmethod

from beacon.schema import TelemetryRecord


class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, record: dict, project_slug: str) -> TelemetryRecord | None:
        """Parse a raw vendor record into a TelemetryRecord. Return None to skip."""
        ...
