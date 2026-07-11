"""regex_forge.thompson -- Thompson NFA simulation (Pike VM).

Runs the shared bytecode breadth-first: all NFA threads advance in lockstep
through the input, one character at a time.  At every input position each
program counter is added to the thread list at most once, so the total work
is O(len(input) * len(program)) -- linear in the input, no matter how the
pattern is written.  This is what makes the engine immune to catastrophic
backtracking.

Threads carry capture slots (Pike's extension of Thompson's construction),
and the thread list is kept in priority order, so the engine returns the
same leftmost / greedy-vs-lazy match a backtracking engine would.
"""

from .compiler import (CHAR, ANY, CLASS, SPLIT, JMP, SAVE, MATCH,
                       BOL, EOL, SETMARK, CHECKMARK)


def run(prog, s, start=0, anchored=False):
    """Execute the program.  Returns the capture-slot tuple of the best
    match, or None.  If anchored, the match must begin exactly at `start`;
    otherwise the leftmost match at or after `start` wins."""
    insts = prog.insts
    n = len(s)
    saves0 = (-1,) * prog.nslots
    marks0 = (-1,) * prog.nmarks

    def addthread(lst, visited, pc, pos, saves, marks):
        """Follow epsilon transitions from pc, appending every reachable
        consuming/match instruction to lst in priority (DFS pre-)order."""
        stack = [(pc, saves, marks)]
        while stack:
            pc, sv, mk = stack.pop()
            while pc not in visited:
                visited.add(pc)
                op, a, b = insts[pc]
                if op == JMP:
                    pc = a
                elif op == SPLIT:
                    stack.append((b, sv, mk))   # lower priority, explore later
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
                    if mk[a] == pos:   # empty loop iteration: kill thread
                        break
                    pc += 1
                else:                  # CHAR / ANY / CLASS / MATCH
                    lst.append((pc, sv, mk))
                    break

    matched = None
    clist, cvis = [], set()
    pos = start
    while True:
        # Seed a new thread trying to start a match at this position.
        # Once a match is found, threads seeded later could only produce
        # a match starting further right -- leftmost semantics forbid it.
        if pos <= n and matched is None and (not anchored or pos == start):
            addthread(clist, cvis, 0, pos, saves0, marks0)
        if not clist:
            break
        ch = s[pos] if pos < n else None
        nlist, nvis = [], set()
        for pc, sv, mk in clist:
            op, a, b = insts[pc]
            if op == MATCH:
                matched = sv
                # Lower-priority threads can no longer win: stop them.
                break
            if op == CHAR:
                if ch == a:
                    addthread(nlist, nvis, pc + 1, pos + 1, sv, mk)
            elif op == ANY:
                if ch is not None and ch != "\n":
                    addthread(nlist, nvis, pc + 1, pos + 1, sv, mk)
            else:  # CLASS
                if ch is not None and a.match(ch):
                    addthread(nlist, nvis, pc + 1, pos + 1, sv, mk)
        clist, cvis = nlist, nvis
        pos += 1
        if pos > n + 1:
            break
    return matched
