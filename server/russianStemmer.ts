/**
 * Pure TypeScript Russian Snowball/Porter stemmer & tokenizer with memoization.
 * Ensures word-form matching across cases and inflections (e.g., "транспортного налога" <-> "транспортный налог").
 */

const VOWELS = /[аеиоуыэюя]/;
const PERFECTIVE_GERUND = /((ив|ивши|ившись|ыв|ывши|ывшись)|((?<=[ая])(в|вши|вшись)))$/;
const REFLEXIVE = /(с[яь])$/;
const ADJECTIVE = /(ее|ие|ые|ое|ими|ыми|ей|ий|ый|ой|ем|им|ым|ом|его|ого|ему|ому|их|ых|ую|юю|ая|яя|ою|ею)$/;
const PARTICIPLE = /((ивш|ывш|ующ)|((?<=[ая])(ем|нн|вш|ющ|щ)))$/;
const VERB = /((ила|ыла|ена|ейте|уйте|ите|или|ыли|ей|уй|ил|ыл|им|ым|ен|ило|ыло|ено|ят|ует|уют|ит|ыт|ены|ить|ыть|ишь|ую|ю)|((?<=[ая])(ла|на|ете|йте|ли|й|л|ем|н|ло|но|ет|ют|ны|ть|ешь|нно)))$/;
const NOUN = /(а|ев|ов|ие|ье|е|иями|ями|ами|еи|ии|и|ией|ей|ой|ий|й|иям|ям|ием|ем|ам|ом|о|у|ах|иях|ях|ы|ь|ию|ью|ю|ия|ья|я)$/;
const SUPERLATIVE = /(ейше|ейш)$/;
const DERIVATIONAL = /(ост|ость)$/;

const STEM_CACHE = new Map<string, string>();
const MAX_CACHE_SIZE = 150_000;

export function stemRussianWord(rawWord: string): string {
  const word = rawWord.toLowerCase().replace(/ё/g, 'е');
  if (word.length < 3 || !/[а-я]/.test(word)) {
    return word;
  }

  const cached = STEM_CACHE.get(word);
  if (cached !== undefined) {
    return cached;
  }

  let rvIndex = -1;
  for (let i = 0; i < word.length; i++) {
    if (VOWELS.test(word[i])) {
      rvIndex = i + 1;
      break;
    }
  }
  if (rvIndex === -1 || rvIndex >= word.length) {
    return word;
  }

  const head = word.slice(0, rvIndex);
  let rv = word.slice(rvIndex);

  // Step 1
  if (PERFECTIVE_GERUND.test(rv)) {
    rv = rv.replace(PERFECTIVE_GERUND, '');
  } else {
    rv = rv.replace(REFLEXIVE, '');
    if (ADJECTIVE.test(rv)) {
      rv = rv.replace(ADJECTIVE, '');
      rv = rv.replace(PARTICIPLE, '');
    } else if (VERB.test(rv)) {
      rv = rv.replace(VERB, '');
    } else {
      rv = rv.replace(NOUN, '');
    }
  }

  // Step 2: remove trailing 'и'
  rv = rv.replace(/и$/, '');

  // Step 3: derivational in R2 (approximated safely)
  if (rv.length > 4 && DERIVATIONAL.test(rv)) {
    rv = rv.replace(DERIVATIONAL, '');
  }

  // Step 4: superlative, undouble н, remove trailing ь
  if (SUPERLATIVE.test(rv)) {
    rv = rv.replace(SUPERLATIVE, '').replace(/нн$/, 'н');
  } else if (/ь$/.test(rv)) {
    rv = rv.replace(/ь$/, '');
  } else {
    rv = rv.replace(/нн$/, 'н');
  }

  const result = head + rv;
  if (STEM_CACHE.size < MAX_CACHE_SIZE) {
    STEM_CACHE.set(word, result);
  }
  return result;
}

export function tokenizeAndStem(text: string): string[] {
  if (!text) return [];
  const matches = text.toLowerCase().match(/[а-яёa-z0-9_-]{2,}/gi);
  if (!matches) return [];
  return matches.map((t) => stemRussianWord(t));
}
