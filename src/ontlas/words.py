"""Korean particles chosen by the word before them, so a sentence never shows 을(를) or (으)로.

A Hangul syllable is read by its final consonant; a digit as it is read (일, 이, 삼 ...); a word in capitals letter by
letter (SQL 에스큐엘, API 에이피아이); any other Latin word by its last sound (Order 오더, Item 아이템, Plan 플랜).
"""
from __future__ import annotations

import re

# the particle pairs a sentence is written with: (after a final consonant, after none)
PAIRS = {"을": ("을", "를"), "를": ("을", "를"), "이": ("이", "가"), "가": ("이", "가"), "은": ("은", "는"), "는": ("은", "는"),
         "과": ("과", "와"), "와": ("과", "와"), "으로": ("으로", "로"), "로": ("으로", "로")}
_DIGIT_FINAL = {"0": 21, "1": 8, "3": 16, "6": 1, "7": 8, "8": 8}  # 영 일 삼 육 칠 팔: the final each is read with
_CAPS_FINAL = {"L": 8, "M": 16, "N": 4, "R": 8}  # 엘 엠 엔 알
_RIEUL = 8  # ㄹ: takes 로, not 으로
_SKIP = "'\"’”)]}>」』 "  # quotes and brackets a word is closed with: the particle reads the word inside
_HELD = re.compile(r"(을\(를\)|를\(을\)|이\(가\)|가\(이\)|은\(는\)|는\(은\)|과\(와\)|와\(과\)|\(으\)로)")
_PARTICLE = {"을(를)": "을", "를(을)": "을", "이(가)": "이", "가(이)": "이", "은(는)": "은", "는(은)": "은", "과(와)": "과",
             "와(과)": "과", "(으)로": "으로"}


def _final(word: str) -> int | None:
    """The final consonant the word ends on (0 for none), or None where it cannot be told."""
    w = str(word or "").rstrip(_SKIP)
    if not w:
        return None
    c = w[-1]
    if "가" <= c <= "힣":
        return (ord(c) - 0xAC00) % 28
    if c.isdigit():
        return _DIGIT_FINAL.get(c, 0)
    if c.isascii() and c.isalpha():
        run = re.search(r"[A-Za-z]+$", w).group(0)
        if run.isupper():  # an abbreviation, read letter by letter
            return _CAPS_FINAL.get(c, 0)
        low = run.lower()
        if len(low) > 2 and low[-1] == "e" and low[-2] in "lmn":  # a silent e: name 네임, file 파일, phone 폰
            low = low[:-1]
        if low.endswith("ng"):
            return 21
        return {"l": _RIEUL, "m": 16, "n": 4}.get(low[-1], 0)
    return None


def josa(word: str, particle: str) -> str:
    """The form of a particle ('을', '이', '은', '과', '으로') that follows the word."""
    with_final, without = PAIRS[particle]
    f = _final(word)
    if f is None:
        return without
    if with_final == "으로":
        return "으로" if f and f != _RIEUL else "로"
    return with_final if f else without


def fix(text: str) -> str:
    """A sentence with each 을(를), 이(가), 은(는), 과(와), (으)로 replaced by the form the word before it takes. A space
    left between the word and the particle goes too."""
    if "(" not in text:
        return text
    out, at = [], 0
    for m in _HELD.finditer(text):
        start = m.start()
        before = text[at:start]
        lead = before.rstrip(" ")
        out.append(lead if lead else before)
        out.append(josa(text[:start].rstrip(" "), _PARTICLE[m.group(0)]))
        at = m.end()
    out.append(text[at:])
    return "".join(out)
