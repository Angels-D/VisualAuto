from dataclasses import dataclass, field
from enum import Enum
import uuid


class ActionType(Enum):
    DELAY = "延时"
    VISUAL = "视觉判断"
    MOUSE_MOVE = "鼠标移动"
    MOUSE_CLICK = "鼠标点击"
    JUMP = "跳转"
    SET_MATERIAL = "设置素材"


@dataclass
class Action:
    name: str = ""
    seq: int = 0
    action_type: ActionType = ActionType.DELAY
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    delay_ms: int = 0

    material_id: str = ""
    on_not_found_jump_seq: int = None
    on_found_jump_seq: int = None
    use_last_material: bool = False

    use_last_detected_pos: bool = False
    dest_x: int = 0
    dest_y: int = 0
    move_duration_ms: int = 0

    click_type: str = "single"

    jump_seq: int = None

    jump_if_material_id: str = ""
    jump_if_material_seq: int = None
    jump_else_seq: int = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "seq": self.seq,
            "action_type": self.action_type.value,
            "delay_ms": self.delay_ms,
            "material_id": self.material_id,
            "on_not_found_jump_seq": self.on_not_found_jump_seq,
            "on_found_jump_seq": self.on_found_jump_seq,
            "use_last_material": self.use_last_material,
            "use_last_detected_pos": self.use_last_detected_pos,
            "dest_x": self.dest_x,
            "dest_y": self.dest_y,
            "move_duration_ms": self.move_duration_ms,
            "click_type": self.click_type,
            "jump_seq": self.jump_seq,
            "jump_if_material_id": self.jump_if_material_id,
            "jump_if_material_seq": self.jump_if_material_seq,
            "jump_else_seq": self.jump_else_seq,
        }

    @staticmethod
    def from_dict(data: dict) -> "Action":
        return Action(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            seq=data.get("seq", 0),
            action_type=ActionType(data.get("action_type", "延时")),
            delay_ms=data.get("delay_ms", 0),
            material_id=data.get("material_id", ""),
            on_not_found_jump_seq=data.get("on_not_found_jump_seq"),
            on_found_jump_seq=data.get("on_found_jump_seq"),
            use_last_material=data.get("use_last_material", False),
            use_last_detected_pos=data.get("use_last_detected_pos", False),
            dest_x=data.get("dest_x", 0),
            dest_y=data.get("dest_y", 0),
            move_duration_ms=data.get("move_duration_ms", 0),
            click_type=data.get("click_type", "single"),
            jump_seq=data.get("jump_seq"),
            jump_if_material_id=data.get("jump_if_material_id", ""),
            jump_if_material_seq=data.get("jump_if_material_seq"),
            jump_else_seq=data.get("jump_else_seq"),
        )