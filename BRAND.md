# Hard9Stats Brand Guidelines

Use this file as the source of truth for all branding, UI and copy decisions in this project. Follow it exactly. Do not invent new brand colors, fonts or logo variations.

## Brand overview

- **Name:** Hard9Stats (written as one word in text; the logo is styled `HARD9STATS`)
- **Tagline:** Stats for Nerds
- **What it is:** A stats site for people who like the numbers.
- **Personality:** Sleek, modern, techy, a little nerdy and self-aware. Confident, never corporate-stiff.
- **Name origin:** The "Hard 9" idea is shown visually with two dice, a 5 and a 4.

## Logo

The logo is a text-only wordmark: `HARD9STATS`, all capitals, on one line, with no spaces.

**Construction rules**
- Font: **Lexend**, weight **500 (Medium)**, normal letter spacing (no tracking).
- Full-size letters: the first **H**, the **9** and the first **S**.
- Smaller letters: **ARD** and **TATS** are set at **80%** of the full size.
- All letters share the same baseline.
- The **9** is the only accent color.

**Logo colors**

| Version | Letters | The 9 | Background |
|---|---|---|---|
| Standard (light backgrounds) | `#111111` | `#0A5C36` | transparent or white |
| Reversed (dark backgrounds) | `#FFFFFF` | `#2ECC85` | `#0B0F0D` |

**Usage rules**
- Always use the exported logo files. Never retype the logo in a font and never recreate it by hand.
- Use the standard version on light backgrounds and the reversed version on dark backgrounds.
- Keep clear space around the logo of at least the height of the full-size **H**.
- Do not stretch, rotate, outline, add shadows or gradients, change the colors, change the font, add spaces between words, or change the letter sizes.
- Do not put the dark green `#0A5C36` 9 on a dark background. It disappears. Use the reversed version.

## Colors

| Role | Name | Hex |
|---|---|---|
| Primary dark / page background (dark mode) | Near black | `#0B0F0D` |
| Text on light | Black | `#111111` |
| Text on dark | White | `#FFFFFF` |
| Accent on light | Dark green | `#0A5C36` |
| Accent on dark | Bright green | `#2ECC85` |

Guidance
- Black, white and green only. Green is an accent, so use it sparingly (highlights, key numbers, links, buttons, chart lines).
- Default to the dark theme (`#0B0F0D` background with white text and `#2ECC85` accent) for the main product UI, since it matches the banner and social assets.
- Only these five colors are defined. If you need more shades (borders, muted text, hover states), derive them from these by adjusting opacity or lightness. Do not introduce new hues.

```css
:root {
  --h9s-bg-dark: #0B0F0D;
  --h9s-black: #111111;
  --h9s-white: #FFFFFF;
  --h9s-green-dark: #0A5C36;   /* accent on light backgrounds */
  --h9s-green-bright: #2ECC85; /* accent on dark backgrounds */
}
```

## Typography

- **Font family:** Lexend (Google Fonts) for everything: headings, body and UI.
- **Logo weight:** 500 (Medium).
- **Suggested UI weights:** 400 for body text, 500 for headings and buttons.
- **Fallback stack:** `'Lexend', system-ui, -apple-system, 'Segoe UI', sans-serif`
- **Tagline style:** capitals, small, widely letter-spaced, in the accent green (for example `STATS FOR NERDS`).
- **Numbers and data:** Lexend is fine. A monospaced font may be used for code, tables of raw numbers and terminal-style elements to support the nerdy tone.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@400;500&display=swap" rel="stylesheet">
```

```css
body { font-family: 'Lexend', system-ui, -apple-system, 'Segoe UI', sans-serif; }
```

## Asset files

Place these in the project's public/static assets folder. File names are exact.

| File | Purpose |
|---|---|
| `hard9stats-logo.svg` / `.png` | Standard logo, transparent background, for light backgrounds |
| `hard9stats-logo-reversed.svg` / `.png` | Reversed logo on black, for dark backgrounds |
| `hard9stats-profile.svg` / `.png` | 1000x1000 social profile picture, `H9S` monogram |
| `hard9stats-banner-tagline.svg` / `.png` | 1500x500 social banner with the tagline |
| `favicon-dice.svg` | Browser tab icon, two dice (5 and 4) |
| `favicon-dice.ico` | Fallback tab icon (16, 32, 48 px) |
| `favicon-dice-32.png` | 32px tab icon |
| `apple-touch-icon-dice.png` | 180px iOS home screen icon |
| `favicon-dice-192.png`, `favicon-dice-512.png` | Android and web app manifest icons |

An earlier favicon set featuring a single green `9` is also available (`favicon.svg`, `favicon.ico`, etc.). The dice version is the current choice.

```html
<link rel="icon" href="/favicon-dice.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-dice.ico" sizes="48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon-dice.png">
```

## Icons and imagery

- **Favicon:** two dice side by side on a near-black rounded square. The left die is white showing 5, the right die is bright green `#2ECC85` showing 4. Pips are `#0B0F0D`.
- **Profile picture:** `H9S` monogram, white letters with a bright green 9, on near black.
- **Banner:** the reversed wordmark centered on near black, a thin green line along the top edge, a faint grid and a low-contrast green line chart along the bottom, and the tagline below the wordmark.
- **Data visuals:** prefer clean line and bar charts. Use bright green for the main series on dark backgrounds and dark green on light backgrounds. Keep grid lines faint (white or black at roughly 5% opacity).

## Voice and copy

- Tone: smart, direct, dry humor, nerd-friendly. Speak to people who love the numbers.
- Write the name as **Hard9Stats** in running text. Use **HARD9STATS** only inside the logo artwork.
- Short sentences. No corporate buzzwords.
- It is fine to lean into nerd culture and dice and odds references, but keep it clean and professional.

## Rules for the coding agent

1. Use only the colors, font and assets defined here.
2. Never recreate the logo with text. Use the provided SVG files.
3. Pick the logo version by background: standard on light, reversed on dark.
4. Default to the dark theme unless told otherwise.
5. Keep green as an accent, not a fill color for large areas.
6. Keep UI clean and modern, with generous spacing, simple shapes and rounded corners that echo the favicon.
7. If something needed is not defined in this file, choose the most neutral option consistent with it, and flag it for review rather than inventing new brand elements.
