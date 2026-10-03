"""
cv_screener/matcher.py  --  Regular-expression keyword & requirement matching.

OWNER: Aiwansoba Eric  (Regular Expressions & Requirement Matching)

For ONE CV and ONE job description, checks every requirement with regular expressions
and reports, per requirement:  FOUND / NOT FOUND, the exact text matched, evidence
snippets, and how many YEARS the CV shows for it (from "5 years of Python" statements
and from dated work history like "Jan 2021 - Present", overlaps counted once).
Degrees are matched by LEVEL and FIELD (B.Sc, HND, OND, Master's, PhD ...).

Regex records evidence only. It never rejects a CV by itself: the ranker (Muhammad)
combines these results with the Gemini AI verdicts.

HOW THE REST OF THE TEAM CALLS IT
    from cv_screener.matcher import RegexMatcher
    results = RegexMatcher().match_all(job, cv)      # -> list[RegexResult], one per requirement
    # `job`: anything with .requirements, or a JobDescription with skills/experience/education
    # `cv` : anything with a .text attribute (the CV text)

This file has NO imports from other team files, so it works even before models.py is finished.
The ONLY part to edit when models.py is finalised is the ADAPTER section at the very bottom.

Sections:  1 experience (years/dates) | 2 degrees | 3 term patterns | 4 matcher | 5 adapter
"""
from __future__ import annotations

import json
import re
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, field
from datetime import date
from functools import cached_property, lru_cache
from typing import Any, Dict, Iterable, List, Optional, Pattern, Sequence, Tuple

JobLike = Any   # whatever the shared JobDescription turns out to be (see ADAPTER section)
CVLike = Any    # whatever the shared CVDocument turns out to be (needs a .text attribute)


@dataclass
class Requirement:
    """One thing the job asks for. The adapter builds these from the shared JobDescription."""
    name: str                                   # e.g. "Python", "Bachelor's degree in Computer Science"
    mandatory: bool = True                      # True = mandatory, False = preferred
    aliases: List[str] = field(default_factory=list)
    min_years: Optional[float] = None           # minimum years of experience, if stated
    id: int = 0                                 # 0 = "assign by position" (1, 2, 3 ...)


# ============================================================================
# 1. EXPERIENCE - years of experience from statements and dates
# ============================================================================

# --------------------------------------------------------------------------- #
# 1. Stated durations
# --------------------------------------------------------------------------- #
NUMBER_WORDS: Dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
_NUM = (r"(?:\d{1,2}(?:\.\d+)?|"
        + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")")

YEARS_RE = re.compile(
    rf"(?<![\w.])(?P<n1>{_NUM})(?:\s*\(\d{{1,2}}\))?\s*(?P<plus>\+)?"
    rf"(?:\s*(?:-|–|—|to)\s*(?P<n2>{_NUM})\s*\+?)?\s*"
    rf"(?P<unit>years?|yrs?|months?|mos?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class YearStatement:
    start: int
    end: int
    years: float          # lower bound of a range, months converted to years
    text: str
    enclosed: bool        # sits inside ( ) or [ ], e.g. "Java (5 years)"


def _to_number(token: str) -> float:
    token = token.lower()
    return float(token) if token[0].isdigit() else float(NUMBER_WORDS[token])


def parse_years_match(m: "re.Match[str]") -> float:
    """Years value of a YEARS_RE match (months are converted to years)."""
    n1 = _to_number(m.group("n1"))
    return n1 if m.group("unit").lower().startswith("y") else n1 / 12.0


def find_year_statements(text: str) -> List[YearStatement]:
    out: List[YearStatement] = []
    for m in YEARS_RE.finditer(text):
        prior = text[max(0, m.start() - 5):m.start()].rstrip()[-1:]
        out.append(YearStatement(m.start(), m.end(), parse_years_match(m),
                                 m.group(0), prior in ("(", "[")))
    return out


_PRE_BREAK = re.compile(r"[\n,;:.]")
_POST_PUNCT = re.compile(r"[\s:\-–—(\[]{0,8}")
_POST_WORDS = re.compile(
    r"\s+(?:[\w\-+#.]+\s+){0,2}(?:with|having|of|for)\s+"
    r"(?:(?:over|more\s+than|about|around|nearly|almost)\s+)?")


def stated_years_for_spans(text: str, statements: Sequence[YearStatement],
                           spans: Sequence[Tuple[int, int]]) -> Optional[YearStatement]:
    """
    Pick the stated duration that belongs to a skill (given its match spans).

    Accepted layouts:  "5 years of experience in <skill>"   (statement before)
                       "<skill> (5 years)", "<skill>: 5 yrs" (statement after)
                       "<skill> developer with 5 years"      (statement after)
    A statement is never attached across a comma, full stop, semicolon, colon
    or line break, and never when another statement sits between it and the
    skill. That stops "Java (5 years), Python (2 years)" giving Python 5 years.

    Statements are in text order, so bisect finds the few candidates next to each
    span instead of comparing every span with every statement.
    """
    best: Optional[YearStatement] = None
    if not statements:
        return best
    starts = [st.start for st in statements]
    ends = [st.end for st in statements]
    n = len(statements)
    for s, e in spans:
        cands: List[YearStatement] = []
        i = bisect_right(ends, s) - 1                        # nearest statement BEFORE the skill
        if i >= 0:
            st = statements[i]
            nxt_ok = i + 1 >= n or statements[i + 1].start >= s
            if (not st.enclosed and s - st.end <= 45 and nxt_ok
                    and not _PRE_BREAK.search(text[st.end:s])):
                cands.append(st)
        j = bisect_left(starts, e)                           # statements AFTER the skill
        while j < n and starts[j] - e <= 40:
            gap = text[e:starts[j]]
            if _POST_PUNCT.fullmatch(gap) or _POST_WORDS.fullmatch(gap):
                cands.append(statements[j])
            j += 1
        for st in cands:
            if best is None or st.years > best.years:
                best = st
    return best


_EXP_AFTER = re.compile(r"['’]?\s*(?:of\s+)?(?:[\w\-]+\s+){0,2}?experience", re.I)


def total_stated_years(text: str, statements: Sequence[YearStatement]) -> Optional[YearStatement]:
    """Largest 'N years (of ...) experience' statement: a lower bound on total experience."""
    best = None
    for st in statements:
        if _EXP_AFTER.match(text, st.end) and (best is None or st.years > best.years):
            best = st
    return best


# --------------------------------------------------------------------------- #
# 2. Date ranges
# --------------------------------------------------------------------------- #
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
          r"aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_YEAR = r"(?:19|20)\d{2}"
_DATE = (rf"(?:\b{_MONTH}\.?,?\s*{_YEAR}(?!\d)"
         rf"|(?<!\d)(?:0?[1-9]|1[0-2])\s*[/.\-]\s*{_YEAR}(?!\d)"
         rf"|(?<!\d){_YEAR}(?!\d))")
_PRESENT = r"(?:present|current(?:ly)?|now|date|ongoing|today)\b"
RANGE_RE = re.compile(
    rf"(?P<start>{_DATE})\s*(?:-|–|—|−|to|until|till|through)\s*(?P<end>{_DATE}|{_PRESENT})",
    re.IGNORECASE,
)
_TOK_MY = re.compile(rf"({_MONTH})\.?,?\s*({_YEAR})", re.I)
_TOK_NUM = re.compile(rf"(\d{{1,2}})\s*[/.\-]\s*({_YEAR})")
_TOK_Y = re.compile(rf"({_YEAR})")


@dataclass(frozen=True)
class DateRange:
    start_pos: int
    end_pos: int
    start_idx: int        # months since year 0, inclusive
    end_idx: int          # exclusive
    text: str


def _token_index(token: str, is_end: bool, today_idx: int) -> Optional[Tuple[int, bool]]:
    t = token.strip().lower()
    if re.match(r"(?:present|current|now|date|ongoing|today)", t):
        return today_idx, False
    m = _TOK_MY.search(t)
    if m:
        mo, y = _MONTHS[m.group(1)[:3]], int(m.group(2))
        return (y * 12 + mo if is_end else y * 12 + mo - 1), False
    m = _TOK_NUM.search(t)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        return (y * 12 + mo if is_end else y * 12 + mo - 1), False
    m = _TOK_Y.search(t)
    if m:
        return int(m.group(1)) * 12 + 6, True        # conservative for year-only dates
    return None


def find_date_ranges(text: str, today: Optional[date] = None) -> List[DateRange]:
    today = today or date.today()
    today_idx = today.year * 12 + today.month
    out: List[DateRange] = []
    for m in RANGE_RE.finditer(text):
        a = _token_index(m.group("start"), False, today_idx)
        b = _token_index(m.group("end"), True, today_idx)
        if a is None or b is None:
            continue
        (s_idx, s_yo), (e_idx, e_yo) = a, b
        e_idx = min(e_idx, today_idx)
        if e_idx == s_idx and s_yo and e_yo:
            e_idx = min(s_idx + 6, today_idx)         # "2022 - 2022" = about six months
        if e_idx <= s_idx or e_idx - s_idx > 600:
            continue
        out.append(DateRange(m.start(), m.end(), s_idx, e_idx, m.group(0)))
    return out


# --------------------------------------------------------------------------- #
# 3. Job blocks (a date range plus the text that belongs to it)
# --------------------------------------------------------------------------- #
_EDU_RE = re.compile(
    r"\b(?:universit(?:y|ies)|college|polytechnic|secondary\s+school|high\s+school|"
    r"bachelor|b\.?\s?sc|m\.?\s?sc|b\.?\s?eng|m\.?\s?eng|ph\.?\s?d|hnd|diploma|"
    r"degree|certificat\w*|bootcamp)\b", re.I)
_SECTION_RE = re.compile(
    r"^\s*(?:(?:technical\s+|key\s+|core\s+)?skills?|core\s+competenc(?:y|ies)|"
    r"education(?:\s+and\s+training)?|academic\s+\w+|certifications?|licen[cs]es?|"
    r"references?|referees|languages?|interests|hobbies|projects?|awards|"
    r"publications|summary|profile|personal\s+(?:details|information)|declaration)"
    r"\s*:?\s*$", re.I | re.M)


@dataclass(frozen=True)
class JobBlock:
    start: int
    end: int
    start_idx: int
    end_idx: int
    is_education: bool
    range_text: str


def _line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def _line_end(text: str, pos: int) -> int:
    i = text.find("\n", pos)
    return len(text) if i == -1 else i


def _prev_nonempty_line_start(text: str, ls: int) -> int:
    p = ls
    while p > 0:
        prev_end = p - 1
        prev_start = text.rfind("\n", 0, prev_end) + 1
        if text[prev_start:prev_end].strip():
            return prev_start
        p = prev_start
    return ls


def build_blocks(text: str, today: Optional[date] = None) -> List[JobBlock]:
    ranges = find_date_ranges(text, today)
    if not ranges:
        return []
    starts, edu_flags = [], []
    for idx, r in enumerate(ranges):
        line_s, line_e = _line_start(text, r.start_pos), _line_end(text, r.end_pos)
        eff = line_s
        flattened = idx > 0 and line_s < ranges[idx - 1].end_pos
        if flattened:
            # several date ranges on one line (text without line breaks): the date comes first
            block_start = r.start_pos
        else:
            near = text[max(line_s, r.start_pos - 60):r.start_pos] + text[r.end_pos:min(line_e, r.end_pos + 60)]
            if len(re.sub(r"[\W_]+", "", near)) < 4:   # date alone on its line -> title is above it
                eff = _prev_nonempty_line_start(text, line_s)
            block_start = eff
        starts.append(block_start)
        lo = max(eff, r.start_pos - 150)
        if flattened:
            lo = max(lo, ranges[idx - 1].end_pos)
        edu_flags.append(bool(_EDU_RE.search(text[lo:min(line_e, r.end_pos + 200)])))
    blocks: List[JobBlock] = []
    for i, r in enumerate(ranges):
        end = len(text)
        if i + 1 < len(ranges):
            end = max(starts[i + 1], r.end_pos)
        end = min(end, starts[i] + 4000)
        hdr = _SECTION_RE.search(text, r.end_pos, end)
        if hdr:
            end = hdr.start()
        blocks.append(JobBlock(starts[i], max(end, r.end_pos), r.start_idx,
                               r.end_idx, edu_flags[i], r.text))
    return blocks


def union_months(intervals: Sequence[Tuple[int, int]]) -> int:
    total, cur_s, cur_e = 0, None, None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total


def skill_years_from_blocks(blocks: Sequence[JobBlock],
                            spans: Sequence[Tuple[int, int]]) -> Tuple[float, List[str]]:
    """Years covered by (non-education) job blocks that mention the skill."""
    used = [b for b in blocks
            if not b.is_education and any(b.start <= s < b.end for s, _ in spans)]
    months = union_months([(b.start_idx, b.end_idx) for b in used])
    return months / 12.0, [b.range_text for b in used]


def total_years_from_blocks(blocks: Sequence[JobBlock]) -> Tuple[float, List[str]]:
    used = [b for b in blocks if not b.is_education]
    months = union_months([(b.start_idx, b.end_idx) for b in used])
    return months / 12.0, [b.range_text for b in used]

# ============================================================================
# 2. DEGREES - level and field of study
# ============================================================================

LEVEL_RANK = {"diploma": 1, "hnd": 2, "bachelor": 3, "master": 4, "doctorate": 5}

# --------------------------------------------------------------------------- #
# CV side
# --------------------------------------------------------------------------- #
_DOCTORATE = (r"(?i:ph\.?\s?d)|D\.?\s?Phil|DBA|"
              r"(?i:doctor(?:ate|al)(?:\s+degree)?|doctor\s+of\s+philosophy)")
_MASTER = (r"M\.?\s?Sc|M\.?\s?Eng|M\.?\s?Tech|MBA|M\.?\s?Phil|LL\.?M|M\.?\s?Ed|M\.?\s?Res|"
           r"M\.\s?A|M\.\s?S|"
           r"(?i:master(?:['’]s|s)(?:\s+degree)?(?:\s+of)?|master\s+degree|master\s+of|"
           r"post[\s-]?graduate\s+degree)")
_BACHELOR = (r"B\.?\s?Sc|B\.?\s?Eng|B\.?\s?Tech|B\.?\s?Com|B\.?\s?Ed|B\.?\s?Pharm|B\.?\s?Arch|"
             r"B\.\s?A|B\.\s?S|BBA|LL\.?B|MBBS|"
             r"(?i:bachelor(?:['’]?s)?(?:\s+degree)?(?:\s+of)?|first\s+degree)|"
             r"(?i:degree(?=\s+(?:in|from)\b|\s*:))")
_HND = r"H\.?N\.?D|(?i:higher\s+national\s+diploma)"
_DIPLOMA = (r"O\.?N\.?D|(?i:ordinary\s+national\s+diploma|national\s+diploma|"
            r"associate(?:['’]s)?\s+degree|diploma)")

_ORDER = [("doctorate", _DOCTORATE), ("master", _MASTER), ("bachelor", _BACHELOR),
          ("hnd", _HND), ("diploma", _DIPLOMA)]
_CV_DEGREE_RE = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(f"(?P<{n}>{p})" for n, p in _ORDER) + r")\.?(?![A-Za-z])")

_FIELD_CUT = re.compile(
    r"[,;|(]|\s[-–—]\s|\b(?:19|20)\d{2}\b|\b(?:from|at)\b|"
    r"\b(?:universit|college|polytechnic|institute|school)", re.I)


@dataclass
class DegreeMention:
    level: str
    rank: int
    text: str
    field: str
    context: str
    start: int
    end: int


def _clean_field(after: str) -> str:
    s = after.strip()
    s = re.sub(r"^\(?\s*hons?\b\.?\s*\)?", "", s, flags=re.I).strip()
    s = re.sub(r"^[\s,:\-–—]*(?:(?:in|of)\s+)?", "", s, flags=re.I)
    s = _FIELD_CUT.split(s, maxsplit=1)[0]
    s = re.split(r"\s+in\s+", s, flags=re.I)[-1]
    return s.strip(" .:-–—")[:80]


def find_degrees(text: str) -> List[DegreeMention]:
    out: List[DegreeMention] = []
    for m in _CV_DEGREE_RE.finditer(text):
        level = m.lastgroup
        ls = text.rfind("\n", 0, m.start()) + 1
        le = text.find("\n", m.end())
        le = len(text) if le == -1 else le
        fld = _clean_field(text[m.end():le])
        context = re.sub(r"\s+", " ", text[ls:le]).strip()
        if not fld and le < len(text):                      # field may sit on the next line
            nxt = text[le + 1:].split("\n", 1)[0].strip()
            if 0 < len(nxt) < 120:
                context += " " + re.sub(r"\s+", " ", nxt)
        out.append(DegreeMention(level, LEVEL_RANK[level], m.group(0).strip(),
                                 fld, context, m.start(), m.end()))
    return out


# --------------------------------------------------------------------------- #
# Job side
# --------------------------------------------------------------------------- #
_REQ_SPECIFIC = [
    (5, r"ph\.?\s?d\b|doctorate|doctoral"),
    (4, r"master['’]?s\b|master\s+(?:degree|of)\b|m\.?\s?sc\b|m\.?\s?eng\b|m\.?\s?tech\b|"
        r"mba\b|post[\s-]?graduate"),
    (3, r"bachelor|b\.?\s?sc\b|b\.?\s?eng\b|b\.?\s?tech\b|first\s+degree"),
    (2, r"hnd\b|higher\s+national\s+diploma"),
    (1, r"ond\b|national\s+diploma|diploma"),
]
_REQ_SPECIFIC_RE = [(r, re.compile(r"(?<![a-z0-9])(?:" + p + ")", re.I)) for r, p in _REQ_SPECIFIC]
_REQ_GENERIC_RE = re.compile(r"(?<![a-z0-9])(?:degree|undergraduate|graduate)\b", re.I)

_GENERIC_FIELD_WORDS = {"a", "an", "the", "related", "relevant", "similar", "equivalent", "field",
                        "fields", "discipline", "disciplines", "subject", "subjects", "area",
                        "areas", "other", "any", "technical", "higher", "higher-level"}
_LEVEL_WORDS = {"bachelor", "bachelors", "bachelor's", "master", "masters", "master's", "degree",
                "diploma", "hnd", "ond", "phd", "doctorate", "bsc", "msc", "beng", "meng",
                "btech", "mtech", "mba", "undergraduate", "postgraduate", "graduate"}

FIELD_GROUPS = {
    "computing": ["computing", "computer", "computers", "software", "information technology",
                  "information systems", "information system", "informatics", "data science",
                  "artificial intelligence", "machine learning", "cyber security",
                  "cybersecurity", "computational", "ict",
                  "information and communication technology"],
}


def required_rank(text: str) -> Optional[int]:
    """Minimum degree level a requirement asks for, or None if it is not a degree requirement."""
    ranks = [rank for rank, rx in _REQ_SPECIFIC_RE if rx.search(text)]
    if ranks:
        return min(ranks)
    if _REQ_GENERIC_RE.search(text):
        return LEVEL_RANK["bachelor"]
    return None


def required_fields(text: str) -> List[str]:
    t = text.lower()
    phrase = None
    m = re.search(r"(?:\bin\b|:)\s*(.+)$", t)
    if m:
        phrase = m.group(1)
    else:
        m = re.search(r"\b(?:bachelor\S*|master\S*|doctorate|degree|diploma)\s+of\s+(.+)$", t)
        if m:
            phrase = m.group(1)
        else:
            m = re.match(r"^(.*?)\s*\b(?:degree|diploma|hnd|b\.?\s?sc|m\.?\s?sc|b\.?\s?eng)\b", t)
            if m:
                phrase = m.group(1)
    if not phrase:
        return []
    phrase = re.split(r"\b(?:with|from|plus|preferred|required|desirable|equivalent|higher)\b|[(.\d]",
                      phrase, maxsplit=1)[0]
    fields: List[str] = []
    for part in re.split(r"\s*(?:,|/|;|&|\bor\b|\band\b)\s*", phrase):
        tokens = [w for w in re.findall(r"[a-z+#]+", part)
                  if w not in _GENERIC_FIELD_WORDS and w not in _LEVEL_WORDS]
        if tokens:
            f = " ".join(tokens)
            if f not in fields:
                fields.append(f)
    return fields


def _word_in(text: str, term: str) -> bool:
    body = r"\s+".join(re.escape(w) for w in term.split())
    return re.search(r"(?<![a-z])" + body + r"(?:e?s)?(?![a-z])", text) is not None


def field_matches(required_field: str, context: str) -> bool:
    ctx, req = context.lower(), required_field.lower()
    for terms in FIELD_GROUPS.values():
        if any(_word_in(req, t) for t in terms) and any(_word_in(ctx, t) for t in terms):
            return True
    if _word_in(ctx, req):
        return True
    toks = req.split()
    return bool(toks) and all(_word_in(ctx, tok) for tok in toks)


@dataclass
class DegreeMatch:
    found: bool
    evidence: List[str] = field(default_factory=list)
    matched: List[str] = field(default_factory=list)
    note: str = ""


def match_degree_requirement(texts: Sequence[str], cv_text: str) -> Optional[DegreeMatch]:
    """
    texts = requirement name + aliases. Returns None when none of them is a degree
    requirement (the normal keyword search then applies).
    """
    specs = []
    for t in texts:
        rank = required_rank(t)
        if rank is not None:
            specs.append((rank, required_fields(t)))
    if not specs:
        return None

    mentions = find_degrees(cv_text)
    for rank, fields in specs:
        for m in mentions:
            if m.rank >= rank and (not fields or any(field_matches(f, m.context) for f in fields)):
                return DegreeMatch(True, [m.context[:200]], [m.text], "")

    if not mentions:
        return DegreeMatch(False, [], [], "No degree or diploma found in the CV text.")
    best = max(mentions, key=lambda m: m.rank)
    min_rank = min(r for r, _ in specs)
    if best.rank < min_rank:
        note = "Qualification found, but below the required level. Needs AI/human check."
    else:
        note = "Degree of the required level found, but its field was not recognised. Needs AI/human check."
    return DegreeMatch(False, [best.context[:200]], [best.text], note)

# ============================================================================
# 3. TERM PATTERNS - skill names, aliases, synonyms
# ============================================================================

_LB_STRONG = r"(?<![A-Za-z0-9_])(?<![A-Za-z0-9_]\.)"
_LB_WEAK = r"(?<![A-Za-z0-9_])"
_LA_STRONG = r"(?![A-Za-z0-9_])(?!\+\+|#)"
_LA_WEAK = r"(?![A-Za-z0-9_])"
_SEP = r"[\s\-_.]*"
_SEP_SPLIT = re.compile(r"(?<=\w)[\s\-_.]+(?=\w)")


def is_case_sensitive(term: str) -> bool:
    return len(re.sub(r"[^A-Za-z0-9]", "", term)) <= 2


def term_to_regex(term: str) -> str:
    term = term.strip()
    pieces = _SEP_SPLIT.split(term)
    parts = []
    for p in pieces:
        trailing_dot = p.endswith(".") and len(p) > 1
        core = p[:-1] if trailing_dot else p
        parts.append(re.escape(core) + (r"\.?" if trailing_dot else ""))
    body = _SEP.join(parts)
    if term[-1:].isalpha() and len(re.sub(r"[^A-Za-z0-9]", "", term)) >= 3:
        body += r"(?:e?s)?"
    lb = _LB_STRONG if term[:1].isalnum() else _LB_WEAK
    la = _LA_STRONG if term[-1:].isalnum() else _LA_WEAK
    return lb + body + la


@lru_cache(maxsize=4096)
def compile_term(term: str) -> Pattern[str]:
    flags = 0 if is_case_sensitive(term) else re.IGNORECASE
    return re.compile(term_to_regex(term), flags)


# --------------------------------------------------------------------------- #
# Requirement name -> list of search terms
# --------------------------------------------------------------------------- #
_FILLER_PREFIX = re.compile(
    r"^(?:(?:strong|solid|good|excellent|proven|hands-on|working|demonstrable|demonstrated|"
    r"extensive|advanced|basic|practical|relevant|professional|commercial)\s+)*"
    r"(?:(?:experience|experienced|knowledge|proficiency|proficient|expertise|familiarity|"
    r"skills?|skilled|competence|competency|background|understanding|command|mastery|ability)"
    r"\s+(?:with|in|of|using|on)\s+)", re.I)
_FILLER_SUFFIX = re.compile(
    r"\s+(?:experience|skills?|knowledge|proficiency|expertise|background)$", re.I)
_YEARS_TAIL = re.compile(
    r"^\W*(?:of\s+)?(?:(?:relevant|professional|commercial|hands-on|working|industry|"
    r"practical|proven|solid)\s+)*(?:experience\s+)?(?:(?:in|with|using|of|on)\s+)?", re.I)
_STOP_TERMS = {"equivalent", "similar", "other", "others", "related", "relevant",
               "any", "etc", "the", "and", "or", "a", "an"}


@dataclass
class ExpandedRequirement:
    core: str                      # requirement name with the years phrase and filler removed
    terms: List[str]               # everything to search for
    min_years: Optional[float]     # parsed from the name, e.g. "5+ years of ..." -> 5


def expand_requirement_terms(name: str, aliases: Iterable[str] = (),
                             synonyms: Optional[Dict[str, List[str]]] = None) -> ExpandedRequirement:
    core = (name or "").strip()
    min_years: Optional[float] = None
    m = YEARS_RE.search(core)
    if m:
        min_years = round(parse_years_match(m), 2)
        tail = _YEARS_TAIL.sub("", core[m.end():].lstrip(" +,:;"))
        core = re.sub(r"[\(\[]\s*[\)\]]", "", core[:m.start()] + " " + tail)
        core = re.sub(r"\s+", " ", core).strip(" ,;:-–—([")

    out: List[str] = []
    seen = set()

    def add(t: Optional[str]) -> None:
        t = re.sub(r"\s+", " ", t or "").strip(" \t,;:–—-").rstrip(".")
        key = t.lower()
        if (not t or key in seen or key in _STOP_TERMS
                or not re.search(r"[A-Za-z0-9]", t) or "(" in t or ")" in t):
            return
        seen.add(key)
        out.append(t)

    stripped_prefix = _FILLER_PREFIX.sub("", core)
    for base in (core, stripped_prefix):
        add(base)
        add(_FILLER_SUFFIX.sub("", base))
    for t in list(out) + [core, stripped_prefix, _FILLER_SUFFIX.sub("", stripped_prefix)]:
        add(re.sub(r"\([^()]*\)", " ", t))
        for inner in re.findall(r"\(([^()]*)\)", t):
            for part in re.split(r"[,/;]", inner):
                add(part)
    for t in list(out):
        if re.search(r"\sor\s", t, re.I):
            for part in re.split(r"\s+or\s+", t, flags=re.I):
                add(part)
    for a in aliases or []:
        add(a)
    if synonyms:
        lowered = {k.lower(): v for k, v in synonyms.items()}
        for t in list(out):
            for alias in lowered.get(t.lower(), []):
                add(alias)
    return ExpandedRequirement(core=core, terms=out, min_years=min_years)

# ============================================================================
# 4. MATCHER - one result per requirement
# ============================================================================

FOUND = "FOUND"
NOT_FOUND = "NOT FOUND"

_GENERIC_EXPERIENCE = re.compile(
    r"^(?:(?:total|overall|relevant|professional|work(?:ing)?|industry|proven|related|prior|"
    r"previous)\s+)*(?:years?\s+of\s+)?experience$", re.I)


class RegexMatchError(Exception):
    """Raised for an unusable pattern. Jeffrey can re-parent this to ScreeningError."""


@dataclass
class RegexResult:
    requirement_id: int
    requirement: str
    status: str = NOT_FOUND
    matched_terms: List[str] = field(default_factory=list)   # exact text matched, e.g. ["JS"]
    evidence: List[str] = field(default_factory=list)        # short snippets around the matches
    mentions: int = 0
    years_found: Optional[float] = None
    years_source: str = ""                                    # "stated" | "dates" | ""
    years_evidence: List[str] = field(default_factory=list)
    min_years: Optional[float] = None
    years_ok: Optional[bool] = None                           # None = no minimum, or no duration evidence
    note: str = ""

    @property
    def found(self) -> bool:
        return self.status == FOUND

    def to_dict(self) -> dict:
        return asdict(self)


class _CVAnalysis:
    """Per-CV work that is shared by all requirements (computed once, lazily)."""

    def __init__(self, text: str, today: date):
        self.text = prepare_text(text)
        self.today = today

    @cached_property
    def statements(self):
        return find_year_statements(self.text)

    @cached_property
    def blocks(self):
        return build_blocks(self.text, self.today)


def prepare_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[\u200b\u00ad]", "", t)
    return re.sub(r"(?<=[A-Za-z])-\n(?=[a-z])", "", t)        # re-join "Machine-\nlearning"


def _snippet(text: str, start: int, end: int, ctx: int) -> str:
    a, b = max(0, start - ctx), min(len(text), end + ctx)
    body = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("…" if a > 0 else "") + body + ("…" if b < len(text) else "")


def _fmt_years(y: float) -> str:
    return f"{y:g}"


class RegexMatcher:
    def __init__(self, synonyms: Optional[Dict[str, List[str]]] = None,
                 context_chars: int = 60, max_evidence: int = 3,
                 today: Optional[date] = None):
        """
        synonyms      optional {"javascript": ["js", "ecmascript"], ...} (e.g. loaded from synonyms.json)
        context_chars characters of context kept on each side of a match
        max_evidence  most snippets stored per requirement
        today         date used for "Present" in date ranges (fixed in tests)
        """
        self.synonyms = synonyms or {}
        self.context_chars = context_chars
        self.max_evidence = max_evidence
        self.today = today or date.today()

    # ------------------------------------------------------------------ API
    @staticmethod
    def load_synonyms(path: str) -> Dict[str, List[str]]:
        """Load synonyms.json; a missing or broken file simply gives no synonyms."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return {str(k): [str(v) for v in vs] for k, vs in data.items()}
        except (OSError, ValueError, AttributeError):
            return {}

    def match_all(self, job: JobLike, cv: CVLike) -> List[RegexResult]:
        analysis = _CVAnalysis(cv.text, self.today)
        return [self.match_requirement(req, cv, i, analysis)
                for i, req in enumerate(requirements_from_job(job), start=1)]

    def match_requirement(self, requirement: Requirement, cv: CVLike, index: int = 1,
                          analysis: Optional[_CVAnalysis] = None) -> RegexResult:
        analysis = analysis or _CVAnalysis(cv.text, self.today)
        text = analysis.text
        result = RegexResult(requirement_id=requirement.id or index, requirement=requirement.name)

        if not text.strip():
            result.note = "CV has no readable text."
            return result

        # 1. degrees and diplomas
        names = [requirement.name] + list(requirement.aliases or [])
        degree = match_degree_requirement(names, text)
        if degree is not None:
            result.status = FOUND if degree.found else NOT_FOUND
            result.matched_terms, result.evidence, result.note = degree.matched, degree.evidence, degree.note
            result.mentions = len(degree.matched)
            return result

        expanded = expand_requirement_terms(requirement.name, requirement.aliases, self.synonyms)
        min_years = requirement.min_years if requirement.min_years is not None else expanded.min_years
        result.min_years = min_years

        # 2. general "N years of experience" requirement
        if _GENERIC_EXPERIENCE.match(expanded.core):
            return self._match_total_experience(result, analysis, min_years)

        # 3. keyword / alias search
        if not expanded.terms:
            result.note = "Requirement has no searchable text."
            return result
        spans = self._find_spans(expanded.terms, text)
        if not spans:
            return result

        result.status = FOUND
        result.mentions = len(spans)
        result.matched_terms = list(dict.fromkeys(g for _, _, g in spans))
        last_end = -10**9
        for s, e, _ in spans:
            if len(result.evidence) >= self.max_evidence:
                break
            if s >= last_end + self.context_chars:
                result.evidence.append(_snippet(text, s, e, self.context_chars))
                last_end = e

        # 4. how long?
        plain = [(s, e) for s, e, _ in spans]
        stated = stated_years_for_spans(text, analysis.statements, plain)
        date_years, ranges = skill_years_from_blocks(analysis.blocks, plain)
        candidates: List[Tuple[float, str, List[str]]] = []
        if stated:
            candidates.append((stated.years, "stated", [stated.text]))
        if date_years > 0:
            candidates.append((date_years, "dates", ranges))
        if candidates:
            years, source, proof = max(candidates, key=lambda c: c[0])
            result.years_found, result.years_source, result.years_evidence = round(years, 1), source, proof
        self._judge_years(result, min_years)
        return result

    # ------------------------------------------------------------ helpers
    def overall_experience_years(self, cv: CVLike) -> Optional[float]:
        """Best estimate of total years of experience (None if the CV gives no evidence)."""
        a = _CVAnalysis(cv.text, self.today)
        stated = total_stated_years(a.text, a.statements)
        dates, _ = total_years_from_blocks(a.blocks)
        values = [v for v in (stated.years if stated else 0.0, dates) if v > 0]
        return round(max(values), 1) if values else None

    def degrees(self, cv: CVLike):
        """All degree mentions in the CV (useful for the report and for the AI prompt)."""
        return find_degrees(prepare_text(cv.text))

    def _find_spans(self, terms: List[str], text: str) -> List[Tuple[int, int, str]]:
        raw: List[Tuple[int, int, str]] = []
        for term in terms:
            try:
                pattern = compile_term(term)
            except re.error as exc:
                raise RegexMatchError(f"Bad pattern for '{term}': {exc}") from exc
            raw.extend((m.start(), m.end(), m.group(0)) for m in pattern.finditer(text))
        raw.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        merged: List[Tuple[int, int, str]] = []
        last_end = -1
        for s, e, g in raw:
            if s >= last_end:
                merged.append((s, e, g))
                last_end = e
        return merged

    def _match_total_experience(self, result: RegexResult, a: _CVAnalysis,
                                min_years: Optional[float]) -> RegexResult:
        stated = total_stated_years(a.text, a.statements)
        dates, ranges = total_years_from_blocks(a.blocks)
        candidates: List[Tuple[float, str, List[str]]] = []
        if stated:
            candidates.append((stated.years, "stated", [stated.text]))
        if dates > 0:
            candidates.append((dates, "dates", ranges))
        if not candidates:
            result.note = "No statement or dated work history found to measure total experience."
            return result
        years, source, proof = max(candidates, key=lambda c: c[0])
        result.status = FOUND
        result.years_found, result.years_source, result.years_evidence = round(years, 1), source, proof
        result.matched_terms = proof[:1]
        result.evidence = proof[: self.max_evidence]
        self._judge_years(result, min_years)
        return result

    @staticmethod
    def _judge_years(result: RegexResult, min_years: Optional[float]) -> None:
        if min_years is None:
            return
        if result.years_found is None:
            result.note = (f"Found, but no duration evidence for the required "
                           f"{_fmt_years(min_years)}+ years. Needs AI/human check.")
        elif result.years_found + 1e-9 >= min_years:
            result.years_ok = True
        else:
            result.years_ok = False
            result.note = (f"Found, but only about {_fmt_years(result.years_found)} years "
                           f"evidenced (required {_fmt_years(min_years)}). Needs AI/human check.")

# ============================================================================
# 5. ADAPTER - the ONLY part to edit when models.py is finished
# ============================================================================


def requirements_from_job(job: JobLike) -> List[Requirement]:
    """
    Turn the shared job object into a list of Requirement.

    Accepted shapes, tried in this order:
      1. job.requirements          -> list of objects with .name (and optionally
                                      .mandatory / .aliases / .min_years / .id)
      2. a JobDescription with any of these attributes (all optional):
           skills | required_skills        list[str]   mandatory skills
           preferred_skills                list[str]   nice-to-have skills
           experience | min_years | min_years_experience | years_experience
                                           number      minimum years of experience overall
           education | degree              str or list[str]
    TODO(Eric): once models.py defines JobDescription, delete the attribute names you do
    not need and keep the ones it really has.
    """
    reqs = getattr(job, "requirements", None)
    if reqs:
        return list(reqs)

    def _first(*names):
        for n in names:
            v = getattr(job, n, None)
            if v:
                return v
        return None

    def _as_list(v) -> List[str]:
        if v is None:
            return []
        return [str(x) for x in v] if isinstance(v, (list, tuple, set)) else [str(v)]

    out: List[Requirement] = []
    out += [Requirement(s, True) for s in _as_list(_first("skills", "required_skills"))]
    out += [Requirement(s, False) for s in _as_list(_first("preferred_skills"))]
    out += [Requirement(e, True) for e in _as_list(_first("education", "degree"))]
    years = _first("experience", "min_years", "min_years_experience", "years_experience")
    if isinstance(years, (int, float)):
        out.append(Requirement("years of experience", True, min_years=float(years)))
    if not out:
        raise RegexMatchError(
            "The job object has no requirements. Expected .requirements, or "
            "skills / education / experience attributes (see requirements_from_job in matcher.py).")
    return out


def apply_to_match_result(result: Any, regex_results: List["RegexResult"],
                          years_experience: Optional[float] = None) -> Any:
    """
    Copy the regex findings onto the shared MatchResult.
    TODO(Eric): rename the attributes below to the real field names in models.py.
    """
    result.regex_results = regex_results
    result.found_skills = [r.requirement for r in regex_results if r.found]
    result.missing_skills = [r.requirement for r in regex_results if not r.found]
    result.years_experience = years_experience
    return result


def match_cv(cv: CVLike, job: JobLike, result: Any = None,
             matcher: Optional["RegexMatcher"] = None) -> List["RegexResult"]:
    """One-call helper: match a CV and (optionally) fill the shared MatchResult."""
    matcher = matcher or RegexMatcher()
    regex_results = matcher.match_all(job, cv)
    if result is not None:
        apply_to_match_result(result, regex_results, matcher.overall_experience_years(cv))
    return regex_results


__all__ = ["FOUND", "NOT_FOUND", "Requirement", "RegexMatcher", "RegexMatchError",
           "RegexResult", "match_cv", "requirements_from_job", "apply_to_match_result"]