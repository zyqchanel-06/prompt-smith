# 怎么写自己的档案

## 从示例开始

```bash
cp profiles/example.json profiles/my-style.json
```

然后逐字段改。下面按重要性排序。

## 1. trigger（触发词）—— 最先定

**它决定这条档案对应什么画风。**

- 用 LoRA：填 LoRA 的触发词，必须逐字准确
- 不用 LoRA：填风格描述，如 `anime style`、`photorealistic`

```json
{ "trigger": "my_style_v2" }
```

⚠️ 触发词**永远**是正向提示词的第一个 tag（框架强制检查）。

## 2. quality（质量词）—— 每次都要有

```json
{ "quality": ["masterpiece", "best quality", "absurdres", "very aesthetic", "highly detailed"] }
```

SDXL 生态里这几个是通用的。不要在这里放风格词（那是 trigger 的事）。

## 3. negative_base（负向基线）

```json
{
  "negative_base": [
    "lowres", "bad anatomy", "bad hands", "extra limbs",
    "worst quality", "low quality", "jpeg artifacts",
    "signature", "watermark", "blurry"
  ]
}
```

**只放结构性缺陷**。不要把你这次的审美偏好放进来。

想强调"少出现某类特征"（如某种发色），加在这里比在正向里堆反义词有效。

## 4. slots（槽位默认值）

每个槽位两个字段：

| 字段 | 作用 |
| --- | --- |
| `default` | 用户没填时**自动补上**的内容 |
| `tags` | 候选词提示（只给人看，不会自动拼接） |

```json
{
  "slots": {
    "framing": { "default": "full body", "tags": ["full body", "upper body", "close-up"] }
  }
}
```

**默认值的选择标准**：问自己"我不填的时候，90% 情况下想要什么"。

## 5. required / forbidden（硬约束）

```json
{
  "required": ["1girl"],
  "forbidden": ["lowres", "watermark", "white theme"]
}
```

- `required`：缺了就 **error**，构建不通过
- `forbidden`：出现在正向里就 **error**

这两个是档案里最有价值的部分——它们把你的踩坑经验**固化成了规则**。

## 6. conflicts（互斥词对）

```json
{
  "conflicts": [
    { "a": "daylight", "b": "candlelight", "reason": "两套光源互斥，画面会平" }
  ]
}
```

只能配两两互斥的词对。规则是"两边同时出现在正向里就 warn"。

## 7. quality_gate（量化门）

```json
{ "quality_gate": { "brightness": [110, 175], "contrast_min": 60 } }
```

标定方法见 [quality-gate.md](quality-gate.md)。

## 8. render（渲染参数，可选）

本库不读这个字段，原样保留给渲染适配器（例如 [prompt-smith-comfyui](https://github.com/zyqchanel-06/prompt-smith-comfyui) 会读 `checkpoint` / `lora` / 尺寸）。

```json
{
  "render": {
    "checkpoint": "your_sdxl.safetensors",
    "lora": { "name": "your_style.safetensors", "strength": 0.8 },
    "width": 832, "height": 1216, "steps": 30, "cfg": 7.0
  }
}
```

## 9. safety（安全层）

```json
{ "safety": { "adult_only": true, "max_tags": 75 } }
```

- `adult_only`：声明角色恒为成年虚构形象
- `max_tags`：tag 数上限（超出给 warn）
- `require_phrase`：如果填了，框架会检查正向里有没有这句话

## 迭代方法：不要一次写完

档案是**养**出来的，不是写出来的：

```
出图 → 哪张不满意 → 问"是缺了必带项，还是出现了红线词，还是根本没约束"
     → 把这条经验写进档案（required / forbidden / conflicts）
     → 下次同一类问题就自动被拦下来
```

**判断标准**：如果某个问题你犯过两次，它就该进档案。

## 验证档案

改完跑一遍：

```bash
promptsmith describe -p profiles/my-style.json          # 看看摘要对不对
promptsmith build -p profiles/my-style.json --subject "1girl"   # 空槽位测试
promptsmith review -p profiles/my-style.json --positive "<你上次满意的提示词>"  # 回归测试
```

最后一条特别有用：把历史好图的正向提示词存下来，每次改档案都 review 一遍，确保没把以前能过的规则改成不通过。
