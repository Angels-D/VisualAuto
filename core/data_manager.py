import json
import os
import sys
import shutil
from typing import Optional

from models.material import Material
from models.script_config import ScriptConfig


def _get_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DataManager:
    def __init__(self, data_dir: str = "data"):
        if not os.path.isabs(data_dir):
            data_dir = os.path.join(_get_base_path(), data_dir)
        self._data_dir = data_dir
        self._images_dir = os.path.join(data_dir, "images")
        self._materials_file = os.path.join(data_dir, "materials.json")
        self._scripts_file = os.path.join(data_dir, "scripts.json")

        self._materials: list[Material] = []
        self._script_config: ScriptConfig = ScriptConfig()

        os.makedirs(self._images_dir, exist_ok=True)
        self._cleanup_temp_files()

    @property
    def materials(self) -> list[Material]:
        return self._materials

    @property
    def script_config(self) -> ScriptConfig:
        return self._script_config

    def load_materials(self) -> list[Material]:
        if os.path.exists(self._materials_file):
            with open(self._materials_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._materials = [Material.from_dict(d) for d in data]
        else:
            self._materials = []
        return self._materials

    def save_materials(self):
        data = [m.to_dict() for m in self._materials]
        with open(self._materials_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_material(self, material: Material, source_image_path: Optional[str] = None):
        if source_image_path and os.path.exists(source_image_path):
            dest = os.path.join(self._images_dir, f"{material.id}.png")
            shutil.copy2(source_image_path, dest)
            material.image_path = f"images/{material.id}.png"
        self._materials.append(material)
        self.save_materials()

    def update_material(self, material: Material, source_image_path: Optional[str] = None):
        if source_image_path and os.path.exists(source_image_path):
            dest = os.path.join(self._images_dir, f"{material.id}.png")
            shutil.copy2(source_image_path, dest)
            material.image_path = f"images/{material.id}.png"
        for i, m in enumerate(self._materials):
            if m.id == material.id:
                self._materials[i] = material
                break
        self.save_materials()

    def delete_material(self, material_id: str):
        self._materials = [m for m in self._materials if m.id != material_id]
        img_path = os.path.join(self._images_dir, f"{material_id}.png")
        if os.path.exists(img_path):
            os.remove(img_path)
        self.save_materials()

    def _cleanup_temp_files(self):
        if not os.path.exists(self._images_dir):
            return
        for fname in os.listdir(self._images_dir):
            if fname.startswith("_temp_") and fname.endswith(".png"):
                try:
                    os.remove(os.path.join(self._images_dir, fname))
                except OSError:
                    pass

    def get_material(self, material_id: str) -> Optional[Material]:
        for m in self._materials:
            if m.id == material_id:
                return m
        return None

    def get_material_image_path(self, material: Material) -> str:
        if material.image_path:
            full = os.path.join(self._data_dir, material.image_path)
            if os.path.exists(full):
                return full
        return ""

    def load_scripts(self) -> ScriptConfig:
        if os.path.exists(self._scripts_file):
            with open(self._scripts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._script_config = ScriptConfig.from_dict(data)
        else:
            self._script_config = ScriptConfig()
        return self._script_config

    def save_scripts(self):
        data = self._script_config.to_dict()
        with open(self._scripts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_action(self, action):
        self._script_config.actions.append(action)
        self.save_scripts()

    def update_action(self, action):
        old_seq = None
        for i, a in enumerate(self._script_config.actions):
            if a.id == action.id:
                old_seq = a.seq
                self._script_config.actions[i] = action
                break
        if old_seq is not None and old_seq != action.seq:
            self._sync_seq_refs(old_seq, action.seq)
        self.save_scripts()

    def delete_action(self, action_id: str):
        deleted_seq = None
        for a in self._script_config.actions:
            if a.id == action_id:
                deleted_seq = a.seq
                break
        self._script_config.actions = [a for a in self._script_config.actions if a.id != action_id]
        if deleted_seq is not None:
            self._clear_seq_refs(deleted_seq)
        self.save_scripts()

    def _sync_seq_refs(self, old_seq: int, new_seq: int):
        for a in self._script_config.actions:
            if a.jump_seq == old_seq:
                a.jump_seq = new_seq
            if a.jump_if_material_seq == old_seq:
                a.jump_if_material_seq = new_seq
            if a.jump_else_seq == old_seq:
                a.jump_else_seq = new_seq
            if a.on_not_found_jump_seq == old_seq:
                a.on_not_found_jump_seq = new_seq
            if a.on_found_jump_seq == old_seq:
                a.on_found_jump_seq = new_seq

    def _clear_seq_refs(self, deleted_seq: int):
        for a in self._script_config.actions:
            if a.jump_seq == deleted_seq:
                a.jump_seq = None
            if a.jump_if_material_seq == deleted_seq:
                a.jump_if_material_seq = None
            if a.jump_else_seq == deleted_seq:
                a.jump_else_seq = None
            if a.on_not_found_jump_seq == deleted_seq:
                a.on_not_found_jump_seq = None
            if a.on_found_jump_seq == deleted_seq:
                a.on_found_jump_seq = None

    def get_available_seqs(self) -> list[int]:
        return [a.seq for a in self._script_config.actions]

    def is_seq_duplicate(self, seq: int, exclude_id: str = None) -> bool:
        for a in self._script_config.actions:
            if a.seq == seq:
                if exclude_id is None or a.id != exclude_id:
                    return True
        return False

    def insert_action_at_seq(self, action_id: str, new_seq: int):
        """将指定动作插入到 new_seq 位置（上方），已有动作及其后续动作的序号全部 +1"""
        current = None
        for a in self._script_config.actions:
            if a.id == action_id:
                current = a
                break
        if current is None:
            return

        old_seq = current.seq

        if old_seq == new_seq:
            return

        old_seq_map = {a.id: a.seq for a in self._script_config.actions}

        if new_seq < old_seq:
            for a in self._script_config.actions:
                if a.id != action_id and new_seq <= a.seq < old_seq:
                    a.seq += 1
        else:
            for a in self._script_config.actions:
                if a.id != action_id and old_seq < a.seq <= new_seq:
                    a.seq -= 1

        current.seq = new_seq

        mapping = {}
        for a in self._script_config.actions:
            old_s = old_seq_map.get(a.id)
            if old_s is not None and old_s != a.seq:
                mapping[old_s] = a.seq

        self._remap_all_seq_refs(mapping)
        self.save_scripts()

    def insert_new_action_at_seq(self, action, new_seq: int):
        """将新动作插入到 new_seq 位置，已有动作及其后续动作的序号全部 +1"""
        old_seq_map = {a.id: a.seq for a in self._script_config.actions}

        for a in self._script_config.actions:
            if a.seq >= new_seq:
                a.seq += 1

        action.seq = new_seq
        self._script_config.actions.append(action)

        mapping = {}
        for a in self._script_config.actions:
            old_s = old_seq_map.get(a.id)
            if old_s is not None and old_s != a.seq:
                mapping[old_s] = a.seq

        self._remap_all_seq_refs(mapping)
        self.save_scripts()

    def swap_action_seq(self, action_id: str, new_seq: int):
        target = None
        current = None
        for a in self._script_config.actions:
            if a.seq == new_seq and a.id != action_id:
                target = a
            if a.id == action_id:
                current = a
        if target is not None and current is not None:
            old_seq = current.seq
            current.seq = new_seq
            target.seq = old_seq
            self._remap_all_seq_refs({old_seq: new_seq, new_seq: old_seq})
            self.save_scripts()

    def _remap_all_seq_refs(self, mapping: dict):
        for a in self._script_config.actions:
            for attr in ("jump_seq", "jump_if_material_seq", "jump_else_seq",
                         "on_not_found_jump_seq", "on_found_jump_seq"):
                val = getattr(a, attr)
                if val is not None and val in mapping:
                    setattr(a, attr, mapping[val])