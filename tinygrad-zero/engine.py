"""
engine.py -- a scalar reverse-mode automatic differentiation engine.

Pure Python, standard library only. Every number in a computation is wrapped
in a `Value` node. Operating on Values builds a directed acyclic graph (DAG)
of the computation; calling `.backward()` on the final node walks that graph
in reverse topological order and accumulates d(output)/d(node) into every
node's `.grad` via the chain rule.
"""

import math


class Value:
    """A scalar that remembers how it was computed, so it can be differentiated."""

    __slots__ = ("data", "grad", "_backward", "_prev", "_op")

    def __init__(self, data, _children=(), _op=""):
        self.data = data
        self.grad = 0.0
        self._backward = None   # closure that propagates grad to children
        self._prev = _children  # tuple of parent Values in the graph
        self._op = _op          # op label (for debugging / graph inspection)

    # ---------------------------------------------------------- arithmetic

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def __pow__(self, k):
        assert isinstance(k, (int, float)), "only constant powers are supported"
        out = Value(self.data ** k, (self,), f"**{k}")

        def _backward():
            self.grad += k * (self.data ** (k - 1)) * out.grad
        out._backward = _backward
        return out

    def __neg__(self):
        return self * -1.0

    def __sub__(self, other):
        return self + (-other if isinstance(other, Value) else -other)

    def __rsub__(self, other):
        return Value(other) + (-self)

    def __radd__(self, other):
        return self + other

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return self * other ** -1

    def __rtruediv__(self, other):
        return Value(other) * self ** -1

    # ------------------------------------------------------- nonlinearities

    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward():
            self.grad += (1.0 - t * t) * out.grad
        out._backward = _backward
        return out

    def relu(self):
        out = Value(self.data if self.data > 0 else 0.0, (self,), "relu")

        def _backward():
            if self.data > 0:
                self.grad += out.grad
        out._backward = _backward
        return out

    def exp(self):
        e = math.exp(self.data)
        out = Value(e, (self,), "exp")

        def _backward():
            self.grad += e * out.grad
        out._backward = _backward
        return out

    def log(self):
        out = Value(math.log(self.data), (self,), "log")

        def _backward():
            self.grad += (1.0 / self.data) * out.grad
        out._backward = _backward
        return out

    # -------------------------------------------------------- fused kernel

    @staticmethod
    def dot(ws, xs, bias):
        """Fused affine op: bias + sum_i ws[i]*xs[i] as a SINGLE graph node.

        Mathematically identical to chaining + and *, but it collapses the
        2n intermediate nodes of a dot product into one, which makes the
        pure-Python engine ~10x faster on neural nets -- the same trick
        (kernel fusion) real frameworks use. Gradients:
            d/dw_i = x_i,   d/dx_i = w_i,   d/dbias = 1
        """
        s = bias.data
        for w, x in zip(ws, xs):
            s += w.data * x.data
        out = Value(s, tuple(ws) + tuple(xs) + (bias,), "dot")

        def _backward():
            g = out.grad
            for w, x in zip(ws, xs):
                w.grad += x.data * g
                x.grad += w.data * g
            bias.grad += g
        out._backward = _backward
        return out

    # ----------------------------------------------------- backpropagation

    def backward(self):
        """Reverse-mode autodiff: seed d(self)/d(self)=1, then apply the
        chain rule to every node in reverse topological order.

        The topological sort is iterative (explicit stack) so that very deep
        graphs -- hundreds of thousands of nodes -- never hit Python's
        recursion limit.
        """
        topo = []
        visited = set()
        stack = [(self, False)]
        while stack:
            node, children_done = stack.pop()
            if children_done:
                topo.append(node)
                continue
            nid = id(node)
            if nid in visited:
                continue
            visited.add(nid)
            stack.append((node, True))
            for child in node._prev:
                if id(child) not in visited:
                    stack.append((child, False))

        self.grad = 1.0
        for node in reversed(topo):
            if node._backward is not None:
                node._backward()

    def __repr__(self):
        return f"Value(data={self.data:.6g}, grad={self.grad:.6g})"
