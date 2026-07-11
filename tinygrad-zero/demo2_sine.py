"""
demo2_sine.py -- fit y = sin(x) with a tiny MLP using the pure-Python
autodiff engine, then plot prediction vs ground truth in ASCII.

Also prints the learned XOR truth table from a 2-2-1 network as a bonus,
because no from-scratch NN demo is complete without XOR.
"""

import math
import sys
import time

from engine import Value
from nn import MLP, SGD, CosineSchedule


def fit_sine(epochs=400, n=48, hidden=16, lr_max=0.05):
    xs = [-math.pi + 2 * math.pi * i / (n - 1) for i in range(n)]
    ys = [math.sin(x) for x in xs]

    model = MLP([1, hidden, hidden, 1], nonlin="tanh", seed=3)
    opt = SGD(model.parameters(), lr=lr_max, momentum=0.9)
    sched = CosineSchedule(lr_max, 0.002, epochs, warmup=5)

    t0 = time.time()
    for epoch in range(epochs):
        opt.lr = sched(epoch)
        preds = [model([Value(x)]) for x in xs]
        loss = sum((p - y) * (p - y) for p, y in zip(preds, ys)) * (1.0 / n)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if epoch % 50 == 0 or epoch == epochs - 1:
            print(f"epoch {epoch:4d} | lr {opt.lr:.4f} | mse {loss.data:.5f} "
                  f"| {time.time()-t0:5.1f}s")
    return model, xs, ys, loss.data


def ascii_plot(model, cols=72, rows=21, lim=math.pi):
    """Overlay ground truth ('·') and model prediction ('o', '#' where both)."""
    grid = [[" "] * cols for _ in range(rows)]
    y_to_r = lambda y: int(round((1.15 - y) / 2.30 * (rows - 1)))
    for c in range(cols):
        x = -lim + 2 * lim * c / (cols - 1)
        rt = y_to_r(math.sin(x))
        rp = y_to_r(model([Value(x)]).data)
        if 0 <= rt < rows:
            grid[rt][c] = "·"
        if 0 <= rp < rows:
            grid[rp][c] = "#" if rp == rt else "o"
    mid = y_to_r(0.0)
    for c in range(cols):
        if grid[mid][c] == " ":
            grid[mid][c] = "-"
    lines = ["|" + "".join(row) + "|" for row in grid]
    frame = "+" + "-" * cols + "+"
    legend = "  '·' = sin(x)   'o' = model   '#' = overlap   x ∈ [-π, π]"
    return "\n".join([frame] + lines + [frame, legend])


def xor_bonus(epochs=300):
    data = [((0, 0), -1), ((0, 1), 1), ((1, 0), 1), ((1, 1), -1)]
    model = MLP([2, 4, 1], nonlin="tanh", seed=11)
    opt = SGD(model.parameters(), lr=0.08, momentum=0.8)
    for _ in range(epochs):
        loss = sum((model([Value(a), Value(b)]) - y) ** 2
                   for (a, b), y in data) * 0.25
        opt.zero_grad()
        loss.backward()
        opt.step()
    print("\nbonus: XOR learned by a 2-4-1 tanh net")
    print("  a b | raw score | predicted")
    ok = True
    for (a, b), y in data:
        s = model([Value(a), Value(b)]).data
        pred = 1 if s > 0 else -1
        ok &= pred == y
        print(f"  {a} {b} | {s:+9.4f} | {'XOR=1' if pred > 0 else 'XOR=0'}")
    print(f"  -> {'all four cases correct' if ok else 'FAILED'}")
    return ok


def main():
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    print("fitting y = sin(x) with a [1,16,16,1] tanh MLP\n")
    model, xs, ys, mse = fit_sine(epochs=epochs)
    print(f"\nfinal mse: {mse:.5f}\n")
    print(ascii_plot(model))
    ok = xor_bonus()
    if mse > 0.01 or not ok:
        sys.exit("demo did not converge as expected")


if __name__ == "__main__":
    main()
