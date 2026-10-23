# prompt-smith

**槽位驱动的 SDXL / Danbooru 提示词构建框架。**

把「想要一张什么图」拆成六个槽位，用一份**可版本化的档案**定义你的口味，由规则引擎合成提示词并做自检——而不是每次都让模型自由发挥，出来一张算一张。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/zyqchanel-06/prompt-smith?color=blue)](https://github.com/zyqchanel-06/prompt-smith/releases)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/runtime%20deps-zero-brightgreen.svg)](#)

---

## 它解决什么问题

用 LLM 写提示词的常见失败，几乎都出在「没有约束」上：

| 症状 | 后果 |
| --- | --- |
| 每次生成的词序不一样 | 同一套画风，出图风格漂移 |
| 触发词被埋在中后段 | LoRA 不生效，怎么调都不像 |
| 「要白的是皮肤」被理解成「整个画面调亮」 | 画面糊成一片白 |
| 必带的质量词忘写 | 细节崩掉，只能重抽 |
| 互斥词同时出现（daylight + candlelight） | 光源打架，画面发平 |

prompt-smith 把这些经验变成**可执行的规则**：

```
档案（你的口味，JSON/YAML）
      ↓
槽位（人物 / 穿搭 / 场景 / 姿势 / 表情 / 构图）
      ↓
规则引擎合成 → positive + negative
      ↓
自检（触发词位置 / 必带项 / 红线词 / 冲突 / 长度）
      ↓
可选：出图后量化核对（亮度 / 对比度）
```

## 特性

- **零运行时依赖** —— 纯标准库，`pip install prompt-smith` 只装这一个包
- **档案即口味** —— 改档案就换风格，可以进 Git、可以分享、可以 A/B
- **可解释** —— 每条自检都带 `code`，能按需忽略或统计，不是黑盒打分
- **可复现** —— 同样的槽位 + 同样的档案，永远得到同一份提示词
- **和渲染器解耦** —— 本库只管提示词；要出图请配合 [prompt-smith-comfyui](https://github.com/zyqchanel-06/prompt-smith-comfyui)

## 安装

```bash
pip install prompt-smith

# 可选：想用 YAML 写档案
pip install 'prompt-smith[yaml]'

# 可选：想出图后做亮度/对比度核对
pip install 'prompt-smith[quality]'
```

## 快速开始

```bash
# 1. 看看示例档案长什么样
promptsmith describe -p profiles/example.json

# 2. 填两个槽位，其余用档案默认值补齐
promptsmith build -p profiles/example.json \
    --subject "1girl, solo" \
    --scene "forest, moonlight" \
    --outfit "black evening dress"
```

输出：

```
POSITIVE:
  anime style, masterpiece, best quality, absurdres, very aesthetic, highly detailed,
  1girl, solo, black evening dress, forest, moonlight, looking at viewer, soft smile, full body
NEGATIVE:
  lowres, bad anatomy, bad hands, ... blurry, ugly, deformed
CHECK:
  · [SLOT_EMPTY] 槽位「姿势」为空且档案没有默认值
VERDICT: PASS
```

`VERDICT: PASS` 才继续出图；`FAIL` 时退出码为 1，可以直接用在脚本 / CI 里。

### 体检一份已有提示词

提示词是别处（LLM、别人的模板）生成的？用 `review` 只跑规则、不重新构建：

```bash
promptsmith review -p profiles/example.json --positive "masterpiece, 1girl, watermark"
```

```
CHECK:
  ✗ [TRIGGER_NOT_FIRST] 正向提示词必须以触发词开头：anime style
  ✗ [FORBIDDEN_TAG] 正向提示词出现红线词：watermark（会破坏画风一致性）
VERDICT: FAIL
```

### 出图后核对

```bash
promptsmith gate --image out/01.png out/02.png -p profiles/example.json
```

```
PASS  out/01.png  亮度=142.3 对比度=68.1
FAIL  out/02.png  亮度=221.7 对比度=23.4  过亮/过曝（221.7 > 175）; 发灰（对比度 23.4 < 60）
```

## 档案格式

一份档案就是一个 JSON（或 YAML）文件，核心字段：

| 字段 | 必填 | 作用 |
| --- | --- | --- |
| `name` | ✅ | 档案名 |
| `trigger` | ✅ | 触发词，**永远是正向提示词的第一个 tag** |
| `quality` | ✅ | 质量词，紧跟触发词 |
| `negative_base` | | 负向基线，每次构建都会带上 |
| `slots` | | 六个槽位的默认值与候选词 |
| `required` | | 必带项，缺一个就是 error |
| `forbidden` | | 红线词，出现在正向里就是 error |
| `conflicts` | | 互斥词对，同时出现给 warn |
| `quality_gate` | | 亮度区间 / 对比度下限 |
| `safety` | | 安全层：成年声明、tag 数上限 |

完整示例见 [profiles/example.json](profiles/example.json)，字段逐条解释见 [docs/writing-profiles.md](docs/writing-profiles.md)。

## 自检规则一览

| code | 等级 | 含义 |
| --- | --- | --- |
| `TRIGGER_NOT_FIRST` | error | 触发词不在第一位（LoRA / 画风会失效） |
| `MISSING_REQUIRED` | error | 缺必带项 |
| `FORBIDDEN_TAG` | error | 正向里出现红线词 |
| `CONFLICT` | warn | 互斥词同时出现 |
| `NEGATIVE_EMPTY` | warn | 负向提示词为空 |
| `TOO_MANY_TAGS` | warn | tag 数超过 CLIP 有效长度 |
| `SLOT_EMPTY` | info | 某槽位为空且档案没给默认值 |
| `SAFETY_PHRASE_MISSING` | warn | 档案要求的安全声明没写 |

## 设计取向

**不做 NLP 猜测。** 槽位由调用方（人或者 LLM）填好，本库只负责合成、自检、核对。原因很直接：

- 规则引擎的行为可以被测试覆盖（本项目 22 个单测）
- 同样的输入永远得到同样的输出，出问题能二分定位
- 换语言、换模型都不用改核心逻辑

如果你想要"自然语言进、提示词出"，那应该在**上一层**做（让 LLM 填槽位），而不是把不确定性塞进提示词合成层。

## 文档

- [docs/methodology.md](docs/methodology.md) —— 六槽位方法论：为什么是这六个
- [docs/prompt-anatomy.md](docs/prompt-anatomy.md) —— 提示词解剖：顺序、权重、长度
- [docs/quality-gate.md](docs/quality-gate.md) —— 量化质量门：用数字判断画面有没有跑偏
- [docs/pitfalls.md](docs/pitfalls.md) —— 实战踩过的坑
- [docs/writing-profiles.md](docs/writing-profiles.md) —— 怎么写自己的档案

## 安全边界

框架内置了 `safety` 层，默认建议：

- 角色恒为**成年虚构形象**，不涉及真人、不涉及未成年形象
- tag 数控制在上限内（超长会被 CLIP 截断，反而降低质量）
- 涉及真实人物的请求应被拒绝

这些规则写在档案里，可以按项目调整；但**不建议关掉**。

## License

MIT —— 见 [LICENSE](LICENSE)。