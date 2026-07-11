"""Command-line interface: match a pattern against text or grep stdin.

    python3 -m regex_forge PATTERN TEXT          # show match + groups
    echo "lines" | python3 -m regex_forge PATTERN  # grep mode
    python3 -m regex_forge --engine backtrack PATTERN TEXT
"""

import sys

import regex_forge as rf


def main(argv):
    engine = "thompson"
    args = []
    it = iter(argv)
    for a in it:
        if a == "--engine":
            engine = next(it, "")
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            args.append(a)
    if not args:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    try:
        regex = rf.compile(args[0], engine=engine)
    except rf.RegexSyntaxError as e:
        print(f"pattern error: {e}", file=sys.stderr)
        return 2

    if len(args) >= 2:                     # match mode
        text = args[1]
        m = regex.search(text)
        if m is None:
            print("no match")
            return 1
        print(f"match: {m.group(0)!r}  span={m.span()}")
        for i in range(1, regex.groups + 1):
            print(f"group {i}: {m.group(i)!r}  span={m.span(i)}")
        return 0

    status = 1                             # grep mode over stdin
    for line in sys.stdin:
        line = line.rstrip("\n")
        if regex.search(line) is not None:
            print(line)
            status = 0
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
