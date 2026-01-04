# VIDURAI BRAND PROTOCOL (v2.2.0)

> **CRITICAL RULE:** Do not invent visual elements. Do not "re-create" the logo with CSS. Use the provided files under `assets/brand/`.

## 1. THE ASSET VAULT

All official assets are located in: `assets/brand/`

### Primary Logo (Source)

- **`assets/brand/logo_primary.png`** — Original kosha-icon, the single source of truth.

### Sized Variants (Auto-Generated)

- **`assets/brand/logo_primary_1024.png`** — 1024×1024, high-res for print/retina.
- **`assets/brand/logo_primary_512.png`** — 512×512, website hero, README headers.
- **`assets/brand/logo_primary_256.png`** — 256×256, documentation, PyPI.
- **`assets/brand/logo_primary_128.png`** — 128×128, Chrome Web Store, VS Code icons.

### Icon

- **`assets/brand/logo_icon.png`** — Same as primary, for favicon/avatar use.

### Social Banner

- **`assets/brand/social_banner.png`** — 1200×628, OpenGraph/Twitter/LinkedIn preview cards.

### Complete File List

```
assets/brand/logo_primary.png
assets/brand/logo_primary_1024.png
assets/brand/logo_primary_512.png
assets/brand/logo_primary_256.png
assets/brand/logo_primary_128.png
assets/brand/logo_icon.png
assets/brand/social_banner.png
```

If any of these files are missing, STOP and ask the maintainer to provide them. Do not generate placeholders.

## 2. COLOR PALETTE (IMMUTABLE)

Do not "eyeball" colors. Copy-paste these hex codes EXACTLY.

- **Vidurai Saffron (Primary Action):** `#FF9933`
- **Deep Indigo (Backgrounds/Headers):** `#2A2A72`
- **Text Primary:** `#1A1A1A`
- **Text Muted:** `#666666`
- **Surface Light:** `#F5F5F7`

These colors define the core Vidurai visual identity, especially for website, dashboards, and marketing surfaces.

## 3. USAGE RULES

- **Aspect Ratio:**
  NEVER stretch the logo. Always preserve aspect ratio (`width="auto"` or `height="auto"`).

- **Clear Space:**
  Leave at least 16px padding around the logo in all directions.

- **Do NOT:**
  - Do NOT use the icon-only logo as the main brand in headers.
  - Do NOT recolor the logo arbitrarily (no random reds, blues, gradients).
  - Do NOT overlay busy backgrounds behind the logo that reduce legibility.

## 4. TYPOGRAPHY & CSS SNIPPET

Use these CSS variables as the default baseline for front-end work:

```css
:root {
  --vidurai-primary: #FF9933;
  --vidurai-bg: #2A2A72;
  --vidurai-surface: #F5F5F7;
  --vidurai-text: #1A1A1A;
  --vidurai-text-muted: #666666;
  --vidurai-font: system-ui, -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
}
```

Any time you define a new component, prefer to use these variables instead of hard-coded colors.

## 5. BRAND INTEGRATION RULES

- BEFORE generating UI (HTML/CSS/React) or README sections with visual elements, read this file.
- ALWAYS reference logos via relative paths under `assets/brand/`.
- If asked for a "new logo" or "rebranding", STOP and ask the maintainer for explicit instructions.

## 6. LINKED PROTOCOLS

This BRAND.md works together with:

- `AGENTS.md` — Global behavior and architectural rules for AI agents.
- `.cursorrules` — IDE-specific coding and behavior rules.
- `active_context.md` — Current project state.

contributor must respect all of them when working on Vidurai.
