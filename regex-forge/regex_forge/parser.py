"""regex_forge.parser -- turn a pattern string into an AST.

Supported syntax:
    literals            a b c ...
    any char            .                (does not match newline, like re)
    character classes   [a-z]  [^a-z]  []a]  [\\d]  [a\\-z]
    escapes             \\d \\D \\w \\W \\s \\S plus \\n \\t \\r \\f \\v \\a \\0
                        \\xHH and escaped metacharacters (\\. \\* \\( ...)
    alternation         a|b
    grouping            (abc)  (?:abc)
    quantifiers         *  +  ?  {n}  {n,}  {n,m}
    lazy quantifiers    *?  +?  ??  {n,m}?
    anchors             ^  $

Semantics mirror Python's `re` module (no flags) on this feature set.
"""

MAX_REPEAT = 1000

CLASS_SHORTHANDS = frozenset("dwsDWS")
CONTROL_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v", "a": "\a", "0": "\0",
}
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class RegexSyntaxError(ValueError):
    def __init__(self, msg, pattern=None, pos=None):
        if pattern is not None:
            msg = "%s at position %s in pattern %r" % (msg, pos, pattern)
        super().__init__(msg)
        self.pos = pos


# --------------------------------------------------------------------------
# AST nodes
# --------------------------------------------------------------------------

class Node:
    __slots__ = ()

    def label(self):
        return type(self).__name__

    def children(self):
        return ()

    def nullable(self):
        """True if this node can match the empty string."""
        raise NotImplementedError

    def __repr__(self):
        return "<%s>" % self.label()


class Empty(Node):
    __slots__ = ()

    def nullable(self):
        return True


class Literal(Node):
    __slots__ = ("ch",)

    def __init__(self, ch):
        self.ch = ch

    def label(self):
        return "Literal %r" % self.ch

    def nullable(self):
        return False


class Dot(Node):
    __slots__ = ()

    def label(self):
        return "Dot '.'"

    def nullable(self):
        return False


class CharClass(Node):
    """items: list of ('char', c) | ('range', lo, hi) | ('class', x) | ('nclass', x)."""
    __slots__ = ("items", "negated")

    def __init__(self, items, negated):
        self.items = items
        self.negated = negated

    def label(self):
        return "CharClass %s" % class_to_str(self.items, self.negated)

    def nullable(self):
        return False


class Anchor(Node):
    __slots__ = ("kind",)

    def __init__(self, kind):
        self.kind = kind  # '^' or '$'

    def label(self):
        return "Anchor %r" % self.kind

    def nullable(self):
        return True


class Group(Node):
    __slots__ = ("body", "index")

    def __init__(self, body, index):
        self.body = body
        self.index = index  # int (capture group number) or None for (?:...)

    def label(self):
        if self.index is None:
            return "Group (?:...)"
        return "Group #%d" % self.index

    def children(self):
        return (self.body,)

    def nullable(self):
        return self.body.nullable()


class Concat(Node):
    __slots__ = ("parts",)

    def __init__(self, parts):
        self.parts = parts

    def label(self):
        return "Concat"

    def children(self):
        return tuple(self.parts)

    def nullable(self):
        return all(p.nullable() for p in self.parts)


class Alt(Node):
    __slots__ = ("branches",)

    def __init__(self, branches):
        self.branches = branches

    def label(self):
        return "Alt |"

    def children(self):
        return tuple(self.branches)

    def nullable(self):
        return any(b.nullable() for b in self.branches)


class Repeat(Node):
    __slots__ = ("body", "min", "max", "lazy")

    def __init__(self, body, min, max, lazy):
        self.body = body
        self.min = min
        self.max = max  # None means unbounded
        self.lazy = lazy

    def label(self):
        lo, hi = self.min, self.max
        if (lo, hi) == (0, None):
            q = "*"
        elif (lo, hi) == (1, None):
            q = "+"
        elif (lo, hi) == (0, 1):
            q = "?"
        elif hi is None:
            q = "{%d,}" % lo
        elif lo == hi:
            q = "{%d}" % lo
        else:
            q = "{%d,%d}" % (lo, hi)
        return "Repeat %s%s" % (q, "? (lazy)" if self.lazy else " (greedy)")

    def children(self):
        return (self.body,)

    def nullable(self):
        return self.min == 0 or self.body.nullable()


# --------------------------------------------------------------------------
# Display helper for character classes
# --------------------------------------------------------------------------

def _display_char(c):
    if c in "\\]^-":
        return "\\" + c
    if c == "\n":
        return "\\n"
    if c == "\t":
        return "\\t"
    if c == "\r":
        return "\\r"
    if ord(c) < 32:
        return "\\x%02x" % ord(c)
    return c


def class_to_str(items, negated):
    out = ["["]
    if negated:
        out.append("^")
    for item in items:
        tag = item[0]
        if tag == "char":
            out.append(_display_char(item[1]))
        elif tag == "range":
            out.append("%s-%s" % (_display_char(item[1]), _display_char(item[2])))
        elif tag == "class":
            out.append("\\" + item[1])
        else:  # nclass
            out.append("\\" + item[1].upper())
    out.append("]")
    return "".join(out)


# --------------------------------------------------------------------------
# Parser (recursive descent)
# --------------------------------------------------------------------------

class Parser:
    def __init__(self, pattern):
        self.pattern = pattern
        self.i = 0
        self.ngroups = 0

    # -- primitives --------------------------------------------------------

    def error(self, msg):
        raise RegexSyntaxError(msg, self.pattern, self.i)

    def more(self):
        return self.i < len(self.pattern)

    def cur(self):
        return self.pattern[self.i] if self.i < len(self.pattern) else None

    def eat(self):
        c = self.pattern[self.i]
        self.i += 1
        return c

    # -- grammar -----------------------------------------------------------

    def parse(self):
        node = self.parse_alt()
        if self.more():  # can only be a stray ')'
            self.error("unbalanced parenthesis")
        return node, self.ngroups

    def parse_alt(self):
        branches = [self.parse_concat()]
        while self.cur() == "|":
            self.eat()
            branches.append(self.parse_concat())
        if len(branches) == 1:
            return branches[0]
        return Alt(branches)

    def parse_concat(self):
        parts = []
        while self.more() and self.cur() not in "|)":
            parts.append(self.parse_repeat())
        if not parts:
            return Empty()
        if len(parts) == 1:
            return parts[0]
        return Concat(parts)

    def parse_repeat(self):
        atom = self.parse_atom()
        q = self.try_quantifier()
        if q is None:
            return atom
        node = Repeat(atom, *q)
        if self.try_quantifier() is not None:
            self.error("multiple repeat")
        return node

    def try_quantifier(self):
        """Return (min, max, lazy) if a quantifier follows, else None."""
        c = self.cur()
        if c == "*":
            self.eat()
            lo, hi = 0, None
        elif c == "+":
            self.eat()
            lo, hi = 1, None
        elif c == "?":
            self.eat()
            lo, hi = 0, 1
        elif c == "{":
            parsed = self._try_counted()
            if parsed is None:
                return None
            lo, hi = parsed
        else:
            return None
        lazy = False
        if self.cur() == "?":
            self.eat()
            lazy = True
        return lo, hi, lazy

    def _try_counted(self):
        """Parse {n} {n,} {n,m} starting at '{'.  Restore position and return
        None when it is not a well-formed counted repeat (then '{' is a
        literal, matching re's behaviour)."""
        start = self.i
        self.eat()  # '{'
        lo_digits = self._digits()
        hi_digits = None
        if self.cur() == ",":
            self.eat()
            hi_digits = self._digits()
        if self.cur() != "}" or (lo_digits == "" and hi_digits is None):
            self.i = start
            return None
        self.eat()  # '}'
        if hi_digits is None:  # {n}
            if lo_digits == "":
                self.i = start
                return None
            lo = hi = int(lo_digits)
        else:
            lo = int(lo_digits) if lo_digits else 0
            hi = int(hi_digits) if hi_digits else None
        if hi is not None and hi < lo:
            self.error("min repeat greater than max repeat")
        if lo > MAX_REPEAT or (hi is not None and hi > MAX_REPEAT):
            self.error("repeat count above %d not supported" % MAX_REPEAT)
        return lo, hi

    def _digits(self):
        out = []
        while self.more() and self.cur().isdigit():
            out.append(self.eat())
        return "".join(out)

    def parse_atom(self):
        c = self.cur()
        if c == "(":
            return self.parse_group()
        if c == "[":
            return self.parse_class()
        if c == ".":
            self.eat()
            return Dot()
        if c == "^":
            self.eat()
            return Anchor("^")
        if c == "$":
            self.eat()
            return Anchor("$")
        if c == "\\":
            item = self.parse_escape_item()
            if item[0] == "char":
                return Literal(item[1])
            return CharClass([item], negated=False)
        if c in "*+?":
            self.error("nothing to repeat")
        self.eat()
        return Literal(c)

    def parse_group(self):
        self.eat()  # '('
        index = None
        if self.cur() == "?":
            self.eat()
            if self.cur() == ":":
                self.eat()  # non-capturing group
            else:
                self.error("unsupported group extension (?%s" % (self.cur() or ""))
        else:
            self.ngroups += 1
            index = self.ngroups
        body = self.parse_alt()
        if self.cur() != ")":
            self.error("missing ), unterminated subpattern")
        self.eat()
        return Group(body, index)

    def parse_escape_item(self):
        """Parse an escape sequence (after seeing '\\').  Returns a class-item
        tuple usable both as an atom and inside a character class."""
        self.eat()  # '\\'
        if not self.more():
            self.error("bad escape (end of pattern)")
        c = self.eat()
        if c in CLASS_SHORTHANDS:
            if c.isupper():
                return ("nclass", c.lower())
            return ("class", c)
        if c in CONTROL_ESCAPES:
            return ("char", CONTROL_ESCAPES[c])
        if c == "x":
            if (self.i + 1 >= len(self.pattern)
                    or self.pattern[self.i] not in HEX_DIGITS
                    or self.pattern[self.i + 1] not in HEX_DIGITS):
                self.error("incomplete escape \\x")
            code = self.eat() + self.eat()
            return ("char", chr(int(code, 16)))
        if c.isdigit():
            self.error("backreferences are not supported")
        if c.isalpha():
            self.error("bad escape \\%s" % c)
        return ("char", c)  # escaped punctuation: \. \* \( \\ ...

    def parse_class(self):
        self.eat()  # '['
        negated = False
        if self.cur() == "^":
            self.eat()
            negated = True
        items = []
        first = True
        while True:
            if not self.more():
                self.error("unterminated character set")
            c = self.cur()
            if c == "]" and not first:
                self.eat()
                break
            first = False
            if c == "\\":
                elem = self.parse_escape_item()
            else:
                self.eat()
                elem = ("char", c)
            # range?
            if (elem[0] == "char" and self.cur() == "-"
                    and self.i + 1 < len(self.pattern)
                    and self.pattern[self.i + 1] != "]"):
                self.eat()  # '-'
                if self.cur() == "\\":
                    elem2 = self.parse_escape_item()
                    if elem2[0] != "char":
                        self.error("bad character range")
                else:
                    elem2 = ("char", self.eat())
                lo, hi = elem[1], elem2[1]
                if ord(hi) < ord(lo):
                    self.error("bad character range %s-%s" % (lo, hi))
                items.append(("range", lo, hi))
            else:
                items.append(elem)
        return CharClass(items, negated)


def parse(pattern):
    """Parse a pattern.  Returns (ast, number_of_capture_groups)."""
    return Parser(pattern).parse()
