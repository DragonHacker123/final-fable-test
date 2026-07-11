"""ReDoS demonstration: why engine choice matters.

The pattern (a+)+$ against "aaaa...a" + "b" is the classic catastrophic
backtracking bomb: the backtracker must try every way of partitioning the
a-run between the inner + and outer +, which is exponential in the run
length. Thompson NFA simulation walks the same input once, in lockstep,
in guaranteed linear time.

The backtracking engine here runs with a step cap so the demo finishes;
the cap it hits IS the explosion.
"""

import time

import regex_forge as rf
from regex_forge.backtrack import BacktrackLimitExceeded

PATTERN = r"(a+)+$"
STEP_CAP = 3_000_000


def time_engine(regex, text, engine):
    t0 = time.perf_counter()
    try:
        regex.search(text, engine=engine,
                     step_limit=STEP_CAP if engine == "backtrack" else None)
        blew_up = False
    except BacktrackLimitExceeded:
        blew_up = True
    ms = (time.perf_counter() - t0) * 1000
    return ms, blew_up


def main():
    regex = rf.compile(PATTERN)
    print(f"pattern: {PATTERN!r}   input: 'a'*n + 'b' (can never match)\n")
    print(f"{'n':>4} | {'thompson':>12} | {'backtracking':>28}")
    print("-" * 52)
    rows = []
    for n in (5, 10, 15, 18, 20, 22, 24, 26, 28):
        text = "a" * n + "b"
        t_ms, _ = time_engine(regex, text, "thompson")
        b_ms, blew = time_engine(regex, text, "backtrack")
        note = f"{b_ms:9.1f} ms  EXPLODED (cap)" if blew else f"{b_ms:9.1f} ms"
        print(f"{n:>4} | {t_ms:9.2f} ms | {note:>28}")
        rows.append((n, t_ms, b_ms, blew))

    print("\nThe backtracker's time roughly doubles with every added 'a'")
    print("until it slams into the step cap; Thompson stays flat because it")
    print("tracks ALL states simultaneously in one linear pass -- this is")
    print("exactly the attack class (ReDoS) that has taken down real")
    print("services, and exactly why RE2/Rust-regex refuse backtracking.")


if __name__ == "__main__":
    main()
