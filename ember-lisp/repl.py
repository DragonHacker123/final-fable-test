#!/usr/bin/env python3
"""Interactive REPL for Ember with multi-line input.

Input is accumulated until all parentheses (and strings) are balanced,
so you can paste or type whole function definitions across lines.
"""

import sys

import ember

BANNER = """\
Ember 1.0 -- a small Lisp in pure Python
Type an expression, or press Ctrl-D to exit.  Multi-line input is
supported: keep typing until your parens balance.
"""

PROMPT = "ember> "
CONT_PROMPT = "  ...> "


def main():
    try:
        import readline  # noqa: F401  -- line editing + history if available
    except ImportError:
        pass

    env = ember.make_global_env()
    print(BANNER)
    buf = ""
    while True:
        try:
            line = input(CONT_PROMPT if buf else PROMPT)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("  (interrupted -- input discarded)")
            buf = ""
            continue

        buf += line + "\n"
        if not buf.strip():
            buf = ""
            continue

        # Keep reading while parens are unbalanced.
        try:
            depth = ember.balanced_depth(buf)
        except Exception:
            depth = 0
        if depth > 0:
            continue

        source, buf = buf, ""
        try:
            forms = ember.parse_all(source)
        except ember.ParseError as e:
            print("parse error: %s" % e)
            continue

        for form in forms:
            try:
                value = ember.seval(form, env)
            except ember.EmberError as e:
                print("error: %s" % e)
                break
            except RecursionError:
                print("error: recursion too deep (non-tail recursion "
                      "exhausted the stack)")
                break
            except KeyboardInterrupt:
                print("\n  (interrupted)")
                break
            print("=> %s" % ember.to_string(value, True))


if __name__ == "__main__":
    main()
