# -*- coding: utf-8 -*-
"""出图后的量化核对（可选特性，需要 Pillow）。

为什么需要它：视觉模型经常超时或连不上，而"这片画面是不是过曝/发灰"
其实可以用平均亮度 + 对比度两个数字粗略判断。把它们做成硬门槛，
就能在交付前自动拦下明显跑偏的图。

    pip install 'prompt-smith[quality]'
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

DEFAULT_GATE = {"brightness": [110, 175], "contrast_min": 60}


class QualityError(RuntimeError):
    """缺少可选依赖或图片无法读取。"""


def _pillow():
    try:
        from PIL import Image, ImageStat  # type: ignore
    except ImportError as exc:  # pragma: no cover - 取决于环境
        raise QualityError(
            "量化核对需要 Pillow：pip install 'prompt-smith[quality]'"
        ) from exc
    return Image, ImageStat


def measure(image_path: str) -> Dict[str, float]:
    """返回 {"brightness": 平均亮度, "contrast": 灰度标准差}。"""
    Image, ImageStat = _pillow()
    if not os.path.exists(image_path):
        raise QualityError("图片不存在：%s" % image_path)
    with Image.open(image_path) as img:
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        return {"brightness": round(stat.mean[0], 1), "contrast": round(stat.stddev[0], 1)}


def gate(image_path: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """按档案的质量门检查一张图，返回结论与数值。"""
    conf = dict(DEFAULT_GATE)
    conf.update((profile or {}).get("quality_gate") or {})
    low, high = conf["brightness"]
    contrast_min = conf["contrast_min"]

    values = measure(image_path)
    brightness, contrast = values["brightness"], values["contrast"]
    reasons: List[str] = []
    if brightness < low:
        reasons.append("过暗（%.1f < %s）" % (brightness, low))
    if brightness > high:
        reasons.append("过亮/过曝（%.1f > %s）" % (brightness, high))
    if contrast < contrast_min:
        reasons.append("发灰（对比度 %.1f < %s）" % (contrast, contrast_min))

    return {
        "image": image_path,
        "brightness": brightness,
        "contrast": contrast,
        "gate": {"brightness": [low, high], "contrast_min": contrast_min},
        "pass": not reasons,
        "reasons": reasons,
    }
