# Common Principles (language-agnostic)

These apply regardless of language. The per-language pack handles surface forms; this file handles the underlying distribution.

## Minimum effective edit

Humanizing is editing, not re-authoring. The input often already contains human sentences — leave them alone.

- Before rewriting, note 3–5 traits of the original worth keeping: vocabulary, cadence, bluntness, humor, hedging, digressions. These must survive the rewrite.
- Fix the spans you diagnosed. Don't rewrite untouched sentences for consistency or make every paragraph equally tidy.
- Removal-only: the rewrite removes AI tells. Never insert stock phrases, hype, or clichés the original didn't have, and never raise the formality level.
- Rough edges already in the original — dashes, exclamations, asides, self-interruptions, colloquial phrases — are evidence of a human hand. Keep them.
- If much more than ~30% of the text changed, you've probably over-polished. Re-check for meaning drift and roll back edits that weren't tied to a diagnosed tell.

## Burstiness — sentence-length variance

Human prose mixes lengths. AI prose clusters around one length (often 18–22 words in English, similar mid-length in other languages).

- After rewriting, the sequence of sentence lengths should look uneven.
- Include at least one very short sentence (1–4 words) per ~5 sentences when tone allows.
- Include at least one long, clause-stacked sentence per paragraph if the topic supports it.
- Two consecutive sentences of near-identical length and structure is an AI tell.

## Perplexity — lexical unpredictability

AI prefers safe, high-frequency words and the same connectors. Humans reach for the specific, the colloquial, the slightly off.

- Replace generic words with concrete ones where possible.
- Use the same word twice when it's the right word — synonyms-for-synonyms-sake is itself an AI tell.
- Avoid the language's known AI-darling vocabulary (see per-language `## AI tells`).

## Register variation

A human writer's register drifts within a piece. AI locks register and never breaks it.

- Allow one or two formality slips toward casual.
- Allow rhetorical questions, asides, or interjections where natural.

## Concrete > abstract

Abstract noun stacks ("the importance of efficiency in optimizing performance") are AI-tell-rich.

- Convert abstract nouns to verbs.
- Prefer specific examples over general claims when the original supports it.

## No meta scaffolding

AI loves to announce its own structure ("First, ... Second, ... Finally, ... In conclusion, ..."). Humans rarely do this in short prose.

- Remove "in conclusion / overall / to summarize" framings unless the piece is long enough to genuinely need them.
- Remove "first/second/third" enumeration if a flowing sentence would carry the same content.

## Rhetoric tells

Sentence-level rhetoric AI reaches for in every language. Surface forms live in the language pack; the shapes are universal.

- Binary-contrast chains — "not X but Y" / "the question isn't X, it's Y" repeated through the piece. One of the strongest measured AI signals. Keep at most one; elsewhere state Y directly.
- Colon reveals — noun phrase, colon, dramatic reveal ("The best part: it learns."). Rewrite as a plain sentence; colons are for lists, labels, quotes.
- Faux-insight setups — "what most people miss", "here's what nobody tells you". Cut the setup and let the claim stand on its own.
- Importance puffery — "marks a pivotal moment", "plays a vital role". State the fact; the reader judges whether it matters.
- Weasel attribution — "experts agree", "studies show". Name the source or cut the claim; don't invent one.
- Superficial trailing analysis — a trailing clause that pretends to explain meaning ("..., highlighting the team's commitment"). Replace with the concrete consequence or cut.
- Personified abstractions — technologies, eras, and concepts performing human verbs ("the collision raises a question"). Give the verb to a person or organization, or weaken the verb.
- Fake-profound kickers — a final aphorism, metaphor, or mic-drop line. Delete it (don't rewrite it into a better metaphor); end on the last concrete point or next action.
- Summary-recap endings — a final paragraph restating the piece. The reader was just there. End on the last concrete point.
- Synonym cycling — rotating labels for the same thing for variety's sake. Repeat the right word.
- Dramatic fragmentation — "That's it. That's the whole thing." Stacked punchy fragments read as performance, not voice.
- Rhetorical setups — "What if I told you...", "Plot twist:", self-answered question-answer pairs. Drop them and make the point.

## Structure shaping

- Bullet-heavy AI output → prose if the content is narrative or argumentative.
- Perfect topic sentences in every paragraph → break the pattern; let some paragraphs start mid-thought.
- Symmetrical "X is not Y, it's Z" parallelism → break or remove.
- Formatting slop → emoji in headings, bold sprinkled mid-sentence, colon-subtitle headings ("Topic: dramatic subtitle"), headers over two-sentence sections. Format should follow content, not decorate it.

## What to preserve

- Facts, numbers, names, citations.
- The argumentative structure (claim → support → conclusion order).
- The original's stance — humanize voice, not opinion.
- Domain terminology — don't dumb down technical terms.
- The original's human quirks — asides, dashes, exclamations, colloquialisms that were already there.
- Real section headings in academic papers and reports (numbered sections, chapter titles) — they're document structure, not decoration.
- Enumeration, possibility phrasing, and other patterns humans also use freely — treat them as tells only when they repeat mechanically, not on first occurrence.

## Validation checklist

Before returning the rewrite:

- [ ] Sentence-length sequence is uneven.
- [ ] No paragraph has all sentences in the same grammatical form.
- [ ] No language-specific AI tells from the rule pack remain (do one final scan).
- [ ] Facts unchanged.
- [ ] No invented anecdotes or opinions.
- [ ] No stock phrases or hype inserted that the original didn't have.
- [ ] Change volume proportional to the tells found — strong human sentences left alone.
- [ ] The original writer would still recognize the piece as their own voice.
