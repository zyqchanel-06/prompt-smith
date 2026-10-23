# -*- coding: utf-8 -*-
"""提示词构建：槽位 + 档案 → positive / negative。

构建规则（与 docs/prompt-anatomy.md 一致）：
    trigger → quality → subject → outfit → scene → pose → expression → framing → extra
同一个 tag 只保留第一次出现的位置；留空的槽位用档案默认值补齐并记录。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import rules
from .schema import BuildResult, SLOT_ORDER, SlotRequest


def split_tags(text: str) -> List[str]:
    """按逗号切 tag，保留 (tag:1.2) 这类权重语法里的逗号。"""
    if not text:
        return []
    out: List[str] = []
    depth = 0
    current: List[str] = []
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")" and depth > 0:
            depth -= 1
        if char == "," and depth == 0:
            tag = "".join(current).strip()
            if tag:
                out.append(tag)
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        out.append(tail)
    return out


def dedupe(tags: List[str]) -> List[str]:
    """去重但保留首次出现顺序（大小写不敏感）。"""
    seen = set()
    out: List[str] = []
    for tag in tags:
        key = tag.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(tag.strip())
    return out


def compose(request: SlotRequest, profile: Dict[str, Any]) -> BuildResult:
    """按档案把槽位合成提示词，并跑一遍自检。"""
    positive_parts: List[str] = [profile["trigger"]]
    positive_parts.extend(profile["quality"])

    filled: List[str] = []
    defaults_used: List[str] = []

    for slot in SLOT_ORDER:
        text = (getattr(request, slot) or "").strip()
        if text:
            filled.append(slot)
        else:
            default = profile["slots"].get(slot, {}).get("default", "")
            if default:
                text = default
                defaults_used.append(slot)
        if text:
            positive_parts.append(text)

    extra = (request.extra_positive or "").strip()
    if extra:
        positive_parts.append(extra)

    positive_tags = dedupe(split_tags(", ".join(positive_parts)))
    positive = ", ".join(positive_tags)

    negative_tags = dedupe(
        split_tags(", ".join(profile.get("negative_base", []) + split_tags(request.extra_negative or "")))
    )
    negative = ", ".join(negative_tags)

    result = BuildResult(
        positive=positive,
        negative=negative,
        profile_name=profile["name"],
        trigger=profile["trigger"],
        filled=filled,
        defaults_used=defaults_used,
    )
    result.checks = rules.check(result, request, profile)
    return result


def review(positive: str, negative: str, profile: Dict[str, Any]) -> BuildResult:
    """对一份**已有**提示词跑自检（不重新构建）。

    适合场景：提示词是别处生成的，只想用本框架的规则体检一遍。
    """
    result = BuildResult(
        positive=positive.strip(),
        negative=negative.strip(),
        profile_name=profile["name"],
        trigger=profile["trigger"],
    )
    result.checks = rules.check(result, SlotRequest(), profile)
    return result
