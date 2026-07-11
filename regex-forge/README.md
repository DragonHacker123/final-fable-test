# Regex Forge

A regular expression engine built from scratch in pure Python — one parser,
one bytecode compiler, and **two interchangeable execution engines** that
embody the two great schools of regex implementation. Differential-tested
against CPython's `re` (11,160 comparisons, all passing).

## Supported syntax

Literals, `.`, character classes `[a-z]` / `[^...]`, shorthand escapes
`\d \w \s \D \W \S`, alternation `|`, capture groups `(...)`, greedy and lazy
quantifiers `* + ? {n} {n,} {n,m}` / `*? +? ?? {n,m}?`, anchors `^ $`.

```python
import regex_forge as rf
m = rf.compile(r"(\w+)@(\w+)").search("mail me at ada@lovelace!")
m.group(0), m.group(1), m.group(2)   # ('ada@lovelace', 'ada', 'lovelace')
```

## The two engines

Both run the **same bytecode** (char / class / split / jmp / save / anchors,
plus empty-loop guard marks), Russ Cox's virtual-machine formulation.

**`backtrack`** — the classic depth-first VM: follow the preferred branch of
every `split`, push the alternative, and on failure pop and retry. Simple,
and captures/laziness fall out naturally — but the number of explored paths
can be *exponential*.

**`thompson`** — Pike's extension of Thompson NFA simulation: every live
thread advances in lockstep through the input, threads are deduplicated per
position, and the thread list keeps priority order so greedy/lazy semantics
and capture groups still come out exactly like the backtracker's. Work is
bounded per input character — **catastrophic backtracking is structurally
impossible**.

## The receipts: `redos_demo.py`

The classic evil pattern `(a+)+$` against `"a"*n + "b"`:

```
   n |     thompson |                 backtracking
----------------------------------------------------
   5 |      0.05 ms |                       0.1 ms
  10 |      0.04 ms |                       3.0 ms
  15 |      0.05 ms |                      89.5 ms
  18 |      0.07 ms |     452.4 ms  EXPLODED (cap)
  20 |      0.08 ms |     454.9 ms  EXPLODED (cap)
  28 |      0.10 ms |     450.2 ms  EXPLODED (cap)
```

The backtracker's cost doubles with every added `a` — it must try every
partition of the run between the two `+` loops — until it hits the
3-million-step safety cap. Thompson doesn't even notice. This asymmetry is
the entire ReDoS attack class, and why RE2 and Rust's `regex` refuse to
backtrack.

## Files

- `regex_forge/parser.py` — recursive-descent parser → AST
- `regex_forge/compiler.py` — AST → VM bytecode (with a disassembler)
- `regex_forge/thompson.py` — lockstep Pike VM (linear time)
- `regex_forge/backtrack.py` — depth-first VM with step cap
- `regex_forge/__init__.py` — `re`-style API: compile/match/search/findall/finditer
- `regex_forge/__main__.py` — CLI: `python3 -m regex_forge 'pat' 'text'`, or pipe stdin to grep
- `visualize.py` — AST tree + bytecode dump for any pattern
- `tests.py` — differential suite vs `re`
- `redos_demo.py` — the timing table above

## A war story from this codebase

Getting the Thompson engine to agree with CPython byte-for-byte required two
genuinely subtle fixes: an unanchored scan must keep seeding new start
positions even when every thread dies (a bare `$` only comes alive at end of
input), and thread deduplication must key on *(pc, loop-marks)* rather than
pc alone — otherwise the final empty iteration of `(a*)*` gets collapsed
away and group 1 captures `'a'` where CPython says `''`. Both were found by
the differential suite, which is the point of having one.
