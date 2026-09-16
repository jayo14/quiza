# Hyperframes Composition Brief: Quiza

## Objective
Create a short, polished, shareable launch video for Quiza that highlights its 100% citation-grounded RAG quiz generation, interactive active recall, and AI weakness detection.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20.5 seconds

## Source Material
- Project root: `/home/codegallantx/moi/quiza`
- Primary files read:
  - `README.md`
  - `frontend/src/styles/global.css`
  - `frontend/src/components/UploadMaterial.jsx`
  - `frontend/src/components/Quiz.jsx`
  - `frontend/src/components/Progress.jsx`
  - `frontend/public/favicon.svg`
- Product name: Quiza
- Tagline / strongest claim: "Turn your study materials into interactive RAG quizzes with zero hallucinations and direct citations."
- Key UI or visual moments to recreate:
  - Material drop card with PDF file badge and background stage indicator ("Generating quiz questions with AI")
  - Interactive quiz question card with multi-choice options and instant green citation check ("✓ Correct · Direct Citation: Lecture 4, Slide 18")
  - Topic mastery analytics card showing weakness severity pill ("HIGH SEVERITY · 45% Accuracy") and "🎯 Practice Topic" CTA button
  - Rounded gradient brand icon with bold "Q" and glowing purple radial backdrop
- Copy that must appear verbatim:
  - "Students spend 80% of study time passively re-reading."
  - "Meet Quiza. Active recall powered by grounded AI."
  - "Generating quiz questions with AI"
  - "✓ Correct · Direct Citation: Lecture 4, Slide 18"
  - "HIGH SEVERITY · 45% Accuracy"
  - "🎯 Practice Topic"
  - "Zero Hallucinations. 100% Grounded Retention."

## Creative Direction
- Tone preset: polished
- Creative direction: clean, high-conviction product launch film
- Interpretation: Restrained, authoritative pacing with generous settled reading holds, smooth dark-mode UI elevations, subtle glowing accents, and crisp motion-matched sound cues.
- Angle: Passive study techniques (re-reading, highlighting) fail. Quiza turns raw documents into 100% grounded active recall quizzes that pinpoint and eliminate cognitive weak spots.
- Hook (first 2-3 seconds):
  "Students spend 80% of study time passively re-reading."
  "Retaining almost nothing."
  "Meet Quiza. Active recall powered by grounded AI."
- Outro / punchline:
  "Zero Hallucinations. 100% Grounded Retention."
  "Stop passively re-reading. Master any subject."
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign

## Visual Identity
- Background: `#0b0b12`
- Secondary background: `#101018`
- Card background: `#171722`
- Card border: `#252532`
- Primary accent: `#7c6aff`
- Primary gradient: `linear-gradient(135deg, #8F80FF 0%, #6854F5 100%)`
- Text primary: `#f5f5f7`
- Text secondary: `#9292a3`
- Success: `#35d07f`
- Warning / Severity: `#ef4444` / `#f5b942`
- Display font: `Inter, system-ui, -apple-system, sans-serif`
- Body font: `Inter, system-ui, -apple-system, sans-serif`
- Visual references from the project:
  - `favicon.svg`: Rounded square gradient icon with white letter "Q"
  - `UploadMaterial.jsx`: Document badge (`PDF`), stage labels, progress indicators
  - `Quiz.jsx`: Multi-choice card layout, selection highlight, status checkmark
  - `Progress.jsx`: Topic mastery cards, accuracy meters, severity tags, practice button

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract:

Scene summary:
1. Scene 1 — The Hook — 4.0s (0.0s - 4.0s) — Problem statement + Quiza reveal
2. Scene 2 — Document Ingestion & Grounded Quiz — 5.5s (4.0s - 9.5s) — Ingest PDF, simulate option selection, direct citation verified
3. Scene 3 — Algorithmic Weakness Analysis — 6.0s (9.5s - 15.5s) — Topic mastery cards, severity tag, click Practice Topic button
4. Scene 4 — Outro / Punchline — 5.0s (15.5s - 20.5s) — Luminous Quiza icon, bold punchline, feature tags

## Audio
- Audio role: Warm, modern electronic bed with subtle audio-reactive glow and tactile UI accents.
- Audio arc: Opens clean with steady rhythm, dips slightly for the interactive quiz clicks, swells with resonant bell on citation verification, and lands confidently on the final brand outro.
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: Starts at 0.0s at volume 0.32, steady clean 110 BPM tempo, smooth fade-out under final logo.
- Music cue guidance: Bundled preset at `~/.gemini/config/skills/brag/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`.
  - Strong cues: 8.74s (citation verification), 13.11s (weakness card arrival), 17.47s / 18.56s (brand lock-in).
  - Beat grid: ~0.54s spacing for sequential option and card reveals.
- Audio-reactive treatment: Subtle; ambient background radial glow breathes gently with music RMS energy. No equalizer visualizers.
- Audio-coupled moments:
  - 0.2s: Soft intro reveal (`assets/sfx/impact/impactSoft_medium_001.ogg`)
  - 4.2s: Document drop into ingestion slot (`assets/sfx/interface/drop_001.ogg`)
  - 7.2s: Option B click selection (`assets/sfx/ui/mouseclick1.ogg`)
  - 7.6s: Citation verified resonant ding (`assets/sfx/impact/impactBell_heavy_000.ogg`)
  - 9.8s: Weakness card drop (`assets/sfx/interface/drop_002.ogg`)
  - 13.6s: Practice Topic button click (`assets/sfx/interface/click_001.ogg`)
  - 16.0s: Outro brand slam (`assets/sfx/impact/impactBell_heavy_003.ogg`)
- SFX files to copy into `brag-output/composition/assets/`:
  - `music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
  - `sfx/impact/impactSoft_medium_001.ogg`
  - `sfx/impact/impactBell_heavy_000.ogg`
  - `sfx/impact/impactBell_heavy_003.ogg`
  - `sfx/interface/drop_001.ogg`
  - `sfx/interface/drop_002.ogg`
  - `sfx/interface/click_001.ogg`
  - `sfx/ui/mouseclick1.ogg`

## Hyperframes Instructions
- Composition directory: `brag-output/composition/`
- Top-level standalone structure: root `<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="20.5">`
- Each scene is a `<section class="clip" data-start="..." data-duration="..." data-track-index="...">`
- `<audio>` elements are direct children of the composition root `#root` (each on its own `data-track-index`)
- Register synchronously: `window.__timelines = window.__timelines || {}; window.__timelines["main"] = tl;`
- Run `npx hyperframes check` and fix any findings before rendering.
