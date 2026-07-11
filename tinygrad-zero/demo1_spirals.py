"""
demo1_spirals.py -- train an MLP to classify the two-spirals dataset,
entirely with the pure-Python autodiff engine. Finishes with an ANSI-colored
ASCII rendering of the learned decision boundary with the data overlaid,
plus a plain-ASCII version suitable for embedding in a README.
"""

import math
import random
import sys
import time

from engine import Value
from nn import MLP, SGD, CosineSchedule


# --------------------------------------------------------------- dataset

def make_spirals(n_per_class=80, turns=1.5, noise=0.06, seed=42):
    """Two interleaved Archimedean spirals, labels +1 / -1."""
    rng = random.Random(seed)
    pts, ys = [], []
    for label, offset in ((1, 0.0), (-1, math.pi)):
        for i in range(n_per_class):
            t = (i + 0.5) / n_per_class            # 0..1 along the spiral
            r = 0.12 + 0.88 * t                     # radius grows outward
            th = turns * 2.0 * math.pi * t + offset
            x = r * math.cos(th) + rng.gauss(0, noise)
            y = r * math.sin(th) + rng.gauss(0, noise)
            pts.append((x, y))
            ys.append(label)
    order = list(range(len(pts)))
    rng.shuffle(order)
    return [pts[i] for i in order], [ys[i] for i in order]


# --------------------------------------------------------------- training

def loss_and_acc(model, pts, ys, alpha=1e-4):
    """Max-margin hinge loss + L2 regularization, and 0/1 accuracy."""
    scores = [model([Value(x), Value(y)]) for (x, y) in pts]
    losses = [(1.0 + -yi * si).relu() for yi, si in zip(ys, scores)]
    data_loss = sum(losses) * (1.0 / len(losses))
    reg = alpha * sum(p * p for p in model.parameters())
    total = data_loss + reg
    acc = sum((s.data > 0) == (yi > 0) for s, yi in zip(scores, ys)) / len(ys)
    return total, acc


def train(model, pts, ys, epochs=260, lr_max=0.20, lr_min=0.005, log_every=10):
    opt = SGD(model.parameters(), lr=lr_max, momentum=0.9)
    sched = CosineSchedule(lr_max, lr_min, epochs, warmup=5)
    t0 = time.time()
    acc = 0.0
    for epoch in range(epochs):
        opt.lr = sched(epoch)
        loss, acc = loss_and_acc(model, pts, ys)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if epoch % log_every == 0 or epoch == epochs - 1:
            print(f"epoch {epoch:4d} | lr {opt.lr:.4f} | loss {loss.data:.4f} "
                  f"| accuracy {100*acc:5.1f}% | {time.time()-t0:6.1f}s")
    return acc


# --------------------------------------------------------------- plotting

RESET = "\x1b[0m"


def _bg(r, g, b):
    return f"\x1b[48;2;{r};{g};{b}m"


def _fg(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m"


def decision_plot(model, pts, ys, cols=64, rows=30, lim=1.25, ansi=True):
    """Render the decision surface over [-lim,lim]^2.

    ansi=True : truecolor blocks (orange = class +1, blue = class -1),
                brightness ~ classifier confidence, data points overlaid.
    ansi=False: plain characters for README embedding.
    """
    # nearest-cell index for each data point
    marks = {}
    for (x, y), lab in zip(pts, ys):
        c = int((x + lim) / (2 * lim) * cols)
        r = int((lim - y) / (2 * lim) * rows)
        if 0 <= c < cols and 0 <= r < rows:
            marks[(r, c)] = lab

    lines = []
    for r in range(rows):
        y = lim - (r + 0.5) / rows * 2 * lim
        row_chars = []
        for c in range(cols):
            x = -lim + (c + 0.5) / cols * 2 * lim
            s = model([Value(x), Value(y)]).data
            conf = math.tanh(abs(s))              # 0..1 confidence
            pos = s > 0
            if ansi:
                if pos:   # warm orange region
                    bg = _bg(int(60 + 130 * conf), int(35 + 55 * conf), 25)
                else:      # cool blue region
                    bg = _bg(25, int(40 + 45 * conf), int(70 + 130 * conf))
                if (r, c) in marks:
                    dot = _fg(255, 210, 120) + "o" if marks[(r, c)] > 0 \
                        else _fg(140, 210, 255) + "x"
                    row_chars.append(bg + dot + RESET)
                else:
                    row_chars.append(bg + " " + RESET)
            else:
                if (r, c) in marks:
                    row_chars.append("o" if marks[(r, c)] > 0 else "x")
                else:
                    row_chars.append(("#" if conf > 0.55 else "+") if pos
                                     else ("." if conf > 0.55 else " "))
        lines.append("".join(row_chars))

    border_top = "+" + "-" * cols + "+"
    body = "\n".join("|" + ln + "|" for ln in lines)
    legend = ("legend: o = spiral A (class +1)   x = spiral B (class -1)\n"
              "        " + ("orange region = predicted +1, blue region = predicted -1"
                            if ansi else
                            "'#'/'+' = predicted +1 (strong/weak), '.'/' ' = predicted -1"))
    return f"{border_top}\n{body}\n{border_top}\n{legend}"


# ------------------------------------------------------------------ main

def main():
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 260
    pts, ys = make_spirals()
    print(f"two-spirals dataset: {len(pts)} points, 2 classes\n")

    model = MLP([2, 16, 16, 1], nonlin="tanh", seed=7)
    print(f"model: {model}")
    print(f"parameters: {len(model.parameters())}\n")

    acc = train(model, pts, ys, epochs=epochs)
    print(f"\nfinal training accuracy: {100*acc:.1f}%")

    print("\nlearned decision boundary (ANSI):\n")
    print(decision_plot(model, pts, ys, ansi=True))
    print("\nplain-ASCII version (README-friendly):\n")
    print(decision_plot(model, pts, ys, ansi=False))
    return acc


if __name__ == "__main__":
    main()
