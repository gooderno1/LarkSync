# LarkSync Logo 高清候选

创建日期：2026-07-06

目标：在不改变旧版 Logo 设计的前提下，尝试提升清晰度。

## 候选文件

- `original-cleaned-reference.png`
  - 旧版原图去边缘连通白底后的参考版。
  - 形状和颜色均来自旧图。
- `same-design-local-hd.png`
  - 本地高清增强版。
  - 不改变轮廓来源，只做颜色、对比度和锐化。
- `same-design-crisp-mask-hd.png`
  - 旧轮廓 mask 锐化版。
  - 边缘更利落，但可能比旧图更硬。
- `same-design-vector-clean-hd.png`
  - 推荐候选。
  - 使用旧版轮廓，平滑色彩噪点并保留旧设计。
- `imagegen-same-design-transparent.png`
  - imagegen 同款高清候选 1。
  - 更清晰，但鸟形、右侧箭头和无限环比例有轻微漂移。
- `imagegen-strict-transparent.png`
  - imagegen 同款高清候选 2。
  - 更清晰，但整体比例漂移更明显。
- `comparison-v4.png`
  - 当前推荐对比图。

## imagegen 提示词

候选 1：

```text
Use case: logo-brand
Asset type: app logo icon candidate
Primary request: Recreate the provided LarkSync icon as a sharper high-resolution raster logo while preserving the exact same design. This is a same-design redraw, not a new logo.
Input image role: the visible reference image is the edit target and strict visual reference.
Subject: the same blue-to-teal infinity sync loop with two arrowheads, the same small bird silhouette embedded on the left side, the same white circular negative space and small white bird eye.
Style/medium: clean polished vector-like app logo, crisp edges, smooth gradients, high resolution, production asset quality.
Composition/framing: centered icon only, same proportions and same orientation as the reference, no text, no extra icon container.
Color palette: preserve the reference blue, cyan, teal, and green gradient as closely as possible.
Constraints: preserve the silhouette, arrow positions, bird shape, negative spaces, proportions, and overall layout from the reference; do not redesign; do not modernize; do not simplify; do not add badges or new shapes; no text; no watermark.
Avoid: new logo concept, different bird, different infinity shape, extra document/cloud symbols, 3D effects, shadows, outlines, background patterns.
```

候选 2：

```text
Use case: precise-object-edit
Asset type: same-logo high-resolution candidate
Primary request: Upscale and cleanly redraw the provided LarkSync icon without changing the logo design. Treat the reference image as a strict tracing source.
Input image role: the visible reference logo is the exact target to reproduce.
Subject: exactly the same LarkSync icon from the reference: a blue-to-green infinity sync loop, top arrow at the left loop, lower arrow at the right loop, and the same small bird silhouette embedded in the left loop with a white circular eye.
Style/medium: flat 2D vector-like raster recreation, crisp but faithful, no new style.
Composition/framing: same icon-only composition, same angle, same relative sizes, same negative spaces, same whitespace relationship; centered on plain white background.
Color palette: match the original blue, turquoise, teal, and green gradient.
Constraints: do not redesign; do not simplify; do not modernize; do not change the bird silhouette; do not change the infinity loop curvature; do not change either arrowhead; do not add text; do not add shadows; do not add outlines; keep the original logo's proportions and asymmetry.
Avoid: any different logo, new geometry, extra symbols, cloud/document marks, badge overlays, 3D, bevel, glow, watermark, text.
```

## 当前判断

imagegen 可以提高清晰度，但不能保证完全复刻旧 Logo。当前更稳的生产候选是 `same-design-vector-clean-hd.png`。
