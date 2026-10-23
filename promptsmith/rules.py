# -*- coding: utf-8 -*-
"""自检规则：在出图**之前**把问题拦下来。

每条规则都带 code，方便调用方按需忽略或统计。等级含义：
    error —— 必须修，构建视为不通过
    warn  —— 建议改，但不阻断
    info  —— 提示性信息
"""
from __future__ import annotations

from typing import Any, Dict, List

from .schema import BuildResult, CheckItem, SLOT_LABELS, SLOT_ORDER, SlotRequest


def _lower(text: str) -> str:
    return (text or "").lower()


def _has_tag(positive_lower: str, tag: str) -> bool:
    """判断一个必带项是否出现；带权重语法的标签按词根匹配。"""
    needle = _lower(tag).strip()
    if not needle:
        return True
    if needle in positive_lower:
        return True
    # (pale skin:1.25) 这类：去掉权重括号后按主干再比一次
    stem = needle
    if stem.startswith("(") and ":" in stem:
        stem = stem[1:].split(":")[0].strip()
    return stem in positive_lower


def check(build: BuildResult, request: SlotRequest, profile: Dict[str, Any]) -> List[CheckItem]:
    items: List[CheckItem] = []
    positive_lower = _lower(build.positive)

    # 1) 触发词必须在最前面 —— 它决定 LoRA / 画风能否生效
    if not build.positive.lower().startswith(_lower(profile["trigger"]).strip()):
        items.append(CheckItem("error", "TRIGGER_NOT_FIRST",
                               "正向提示词必须以触发词开头：%s" % profile["trigger"]))

    # 2) 必带项
    for tag in profile.get("required", []):
        if not _has_tag(positive_lower, tag):
            items.append(CheckItem("error", "MISSING_REQUIRED",
                                   "缺少必带项：%s" % tag))

    # 3) 红线词出现在正向里
    for tag in profile.get("forbidden", []):
        if _lower(tag) and _lower(tag) in positive_lower:
            items.append(CheckItem("error", "FORBIDDEN_TAG",
                                   "正向提示词出现红线词：%s（会破坏画风一致性）" % tag))

    # 4) 冲突词对同时出现
    for pair in profile.get("conflicts", []):
        both = _lower(pair["a"]) in positive_lower and _lower(pair["b"]) in positive_lower
        if both:
            reason = pair.get("reason") or "两者互斥"
            items.append(CheckItem("warn", "CONFLICT",
                                   "同时出现 %s 与 %s：%s" % (pair["a"], pair["b"], reason)))

    # 5) 空槽位提示（只提示，不阻断 —— 档案默认值已兜底）
    if request.filled_slots():
        for slot in request.empty_slots():
            if slot in build.defaults_used:
                continue
            items.append(CheckItem("info", "SLOT_EMPTY",
                                   "槽位「%s」为空且档案没有默认值" % SLOT_LABELS[slot], slot=slot))

    # 6) 负向提示词别为空 —— 没有负向基线时出图质量会明显不稳
    if not build.negative.strip():
        items.append(CheckItem("warn", "NEGATIVE_EMPTY",
                               "负向提示词为空：建议在档案里配置 negative_base"))

    # 7) 安全层：成年虚构形象声明（档案开启时）
    safety = profile.get("safety") or {}
    if safety.get("adult_only"):
        must = _lower(str(safety.get("require_phrase", ""))).strip()
        if must and must not in positive_lower:
            items.append(CheckItem("warn", "SAFETY_PHRASE_MISSING",
                                   "建议在正向词里显式声明：%s" % must))

    # 8) 提示词长度体检：SDXL 的 CLIP 对超长提示词会截断
    tag_count = len([t for t in build.positive.split(",") if t.strip()])
    limit = int(safety.get("max_tags", 75))
    if tag_count > limit:
        items.append(CheckItem("warn", "TOO_MANY_TAGS",
                               "提示词共 %d 个 tag，超过建议上限 %d，超出部分可能被 CLIP 截断" % (tag_count, limit)))

    return items
