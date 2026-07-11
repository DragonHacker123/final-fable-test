# WFC Cartographer

Procedural fantasy map generation via **Wave Function Collapse** — pure Python,
zero dependencies, renders straight to your terminal in ANSI color.

```
$ python3 wfc.py --seed 11
~~~≈≈~~≈≈≈≈~░░░░~~~~░░~≈~~≈≈~~░~~~≈~≈~░.♣≀,.≀♠♣+.♣.nn▲△▲▲▲▲▲
≈~~~~≈~~≈~≈≈~~~~≈~~≈~~~≈≈≈~~░░░~░~≈~~░~░≀░░+n,,,..n♣n▲▲△▲▲▲▲
≈~~~~~~≈≈≈≈≈≈~≈~~~~~~░~≈~~≈~░░,░░~≈~~~~░░~~░..+,,n▲nn▲▲▲n△▲△
~~~≈~≈≈≈~~~~░~≈~≈~░~≈≈~~~~~~~~░.,,,.♠♣♣.♣...,,.n▲▲▲△nn△▲▲▲n▲
        (ocean)        (coast)   (plains/forest)  (mountains)
```

## How it works

Every cell starts as a **superposition** of all 13 terrain tiles, stored as a
bitmask. Then, repeatedly:

1. **Observe** — pick the cell with the lowest Shannon entropy over its
   remaining tile weights (the "most decided but not yet decided" cell, with
   tiny random noise to break ties).
2. **Collapse** — sample one tile from the cell's remaining options, weighted
   by tile frequency *and* a positional continent gradient.
3. **Propagate** — AC-3-style constraint propagation: each collapsed or
   narrowed cell restricts its four neighbors to tiles whose terrain classes
   are allowed to touch (`mountain` never borders `sea`, `town` needs `plain`
   or `river` or `road`, ...). Contradictions trigger a restart with a new
   seed offset.

### The continent gradient

Raw WFC produces homogeneous noise — locally consistent, globally shapeless.
The trick that turns it into *geography* is biasing the collapse weights by
position: ocean weight decays as `(1-t)^5` moving east, mountain weight grows
as `t^5`, and plains/forest/towns peak mid-continent. Constraint propagation
then forces coherent coastlines, foothills, and river valleys at every
boundary the gradient creates.

## Usage

```bash
python3 wfc.py                    # 60x28 map, random seed
python3 wfc.py --seed 7           # reproducible
python3 wfc.py -w 100 -H 40      # bigger world
python3 wfc.py --animate          # watch the wave collapse cell by cell
```

`--animate` is the fun one: you can watch superposed cells (shaded blocks)
resolve into terrain as constraints ripple across the map.

## Files

- `wfc.py` — the whole thing: tile set, adjacency rules, bitmask wave,
  entropy selection, propagation queue, ANSI renderer, CLI.
