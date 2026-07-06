import json
from pathlib import Path
from typing import Dict, List, Any
from benchmark.config import ROOT_DIR


class WorkloadLoader:
    """Loads and parses workload configurations and metadata from the workloads directory."""

    def __init__(self, workloads_dir: Path = None):
        self.workloads_dir = workloads_dir or (ROOT_DIR / "workloads")

    def list_workloads(self) -> List[str]:
        """Lists all available workload names based on subdirectories in workloads/."""
        if not self.workloads_dir.exists():
            return []
        return [
            d.name for d in self.workloads_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def get_metadata(self, workload_name: str) -> Dict[str, Any]:
        """Retrieves metadata for a specific workload. Parses yaml structure cleanly."""
        workload_path = self.workloads_dir / workload_name
        metadata_file = workload_path / "metadata.yaml"
        
        metadata: Dict[str, Any] = {
            "name": workload_name,
            "path": str(workload_path),
            "dockerfiles": {}
        }

        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                in_dockerfiles = False
                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    
                    # Detect dockerfiles: section
                    if line.rstrip().endswith("dockerfiles:"):
                        in_dockerfiles = True
                        continue
                    # Any top-level key ends the nested dockerfiles block
                    elif not line.startswith(" ") and not line.startswith("\t"):
                        in_dockerfiles = False
                    
                    if ":" in stripped:
                        key, val = stripped.split(":", 1)
                        key = key.strip()
                        val = val.strip()
                        if in_dockerfiles:
                            metadata["dockerfiles"][key] = val
                        else:
                            metadata[key] = val
            except Exception:
                pass

        return metadata
