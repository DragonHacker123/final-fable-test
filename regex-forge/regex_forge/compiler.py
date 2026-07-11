"""regex_forge.compiler -- lower the AST to Pike/Russ-Cox style bytecode.

One instruction set, two interpreters:
  * regex_forge.thompson  -- lockstep NFA simulation (linear time)
  * regex_forge.backtrack -- depth-first backtracking VM

Instructions are (op, a, b) tuples:

    CHAR c          consume one char equal to c
    ANY             consume any char except '\\n'
    CLASS m         consume one char accepted by ClassMatcher m
    SPLIT x, y      fork execution; x is the preferred branch
    JMP x           unconditional jump
    SAVE n          store current position in capture slot n
    MATCH           accept
    BOL             zero-width: assert position 0            (^)
    EOL             zero-width: assert end (or before final '\\n')  ($)
    SETMARK k       store current position in progress-mark k
    CHECKMARK k     fail this thread if no progress since SETMARK k
                    (guards unbounded loops whose body can match empty,
                    e.g. (a*)* -- prevents infinite empty iterations)
"""

from . import parser as P

CHAR, ANY, CLASS, SPLIT, JMP, SAVE, MATCH, BOL, EOL, SETMARK, CHECKMARK = range(11)

OP_NAMES = ["char", "any", "class", "split", "jmp", "save", "match",
            "bol", "eol", "setmark", "checkmark"]


def _shorthand_match(letter, ch):
    if letter == "d":
        return "0" <= ch <= "9"
    if letter == "w":
        return ch == "_" or ch.isalnum()
    # 's'
    return ch in " \t\n\r\f\v"


class ClassMatcher:
    """Compiled character class: a predicate over single characters."""
    __slots__ = ("items", "negated", "desc")

    def __init__(self, items, negated):
        self.items = items
        self.negated = negated
        self.desc = P.class_to_str(items, negated)

    def match(self, ch):
        hit = False
        for item in self.items:
            tag = item[0]
            if tag == "char":
                hit = ch == item[1]
            elif tag == "range":
                hit = item[1] <= ch <= item[2]
            elif tag == "class":
                hit = _shorthand_match(item[1], ch)
            else:  # nclass
                hit = not _shorthand_match(item[1], ch)
            if hit:
                break
        return hit != self.negated

    def __repr__(self):
        return "ClassMatcher(%s)" % self.desc


class Program:
    __slots__ = ("insts", "nslots", "nmarks", "ngroups")

    def __init__(self, insts, nslots, nmarks, ngroups):
        self.insts = insts      # tuple of (op, a, b)
        self.nslots = nslots    # 2 * (ngroups + 1) capture slots
        self.nmarks = nmarks    # progress marks for empty-loop guards
        self.ngroups = ngroups

    def __len__(self):
        return len(self.insts)


class _Compiler:
    def __init__(self):
        self.out = []
        self.nmarks = 0

    @property
    def pc(self):
        return len(self.out)

    def emit(self, inst):
        self.out.append(inst)
        return inst

    # -- node dispatch -------------------------------------------------

    def node(self, n):
        t = type(n)
        if t is P.Literal:
            self.emit([CHAR, n.ch, None])
        elif t is P.Dot:
            self.emit([ANY, None, None])
        elif t is P.CharClass:
            self.emit([CLASS, ClassMatcher(n.items, n.negated), None])
        elif t is P.Anchor:
            self.emit([BOL if n.kind == "^" else EOL, None, None])
        elif t is P.Group:
            if n.index is None:
                self.node(n.body)
            else:
                self.emit([SAVE, 2 * n.index, None])
                self.node(n.body)
                self.emit([SAVE, 2 * n.index + 1, None])
        elif t is P.Concat:
            for part in n.parts:
                self.node(part)
        elif t is P.Alt:
            self.alt(n)
        elif t is P.Repeat:
            self.repeat(n)
        elif t is P.Empty:
            pass
        else:  # pragma: no cover
            raise TypeError("unknown AST node %r" % n)

    # -- constructs ------------------------------------------------------

    def alt(self, n):
        jmps = []
        for branch in n.branches[:-1]:
            sp = self.emit([SPLIT, None, None])
            sp[1] = self.pc          # preferred: this branch
            self.node(branch)
            jmps.append(self.emit([JMP, None, None]))
            sp[2] = self.pc          # alternative: next branch
        self.node(n.branches[-1])
        end = self.pc
        for j in jmps:
            j[1] = end

    def repeat(self, r):
        if r.max is not None:
            for _ in range(r.min):
                self.node(r.body)
            self.optionals(r.body, r.max - r.min, r.lazy)
        elif r.min == 0:
            self.star(r.body, r.lazy)
        else:
            for _ in range(r.min - 1):
                self.node(r.body)
            self.plus(r.body, r.lazy)

    def plus(self, body, lazy):
        """body+  ==  L1: body; SPLIT loop,end; loop: [guard] JMP L1; end:"""
        guard = body.nullable()
        mark = None
        if guard:
            mark = self.nmarks
            self.nmarks += 1
        l1 = self.pc
        if guard:
            self.emit([SETMARK, mark, None])
        self.node(body)
        sp = self.emit([SPLIT, None, None])
        loop = self.pc
        if guard:
            self.emit([CHECKMARK, mark, None])
        self.emit([JMP, l1, None])
        end = self.pc
        if lazy:
            sp[1], sp[2] = end, loop
        else:
            sp[1], sp[2] = loop, end

    def star(self, body, lazy):
        """body*  ==  (body+)?  with matching greediness."""
        sp = self.emit([SPLIT, None, None])
        enter = self.pc
        self.plus(body, lazy)
        end = self.pc
        if lazy:
            sp[1], sp[2] = end, enter
        else:
            sp[1], sp[2] = enter, end

    def optionals(self, body, k, lazy):
        """body{0,k} as nested optionals: (body (body (...)?)?)? so that
        skipping at level i skips everything after it."""
        splits = []
        for _ in range(k):
            sp = self.emit([SPLIT, None, None])
            splits.append((sp, self.pc))
            self.node(body)
        end = self.pc
        for sp, enter in splits:
            if lazy:
                sp[1], sp[2] = end, enter
            else:
                sp[1], sp[2] = enter, end


def compile_ast(ast, ngroups):
    c = _Compiler()
    c.emit([SAVE, 0, None])
    c.node(ast)
    c.emit([SAVE, 1, None])
    c.emit([MATCH, None, None])
    insts = tuple(tuple(i) for i in c.out)
    return Program(insts, 2 * (ngroups + 1), c.nmarks, ngroups)


def disassemble(prog):
    """Return the program as a list of printable lines."""
    lines = []
    for i, (op, a, b) in enumerate(prog.insts):
        if op == CHAR:
            body = "char      %r" % a
        elif op == ANY:
            body = "any"
        elif op == CLASS:
            body = "class     %s" % a.desc
        elif op == SPLIT:
            body = "split     -> %d, %d" % (a, b)
        elif op == JMP:
            body = "jmp       -> %d" % a
        elif op == SAVE:
            group, which = divmod(a, 2)
            what = "start" if which == 0 else "end"
            target = "match" if group == 0 else "group %d" % group
            body = "save      %-2d          ; %s of %s" % (a, what, target)
        elif op == MATCH:
            body = "match"
        elif op == BOL:
            body = "bol                   ; ^"
        elif op == EOL:
            body = "eol                   ; $"
        elif op == SETMARK:
            body = "setmark   %d           ; empty-loop guard" % a
        else:
            body = "checkmark %d           ; fail if no progress" % a
        lines.append("%4d  %s" % (i, body))
    return lines
