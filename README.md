# ⚡ Fable 5 Demo Blitz

Nine ambitious, self-contained demos — every line designed, written, debugged,
and verified by **Claude Fable 5** running in Claude Code, most of them built
by parallel agents in a single session.

Zero external dependencies anywhere: the Python projects are stdlib-only, and
the web projects are single HTML files you can open directly in a browser.

## The demos

| Demo | What it is | Run it |
|------|-----------|--------|
| [`ray-tracer/`](ray-tracer/) | Physically-based path tracer in pure Python — Monte Carlo rendering, glass/metal/diffuse materials, depth of field | `python3 render.py` |
| [`dungeon-depths/`](dungeon-depths/) | Full roguelike dungeon crawler — procedural levels, shadowcast FOV, monster AI, loot, particles | open `index.html` |
| [`synthwave-studio/`](synthwave-studio/) | Polyphonic Web Audio synth + 16-step sequencer + drum machine + neon visualizer, demo song included | open `index.html` |
| [`ember-lisp/`](ember-lisp/) | A complete Lisp dialect: closures, TCO, real macros, a prelude written in itself, REPL, metacircular evaluator | `python3 repl.py` |
| [`tinygrad-zero/`](tinygrad-zero/) | Deep-learning framework from scratch (no numpy!) — reverse-mode autodiff, gradcheck, trains on two-spirals with ASCII decision boundary | see its README |
| [`galaxy-forge/`](galaxy-forge/) | N-body galaxy collision simulator — Barnes-Hut quadtree gravity, thousands of stars, tidal tails | open `index.html` |
| [`atelier/`](atelier/) | Generative art gallery — flow fields, L-systems, reaction-diffusion, strange attractors, Voronoi stained glass, and more | open `index.html` |
| [`regex-forge/`](regex-forge/) | Regex engine from scratch — Thompson NFA + backtracking VM, differential-tested against `re`, live ReDoS demonstration | see its README |
| [`wfc-cartographer/`](wfc-cartographer/) | Wave Function Collapse fantasy-map generator with a continent gradient, animated collapse in the terminal | `python3 wfc.py` |

## Why these nine?

Each one stresses a different axis: rendering math, game design, DSP and
audio synthesis, programming-language implementation, machine learning
fundamentals, computational physics, visual creativity, computer-science
theory, and constraint solving. Together they're a tour of what one model
can build in one sitting.
