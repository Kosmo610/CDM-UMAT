# humanize-text

A Claude / agent Skill that rewrites AI-generated text so it reads as human-written. Multi-language with per-language rule packs.

Currently supports **Korean (ko)** and **English (en)**.

## Install

Uses [`npx skills`](https://github.com/vercel-labs/skills) to install into any supported agent (Claude Code, Cursor, Codex, etc.):

```bash
# Project-scoped (committed with your repo)
npx skills add korECM/humanize

# User-scoped (available across all projects)
npx skills add korECM/humanize -g

# Install to a specific agent only
npx skills add korECM/humanize -a claude-code
```

After install, reload your agent to pick up the skill.

## Usage

Once installed, ask your agent to humanize text:

```
이 글 humanize 해줘:
{붙여넣은 AI 글}
```

```
Make this read more human:
{paste AI text}
```

The skill auto-detects the language and applies the matching rule pack.

## What it does

- Detects language (`ko` / `en`).
- Loads `references/<lang>.md` — the language-specific rule pack.
- Scans for AI tells (uniform sentence length, translationese, hedge clichés, em-dash overuse, abstract noun stacks, meta scaffolding).
- Rewrites applying per-language rewrite rules and injects human signals (burstiness, register drift, sentence fragments, natural connectives).
- Preserves facts, numbers, names, and the original argument.

## Adding a new language

1. `references/<lang>.md` — same section structure as `ko.md`:
   `## AI tells` → `## Human signals` → `## Rewrite rules` → `## Examples`
2. `scripts/rules/<lang>.json` — deterministic regex substitutions.
3. `scripts/detect-lang.js` — add the language code to `SUPPORTED`.

The procedure in `SKILL.md` is language-agnostic; only the rule packs need updating.

## Layout

```
humanize-text/
├── SKILL.md                    # language-agnostic procedure
├── references/
│   ├── _common.md              # burstiness / register / validation
│   ├── ko.md                   # Korean rule pack
│   └── en.md                   # English rule pack
└── scripts/
    ├── detect-lang.js          # CJK-weighted language detection
    └── rules/
        ├── ko.json             # deterministic Korean substitutions
        └── en.json             # deterministic English substitutions
```

## License

MIT
