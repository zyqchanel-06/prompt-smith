# -*- coding: utf-8 -*-
"""prompt-smith —— 槽位驱动的 SDXL / Danbooru 提示词构建框架。

    from promptsmith import load_profile, SlotRequest, compose

    profile = load_profile("profiles/example.json")
    result = compose(SlotRequest(outfit="black evening dress", scene="ballroom"), profile)
    print(result.positive)
    print(result.negative)

设计取向：纯规则、可解释、零依赖。不做 NLP 猜测——槽位由调用方填，
本库负责合成、自检、以及可选的质量门。
"""
from .builder import compose, dedupe, review, split_tags
from .profile import ProfileError, describe_profile, load_profile, normalize_profile
from .schema import (
    BuildResult,
    CheckItem,
    SLOT_LABELS,
    SLOT_ORDER,
    SlotRequest,
)

__version__ = "0.1.0"

__all__ = [
    "BuildResult",
    "CheckItem",
    "ProfileError",
    "SLOT_LABELS",
    "SLOT_ORDER",
    "SlotRequest",
    "compose",
    "dedupe",
    "describe_profile",
    "load_profile",
    "normalize_profile",
    "review",
    "split_tags",
    "__version__",
]
