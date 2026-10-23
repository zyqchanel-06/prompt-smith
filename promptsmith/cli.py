# -*- coding: utf-8 -*-
"""命令行入口：build / review / describe / gate。

    promptsmith build --profile profiles/example.json --subject "1girl, solo" --json
    promptsmith review --profile p.json --positive "anime style, ..."
    promptsmith describe --profile p.json
    promptsmith gate --image out/01.png --profile p.json
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .builder import compose, review
from .profile import ProfileError, describe_profile, load_profile
from .schema import SLOT_LABELS, SLOT_ORDER, SlotRequest


def _add_profile_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", "-p", required=True, help="档案路径（.json / .yaml）")


def _print_result(payload: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print("POSITIVE:")
    print("  " + payload["positive"])
    print("NEGATIVE:")
    print("  " + payload["negative"])
    checks = payload.get("checks") or []
    if checks:
        print("CHECK:")
        for item in checks:
            mark = {"error": "✗", "warn": "!", "info": "·"}.get(item["level"], "-")
            print("  %s [%s] %s" % (mark, item["code"], item["message"]))
    print("VERDICT:", "PASS" if payload["ok"] else "FAIL")


def cmd_build(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    request = SlotRequest(
        subject=args.subject or "",
        outfit=args.outfit or "",
        scene=args.scene or "",
        pose=args.pose or "",
        expression=args.expression or "",
        framing=args.framing or "",
        extra_positive=args.extra or "",
        extra_negative=args.extra_negative or "",
    )
    result = compose(request, profile)
    payload = result.as_dict()
    _print_result(payload, args.json)
    return 0 if result.ok else 1


def cmd_review(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    result = review(args.positive, args.negative or "", profile)
    payload = result.as_dict()
    _print_result(payload, args.json)
    return 0 if result.ok else 1


def cmd_describe(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(describe_profile(profile))
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    from .quality import QualityError, gate

    profile = load_profile(args.profile) if args.profile else None
    exit_code = 0
    for image in args.image:
        try:
            result = gate(image, profile)
        except QualityError as exc:
            print("ERROR:", exc)
            return 2
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            verdict = "PASS" if result["pass"] else "FAIL"
            print("%s  %s  亮度=%.1f 对比度=%.1f  %s"
                  % (verdict, result["image"], result["brightness"], result["contrast"],
                     "; ".join(result["reasons"])))
        if not result["pass"]:
            exit_code = 1
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promptsmith",
        description="槽位驱动的 SDXL / Danbooru 提示词构建框架",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="用档案把槽位合成提示词并自检")
    _add_profile_arg(p_build)
    for slot in SLOT_ORDER:
        p_build.add_argument("--" + slot, help="%s槽位" % SLOT_LABELS[slot])
    p_build.add_argument("--extra", help="额外的正向 tag（追加在最后）")
    p_build.add_argument("--extra-negative", help="额外的负向 tag")
    p_build.add_argument("--json", action="store_true", help="输出 JSON")
    p_build.set_defaults(func=cmd_build)

    p_review = sub.add_parser("review", help="对已有提示词跑自检")
    _add_profile_arg(p_review)
    p_review.add_argument("--positive", required=True)
    p_review.add_argument("--negative", default="")
    p_review.add_argument("--json", action="store_true")
    p_review.set_defaults(func=cmd_review)

    p_desc = sub.add_parser("describe", help="查看档案摘要")
    _add_profile_arg(p_desc)
    p_desc.add_argument("--json", action="store_true", help="输出完整档案 JSON")
    p_desc.set_defaults(func=cmd_describe)

    p_gate = sub.add_parser("gate", help="检查出图的亮度/对比度（需 Pillow）")
    p_gate.add_argument("--image", nargs="+", required=True, help="一张或多张图片")
    p_gate.add_argument("--profile", "-p", help="可选：用档案里的 quality_gate 阈值")
    p_gate.add_argument("--json", action="store_true")
    p_gate.set_defaults(func=cmd_gate)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ProfileError as exc:
        print("档案错误:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
