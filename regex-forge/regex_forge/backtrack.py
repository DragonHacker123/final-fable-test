"""regex_forge.backtrack -- depth-first backtracking VM.

Runs the same bytecode as the Thompson engine, but the classic way: follow
the preferred branch of every SPLIT immediately, push the alternative on a
stack, and on failure pop the most recent alternative and try again.

This gives capture groups and lazy quantifiers "for free" (the first path
that reaches MATCH is the answer), but the number of explored paths can be
exponential in the input length for patterns like (a+)+$ -- catastrophic
backtracking.  `step_limit` is the safety cap used by the ReDoS demo.
"""

from .compiler import (CHAR, ANY, CLASS, SPLIT, JMP, SAVE, MATCH,
                       BOL, EOL, SETMARK, CHECKMARK)


class BacktrackLimitExceeded(Exception):
    """Raised when the VM burns through `step_limit` instructions."""

    def __init__(self, steps):
        super().__init__("backtracking VM exceeded %d steps" % steps)
        self.steps = steps


def run(prog, s, start=0, anchored=False, step_limit=None):
    """Execute the program.  Returns (saves, steps): the capture-slot tuple
    of the match (or None) and the number of VM instructions executed."""
    insts = prog.insts
    n = len(s)
    saves0 = (-1,) * prog.nslots
    marks0 = (-1,) * prog.nmarks
    steps = 0

    last_start = start if anchored else n
    for sp0 in range(start, last_start + 1):
        # One backtracking search anchored at sp0.
        stack = [(0, sp0, saves0, marks0)]
        while stack:
            pc, pos, sv, mk = stack.pop()
            while True:
                steps += 1
                if step_limit is not None and steps > step_limit:
                    raise BacktrackLimitExceeded(steps)
                op, a, b = insts[pc]
                if op == CHAR:
                    if pos < n and s[pos] == a:
                        pc += 1
                        pos += 1
                    else:
                        break  # dead end: backtrack
                elif op == ANY:
                    if pos < n and s[pos] != "\n":
                        pc += 1
                        pos += 1
                    else:
                        break
                elif op == CLASS:
                    if pos < n and a.match(s[pos]):
                        pc += 1
                        pos += 1
                    else:
                        break
                elif op == SPLIT:
                    stack.append((b, pos, sv, mk))  # try later
                    pc = a                          # preferred branch now
                elif op == JMP:
                    pc = a
                elif op == SAVE:
                    sv = sv[:a] + (pos,) + sv[a + 1:]
                    pc += 1
                elif op == BOL:
                    if pos != 0:
                        break
                    pc += 1
                elif op == EOL:
                    if pos == n or (pos == n - 1 and s[pos] == "\n"):
                        pc += 1
                    else:
                        break
                elif op == SETMARK:
                    mk = mk[:a] + (pos,) + mk[a + 1:]
                    pc += 1
                elif op == CHECKMARK:
                    if mk[a] == pos:
                        break  # empty loop iteration: backtrack
                    pc += 1
                else:  # MATCH -- first path to arrive wins
                    return sv, steps
    return None, steps
