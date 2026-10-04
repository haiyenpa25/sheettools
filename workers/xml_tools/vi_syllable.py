"""Evidence-constrained Vietnamese diacritic fusion.

RapidOCR's default recognizer reads base Latin letters and punctuation
reliably but drops Vietnamese marks. Tesseract `vie` reads marks but often
garbles letters or adds stray punctuation. This module fuses both:

* base letters and punctuation come from the detector-aligned token;
* every orthographically valid way to add marks to those letters is generated;
* the variant closest to the mark-bearing readings is chosen.

Nothing is invented without visual evidence: when no reading supports a
variant, the original text is kept and the token is flagged for review.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from itertools import product

TONES = ('', '́', '̀', '̉', '̃', '̣')
ONSETS = ('ngh', 'ng', 'nh', 'ch', 'gh', 'gi', 'kh', 'ph', 'qu', 'th', 'tr',
          'b', 'c', 'd', 'đ', 'g', 'h', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'x', '')
RHYMES = frozenset('''
a ai ao au ay ac ach am an ang anh ap at
ă ăc ăm ăn ăng ăp ăt
â âc âm ân âng âp ât âu ây
e ec em en eng eo ep et
ê êch êm ên ênh êp êt êu
i ia ich im in inh ip it iu
iêc iêm iên iêng iêp iêt iêu
o oa oac oach oai oam oan oang oanh oao oap oat oay oc oe oen oeo oet oi om on ong op ot ooc oong
ô ôc ôi ôm ôn ông ôp ôt
ơ ơi ơm ơn ơp ơt
u ua uân uâng uât uây uc uê uênh uêch uêt uy uya uych uyên uyêt uynh uyt uyu ui um un ung uôc uôi uôm uôn uông uôt up ut uơ
ư ưa ưc ưi ưm ưn ưng ưt ưu ươc ươi ươm ươn ương ươp ươt ươu
y yêm yên yêng yêt yêu
'''.split())
STOP_CODAS = ('p', 't', 'c', 'ch')
SHAPES = {'a': 'aăâ', 'e': 'eê', 'o': 'oôơ', 'u': 'uư', 'd': 'dđ'}
VOWELS = set('aăâeêioôơuưy')
DIGIT_FIXES = str.maketrans({'0': 'o', '6': 'ô'})
EDGE_JUNK = re.compile(r'^[^\wÀ-ỹĐđ]+|[^\wÀ-ỹĐđ]+$', re.UNICODE)
TRAILING_PUNCT = re.compile(r'[,.;:!?…]+$')


def _nfd(text: str) -> str:
    return unicodedata.normalize('NFD', text)


def _nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)


def fold(text: str) -> str:
    """Lowercase base letters only (đ→d); used to compare readings."""
    return ''.join(c for c in _nfd(text.lower().replace('đ', 'd')) if unicodedata.category(c) != 'Mn' and c.isalnum())


def tone_of(text: str) -> str:
    return next((c for c in _nfd(text) if c in TONES[1:]), '')


def strip_tone(text: str) -> str:
    """Keep vowel shapes (â, ơ, ư...) and remove only the tone mark."""
    return _nfc(''.join(c for c in _nfd(text) if c not in TONES[1:]))


def core(text: str) -> str:
    return EDGE_JUNK.sub('', str(text or '').strip())


def _split_onset(word: str) -> tuple[str, str] | None:
    for onset in ONSETS:
        if not word.startswith(onset):
            continue
        rest = word[len(onset):]
        if onset == 'qu':
            if rest and (rest in RHYMES or ('u' + rest) in RHYMES):
                return onset, rest
            continue
        if onset == 'gi' and (not rest or (rest not in RHYMES and ('i' + rest) in RHYMES)):
            return onset, rest
        if rest in RHYMES:
            return onset, rest
    return None


def is_valid_syllable(text: str) -> bool:
    """Orthographic check on one syllable (tone allowed, case ignored)."""
    word = strip_tone(text.lower())
    parsed = _split_onset(word)
    if not parsed:
        return False
    onset, rhyme = parsed
    if onset in ('k', 'gh', 'ngh') and rhyme[:1] not in ('i', 'e', 'ê', 'y'):
        return False
    if onset in ('c', 'g', 'ng') and rhyme[:1] in ('e', 'ê', 'i'):
        return False
    if rhyme.endswith(STOP_CODAS) and tone_of(text) not in ('́', '̣'):
        return False
    return True


def _tone_index(word: str) -> int:
    """Index of the vowel carrying the tone (traditional placement: hòa, thủy)."""
    parsed = _split_onset(word)
    start = len(parsed[0]) if parsed else 0
    nucleus = [i for i in range(start, len(word)) if word[i] in VOWELS]
    if not nucleus:
        nucleus = [i for i, c in enumerate(word) if c in VOWELS]
        if not nucleus:
            return -1
    shaped = [i for i in nucleus if word[i] in 'ăâêôơư']
    if shaped:
        return shaped[-1]
    has_coda = nucleus[-1] < len(word) - 1
    if has_coda or len(nucleus) == 1:
        return nucleus[-1]
    return nucleus[1] if len(nucleus) == 3 else nucleus[0]


def _apply_tone(word: str, tone: str) -> str:
    if not tone:
        return word
    index = _tone_index(word)
    if index < 0:
        return word
    return _nfc(word[:index + 1] + tone + word[index + 1:])


@lru_cache(maxsize=4096)
def variants(base: str) -> tuple[str, ...]:
    """All valid marked syllables whose folded form is `base` (lowercase)."""
    if not base or len(base) > 8 or not base.isalpha():
        return ()
    options = [SHAPES.get(c, c) if (c != 'd' or i == 0) else c for i, c in enumerate(base)]
    if sum(len(option) > 1 for option in options) > 5:
        return ()
    result = []
    for letters in product(*options):
        shaped = ''.join(letters)
        if not _split_onset(shaped):
            continue
        for tone in TONES:
            candidate = _apply_tone(shaped, tone)
            if is_valid_syllable(candidate):
                result.append(candidate)
    return tuple(dict.fromkeys(result))


def _match_case(template: str, word: str) -> str:
    letters = [c for c in template if c.isalpha()]
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return word.upper()
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


def fuse_syllable(base_token: str, readings: list[tuple[str, float]], lexicon: frozenset[str] | None = None) -> dict:
    """Choose the marked form of `base_token` best supported by `readings`.

    `readings` are (text, weight) pairs from mark-bearing engines.
    """
    raw = str(base_token or '').strip()
    letters = core(raw).translate(DIGIT_FIXES)
    suffix_match = TRAILING_PUNCT.search(raw)
    suffix = suffix_match.group(0) if suffix_match else ''
    base = fold(letters)
    cleaned = [(core(text), weight) for text, weight in readings if core(text)]
    votes: dict[str, float] = {}
    for text, weight in cleaned:
        if fold(text) == base and is_valid_syllable(text):
            votes[text.lower()] = votes.get(text.lower(), 0.0) + weight
    if votes:
        ranked_votes = sorted(votes.items(), key=lambda item: -item[1])
        winner, top = ranked_votes[0]
        contested = len(ranked_votes) > 1 and ranked_votes[1][1] >= top * .75
        return {'text': _match_case(letters, winner) + suffix, 'source': 'reading',
                'support': round(top / sum(votes.values()), 3), 'needs_review': contested}
    candidates = variants(base)
    if not candidates or not cleaned:
        for text, _ in cleaned:
            if is_valid_syllable(text) and SequenceMatcher(None, fold(text), base).ratio() >= .75:
                return {'text': _match_case(letters or text, text.lower()) + suffix, 'source': 'reading_close', 'support': .6, 'needs_review': True}
        if letters and base in {fold(v) for v in candidates} and is_valid_syllable(letters):
            return {'text': letters + suffix, 'source': 'detector', 'support': .5, 'needs_review': not cleaned}
        return {'text': (letters + suffix) if letters else raw, 'source': 'detector', 'support': 0.0,
                'needs_review': bool(letters) and not is_valid_syllable(letters)}

    def score(candidate: str) -> float:
        total = 0.0
        for text, weight in cleaned:
            shape = SequenceMatcher(None, strip_tone(candidate), strip_tone(text.lower())).ratio()
            # A reading with garbled letters carries proportionally weaker tone evidence.
            letters_agree = SequenceMatcher(None, fold(text), base).ratio()
            total += weight * (shape + (.6 * letters_agree if tone_of(candidate) == tone_of(text) else 0.0))
        if lexicon and candidate in lexicon:
            total += .5
        return total

    ranked = sorted(candidates, key=score, reverse=True)
    best = ranked[0]
    margin = score(best) - (score(ranked[1]) if len(ranked) > 1 else 0.0)
    weight_sum = sum(weight for _, weight in cleaned) or 1.0
    support = min(1.0, score(best) / (1.6 * weight_sum + (.5 if lexicon else 0.0)))
    return {'text': _match_case(letters, best) + suffix, 'source': 'variant', 'support': round(support, 3),
            'needs_review': margin < .15 or support < .45}


def align_tokens(base_tokens: list[str], reading_tokens: list[str]) -> list[str | None]:
    """Monotonic alignment of a line reading onto detector tokens by folded letters."""
    n, m = len(base_tokens), len(reading_tokens)
    if not n:
        return []
    fb = [fold(t) for t in base_tokens]
    fr = [fold(t) for t in reading_tokens]
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back: list[list[str | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0], back[i][0] = dp[i - 1][0], 'skip_base'
    for j in range(1, m + 1):
        dp[0][j], back[0][j] = dp[0][j - 1], 'skip_read'
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sim = SequenceMatcher(None, fb[i - 1], fr[j - 1]).ratio() if fb[i - 1] and fr[j - 1] else 0.0
            options = [(dp[i - 1][j - 1] + (sim if sim >= .34 else -1.0), 'match'),
                       (dp[i - 1][j], 'skip_base'), (dp[i][j - 1], 'skip_read')]
            dp[i][j], back[i][j] = max(options, key=lambda item: item[0])
    result: list[str | None] = [None] * n
    i, j = n, m
    while i > 0 or j > 0:
        step = back[i][j]
        if step == 'match':
            result[i - 1] = reading_tokens[j - 1]
            i, j = i - 1, j - 1
        elif step == 'skip_base':
            i -= 1
        else:
            j -= 1
    return result


def fuse_line(base_tokens: list[str], line_readings: list[tuple[str, float]],
              token_readings: list[list[tuple[str, float]]] | None = None,
              lexicon: frozenset[str] | None = None) -> list[dict]:
    """Fuse detector tokens with whole-line readings and optional per-token readings."""
    per_token = [list(extra) for extra in (token_readings or [])]
    while len(per_token) < len(base_tokens):
        per_token.append([])
    for text, weight in line_readings:
        for index, reading in enumerate(align_tokens(base_tokens, str(text).split())):
            if reading:
                per_token[index].append((reading, weight))
    fused = []
    for token, readings in zip(base_tokens, per_token):
        if not any(c.isalpha() for c in token):
            fused.append({'text': token, 'source': 'detector', 'support': 0.0, 'needs_review': False})
            continue
        fused.append(fuse_syllable(token, readings, lexicon))
    return fused
