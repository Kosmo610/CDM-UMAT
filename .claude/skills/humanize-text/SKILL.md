---
name: humanize-text
description: Rewrite AI-generated text so it reads as if written by a human, or audit text for AI tells without rewriting. Removes AI tells (uniform sentence length, hedge clichés, translationese, em-dash overuse, abstract noun stacks, stock phrases, perfect topic sentences) and injects human signals (burstiness, casual register, sentence fragments, personal voice, register variation). Multi-language with per-language rule packs in references/<lang>.md. Use when the user asks to humanize text, make AI writing sound natural, remove ChatGPT/Claude tells, rewrite formal text in a casual human voice, or asks whether a piece reads as AI-written.
---

# Humanize Text

Rewrite text so it reads as human-written. Language-agnostic procedure + per-language rule packs.

## Procedure

1. **Detect language** of the input.
   - Use `scripts/detect-lang.js <file>` if available, or judge from script + vocabulary.
   - Supported: `ko`, `en`. Fallback to closest match for other languages, but warn the user.

2. **Load the rule pack** for that language: `references/<lang>.md`.
   - Always also load `references/_common.md` for language-agnostic principles.

3. **Diagnose AI tells** in the input against the rule pack's `## AI tells` section.
   - List the specific tells you found (line/phrase level). Do not skip this.
   - Also note the human traits already present (voice markers, quirks, distinctive phrasing) — these must survive the rewrite. See `_common.md` `## Minimum effective edit`.

4. **Rewrite** applying the rule pack's `## Rewrite rules`. Then apply `## Human signals` to inject naturalness.
   - Preserve meaning, facts, numbers, names, structure of argument.
   - Do not invent new claims, opinions, or anecdotes the original does not imply.
   - Edit only diagnosed spans; leave sentences that already read human untouched.

5. **Validate** against `_common.md` metrics:
   - Burstiness — sentence-length variance (mix short and long).
   - Register variation — not every sentence in the same form.
   - Concrete > abstract — abstract nouns reduced.
   - No meta scaffolding ("In conclusion / 결론적으로 / 따라서") unless the original explicitly needs it.
   - Change volume proportional to the tells found — if most of the text changed, re-check for meaning drift and over-polish.

6. **Optional deterministic post-pass**: if the working tree has `scripts/rules/<lang>.json`, you may run the regex substitutions in it as a final pass. These are safe one-to-one swaps (translationese phrases, AI vocab blocklist).

## Output format

Default: return only the rewritten text. No preamble, no explanation.

If the user asks "what did you change" or "diff", produce a brief diagnosis list (the AI tells found, the rules applied) followed by the rewritten text.

### Detect-only mode

If the user asks whether the text reads as AI-written, or to audit/scan/flag a draft without rewriting: run steps 1–3 only. For each tell found, quote the phrase and give the fix in a few words. Do not rewrite, do not produce a score, and do not claim to know who wrote it — detectors guess, named patterns are evidence the user can check. Offer to rewrite afterward.

## When NOT to humanize

- Legal, regulatory, academic-formal contexts where the formal register is required — confirm with the user first.
- Code, command output, structured data (JSON, YAML).
- Direct quotations.

## Adding a new language

1. Create `references/<lang>.md` with the same section structure as `ko.md`:
   `## AI tells` → `## Human signals` → `## Rewrite rules` → `## Examples`
2. Create `scripts/rules/<lang>.json` with `{ "translationese": [[pattern, replacement], ...], "blocklist": [...] }`.
3. Add the language to `scripts/detect-lang.js`'s supported list.

The procedure above is language-agnostic. Rules live entirely in the language pack.
