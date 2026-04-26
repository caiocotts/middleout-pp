import argparse
import re
from ollama import ChatResponse, Client

MODEL = 'gemma4:e4b'

VOWELS = set('aeiouAEIOU')

# Words whose vowel-stripped skeleton is ambiguous between 2+ common words.
# The compressor will leave these intact rather than risk irrecoverable errors.
AMBIGUOUS_SKELETONS = {
    'brd',   # bird/bored/board/bread/brad
    'grd',   # grid/grad/gored/guard
    'fnd',   # find/fond/fend/fund/fiend
    'fld',   # fled/fold/fluid/field
    'mn',    # man/men/moan/moon/mine/mean
    'bt',    # bit/bat/bot/but/beat/bite
    'wrd',   # word/ward/weird
    'plt',   # plot/plait/pleat
    'st',    # sit/set/sat/sot/suit
    'lt',    # lot/let/lat/loot/lute
    'bn',    # ban/bin/bone/boon/bean
    'pn',    # pan/pen/pin/pun/pain/pine
    'prd',   # prod/proud/prude/pried
    'trd',   # trod/trade/tired/tried
    'crs',   # cars/cures/cores/cares
    'hrs',   # hers/hours/hires/heirs
}


def compress_word(token: str, at_sentence_start: bool) -> str:
    """Strip internal vowels from a single whitespace-delimited token."""
    # Separate leading/trailing punctuation from the alphabetic core
    match = re.fullmatch(r'([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)', token)
    if not match:
        return token
    pre, core, post = match.groups()

    # Skip contractions
    if "'" in token:
        return token
    # Skip all-caps (acronyms / initialisms)
    if core.isupper():
        return token
    # Skip proper nouns: capitalized words that are not at a sentence start
    if core[0].isupper() and not at_sentence_start:
        return token
    # Skip short words (4 chars or fewer)
    if len(core) <= 4:
        return token

    first, middle, last = core[0], core[1:-1], core[-1]
    stripped_middle = ''.join(c for c in middle if c not in VOWELS)
    skeleton = (first + stripped_middle + last).lower()

    # Skip if the resulting skeleton is known to be ambiguous
    if skeleton in AMBIGUOUS_SKELETONS:
        return token
    # Skip if compression saves fewer than 2 characters (not worth the noise)
    compressed_core = first + stripped_middle + last
    if len(core) - len(compressed_core) < 2:
        return token
    # Skip if the compressed form would be < 4 chars — the decompressor can't
    # reliably detect it, and short skeletons are highly ambiguous (e.g. yrs, txc)
    if len(compressed_core) < 4:
        return token

    return pre + compressed_core + post


# Characters that, when appearing at the end of a token (after stripping closing
# quotes/brackets), signal the end of a sentence.
_SENTENCE_ENDERS = frozenset('.!?')
_CLOSING = frozenset('"\'»)')


def compress(text: str) -> str:
    tokens = re.split(r'(\s+)', text)  # split on whitespace, preserving it
    result = []
    at_sentence_start = True  # beginning of text counts as a sentence start

    for token in tokens:
        if token.isspace():
            if '\n\n' in token:
                at_sentence_start = True
            result.append(token)
            continue

        result.append(compress_word(token, at_sentence_start))

        # Determine whether the *next* word begins a new sentence by checking
        # what punctuation this token ends with (ignoring trailing quotes etc.)
        bare = token.rstrip(''.join(_CLOSING))
        at_sentence_start = bool(bare) and bare[-1] in _SENTENCE_ENDERS

    return ''.join(result)


DECOMPRESS_SYSTEM_PROMPT = """\
You are a lossless text decompressor. The input is a compressed version of an original text.

Compressed tokens are self-identifying by this exact rule:
  A token is compressed if and only if ALL of the following are true:
  1. Its alphabetic core (the full sequence of letters, ignoring any surrounding punctuation) is 4 or more characters long. Count ALL letters including the first and last.
  2. Every character BETWEEN the first and last letter of that core is a consonant — i.e. none of: a, e, i, o, u (case-insensitive). Only check the interior characters, not the first or last.

  Example check for "Bsde": core = "Bsde", length = 4 ✓, interior = "sd" (no vowels) ✓ → COMPRESSED → expand it.
  Example check for "the": core = "the", length = 3 ✗ → NOT compressed → copy verbatim.
  Example check for "pizza": core = "pizza", length = 5 ✓, interior = "izz" (contains 'i') ✗ → NOT compressed → copy verbatim.

═══ HARD CONSTRAINTS (never violate) ═══

C1. COPY ALL ORIGINAL TOKENS VERBATIM. If a token does not meet the compressed-token rule above, output it exactly as-is. Never correct spelling, change tense, or substitute synonyms on original tokens.

C2. ONE-TO-ONE MAPPING. Each compressed token expands to exactly one word. Never split one token into two words or merge two tokens.

C3. INSERT ONLY VOWELS. To expand a compressed token, insert the minimum vowels needed between its existing consonants to form a real English word. Do not add, remove, or rearrange any consonants.

C4. USE CONTEXT TO DISAMBIGUATE. If multiple vowel insertions produce valid words, choose the one that best fits the surrounding sentence grammatically and semantically.

C5. PRESERVE ALL PUNCTUATION AND SPACING EXACTLY. Do not add, remove, or change punctuation marks, capitalisation, or sentence boundaries.

C6. OUTPUT ONLY THE RECONSTRUCTED TEXT. No explanations, metadata, or commentary.

Begin your response with the first word of the reconstructed text.
"""


def decompress(text: str) -> str:
    client = Client(host='hyperion.caiocotts.com:11434')
    response: ChatResponse = client.chat(model=MODEL, messages=[
        {'role': 'system', 'content': DECOMPRESS_SYSTEM_PROMPT},
        {'role': 'user', 'content': f'Restore the missing letters in the following compressed text:\n"""\n{text}\n"""'},
    ])
    return response['message']['content']


def main():
    parser = argparse.ArgumentParser(description='Middleout: LLM-assisted hybrid compression POC')
    parser.add_argument('mode', choices=['compress', 'decompress', 'roundtrip'],
                        help='compress: phase 1 only (algorithmic) | decompress: phase 2 only (LLM) | roundtrip: both phases in sequence')
    parser.add_argument('input', help='Path to input text file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        text = f.read()

    if args.mode == 'compress':
        print(compress(text))

    elif args.mode == 'decompress':
        print(decompress(text))

    elif args.mode == 'roundtrip':
        compressed = compress(text)
        ratio = (1 - len(compressed) / len(text)) * 100
        print(f'=== COMPRESSED ({ratio:.1f}% smaller) ===')
        print(compressed)
        print('\n=== RECONSTRUCTED ===')
        print(decompress(compressed))


if __name__ == '__main__':
    main()

