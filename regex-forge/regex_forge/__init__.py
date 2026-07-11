"""regex_forge -- a regular expression engine built from scratch.

    >>> import regex_forge as rf
    >>> m = rf.compile(r"(\\w+)@(\\w+)").search("mail me at ada@lovelace!")
    >>> m.group(0), m.group(1), m.group(2)
    ('ada@lovelace', 'ada', 'lovelace')

One parser, one bytecode compiler, two interchangeable engines:

    'thompson'  -- lockstep NFA simulation, guaranteed linear time
    'backtrack' -- classic depth-first VM, can blow up on evil patterns

Pure standard library; the `re` module is used only by the test suite for
differential testing.
"""

from . import parser as _parser
from . import compiler as _compiler
from . import thompson as _thompson
from . import backtrack as _backtrack

from .parser import RegexSyntaxError
from .backtrack import BacktrackLimitExceeded

__all__ = ["compile", "Regex", "Match", "RegexSyntaxError",
           "BacktrackLimitExceeded", "ENGINES"]

ENGINES = ("thompson", "backtrack")


class Match:
    """Result of a successful match.  API modelled on re.Match."""
    __slots__ = ("re", "string", "_saves")

    def __init__(self, regex, string, saves):
        self.re = regex
        self.string = string
        self._saves = saves

    def _span(self, i):
        if not 0 <= i <= self.re.groups:
            raise IndexError("no such group: %r" % i)
        return self._saves[2 * i], self._saves[2 * i + 1]

    def group(self, *indices):
        if not indices:
            indices = (0,)
        out = []
        for i in indices:
            lo, hi = self._span(i)
            out.append(None if lo == -1 else self.string[lo:hi])
        return out[0] if len(out) == 1 else tuple(out)

    def groups(self, default=None):
        return tuple(
            default if self._saves[2 * i] == -1 else
            self.string[self._saves[2 * i]:self._saves[2 * i + 1]]
            for i in range(1, self.re.groups + 1)
        )

    def start(self, i=0):
        return self._span(i)[0]

    def end(self, i=0):
        return self._span(i)[1]

    def span(self, i=0):
        return self._span(i)

    def __getitem__(self, i):
        return self.group(i)

    def __repr__(self):
        return "<regex_forge.Match span=%r, match=%r>" % (
            self.span(), self.group(0))


class Regex:
    """A compiled pattern.  `engine` picks the default execution engine;
    every method also accepts a per-call `engine=` override."""

    def __init__(self, pattern, engine="thompson"):
        if engine not in ENGINES:
            raise ValueError("engine must be one of %r" % (ENGINES,))
        self.pattern = pattern
        self.engine = engine
        self.ast, self.groups = _parser.parse(pattern)
        self.program = _compiler.compile_ast(self.ast, self.groups)

    # -- core execution --------------------------------------------------

    def _run(self, string, pos, anchored, engine, step_limit):
        engine = engine or self.engine
        if engine == "thompson":
            saves = _thompson.run(self.program, string, pos, anchored)
        elif engine == "backtrack":
            saves, _ = _backtrack.run(self.program, string, pos, anchored,
                                      step_limit=step_limit)
        else:
            raise ValueError("engine must be one of %r" % (ENGINES,))
        return None if saves is None else Match(self, string, saves)

    # -- public API --------------------------------------------------------

    def match(self, string, pos=0, engine=None, step_limit=None):
        """Match anchored at `pos` (like re.match)."""
        return self._run(string, pos, True, engine, step_limit)

    def search(self, string, pos=0, engine=None, step_limit=None):
        """Find the leftmost match at or after `pos` (like re.search)."""
        return self._run(string, pos, False, engine, step_limit)

    def finditer(self, string, engine=None, step_limit=None):
        """Yield non-overlapping matches left to right (like re.finditer)."""
        pos, n = 0, len(string)
        while pos <= n:
            m = self._run(string, pos, False, engine, step_limit)
            if m is None:
                return
            yield m
            end = m.end()
            pos = end + 1 if end == m.start() else end

    def findall(self, string, engine=None, step_limit=None):
        """Like re.findall, including its group conventions."""
        out = []
        for m in self.finditer(string, engine, step_limit):
            if self.groups == 0:
                out.append(m.group(0))
            elif self.groups == 1:
                g = m.group(1)
                out.append("" if g is None else g)
            else:
                out.append(tuple("" if g is None else g for g in m.groups()))
        return out

    def __repr__(self):
        return "regex_forge.compile(%r, engine=%r)" % (self.pattern, self.engine)


def compile(pattern, engine="thompson"):
    """Compile a pattern into a Regex object."""
    return Regex(pattern, engine)
