from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Material:
    name: str = ""
    detect_region: tuple = (0, 0, 0, 0)
    image_path: str = ""
    threshold: float = 0.75
    target_pos: Optional[tuple] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "detect_region": list(self.detect_region),
            "image_path": self.image_path,
            "threshold": self.threshold,
            "target_pos": list(self.target_pos) if self.target_pos is not None else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "Material":
        tp = data.get("target_pos", None)
        return Material(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            detect_region=tuple(data.get("detect_region", [0, 0, 0, 0])),
            image_path=data.get("image_path", ""),
            threshold=data.get("threshold", 0.75),
            target_pos=tuple(tp) if tp is not None else None,
        )