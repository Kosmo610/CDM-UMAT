#!/usr/bin/env node
// Detect the dominant language of a text file or stdin.
// Output: a single lang code on stdout (e.g. "ko", "en"), exit 0 on success.
// Supported: ko, en. Falls back to "en" with a warning on stderr for others.

const fs = require('fs');

const SUPPORTED = ['ko', 'en'];

function readInput() {
  const arg = process.argv[2];
  if (arg && arg !== '-') return fs.readFileSync(arg, 'utf8');
  return fs.readFileSync(0, 'utf8');
}

function detect(text) {
  const raw = {
    ko: (text.match(/[가-힯ᄀ-ᇿ㄰-㆏]/g) || []).length,
    ja: (text.match(/[぀-ゟ゠-ヿ]/g) || []).length,
    zh: (text.match(/[一-鿿]/g) || []).length,
    en: (text.match(/[a-zA-Z]/g) || []).length,
  };

  // One CJK syllable carries roughly the information of a whole English word.
  // Without weighting, a sentence with a few English loanwords flips to 'en'.
  // Average English word ~4–5 letters, so weight CJK ~4x.
  const WEIGHT = { ko: 4, ja: 4, zh: 4, en: 1 };
  const weighted = Object.fromEntries(
    Object.entries(raw).map(([k, v]) => [k, v * WEIGHT[k]])
  );

  const total = Object.values(weighted).reduce((a, b) => a + b, 0);
  if (total === 0) return { lang: 'en', confidence: 0, counts: raw };

  const ranked = Object.entries(weighted).sort((a, b) => b[1] - a[1]);
  const [top, topScore] = ranked[0];
  return { lang: top, confidence: topScore / total, counts: raw };
}

function main() {
  const text = readInput();
  const { lang, confidence, counts } = detect(text);

  if (!SUPPORTED.includes(lang)) {
    process.stderr.write(
      `warn: detected '${lang}' (confidence ${confidence.toFixed(2)}), ` +
      `not in supported list [${SUPPORTED.join(', ')}]. Falling back to 'en'.\n` +
      `counts: ${JSON.stringify(counts)}\n`
    );
    process.stdout.write('en\n');
    return;
  }

  process.stdout.write(`${lang}\n`);
}

main();
