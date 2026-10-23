# -*- coding: utf-8 -*-
"""数据模型：六槽位请求、构建结果、自检报告。

框架刻意保持"纯规则"——槽位由调用方（人或 LLM）填好，
本库负责把槽位 + 档案合成提示词，并给出可解释的自检结果。
不在这里做 NLP 猜测，行为才可复现。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# 六个槽位。顺序即提示词里的推荐排列顺序（详见 docs/prompt-anatomy.md）。
SLOT_ORDER = ("subject", "outfit", "scene", "pose", "expression", "framing")

SLOT_LABELS = {
    "subject": "人物",
    "outfit": "穿搭",
    "scene": "场景",
    "pose": "姿势动作",
    "expression": "表情氛围",
    "framing": "构图",
}


@dataclass
class SlotRequest:
    """一次出图需求的槽位描述。

    每个槽位可以是自由文本，也可以直接是逗号分隔的 Danbooru tag。
    留空的槽位会由档案里的默认值补齐 —— 用户不必每次都写全。
    """

    subject: str = ""
    outfit: str = ""
    scene: str = ""
    pose: str = ""
    expression: str = ""
    framing: str = ""
    extra_positive: str = ""
    extra_negative: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {name: getattr(self, name) for name in SLOT_ORDER}

    def filled_slots(self) -> List[str]:
        return [name for name in SLOT_ORDER if getattr(self, name).strip()]

    def empty_slots(self) -> List[str]:
        return [name for name in SLOT_ORDER if not getattr(self, name).strip()]


@dataclass
class CheckItem:
    """一条自检结果。level: info / warn / error。"""

    level: str
    code: str
    message: str
    slot: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        out: Dict[str, object] = {"level": self.level, "code": self.code, "message": self.message}
        if self.slot:
            out["slot"] = self.slot
        return out


@dataclass
class BuildResult:
    """构建结果：提示词 + 自检 + 元信息。"""

    positive: str
    negative: str
    profile_name: str
    trigger: str
    filled: List[str] = field(default_factory=list)
    defaults_used: List[str] = field(default_factory=list)
    checks: List[CheckItem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """没有 error 级自检项才算通过。"""
        return not any(item.level == "error" for item in self.checks)

    def errors(self) -> List[CheckItem]:
        return [item for item in self.checks if item.level == "error"]

    def warnings(self) -> List[CheckItem]:
        return [item for item in self.checks if item.level == "warn"]

    def as_dict(self) -> Dict[str, object]:
        return {
            "ok": self.ok,
            "profile": self.profile_name,
            "trigger": self.trigger,
            "positive": self.positive,
            "negative": self.negative,
            "filled": self.filled,
            "defaults_used": self.defaults_used,
            "checks": [item.as_dict() for item in self.checks],
        }
