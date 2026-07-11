"""Pretty-print a pattern's AST and its compiled bytecode.

    python3 visualize.py '(a+)+$'
    python3 visualize.py '(\w+)@(\w+)' --tree-only
"""

import sys

from regex_forge import parser as P
from regex_forge import compiler as C


def render(node, prefix="", is_last=True):
    """Recursive box-drawing tree renderer."""
    branch = "└─ " if is_last else "├─ "
    child_prefix = prefix + ("   " if is_last else "│  ")

    if isinstance(node, P.Literal):
        label = f"Literal {node.ch!r}"
        kids = []
    elif isinstance(node, P.Dot):
        label = "Dot  (any char but newline)"
        kids = []
    elif isinstance(node, P.Empty):
        label = "Empty"
        kids = []
    elif isinstance(node, P.CharClass):
        label = f"CharClass {P.class_to_str(node.items, node.negated)}"
        kids = []
    elif isinstance(node, P.Anchor):
        label = f"Anchor {'^ start of line' if node.kind == 'bol' else '$ end of line'}"
        kids = []
    elif isinstance(node, P.Group):
        label = f"Group #{node.index}"
        kids = [node.body]
    elif isinstance(node, P.Concat):
        label = "Concat"
        kids = list(node.parts)
    elif isinstance(node, P.Alt):
        label = "Alt  (|)"
        kids = list(node.branches)
    elif isinstance(node, P.Repeat):
        hi = "∞" if node.max is None else node.max
        kind = "lazy" if node.lazy else "greedy"
        label = f"Repeat {{{node.min},{hi}}} {kind}"
        kids = [node.body]
    else:
        label = type(node).__name__
        kids = []

    lines = [prefix + branch + label]
    for i, kid in enumerate(kids):
        lines.extend(render(kid, child_prefix, i == len(kids) - 1))
    return lines


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__.strip())
    pattern = args[0]
    ast, ngroups = P.parse(pattern)

    print(f"pattern: {pattern!r}   ({ngroups} capture group"
          f"{'s' if ngroups != 1 else ''})\n")
    print("AST")
    print("\n".join(render(ast, "", True)))

    if "--tree-only" not in sys.argv:
        prog = C.compile_ast(ast, ngroups)
        print(f"\nbytecode  ({len(prog.insts)} instructions, "
              f"{prog.nslots} save slots, {prog.nmarks} loop marks)")
        for line in C.disassemble(prog):
            print(line)


if __name__ == "__main__":
    main()
