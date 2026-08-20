# BBCIncorp Design System

A brand & UI design system for **BBCIncorp** — a B2B company-formation and corporate-services provider helping entrepreneurs, startups and SMEs incorporate in Hong Kong, Singapore and offshore jurisdictions.

> ✅ **Logo:** the **official BBCIncorp logo** (aperture mark + wordmark, with ®) is installed from the brand's own transparent source — `assets/logo-full.png` (dark wordmark, for light backgrounds) and `assets/logo-full-light.png` (white wordmark, for dark, derived from the transparent original). The `Logo` component embeds this artwork so it renders anywhere. Iconography still uses **Lucide** (CDN) as a substitute for BBCIncorp's in-house icon set — flag if you have the originals.

---

## Company context

Founded in 2017, BBCIncorp provides corporate services that empower global businesses — company formation, banking assistance, accounting & tax, corporate secretary, virtual office and legal administration across Hong Kong, Singapore and 20+ countries. The platform is **digital-first**: remote onboarding, e-KYC, and incorporation in as little as 24 hours, all tracked in a Client Portal. Partners include Airwallex and Aspire (banking) and Xero (accounting).

**Audience:** entrepreneurs, startups and SMEs worldwide setting up businesses in Asia.
**Content surfaces:** marketing website, informative/educational social posts, service highlights, promotional banners and carousels.

### Sources referenced
- Brand spec provided by the user (colors, type, logo, voice, design style).
- Public site copy: `bbcincorp.com/hk`, `/about-us`, `/company-incorporation` (paraphrased for fidelity; not production data).
- These are stored for the reader; the agent does not assume you have access.

---

## CONTENT FUNDAMENTALS

**Voice:** professional yet approachable; trustworthy, expert, empowering. Confident and solution-focused — making founders feel supported and informed.

- **Person:** speaks to "**you**" / "your business"; the company is "**we**" / "BBCIncorp". Warm and direct.
- **Tone:** demystifying and reassuring. Leads with the customer's goal, then positions BBCIncorp as the partner who removes friction. *"Focus on what matters most: starting and growing your business, and leave the details to BBCIncorp."*
- **Casing:** sentence case for headlines and body. Eyebrows/overlines are UPPERCASE with wide tracking. Title Case only for proper nouns and product names.
- **Jargon:** minimal. Where regulatory terms appear (BRN, NAR1, eKYC), they're explained in plain language.
- **Sentence length:** short, scannable. Benefit-first. Often a question → answer pattern: *"Fed up with paperwork? Discover how BBCIncorp eases the process."*
- **Numbers & proof:** concrete stats build trust (24-hour processing, 200+ countries, government fees included). Use real figures; avoid vague hype.
- **Emoji:** used **sparingly** in social/promo only (🎉 for offers, ❤️ on community posts). Never in product UI or formal copy.
- **CTAs:** action-led and short — "Get started", "Claim now", "Check availability", "Book a consultation", "Talk to an expert". One primary CTA per surface.

**Sounds like us:** "Let's turn your business vision into reality." · "Set up your Hong Kong company from anywhere — fast, simple, no hidden fees."
**Avoid:** heavy legalese without explanation; cold corporate-speak; over-promising.

---

## VISUAL FOUNDATIONS

**Color.** Primary **Blue #007EFF** drives CTAs, links and highlights. **Dark Navy #004099** for headings and dark buttons. Accents: **Gold #FFAB00** (secondary CTAs), **Amber #F59E0B** (promotions), **Green #01D167** (promo tags & success). **Ink #0A0E1A** anchors dark hero sections. Cool, blue-tuned neutral ramp for text and borders. See `tokens/colors.css`.

**Type.** **Poppins** for *everything* — headings, body, CTAs. Weights 400/500/600/700/800. Headings are Bold/ExtraBold with tight tracking (−0.02em), navy on light or white on dark. Body is Regular/Medium gray. Generous line-height (1.5–1.65) on body. See `tokens/typography.css`.

**Backgrounds.** Two worlds: (1) **cosmic dark** hero/promo sections — radial navy→ink gradient with a subtle starfield and a blurred blue glow; (2) **light** sections — white or soft `#F6F8FB`, plenty of white space. No photography is bundled; brand leans on gradient + geometric treatment. Promo accents use **blue→cyan** and **navy→blue** gradients.

**Gradients.** Signature blue→cyan (`--bbc-grad-blue`) on feature-icon tiles and highlights; navy→blue (`--bbc-grad-navy`) on CTA bands and gradient cards; radial cosmic hero (`--bbc-grad-hero`).

**Corners & cards.** Rounded throughout. Cards use 24px radius (`--radius-xl`), white surface, 1px subtle border, soft cool shadow (`--shadow-md`), lifting −4px on hover. CTAs are **pill** (`--radius-pill`). Inputs 12px radius.

**Shadows.** Soft and blue-tinted, never harsh black. Primary CTAs carry a blue glow (`--shadow-blue`); gold CTAs a warm glow (`--shadow-gold`). Elevation ramps xs→lg.

**Motion.** Restrained and smooth. Hover = brightness +6% and/or −4px lift; press = scale 0.92–0.97. Easing `cubic-bezier(0.22,1,0.36,1)` (ease-out) over 140–360ms. No bounces, no infinite decorative loops in product UI.

**Borders & transparency.** Light UI: 1px `--border-subtle` (#DCE3ED). Dark UI: `rgba(255,255,255,0.12)` hairlines. Glass surfaces (nav, hero form) use translucent fills + `backdrop-filter: blur` over the cosmic background.

**Layout.** Centered containers (1080–1280px), 4px spacing grid, large section padding (96px). Clear hierarchy: eyebrow → headline → lead → CTA. Sticky translucent header.

---

## ICONOGRAPHY

- **System:** BBCIncorp's own product icons were not available to copy, so the system standardizes on **[Lucide](https://lucide.dev)** (loaded from CDN: `unpkg.com/lucide`) — a clean, consistent 24px stroke set that matches the brand's modern, tech-forward feel. **Substitution flagged** — replace with the official set if provided.
- **Treatment:** icons are most often presented inside a **gradient rounded-square tile** (`FeatureIcon`, blue→cyan) for services/features, or inline in stroke form (links, list checks, footer social).
- **Stroke weight:** Lucide default (~2px), `currentColor` so tiles/contexts recolor them.
- **Common glyphs:** `building-2` (formation), `landmark` (banking), `calculator` (accounting), `shield-check` (secretary), `mail` (virtual office), `scale` (legal), `arrow-right` (CTAs), `check` (benefit lists).
- **Emoji:** social/promo only and sparingly (🎉, ❤️). Not in product UI.
- **Logo:** circular **orbit / arrow** mark + "BBCIncorp" wordmark. Light (white) version for dark backgrounds, dark (navy/blue) for light. Placeholder art in `assets/` until the official SVG is supplied.

---

## Index / manifest

**Foundations**
- `styles.css` — entry point (consumers link this). `@import`s only.
- `tokens/` — `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `effects.css`, `tech.css` *(v2)*.
- `assets/` — `logo-full.png` (dark wordmark), `logo-full-light.png` (white wordmark) — **real brand logo**.

**Components** (`window.DesignSystem_9250fc.*`)
- `components/actions/` — **Button**, **IconButton**
- `components/data-display/` — **Card**, **Badge**, **Stat**, **Eyebrow**, **FeatureIcon**, **ProcessStep** *(v2)*, **StatCounter** *(v2)*, **LogoMarquee** *(v2)*
- `components/forms/` — **Input**
- `components/feedback/` — **AiBadge** *(v2)*, **BSmartWidget** *(v2)*
- `components/brand/` — **Logo**

**UI kits**
- `ui_kits/website/` — `index.html` marketing homepage (v1: header, cosmic hero, services, CTA, footer) + `tech-v2.html` platform homepage (v2: AI hero, BSmart widget, process/stats, trusted-by marquee).
- `ui_kits/social/` — 1080×1080 social post templates (promo, service, carousel, stat).

**Specimen cards** — `guidelines/*.card.html` (Colors, Type, Spacing, Brand) + per-component cards populate the Design System tab.

**Skill** — `SKILL.md` (Agent-Skills compatible).

---

## BRAND V2 — TECH-DRIVEN DIRECTION

Extracted from the new platform demo: **https://bbcincorptech.framer.website/home/opt3_2**

> ✅ **Visual tokens confirmed from the real demo screenshot** (July 2026). Key findings now locked in: **headlines are set in MONOSPACE** (a tech-forward display face — `--font-display-mono`, JetBrains Mono as a close match; confirm the exact face if you have it), the page background is a **warm cream `#FBF8F3`** (not pure white), and the accent gradient matches the **logo's blue→cyan** (`#00A7FD → #00F5FF`). Body copy stays Poppins.

**What changed — positioning.** v1 reads as a *corporate-services provider*; v2 reads as a **tech platform that automates the busywork**. The company is now "one platform" with a **dedicated team + AI**.

**New brand element — BSmart.** An **AI assistant** (`BSmartWidget`) is the signature product surface: a glass chat card with quick-reply chips ("Incorporate a new company", "Open a business bank account", "View pricing plans"). Announced via the `AiBadge` pill — *"New · Smart task routing powered by AI."*

**Voice shift (v2).** Still professional & approachable, now more **product/platform + outcome-led**: "automate the busywork", "keeps your entire journey in one place", "never miss a statutory deadline", "connect your tools", "real-time analytics". Headline: *"Turning your idea into a successful business."* Process framed as **Incorporate → Comply → Manage**.

**New visual motifs (v2).**
- **Blueprint grid + node network** — a faint `--grid-line` grid with connected nodes = the "automation layer / connect your tools" idea. Masked with a radial fade. Tokens in `tokens/tech.css`.
- **Glass surfaces** — `--glass-fill` / `--glass-border` + `backdrop-filter: blur` over the cosmic dark background (BSmart card, AI badge).
- **Cyan tech accent** — `--bbc-cyan #00C6FB` and `--bbc-grad-ai` (blue→cyan) for AI/automation highlights, with an `--glow-ai` glow. The word most likely to be highlighted is now gradient blue→cyan.
- **Mono data type** — `--font-mono` (JetBrains Mono, *inferred*) for stat counters and code-like data labels only (`StatCounter`), giving a dashboard/analytics feel. Rest of type stays Poppins.
- **Numbered process** — `01 / 02 / 03` steps with cyan active accent (`ProcessStep`).
- **Rolling stat counters** — big tabular-mono metrics ("24,690+", "4.9/5", "99.1%") in a `StatCounter` band.
- **Trusted-by marquee** — auto-scrolling partner logos with edge fade (`LogoMarquee`).
- **Product screenshots** — dashboards showing "All checks passed · 0 errors · Audit ready · 99.1% completion" (represent with real screenshots when supplied; placeholders otherwise).

**IA of the v2 homepage** (see `ui_kits/website/tech-v2.html`): AI-badge hero + BSmart widget → trusted-by marquee → offer band (US$999 rebate) → 3-step process (Incorporate/Comply/Manage) → services grid → why-founders stats → resource hub / interactive tools → insights → services footer.

**v2 components:** `AiBadge`, `BSmartWidget` (`components/feedback/`), `ProcessStep`, `StatCounter`, `LogoMarquee` (`components/data-display/`). All layer on the existing palette and the cosmic dark background.
