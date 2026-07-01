import json
from pathlib import Path
from typing import Any, Dict, Optional


class ArtifactStore:
    def __init__(self, reports_dir: str = "reports") -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def report_path(self, dataset_id: str) -> Path:
        return self.reports_dir / f"{dataset_id}.json"

    def save(self, dataset_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
        path = self.report_path(dataset_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=4)
        return report

    def load(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        path = self.report_path(dataset_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

