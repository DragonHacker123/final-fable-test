"""Differential test suite: regex_forge vs Python's `re`.

For every (pattern, input) case we compare, for BOTH engines:
  * search():  found / span / all group captures
  * match():   found / span / all group captures
  * findall(): full result list

`re` is the oracle; any disagreement on the supported feature set is a bug.
"""

import re
import sys

import regex_forge as rf

PATTERNS = [
    # literals & dot
    r"abc", r"a.c", r"...", r"",
    # classes & escapes
    r"[abc]+", r"[^abc]+", r"[a-z0-9]+", r"[-a]", r"[a-]", r"[]a]",
    r"\d+", r"\D+", r"\w+", r"\W+", r"\s+", r"\S+", r"[\d\s]+",
    r"\.", r"\+", r"\(", r"\[", r"\\",
    # alternation & grouping
    r"a|b", r"ab|cd", r"a(b|c)d", r"(a|b)(c|d)", r"(ab)+", r"(a|ab)(c|bc)",
    # quantifiers, greedy
    r"a*", r"a+", r"a?", r"a{3}", r"a{2,}", r"a{1,3}", r"(ab){2,3}",
    r"a*b", r"a+b", r"ab?c",
    # quantifiers, lazy
    r"a*?b", r"a+?b", r"a??b", r"<.*>", r"<.*?>", r"a{1,3}?",
    # anchors
    r"^abc", r"abc$", r"^abc$", r"^", r"$", r"^a|b$",
    # captures incl. nesting and optional groups
    r"(a)(b)(c)", r"((a)b)c", r"(a(b(c)))", r"(a)?(b)", r"(a*)(b*)",
    r"(\w+)@(\w+)", r"(\d+)-(\d+)", r"(a|(b))c",
    # torture-adjacent but safe sizes
    r"(a+)+b", r"(a*)*b", r"(x|y|z){2,4}", r"([a-c]+d)+",
]

INPUTS = [
    "", "a", "b", "ab", "abc", "abcd", "aaab", "aaa", "aab", "ba",
    "hello world", "ada@lovelace", "12-34", "a1 b22 c333",
    "xyzzy", "aaaaaab", "<p>text</p>", "  spaced  ",
    "abcabcabc", "xxyyzz", "aXbXc", "9-1-1", "\tmixed 42 bag\n",
    "abd", "acd", "abcbcd", "..a..", "[wow]", "a+b", "\\d",
]


def spans_and_groups(m):
    if m is None:
        return None
    return (m.span(), tuple(m.group(i) for i in range(m.re.groups + 1)))


def rf_spans_and_groups(m):
    if m is None:
        return None
    return (m.span(), tuple(m.group(i) for i in range(m.re.groups + 1)))


def main():
    total = failures = 0
    for pat in PATTERNS:
        gold = re.compile(pat)
        mine = rf.compile(pat)
        for s in INPUTS:
            for engine in rf.ENGINES:
                total += 1
                bad = []
                want = spans_and_groups(gold.search(s))
                got = rf_spans_and_groups(mine.search(s, engine=engine))
                if want != got:
                    bad.append(f"search: want {want}, got {got}")
                want = spans_and_groups(gold.match(s))
                got = rf_spans_and_groups(mine.match(s, engine=engine))
                if want != got:
                    bad.append(f"match: want {want}, got {got}")
                want = gold.findall(s)
                got = mine.findall(s, engine=engine)
                if want != got:
                    bad.append(f"findall: want {want!r}, got {got!r}")
                if bad:
                    failures += 1
                    print(f"MISMATCH pattern={pat!r} input={s!r} engine={engine}")
                    for b in bad:
                        print("   ", b)

    cases = total // 2
    print(f"\n{cases} (pattern, input) cases x 2 engines x 3 methods "
          f"= {total * 3} comparisons against `re`")
    if failures:
        print(f"FAILED: {failures} mismatching case/engine pairs")
        sys.exit(1)
    print("ALL DIFFERENTIAL TESTS PASSED")


if __name__ == "__main__":
    main()
