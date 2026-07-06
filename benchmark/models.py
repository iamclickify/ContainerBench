from dataclasses import dataclass
from datetime import datetime


@dataclass
class Experiment:
    workload: str
    strategy: str
    dockerfile: str
    image_tag: str
    build_type: str

    build_time: float = 0.0
    image_size_mb: float = 0.0
    status: str = "PENDING"
    notes: str = ""

    timestamp: str = datetime.now().isoformat()