#!/usr/bin/env python3
"""Ember -- a small Lisp dialect implemented in pure Python (stdlib only).

Features:
  * Reader with ints, floats, strings (with escapes), symbols, keywords,
    quote / quasiquote / unquote / unquote-splicing sugar, and ; comments
  * Special forms: quote, quasiquote, define, lambda (variadic), if, cond,
    let, let*, set!, begin, and, or, while, defmacro
  * Lexical scoping, proper closures, and tail-call optimization
    (the evaluator is a loop, so tail-recursive Ember code runs in
    constant Python stack space)
  * Macros via defmacro + quasiquote templates (see prelude.em)
  * A rich builtin library (arithmetic, lists, strings, higher-order fns)

Run a file:      python3 ember.py program.em
Interactive:     python3 repl.py
"""

import math
import os
import re
import sys

sys.setrecursionlimit(20000)  # non-tail Ember recursion nests Python frames


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class EmberError(Exception):
    """Any error raised by the Ember reader or evaluator."""


class ParseError(EmberError):
    """A syntax error found while reading source text."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
# Lists   -> Python lists            Numbers  -> int / float
# Symbols -> Symbol (str subclass)   Strings  -> str
# Keywords-> Keyword (str subclass)  Booleans -> True / False (#t / #f)
# nil / empty list -> []

class Symbol(str):
    __slots__ = ()

    def __repr__(self):
        return "Symbol(%s)" % str.__repr__(self)


class Keyword(str):
    """Self-evaluating :keyword. The stored text includes the colon."""
    __slots__ = ()

    def __repr__(self):
        return "Keyword(%s)" % str.__repr__(self)


def S(name):
    return Symbol(name)


_QUOTE = S("quote")
_QUASI = S("quasiquote")
_UNQUOTE = S("unquote")
_SPLICE = S("unquote-splicing")
_BEGIN = S("begin")
_ELSE = S("else")
_DOT = S(".")

NIL = []  # canonical empty list; treat as read-only


def truthy(v):
    """Only #f and nil/() are false."""
    return not (v is False or (isinstance(v, list) and not v))


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

_DELIMS = set("()'`,;\"")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}
_NUM_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def _line_col(src, pos):
    line = src.count("\n", 0, pos) + 1
    col = pos - src.rfind("\n", 0, pos)
    return line, col


def _err(src, pos, msg):
    line, col = _line_col(src, pos)
    return ParseError("line %d, col %d: %s" % (line, col, msg))


def tokenize(src):
    """Yield (kind, value, pos) tuples. kind is 'punct', 'string', or 'atom'."""
    toks = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
        elif c == ";":  # comment to end of line
            while i < n and src[i] != "\n":
                i += 1
        elif c in "()'`":
            toks.append(("punct", c, i))
            i += 1
        elif c == ",":
            if i + 1 < n and src[i + 1] == "@":
                toks.append(("punct", ",@", i))
                i += 2
            else:
                toks.append(("punct", ",", i))
                i += 1
        elif c == '"':
            start = i
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise _err(src, start, "unterminated string literal")
                ch = src[i]
                if ch == "\\":
                    if i + 1 >= n:
                        raise _err(src, start, "unterminated string literal")
                    esc = src[i + 1]
                    if esc not in _ESCAPES:
                        raise _err(src, i, "unknown escape '\\%s' in string" % esc)
                    buf.append(_ESCAPES[esc])
                    i += 2
                elif ch == '"':
                    i += 1
                    break
                else:
                    buf.append(ch)
                    i += 1
            toks.append(("string", "".join(buf), start))
        else:
            start = i
            while i < n and src[i] not in _DELIMS and not src[i].isspace():
                i += 1
            toks.append(("atom", src[start:i], start))
    return toks


def parse_atom(text):
    if text == "#t":
        return True
    if text == "#f":
        return False
    if text == "nil":
        return []
    if _NUM_RE.match(text):
        if "." in text or "e" in text or "E" in text:
            return float(text)
        return int(text)
    if text.startswith(":") and len(text) > 1:
        return Keyword(text)
    return Symbol(text)


_SUGAR = {"'": _QUOTE, "`": _QUASI, ",": _UNQUOTE, ",@": _SPLICE}


def _read_form(toks, pos, src):
    if pos[0] >= len(toks):
        raise _err(src, len(src), "unexpected end of input")
    kind, val, tpos = toks[pos[0]]
    pos[0] += 1
    if kind == "string":
        return val
    if kind == "atom":
        return parse_atom(val)
    # punct
    if val == "(":
        lst = []
        while True:
            if pos[0] >= len(toks):
                raise _err(src, tpos, "unclosed '(' -- expected ')'")
            k, v, p = toks[pos[0]]
            if k == "punct" and v == ")":
                pos[0] += 1
                return lst
            lst.append(_read_form(toks, pos, src))
    if val == ")":
        raise _err(src, tpos, "unexpected ')'")
    if val in _SUGAR:
        return [_SUGAR[val], _read_form(toks, pos, src)]
    raise _err(src, tpos, "unexpected token %r" % val)


def parse_all(src):
    """Parse source text into a list of forms."""
    toks = tokenize(src)
    pos = [0]
    forms = []
    while pos[0] < len(toks):
        forms.append(_read_form(toks, pos, src))
    return forms


def balanced_depth(src):
    """Paren depth of src ignoring strings/comments. 0 means complete,
    > 0 means more input is needed (also if inside an open string)."""
    depth = 0
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == ";":
            while i < n and src[i] != "\n":
                i += 1
        elif c == '"':
            i += 1
            closed = False
            while i < n:
                if src[i] == "\\":
                    i += 2
                elif src[i] == '"':
                    closed = True
                    i += 1
                    break
                else:
                    i += 1
            if not closed:
                return max(depth, 0) + 1
        elif c == "(":
            depth += 1
            i += 1
        elif c == ")":
            depth -= 1
            i += 1
        else:
            i += 1
    return depth


# ---------------------------------------------------------------------------
# Printer
# ---------------------------------------------------------------------------

_UNSUGAR = {"quote": "'", "quasiquote": "`", "unquote": ",", "unquote-splicing": ",@"}


def to_string(v, readable=True):
    if v is True:
        return "#t"
    if v is False:
        return "#f"
    if isinstance(v, (Symbol, Keyword)):
        return str(v)
    if isinstance(v, str):
        if readable:
            out = v.replace("\\", "\\\\").replace('"', '\\"')
            out = out.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
            return '"%s"' % out
        return v
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        if len(v) == 2 and isinstance(v[0], Symbol) and str(v[0]) in _UNSUGAR:
            return _UNSUGAR[str(v[0])] + to_string(v[1], readable)
        return "(" + " ".join(to_string(x, readable) for x in v) + ")"
    if isinstance(v, Lambda):
        return "#<procedure %s>" % (v.name or "lambda")
    if isinstance(v, Macro):
        return "#<macro %s>" % (v.name or "macro")
    if callable(v):
        return "#<builtin %s>" % getattr(v, "ember_name", getattr(v, "__name__", "?"))
    return str(v)


# ---------------------------------------------------------------------------
# Environments, procedures, macros
# ---------------------------------------------------------------------------

class Env:
    __slots__ = ("vars", "parent")

    def __init__(self, vars=None, parent=None):
        self.vars = vars if vars is not None else {}
        self.parent = parent

    def lookup(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise EmberError("unbound symbol '%s'" % name)

    def set(self, name, value):
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        raise EmberError("set!: cannot set undefined symbol '%s'" % name)

    def define(self, name, value):
        self.vars[name] = value


class Lambda:
    __slots__ = ("params", "body", "env", "name")

    def __init__(self, params, body, env, name=None):
        self.params = params
        self.body = body
        self.env = env
        self.name = name


class Macro:
    __slots__ = ("params", "body", "env", "name")

    def __init__(self, params, body, env, name):
        self.params = params
        self.body = body
        self.env = env
        self.name = name


def bind_params(params, args, name):
    """Build a frame dict binding params to args.

    params may be:  a bare symbol (collects all args as a list),
    a plain list of symbols, or a list with a dotted rest:  (a b . rest)
    """
    if isinstance(params, Symbol):
        return {params: list(args)}
    if not isinstance(params, list):
        raise EmberError("%s: bad parameter list" % name)
    frame = {}
    if _DOT in params:
        di = params.index(_DOT)
        if di != len(params) - 2:
            raise EmberError("%s: malformed dotted parameter list" % name)
        required = params[:di]
        rest = params[di + 1]
        if len(args) < len(required):
            raise EmberError("%s: expected at least %d argument%s, got %d"
                             % (name, len(required),
                                "" if len(required) == 1 else "s", len(args)))
        for p, a in zip(required, args):
            frame[p] = a
        frame[rest] = list(args[len(required):])
    else:
        if len(args) != len(params):
            raise EmberError("%s: expected %d argument%s, got %d"
                             % (name, len(params),
                                "" if len(params) == 1 else "s", len(args)))
        for p, a in zip(params, args):
            frame[p] = a
    return frame


def apply_proc(f, args):
    """Apply an Ember procedure or Python builtin to already-evaluated args.
    Used by builtins like map/filter/reduce/sort and by `apply`."""
    if isinstance(f, Lambda):
        env = Env(bind_params(f.params, args, f.name or "lambda"), f.env)
        result = []
        for form in f.body:
            result = seval(form, env)
        return result
    if callable(f):
        return f(*args)
    raise EmberError("not a procedure: %s" % to_string(f))


# ---------------------------------------------------------------------------
# Quasiquote
# ---------------------------------------------------------------------------

def eval_quasiquote(x, env, depth):
    if not isinstance(x, list) or not x:
        return x
    head = x[0]
    if head == _UNQUOTE and isinstance(head, Symbol):
        if len(x) != 2:
            raise EmberError("unquote: expected one form")
        if depth == 1:
            return seval(x[1], env)
        return [_UNQUOTE, eval_quasiquote(x[1], env, depth - 1)]
    if head == _QUASI and isinstance(head, Symbol):
        return [_QUASI, eval_quasiquote(x[1], env, depth + 1)]
    out = []
    for item in x:
        if (isinstance(item, list) and item
                and isinstance(item[0], Symbol) and item[0] == _SPLICE):
            if len(item) != 2:
                raise EmberError("unquote-splicing: expected one form")
            if depth == 1:
                spliced = seval(item[1], env)
                if not isinstance(spliced, list):
                    raise EmberError("unquote-splicing: expected a list, got %s"
                                     % to_string(spliced))
                out.extend(spliced)
            else:
                out.append([_SPLICE, eval_quasiquote(item[1], env, depth - 1)])
        else:
            out.append(eval_quasiquote(item, env, depth))
    return out


# ---------------------------------------------------------------------------
# The evaluator (loop-based => tail-call optimized)
# ---------------------------------------------------------------------------

def seval(x, env):
    while True:
        if isinstance(x, Symbol):
            return env.lookup(x)
        if not isinstance(x, list):
            return x  # numbers, strings, keywords, booleans self-evaluate
        if not x:
            return x  # nil evaluates to itself

        head = x[0]
        if isinstance(head, Symbol):
            h = str(head)

            if h == "quote":
                if len(x) != 2:
                    raise EmberError("quote: expected one form")
                return x[1]

            if h == "quasiquote":
                if len(x) != 2:
                    raise EmberError("quasiquote: expected one form")
                return eval_quasiquote(x[1], env, 1)

            if h in ("unquote", "unquote-splicing"):
                raise EmberError("%s outside of quasiquote" % h)

            if h == "if":
                if len(x) not in (3, 4):
                    raise EmberError("if: expected (if test then [else])")
                if truthy(seval(x[1], env)):
                    x = x[2]
                elif len(x) == 4:
                    x = x[3]
                else:
                    return []
                continue  # tail position

            if h == "define":
                if len(x) < 2:
                    raise EmberError("define: expected a name")
                target = x[1]
                if isinstance(target, list):
                    # (define (name . params) body...)
                    if not target or not isinstance(target[0], Symbol):
                        raise EmberError("define: bad function form")
                    fname = target[0]
                    lam = Lambda(target[1:], x[2:], env, str(fname))
                    env.define(fname, lam)
                    return fname
                if not isinstance(target, Symbol):
                    raise EmberError("define: name must be a symbol, got %s"
                                     % to_string(target))
                value = seval(x[2], env) if len(x) > 2 else []
                if isinstance(value, Lambda) and value.name is None:
                    value.name = str(target)
                env.define(target, value)
                return target

            if h == "set!":
                if len(x) != 3 or not isinstance(x[1], Symbol):
                    raise EmberError("set!: expected (set! name value)")
                env.set(x[1], seval(x[2], env))
                return []

            if h == "lambda":
                if len(x) < 2:
                    raise EmberError("lambda: expected a parameter list")
                return Lambda(x[1], x[2:], env)

            if h == "begin":
                if len(x) == 1:
                    return []
                for form in x[1:-1]:
                    seval(form, env)
                x = x[-1]
                continue  # tail position

            if h in ("let", "let*"):
                if len(x) < 3 or not isinstance(x[1], list):
                    raise EmberError("%s: expected (%s ((name value)...) body...)"
                                     % (h, h))
                bindings = x[1]
                if h == "let":
                    frame = {}
                    for b in bindings:
                        if (not isinstance(b, list) or len(b) != 2
                                or not isinstance(b[0], Symbol)):
                            raise EmberError("let: bad binding %s" % to_string(b))
                        frame[b[0]] = seval(b[1], env)
                    env = Env(frame, env)
                else:
                    for b in bindings:
                        if (not isinstance(b, list) or len(b) != 2
                                or not isinstance(b[0], Symbol)):
                            raise EmberError("let*: bad binding %s" % to_string(b))
                        env = Env({b[0]: seval(b[1], env)}, env)
                x = [_BEGIN] + x[2:]
                continue  # tail position

            if h == "cond":
                matched = False
                for clause in x[1:]:
                    if not isinstance(clause, list) or not clause:
                        raise EmberError("cond: bad clause %s" % to_string(clause))
                    if isinstance(clause[0], Symbol) and clause[0] == _ELSE:
                        x = [_BEGIN] + clause[1:]
                        matched = True
                        break
                    t = seval(clause[0], env)
                    if truthy(t):
                        if len(clause) == 1:
                            return t
                        x = [_BEGIN] + clause[1:]
                        matched = True
                        break
                if matched:
                    continue  # tail position
                return []

            if h == "and":
                if len(x) == 1:
                    return True
                for form in x[1:-1]:
                    v = seval(form, env)
                    if not truthy(v):
                        return v
                x = x[-1]
                continue  # tail position

            if h == "or":
                if len(x) == 1:
                    return False
                for form in x[1:-1]:
                    v = seval(form, env)
                    if truthy(v):
                        return v
                x = x[-1]
                continue  # tail position

            if h == "while":
                if len(x) < 2:
                    raise EmberError("while: expected (while test body...)")
                while truthy(seval(x[1], env)):
                    for form in x[2:]:
                        seval(form, env)
                return []

            if h == "defmacro":
                if len(x) < 3 or not isinstance(x[1], Symbol):
                    raise EmberError(
                        "defmacro: expected (defmacro name (params...) body...)")
                env.define(x[1], Macro(x[2], x[3:], env, str(x[1])))
                return x[1]

        # --- application ---------------------------------------------------
        f = seval(head, env)

        if isinstance(f, Macro):
            menv = Env(bind_params(f.params, x[1:], f.name), f.env)
            expansion = []
            for form in f.body:
                expansion = seval(form, menv)
            x = expansion
            continue  # evaluate the expansion in place (still TCO-friendly)

        args = [seval(a, env) for a in x[1:]]

        if isinstance(f, Lambda):
            env = Env(bind_params(f.params, args, f.name or "lambda"), f.env)
            if not f.body:
                return []
            for form in f.body[:-1]:
                seval(form, env)
            x = f.body[-1]
            continue  # tail call: loop instead of recursing

        if callable(f):
            try:
                return f(*args)
            except EmberError:
                raise
            except (TypeError, ValueError, ZeroDivisionError,
                    IndexError, KeyError, AttributeError) as e:
                bname = getattr(f, "ember_name", getattr(f, "__name__", "builtin"))
                raise EmberError("%s: %s" % (bname, e)) from None

        raise EmberError("not a procedure: %s" % to_string(f))


def macroexpand_1(x, env):
    """Expand the outermost macro call in x once (used by tests/tools)."""
    if isinstance(x, list) and x and isinstance(x[0], Symbol):
        try:
            f = env.lookup(x[0])
        except EmberError:
            return x, False
        if isinstance(f, Macro):
            menv = Env(bind_params(f.params, x[1:], f.name), f.env)
            expansion = []
            for form in f.body:
                expansion = seval(form, menv)
            return expansion, True
    return x, False


# ---------------------------------------------------------------------------
# Builtins
# ---------------------------------------------------------------------------

def _check_num(name, *vals):
    for v in vals:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise EmberError("%s: expected a number, got %s" % (name, to_string(v)))


def b_add(*a):
    _check_num("+", *a)
    return sum(a)


def b_sub(first, *rest):
    _check_num("-", first, *rest)
    if not rest:
        return -first
    r = first
    for v in rest:
        r -= v
    return r


def b_mul(*a):
    _check_num("*", *a)
    r = 1
    for v in a:
        r *= v
    return r


def b_div(first, *rest):
    _check_num("/", first, *rest)
    if not rest:
        rest, first = (first,), 1
    r = first
    for v in rest:
        if v == 0:
            raise EmberError("/: division by zero")
        if isinstance(r, int) and isinstance(v, int) and r % v == 0:
            r //= v
        else:
            r /= v
    return r


def _chain(name, op):
    def cmp(*a):
        _check_num(name, *a)
        if len(a) < 2:
            raise EmberError("%s: expected at least 2 arguments" % name)
        return all(op(a[i], a[i + 1]) for i in range(len(a) - 1))
    return cmp


def b_num_eq(*a):
    return _chain("=", lambda p, q: p == q)(*a)


def b_equal(a, b):
    return ember_equal(a, b)


def ember_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, Symbol) != isinstance(b, Symbol):
        return False
    if isinstance(a, Keyword) != isinstance(b, Keyword):
        return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(ember_equal(p, q) for p, q in zip(a, b))
    return a == b


def b_eq(a, b):
    if isinstance(a, (Symbol, Keyword, int, float, bool, str)) and \
       isinstance(b, (Symbol, Keyword, int, float, bool, str)):
        return ember_equal(a, b)
    return a is b


def b_cons(x, lst):
    if not isinstance(lst, list):
        raise EmberError("cons: second argument must be a list (Ember has no "
                         "improper pairs), got %s" % to_string(lst))
    return [x] + lst


def b_car(lst):
    if not isinstance(lst, list) or not lst:
        raise EmberError("car: expected a non-empty list, got %s" % to_string(lst))
    return lst[0]


def b_cdr(lst):
    if not isinstance(lst, list) or not lst:
        raise EmberError("cdr: expected a non-empty list, got %s" % to_string(lst))
    return lst[1:]


def b_map(f, *lists):
    if not lists:
        raise EmberError("map: expected at least one list")
    for l in lists:
        if not isinstance(l, list):
            raise EmberError("map: expected a list, got %s" % to_string(l))
    return [apply_proc(f, list(t)) for t in zip(*lists)]


def b_filter(f, lst):
    return [v for v in lst if truthy(apply_proc(f, [v]))]


def b_reduce(f, init, lst):
    acc = init
    for v in lst:
        acc = apply_proc(f, [acc, v])
    return acc


def b_apply(f, args):
    if not isinstance(args, list):
        raise EmberError("apply: last argument must be a list")
    return apply_proc(f, args)


def b_sort(lst, less=None):
    if less is None:
        return sorted(lst)
    import functools
    return sorted(lst, key=functools.cmp_to_key(
        lambda a, b: -1 if truthy(apply_proc(less, [a, b]))
        else (1 if truthy(apply_proc(less, [b, a])) else 0)))


def b_range(*a):
    _check_num("range", *a)
    if len(a) == 1:
        return list(range(int(a[0])))
    if len(a) == 2:
        return list(range(int(a[0]), int(a[1])))
    if len(a) == 3:
        return list(range(int(a[0]), int(a[1]), int(a[2])))
    raise EmberError("range: expected 1-3 arguments")


def b_assoc(key, alist):
    for entry in alist:
        if isinstance(entry, list) and entry and ember_equal(entry[0], key):
            return entry
    return False


def b_member(x, lst):
    for i, v in enumerate(lst):
        if ember_equal(v, x):
            return lst[i:]
    return False


def b_nth(lst, i):
    if not isinstance(lst, list) or not (0 <= i < len(lst)):
        raise EmberError("nth: index %s out of range for %s"
                         % (i, to_string(lst)))
    return lst[i]


def b_display(*a):
    sys.stdout.write("".join(to_string(v, False) for v in a))
    return []


def b_println(*a):
    sys.stdout.write(" ".join(to_string(v, False) for v in a) + "\n")
    return []


def b_newline():
    sys.stdout.write("\n")
    return []


def b_error(*a):
    raise EmberError(" ".join(to_string(v, False) for v in a) or "error")


def b_substring(s, start, end=None):
    return s[start:end] if end is not None else s[start:]


def b_string_to_number(s):
    v = parse_atom(s)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return v


_gensym_counter = [0]


def b_gensym(prefix="g"):
    _gensym_counter[0] += 1
    return Symbol("#:%s%d" % (prefix, _gensym_counter[0]))


def _is_string(v):
    return isinstance(v, str) and not isinstance(v, (Symbol, Keyword))


def b_str(*a):
    return "".join(to_string(v, False) for v in a)


GLOBAL_FOR_EVAL = [None]  # set by make_global_env; used by the `eval` builtin


def b_eval(form, env=None):
    return seval(form, GLOBAL_FOR_EVAL[0])


def b_read_string(s):
    forms = parse_all(s)
    if len(forms) != 1:
        raise EmberError("read-string: expected exactly one form")
    return forms[0]


def make_builtins():
    b = {
        # arithmetic
        "+": b_add, "-": b_sub, "*": b_mul, "/": b_div,
        "mod": lambda a, bb: a % bb,
        "modulo": lambda a, bb: a % bb,
        "quotient": lambda a, bb: math.trunc(a / bb),
        "remainder": lambda a, bb: int(math.fmod(a, bb)),
        "abs": abs, "min": min, "max": max,
        "floor": lambda a: math.floor(a), "ceiling": lambda a: math.ceil(a),
        "round": lambda a: round(a), "sqrt": math.sqrt, "expt": lambda a, bb: a ** bb,
        "exp": math.exp, "log": math.log,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "even?": lambda n: n % 2 == 0, "odd?": lambda n: n % 2 != 0,
        "zero?": lambda n: n == 0,
        "positive?": lambda n: n > 0, "negative?": lambda n: n < 0,
        # comparison / equality
        "=": b_num_eq,
        "<": _chain("<", lambda p, q: p < q),
        ">": _chain(">", lambda p, q: p > q),
        "<=": _chain("<=", lambda p, q: p <= q),
        ">=": _chain(">=", lambda p, q: p >= q),
        "equal?": b_equal, "eq?": b_eq,
        "not": lambda v: not truthy(v),
        # lists
        "cons": b_cons, "car": b_car, "cdr": b_cdr,
        "list": lambda *a: list(a),
        "length": lambda l: len(l),
        "append": lambda *ls: [v for l in ls for v in l],
        "reverse": lambda l: list(reversed(l)),
        "nth": b_nth,
        "first": b_car, "rest": b_cdr,
        "last": lambda l: b_car(l[-1:] if l else []),
        "take": lambda n, l: l[:n], "drop": lambda n, l: l[n:],
        "null?": lambda v: isinstance(v, list) and not v,
        "pair?": lambda v: isinstance(v, list) and bool(v),
        "list?": lambda v: isinstance(v, list),
        "member": b_member, "assoc": b_assoc,
        "range": b_range,
        "zip": lambda *ls: [list(t) for t in zip(*ls)],
        "sort": b_sort,
        # higher-order
        "map": b_map, "filter": b_filter, "reduce": b_reduce, "apply": b_apply,
        "for-each": lambda f, l: ([apply_proc(f, [v]) for v in l], [])[1],
        # type predicates
        "number?": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer?": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "float?": lambda v: isinstance(v, float),
        "string?": _is_string,
        "symbol?": lambda v: isinstance(v, Symbol),
        "keyword?": lambda v: isinstance(v, Keyword),
        "boolean?": lambda v: isinstance(v, bool),
        "procedure?": lambda v: isinstance(v, Lambda) or callable(v),
        # strings
        "str": b_str,
        "string-append": lambda *ss: "".join(ss),
        "string-length": lambda s: len(s),
        "substring": b_substring,
        "string-ref": lambda s, i: s[i],
        "string-upcase": lambda s: s.upper(),
        "string-downcase": lambda s: s.lower(),
        "string-split": lambda s, sep: s.split(sep),
        "string-join": lambda ls, sep: sep.join(ls),
        "string-contains?": lambda s, sub: sub in s,
        "string->number": b_string_to_number,
        "number->string": lambda n: to_string(n, False),
        "string->symbol": lambda s: Symbol(s),
        "symbol->string": lambda s: str(s),
        "string->list": lambda s: [c for c in s],
        # io / misc
        "display": b_display, "print": b_display,
        "println": b_println, "newline": b_newline,
        "error": b_error,
        "gensym": b_gensym,
        "eval": b_eval,
        "read-string": b_read_string,
    }
    out = {}
    for name, fn in b.items():
        try:
            fn.ember_name = name
        except AttributeError:
            pass
        out[Symbol(name)] = fn
    return out


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

def eval_string(src, env):
    """Evaluate all forms in src, returning the last result."""
    result = []
    for form in parse_all(src):
        result = seval(form, env)
    return result


def run_file(path, env):
    with open(path, "r") as f:
        return eval_string(f.read(), env)


def make_global_env(load_prelude=True):
    env = Env(make_builtins(), None)
    env.define(Symbol("nil"), [])
    GLOBAL_FOR_EVAL[0] = env
    if load_prelude:
        prelude = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "prelude.em")
        run_file(prelude, env)
    return env


def main(argv):
    if len(argv) < 2:
        print("usage: python3 ember.py <file.em>   (or: python3 repl.py)")
        return 2
    env = make_global_env()
    try:
        run_file(argv[1], env)
    except EmberError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
