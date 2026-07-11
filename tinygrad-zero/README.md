# tinygrad-zero

A complete deep-learning framework in pure Python — **no numpy, no anything**
— from a scalar reverse-mode autodiff engine up through trained neural
networks, with results plotted in your terminal.

```bash
python3 gradcheck.py        # verify every gradient against finite differences
python3 demo1_spirals.py    # train a classifier on two spirals (~4 min)
python3 demo2_sine.py       # regression + XOR (~1 min)
```

## The engine (`engine.py`)

A `Value` wraps one float and remembers how it was computed. Operators
(`+ - * / **`, `tanh`, `relu`, `exp`, `log`) build a computation graph;
`.backward()` topologically sorts it and applies the chain rule in reverse,
accumulating `dL/dnode` into every `.grad`. That's reverse-mode automatic
differentiation — the same algorithm as PyTorch, at 1/1000th the scale.

**Trust, but verify:** `gradcheck.py` compares every analytic gradient
against central finite differences `(f(x+h) - f(x-h)) / 2h` on 10 hand-built
expressions plus 30 random expression trees. All 40 pass with max relative
error ~1e-10.

## The library (`nn.py`)

`Neuron` → `Layer` → `MLP` modules with `parameters()` / `zero_grad()`, an
`SGD` optimizer with momentum, and a cosine learning-rate schedule with
warmup.

## Demo 1: two spirals (`demo1_spirals.py`)

Two interleaved noisy spirals, 160 points — the classic "linear models need
not apply" benchmark. A `[2, 32, 32, 1]` tanh MLP trained with hinge loss
reaches **99.4% training accuracy**, then renders its decision surface:

```
+----------------------------------------------------------------+
|###################o#########o#o##o#############################|
|####################o###o###++#####o#######o####################|
|################o+    ++++  ..  +++####o###o####################|
|############oo#+ ....x...x..xx....       +######################|
|############### .........x.....x...xx....x o#o#o################|
|#############o+ x.....xx.. ###+ ...x...x... +#o#################|
|#######o######+ ..x.....x########+ ..x...... +################++|
|########o####+  .......+o#o#####o##o+ .....x. +#o##o######++++  |
|######o#####++x ..... +#oo#oo#o#ooo#o .x...xx +#########+++  ...|
|######o##+++  ...x.+#o#o++  +x####ooo+....... o###o###++  ......|
|#####+++ ........+###o##+...x.x +##oo x.xx.. +###o#o++ ....x....|
|#++  ..........x+#####o#+...x.... oo+ ..... +##x###+  ..........|
| .........x..x. ###o##o#+x....x...x.....x.. +#####++  .x........|
|..............x +######o#+.x.xxxxx.....xx.. +###o#o++  .........|
|...............x  +o######o+.x..x...x   x.x+######o++  .........|
|............x....x  +##oo######+    ++##+#####oo#+++  x.x.......|
|................x.. ++#####################o##++   .............|
|.................... ++####o###o###o#+#oo##o+  x.....x..........|
|..................x..  +#######o####+  ++##+ ...................|
|..................xx.....  +#######+....   ....x....x...........|
+----------------------------------------------------------------+
  o / '#' = spiral A and its predicted region
  x / '.' = spiral B and its predicted region
```

The learned regions *wind around each other* — the network invented a spiral
coordinate system out of nothing but tanh units. (The in-terminal version is
truecolor with confidence shading.)

## Demo 2: sine regression + XOR (`demo2_sine.py`)

A `[1,16,16,1]` MLP fits `y = sin(x)` to MSE ≈ 0.004 and overlays prediction
against ground truth in ASCII; then a 2-4-1 net learns XOR and prints its
truth table (4/4 correct) — the function that famously killed the
single-layer perceptron.

## Why pure Python?

No vectorization means every multiply-accumulate is visible in the profiler
and the debugger: ~300 parameters × 160 points × 600 epochs ≈ tens of
millions of scalar chain-rule applications, all inspectable. It's an
implementation you can read end-to-end in an afternoon and single-step
through backprop with `pdb`.
