# -*- coding: utf-8 -*-
"""核心行为测试：构建顺序、去重、自检规则、档案校验。

跑法：python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promptsmith import ProfileError, SlotRequest, compose, load_profile, normalize_profile, review, split_tags  # noqa: E402
from promptsmith.builder import dedupe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(os.path.dirname(HERE), "profiles", "example.json")


def load_example():
    return load_profile(PROFILE_PATH)


class TestSplitTags(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(split_tags("a, b, c"), ["a", "b", "c"])

    def test_weight_syntax_keeps_inner_comma(self):
        # 权重括号里的逗号不该被切开
        self.assertEqual(
            split_tags("(pale skin:1.2), (red hair, blue eyes:1.1)"),
            ["(pale skin:1.2)", "(red hair, blue eyes:1.1)"],
        )

    def test_empty(self):
        self.assertEqual(split_tags(""), [])
        self.assertEqual(split_tags("  ,  , "), [])


class TestDedupe(unittest.TestCase):
    def test_keeps_first_order(self):
        self.assertEqual(dedupe(["a", "b", "a", "A"]), ["a", "b"])

    def test_strips(self):
        self.assertEqual(dedupe([" a ", "a"]), ["a"])


class TestCompose(unittest.TestCase):
    def setUp(self):
        self.profile = load_example()

    def test_trigger_first_and_quality_second(self):
        result = compose(SlotRequest(subject="1girl"), self.profile)
        self.assertTrue(result.positive.startswith("anime style"))
        self.assertIn("masterpiece", result.positive)

    def test_slot_order_followed(self):
        request = SlotRequest(subject="1girl", outfit="red dress", scene="forest",
                              pose="standing", expression="smile", framing="full body")
        result = compose(request, self.profile)
        idx = [result.positive.index(t) for t in
               ["1girl", "red dress", "forest", "standing", "smile", "full body"]]
        self.assertEqual(idx, sorted(idx), "槽位顺序必须按 subject→outfit→scene→pose→expression→framing")

    def test_empty_slot_uses_default(self):
        result = compose(SlotRequest(subject="1girl"), self.profile)
        # 档案里 pose 默认 looking at viewer
        self.assertIn("looking at viewer", result.positive)
        self.assertIn("pose", result.defaults_used)

    def test_extra_positive_appended(self):
        result = compose(SlotRequest(subject="1girl", extra_positive="cinematic lighting"), self.profile)
        self.assertIn("cinematic lighting", result.positive)
        self.assertTrue(result.positive.endswith("cinematic lighting"))

    def test_negative_contains_base(self):
        result = compose(SlotRequest(subject="1girl"), self.profile)
        self.assertIn("lowres", result.negative)

    def test_dedupe_across_slots(self):
        # 槽位里重复给同一个 tag，只应保留一次
        result = compose(SlotRequest(subject="1girl", extra_positive="1girl"), self.profile)
        self.assertEqual(result.positive.lower().count("1girl"), 1)


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.profile = load_example()

    def test_ok_when_valid(self):
        result = compose(SlotRequest(subject="1girl, solo"), self.profile)
        self.assertTrue(result.ok, [c.message for c in result.errors()])

    def test_missing_required_is_error(self):
        # 档案 required 是 1girl；把它从 subject 和默认值里都拿掉
        profile = normalize_profile(dict(self.profile, required=["1girl"], slots={}))
        result = compose(SlotRequest(subject="1boy"), profile)
        codes = [c.code for c in result.errors()]
        self.assertIn("MISSING_REQUIRED", codes)

    def test_forbidden_is_error(self):
        result = compose(SlotRequest(subject="1girl", extra_positive="watermark"), self.profile)
        codes = [c.code for c in result.errors()]
        self.assertIn("FORBIDDEN_TAG", codes)

    def test_conflict_is_warning(self):
        result = compose(SlotRequest(subject="1girl", scene="daylight candlelight"), self.profile)
        codes = [c.code for c in result.warnings()]
        self.assertIn("CONFLICT", codes)

    def test_trigger_not_first_is_error(self):
        broken = review("masterpiece, 1girl", "lowres", self.profile)
        codes = [c.code for c in broken.errors()]
        self.assertIn("TRIGGER_NOT_FIRST", codes)

    def test_review_does_not_rebuild(self):
        positive = "anime style, masterpiece, 1girl, solo"
        result = review(positive, "lowres", self.profile)
        self.assertEqual(result.positive, positive)


class TestProfileValidation(unittest.TestCase):
    def test_missing_required_key(self):
        with self.assertRaises(ProfileError):
            normalize_profile({"name": "x", "trigger": "y"})  # 缺 quality

    def test_empty_quality_rejected(self):
        with self.assertRaises(ProfileError):
            normalize_profile({"name": "x", "trigger": "y", "quality": []})

    def test_bad_slots_type(self):
        with self.assertRaises(ProfileError):
            normalize_profile({"name": "x", "trigger": "y", "quality": ["q"], "slots": []})

    def test_string_slot_accepted(self):
        p = normalize_profile({"name": "x", "trigger": "y", "quality": ["q"],
                               "slots": {"subject": "1girl"}})
        self.assertEqual(p["slots"]["subject"]["default"], "1girl")

    def test_example_profile_loads(self):
        profile = load_example()
        self.assertEqual(profile["name"], "anime-general")
        self.assertTrue(profile["negative_base"])


if __name__ == "__main__":
    unittest.main()
