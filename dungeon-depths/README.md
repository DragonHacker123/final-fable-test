# Dungeon Depths

A complete roguelike dungeon crawler in **one self-contained HTML file** — no
frameworks, no assets, no network requests. Open `index.html` in any browser
and press Enter.

Five floors down, the Ember of the Deep smolders in a dead king's fist.
Take it. Survive what happens next.

## How to play

| Key | Action |
|-----|--------|
| `WASD` / arrow keys | move — walk into a monster to attack it |
| `Space` / `.` | wait a turn |
| `1` / `Q` | quaff a healing potion |
| `M` | toggle sound |
| `R` | restart |

Reach the stairs (`>`) to descend. On depth 5, the Hollow King guards the
Ember (`♦`). Taking it starts a **45-turn dungeon collapse** — sprint back to
the portal that tears open at your entry point before the roof comes down.

## What's inside

- **Procedural levels** — up to 13 non-overlapping rooms joined by
  L-corridors plus extra loop connections, different every run, five themed
  depths of escalating difficulty.
- **Field of view** — recursive shadowcasting over 8 octants, with a
  persistent "seen" layer rendered as dim fog and a torch-radius light
  falloff that flickers.
- **Six monster AIs** driven by a BFS distance map flowing from the player
  (Dijkstra-lite): pack rats that only fight in groups and flank for bonus
  damage, ghoul chasers, skeleton archers with Bresenham line-of-sight who
  keep their distance, cultists that flee to lick their wounds and come back,
  wraiths that phase straight through walls, and a two-speed boss.
- **Loot** — potions, gold, five tiers of weapons and armor (worse gear gets
  scrapped for gold automatically), an XP/level system.
- **Juice** — screen shake, hit-flash, particle bursts, floating damage
  numbers, blood decals, drifting torch embers, a vignette, and a tiny
  WebAudio synth (every sound effect is an oscillator envelope — zero audio
  files).
- **Three screens** — animated title, epitaph-bearing death screen, and a
  slow-fade victory screen with stats.

## Architecture notes

The game is strictly turn-based under a real-time renderer: input mutates
game state and calls `endTurn()`, which advances every monster, recomputes
FOV and the distance map, then the `requestAnimationFrame` loop just draws
whatever the state is (plus particles/shake/flash, which are cosmetic and
frame-rate-based).

Monster pathing never runs per-monster searches: one BFS flood fill from the
player per turn gives every monster a downhill gradient to chase (or climb,
to flee) in O(1) per step.

Verified headlessly with a DOM-stub harness: 120,000 random-walk turns
without a crash, plus scripted checks of the artifact → collapse → portal
win path and the collapse-timer death path.
