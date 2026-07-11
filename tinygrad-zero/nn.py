"""
nn.py -- a tiny neural network library built on the autodiff engine.

Modules (Neuron / Layer / MLP) hold their weights as Values; the forward
pass is just ordinary arithmetic on Values, so gradients come for free.
Also provides SGD with momentum and learning-rate schedules.
"""

import math
import random

from engine import Value


class Module:
    def parameters(self):
        return []

    def zero_grad(self):
        for p in self.parameters():
            p.grad = 0.0


class Neuron(Module):
    """w . x + b, optionally followed by a nonlinearity."""

    def __init__(self, nin, nonlin="tanh", rng=random):
        # Xavier-ish init: scale by 1/sqrt(fan_in) so activations don't saturate
        s = 1.0 / math.sqrt(nin)
        self.w = [Value(rng.uniform(-s, s)) for _ in range(nin)]
        self.b = Value(0.0)
        self.nonlin = nonlin

    def __call__(self, x):
        act = self.b
        for wi, xi in zip(self.w, x):
            act = act + wi * xi
        if self.nonlin == "tanh":
            return act.tanh()
        if self.nonlin == "relu":
            return act.relu()
        return act  # linear

    def parameters(self):
        return self.w + [self.b]

    def __repr__(self):
        return f"{self.nonlin or 'linear'}Neuron({len(self.w)})"


class Layer(Module):
    def __init__(self, nin, nout, **kw):
        self.neurons = [Neuron(nin, **kw) for _ in range(nout)]

    def __call__(self, x):
        out = [n(x) for n in self.neurons]
        return out[0] if len(out) == 1 else out

    def parameters(self):
        return [p for n in self.neurons for p in n.parameters()]

    def __repr__(self):
        return f"Layer[{', '.join(str(n) for n in self.neurons)}]"


class MLP(Module):
    """Multi-layer perceptron. sizes=[2,16,16,1] gives 2 hidden tanh layers
    and a linear scalar output."""

    def __init__(self, sizes, nonlin="tanh", seed=None):
        rng = random.Random(seed) if seed is not None else random
        self.layers = [
            Layer(sizes[i], sizes[i + 1],
                  nonlin=nonlin if i < len(sizes) - 2 else None, rng=rng)
            for i in range(len(sizes) - 1)
        ]

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self):
        return [p for layer in self.layers for p in layer.parameters()]

    def __repr__(self):
        return f"MLP of [{', '.join(str(l) for l in self.layers)}]"


class SGD:
    """Stochastic gradient descent with classical momentum:

        v <- mu * v - lr * grad
        p <- p + v
    """

    def __init__(self, params, lr=0.05, momentum=0.9, weight_decay=0.0):
        self.params = list(params)
        self.lr = lr
        self.momentum = momentum
        self.weight_decay = weight_decay
        self._v = [0.0] * len(self.params)

    def step(self):
        mu, lr, wd = self.momentum, self.lr, self.weight_decay
        for i, p in enumerate(self.params):
            g = p.grad + wd * p.data
            self._v[i] = mu * self._v[i] - lr * g
            p.data += self._v[i]

    def zero_grad(self):
        for p in self.params:
            p.grad = 0.0


class CosineSchedule:
    """Cosine-annealed learning rate: lr(t) decays smoothly from lr_max to
    lr_min over total_steps, after a short linear warmup."""

    def __init__(self, lr_max, lr_min, total_steps, warmup=0):
        self.lr_max, self.lr_min = lr_max, lr_min
        self.total, self.warmup = total_steps, warmup

    def __call__(self, t):
        if t < self.warmup:
            return self.lr_max * (t + 1) / self.warmup
        frac = min(1.0, (t - self.warmup) / max(1, self.total - self.warmup))
        return self.lr_min + 0.5 * (self.lr_max - self.lr_min) * (1 + math.cos(math.pi * frac))
