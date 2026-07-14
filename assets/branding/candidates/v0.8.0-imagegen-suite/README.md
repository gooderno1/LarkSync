# LarkSync Imagegen Single-Asset Suite

Date: 2026-07-06

This folder stores imagegen candidates for a same-design LarkSync logo asset suite.
The rule for this round is strict: one imagegen call creates one minimal asset.
The preview image is only for review and is not a source asset.

## Source Reference

- Original icon: `assets/branding/archive/2026-07-06-original/branding/LarkSync_Logo_Icon_FullColor.png`
- Original horizontal lockup: `assets/branding/archive/2026-07-06-original/branding/LarkSync_Logo_Horizontal_Lockup_FullColor.png`
- Original compact vertical lockup: `assets/branding/archive/2026-07-06-original/branding/LarkSync_Logo_CompactVertical_FullColor.png`

## Outputs

| Asset | Raw imagegen output | Transparent processed output | Initial judgement |
| --- | --- | --- | --- |
| Icon mark | `01-icon-mark-raw.png` | `01-icon-mark-transparent.png` | Usable candidate. Shape is close to the old logo, with cleaner edges. |
| Horizontal lockup | `02-horizontal-lockup-raw.png` | `02-horizontal-lockup-transparent.png` | Needs review. Text is correct, but wordmark styling has mild drift. |
| Compact vertical lockup | `03-compact-vertical-lockup-raw.png` | `03-compact-vertical-lockup-transparent.png` | Needs review. Text is correct, but lockup proportions and wordmark styling have mild drift. |
| Tray idle | `04-tray-idle-raw.png` | `04-tray-idle-transparent.png` | Usable candidate. Similar to icon mark. |
| Tray syncing | `05-tray-syncing-raw.png` | `05-tray-syncing-transparent.png` | Usable candidate. Same shape with a brighter active palette. |
| Tray paused | `06-tray-paused-raw.png` | `06-tray-paused-transparent.png` | Usable candidate. Same shape with muted grayscale palette. |
| Tray error | `07-tray-error-raw.png` | `07-tray-error-transparent.png` | Usable candidate. Same shape with red error palette. |
| Review preview | n/a | `suite-preview.png` | Review-only composition, not a source asset. |

## Prompt Pattern

All prompts used the same structure:

- Use case: `logo-brand`
- Asset type: one specific minimal asset only.
- Primary request: high-resolution same-design redraw of the old LarkSync logo.
- Input image: visible reference image is the strict visual reference.
- Constraints: preserve the old logo identity; no redesign; no new concept; no extra elements; no badge; no container; no shadow; no outline.
- Avoid: new logo concepts, cloud/document symbols, changed bird shape, 3D, bevel, glow, watermark, asset sheet, multiple icons.

Per-asset color intent:

- `01-icon-mark`: original blue/cyan/teal/green gradient.
- `02-horizontal-lockup`: original icon plus exact text `LarkSync`.
- `03-compact-vertical-lockup`: original icon above exact text `LarkSync`.
- `04-tray-idle`: original blue/cyan/teal/green gradient.
- `05-tray-syncing`: brighter electric blue/cyan/green active sync palette.
- `06-tray-paused`: grayscale and low-saturation cool gray palette.
- `07-tray-error`: red/rose/warm magenta error palette.

## Processing

Raw imagegen outputs are preserved. Transparent outputs were generated locally by:

- removing only near-white background connected to the canvas edge;
- preserving internal white details such as the bird eye;
- trimming alpha bounds with a small margin;
- leaving the generated logo geometry otherwise unchanged.

Formal app assets are not replaced by these candidates until visual review confirms which files are accepted.
