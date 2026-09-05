from dataclasses import dataclass, field
from .action import Action


@dataclass
class ScriptConfig:
    hotkey: str = "Ctrl+Shift+F1"
    actions: list[Action] = field(default_factory=list)
    auto_restart_on_crash: bool = True
    preserve_run_state: bool = False

    def to_dict(self) -> dict:
        return {
            "hotkey": self.hotkey,
            "actions": [a.to_dict() for a in self.actions],
            "auto_restart_on_crash": self.auto_restart_on_crash,
            "preserve_run_state": self.preserve_run_state,
        }

    @staticmethod
    def from_dict(data: dict) -> "ScriptConfig":
        return ScriptConfig(
            hotkey=data.get("hotkey", "Ctrl+Shift+F1"),
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            auto_restart_on_crash=data.get("auto_restart_on_crash", True),
            preserve_run_state=data.get("preserve_run_state", False),
        )