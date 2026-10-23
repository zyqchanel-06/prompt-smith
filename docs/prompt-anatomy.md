# 提示词解剖：顺序、权重、长度

## 一个 SDXL 提示词的实际结构

```
[触发词] [质量词] [主体] [服饰] [场景] [姿势] [表情] [构图] [额外]
```

每一段的作用不同，**位置本身就是一种权重**。

## 为什么触发词必须第一位

LoRA 的触发词靠文本编码器在前若干 token 内建立的关联来激活。放在中后段时：

- 前面的语义已经占据注意力
- 触发词的影响力被稀释
- 结果就是"LoRA 好像没生效"

这也是本框架把 `TRIGGER_NOT_FIRST` 设成 **error** 而不是 warn 的原因——它不是风格问题，是功能问题。

## 权重语法

Danbooru 风格的权重写法：

```
(tag:1.2)     # 加强
(tag:0.8)     # 减弱
((tag))       # 等价于 (tag:1.1)，不推荐，难读
```

建议：

- 只在**确实需要**时加权重，默认 1.0
- 一次不超过 2~3 个加权项，加多了整体会失衡
- 权重范围 0.8~1.3，超过 1.5 容易出畸形

本框架的 `split_tags()` 会正确识别括号内的逗号，不会把 `(red hair, blue eyes:1.1)` 拆坏。

## 去重规则

同一个 tag 出现两次不会让它"更强"，只会浪费 token。框架在合成时会按**大小写不敏感**去重，保留第一次出现的位置：

```
subject: 1girl, solo
extra:   1girl        → 合成后只保留一个 1girl
```

## 长度：CLIP 的 75 token 墙

SDXL 的 CLIP 文本编码器单段上限是 75 个 token。超长时：

- 不同实现行为不同（截断 / 分段拼接 / 直接报错）
- 但**超出的部分一定不会按你以为的方式生效**

经验值：

| tag 数 | 状态 |
| --- | --- |
| < 40 | 安全 |
| 40~75 | 通常可用（长 tag 会占更多 token） |
| > 75 | 会被截断，末尾的构图/氛围词最先丢失 |

框架的 `TOO_MANY_TAGS` 检查用的就是 tag 计数，阈值可在档案 `safety.max_tags` 配置。

## 负向提示词不是越长越好

`negative_base` 的常见坑：

- **把不想看到的词全塞进去** → 负向也占 token，且过强的负向会让画面变"干净到发假"
- **负向里放风格词** → 例如把所有 `dark` 都放负向，会强制把画面推亮，反而破坏原本的暗调

原则：**负向只放"结构性缺陷"**（`bad anatomy`、`extra limbs`、`watermark`），不放审美偏好。

## 一份"健康"的提示词长什么样

```
anime style, masterpiece, best quality, absurdres,      ← 画风 + 质量
1girl, solo, long silver hair,                                ← 主体
black evening dress, long gloves,                             ← 服饰
ballroom, crystal chandelier,                                 ← 场景
standing, looking at viewer,                                  ← 姿势
soft smile, blush, candlelight, cinematic lighting,           ← 表情氛围
full body                                                     ← 构图
```

约 20 个 tag，结构清晰，任何一段换掉都不影响其他段——这正是槽位化想要的效果。
