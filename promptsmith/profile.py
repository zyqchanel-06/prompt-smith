# -*- coding: utf-8 -*-
"""档案（profile）加载与校验。

档案就是"某个人的口味"，格式为 JSON（零依赖）；
装了 PyYAML 时也可以直接用 YAML。字段见 profiles/example.yaml。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .schema import SLOT_ORDER


class ProfileError(ValueError):
    """档案不合法。"""


_REQUIRED_KEYS = ("name", "trigger", "quality")


def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - 取决于环境
        raise ProfileError(
            "读取 YAML 档案需要 PyYAML：pip install 'prompt-smith[yaml]'；"
            "或者把档案保存成 .json"
        ) from exc
    return yaml.safe_load(text)


def load_profile(path: str) -> Dict[str, Any]:
    """从 .json / .yaml / .yml 读档案并校验。"""
    if not os.path.exists(path):
        raise ProfileError("档案不存在：%s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        raw = _load_yaml(text)
    else:
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProfileError("档案不是合法 JSON：%s（%s）" % (path, exc)) from exc
    return normalize_profile(raw, source=path)


def _as_tag_list(value: Any, field: str) -> List[str]:
    """把 "a, b, c" 或 ["a","b","c"] 统一成 ["a","b","c"]。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ProfileError("%s 只能是字符串数组，收到 %r" % (field, item))
            if item.strip():
                out.append(item.strip())
        return out
    raise ProfileError("%s 必须是字符串或字符串数组，收到 %r" % (field, value))


def normalize_profile(raw: Any, source: str = "<memory>") -> Dict[str, Any]:
    """把任意输入收敛成框架认识的档案结构；不合法直接抛 ProfileError。"""
    if not isinstance(raw, dict):
        raise ProfileError("档案根节点必须是对象（%s）" % source)

    for key in _REQUIRED_KEYS:
        if key not in raw:
            raise ProfileError("档案缺少必填字段 %r（%s）" % (key, source))

    name = raw["name"]
    trigger = raw["trigger"]
    if not isinstance(name, str) or not name.strip():
        raise ProfileError("name 必须是非空字符串（%s）" % source)
    if not isinstance(trigger, str) or not trigger.strip():
        raise ProfileError("trigger 必须是非空字符串（触发词，会放在正向提示词最前）")

    profile: Dict[str, Any] = {
        "name": name.strip(),
        "description": str(raw.get("description", "")).strip(),
        "trigger": trigger.strip(),
        "quality": _as_tag_list(raw.get("quality"), "quality"),
        "negative_base": _as_tag_list(raw.get("negative_base"), "negative_base"),
        "slots": {},
        "required": _as_tag_list(raw.get("required"), "required"),
        "forbidden": _as_tag_list(raw.get("forbidden"), "forbidden"),
        "conflicts": [],
        "render": dict(raw.get("render") or {}),
        "quality_gate": dict(raw.get("quality_gate") or {}),
        "safety": dict(raw.get("safety") or {}),
    }

    if not profile["quality"]:
        raise ProfileError("quality 不能为空：至少给一条质量词，如 masterpiece")

    # 注意：不能用 raw.get("slots") or {} —— 空列表/空串会被静默当成 {}，
    # 那样"类型写错了"就变成了"没有配置"，配置错误被吞掉。
    slots_raw = raw.get("slots")
    if slots_raw is None:
        slots_raw = {}
    if not isinstance(slots_raw, dict):
        raise ProfileError("slots 必须是对象，收到 %s" % type(slots_raw).__name__)
    for slot in SLOT_ORDER:
        entry = slots_raw.get(slot)
        if entry is None:
            profile["slots"][slot] = {"default": "", "tags": []}
            continue
        if isinstance(entry, str):
            profile["slots"][slot] = {"default": entry.strip(), "tags": []}
            continue
        if not isinstance(entry, dict):
            raise ProfileError("slots.%s 必须是字符串或对象" % slot)
        profile["slots"][slot] = {
            "default": str(entry.get("default", "")).strip(),
            "tags": _as_tag_list(entry.get("tags"), "slots.%s.tags" % slot),
        }

    conflicts = raw.get("conflicts") or []
    if not isinstance(conflicts, list):
        raise ProfileError("conflicts 必须是数组")
    for item in conflicts:
        if not isinstance(item, dict):
            raise ProfileError('conflicts 的每一项必须是对象，形如 {"a": "...", "b": "...", "reason": "..."}')
        a, b = item.get("a"), item.get("b")
        if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
            raise ProfileError("conflicts 项缺少 a / b")
        profile["conflicts"].append({"a": a, "b": b, "reason": str(item.get("reason", "")).strip()})

    return profile


def describe_profile(profile: Dict[str, Any]) -> str:
    """人类可读的档案摘要（CLI 用）。"""
    lines = [
        "档案: %s" % profile["name"],
        "触发词: %s" % profile["trigger"],
        "质量词: %s" % ", ".join(profile["quality"]),
        "必带项: %s" % (", ".join(profile["required"]) or "(无)"),
        "红线词: %s" % (", ".join(profile["forbidden"]) or "(无)"),
        "槽位默认值:",
    ]
    for slot in SLOT_ORDER:
        entry = profile["slots"][slot]
        if entry["default"] or entry["tags"]:
            lines.append("  %-10s %s" % (slot, entry["default"] or ", ".join(entry["tags"])))
    gate = profile.get("quality_gate") or {}
    if gate:
        lines.append("质量门: 亮度 %s / 对比度 ≥ %s" % (gate.get("brightness", "-"), gate.get("contrast_min", "-")))
    safety = profile.get("safety") or {}
    if safety.get("adult_only"):
        lines.append("安全: 角色恒为成年虚构形象")
    return "\n".join(lines)
