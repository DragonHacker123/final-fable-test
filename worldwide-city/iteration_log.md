# Iteration log — how Meridian got to version 6

Five substantive iterations (v1 → v6). Format per iteration: the flaw identified in the
previous version and why it matters, the fix, and the trade-off the fix introduces —
because every fix has one.

---

## v1 — the starting point (for the record)

A monumental radial city: one grand civic centre, ring boulevards, and residential
**towers-in-a-park** superblocks (25–40 storeys in open lawns) to maximise density and
green space simultaneously. Single consolidated emergency HQ campus. Food from
high-tech vertical farm towers integrated into the skyline. Governance: an elected
technocratic council with broad powers, assuming high civic participation.

It looked spectacular. Most of it was wrong.

---

## Iteration 1 → v2: the urban form was a proven failure

**Flaw identified (and why it matters):** towers-in-a-park plus a single monumental
centre is the most thoroughly *tested and failed* urban model of the 20th century.
The parkland between towers is space nobody owns and nobody watches — Oscar Newman's
defensible-space studies and the demolition arc from Pruitt-Igoe (1972) to the European
estate demolitions of the 1990s–2010s document the mechanism: no natural surveillance,
no active ground floors, crime and disorder concentrate, the buildings themselves
become stigma. Monocentricity compounds it: every commute, every service trip, and
every emergency crossing converges on one centre, so congestion and vulnerability
concentrate at exactly one point. This isn't an aesthetic quibble; it undermines the
crime, commute, and resilience requirements simultaneously.

**Fix:** replace the model wholesale with **polycentric hexagonal districts of
perimeter blocks** — 6–8 storey courtyard fabric on a fine street grid (Barcelona /
Vienna / Paris typology), seven district centres instead of one, density held by
coverage rather than height. Eyes on every street, a quiet courtyard side for every
dwelling, and no single point of urban failure.

**Trade-off introduced:** peak density drops. Towers can exceed perimeter blocks in
purely arithmetic residents-per-hectare, and the skyline — with its real symbolic and
tourism value — is largely given up. Land consumed per resident rises ~20–30%, which
later tightens the self-sufficiency land budget (and collides with iteration 3).
Accepted: the template optimises for retention and safety, not for a postcard.

---

## Iteration 2 → v3: emergency response was asserted, not computed

**Flaw identified (and why it matters):** v2 kept consolidated emergency services —
three large "campus" stations, justified by economies of scale — and *asserted* they'd
be fast because the city is compact. Writing `response_model.py` (100 m street-grid
BFS, 75 s turnout, 36 km/h emergency travel speed) falsified the assertion:

| Config | Stations | Mean | p90 | Max |
|---|---|---|---|---|
| A — 3 consolidated campuses (v2) | 3 | 5.3 min | **8.1 min** | 11.1 min |
| B — 7 district stations | 7 | 3.5 min | 4.4 min | 5.1 min |
| C — micro-station lattice | 33 | 2.3 min | **2.8 min** | 3.9 min |
| C with 25% of stations destroyed | 24 | 2.6 min | 3.6 min | 4.9 min |

Config A fails the NFPA 1710 benchmark (first engine in 5:20 at p90) by nearly three
minutes. In cardiac arrest terms — survival falls roughly 7–10% per minute without
CPR/defibrillation — the difference between A and C at the 90th percentile is most of a
life. Worse, consolidation concentrates seismic risk: lose one campus in the quake the
city is designed for and a third of the city's response capacity is gone at the moment
of maximum demand.

**Fix:** a **33-station micro-lattice** (~1.4 km triangular spacing), each station a
small base-isolated, power-islanded post with one pumper, one ambulance, and a
cross-trained fire/EMS/community-police crew; 4 hospitals arranged so p90 transport is
6.5 min. The degraded-mode row is the decisive argument: the lattice *with a quarter of
its stations rubble* still beats the intact 7-station design.

**Trade-off introduced:** cost and staffing. Thirty-three small stations need roughly
2× the per-capita staffing of three campuses, lose specialist economies of scale
(heavy rescue, hazmat stay centralised at 3 of the 33), and cross-training crews is a
permanent training burden. This is the most expensive single line in the city's service
budget and is named as such in the masterplan.

---

## Iteration 3 → v4: the self-sufficiency arithmetic did not close

**Flaw identified (and why it matters):** v3 fed the city from vertical farm towers and
claimed autarky within the 54.5 km² urban footprint. Running the numbers destroyed
both claims. Calories: 1M people ≈ 840 billion kcal/yr; staple crops grown under
electric light cost so much energy that indoor wheat is a luxury good (published
analyses of plant-factory wheat put the electricity cost of a single loaf in absurd
territory) — the *entire* city energy budget could not grow the city's bread, let alone
its protein. Land: even with heroic intensity, a real diet needs ~800–1,000 m² of
productive land per person → ~1,000 km² for 1M people, i.e. ~18× the urban footprint.
"The towers will feed us" was not a plan; it was set-dressing. Since self-sufficiency
is a hard requirement, this was a foundational failure, not a detail.

**Fix:** redefine the self-sufficient unit as **city-region**: the 54.5 km² core plus a
~20 km-radius, ~1,250 km² stewarded hinterland — food belt (staples, protein,
horticulture), forestry belt (structural timber for the CLT fabric), energy fields
(agrivoltaics, wind), water catchment, and wild land. Vertical farming is demoted to
what it demonstrably does well: leafy greens and seedlings (~2% of calories, most of
the salad). Diet policy becomes structural: plant-forward, because a beef-heavy diet
needs 2–3× the land and does not fit. Nutrient loops close via biosolids return and
phosphorus recovery; 18-month grain buffers per district.

**Trade-off introduced:** the elegant compact city becomes a **1,250 km² territorial
claim**, which multiplies siting difficulty (the template now needs contiguous
farmland, not just a 55 km² plot) and creates a governance seam between urban
residents and hinterland workers that L18 and the Job Guarantee must actively manage.
And honesty costs: the "no imports" claim now carries two published asterisks —
construction-phase imports, and a diet without imported luxuries. The masterplan
states both rather than hiding them.

---

## Iteration 4 → v5: the design assumed ideal humans

**Flaw identified (and why it matters):** v4's institutions quietly assumed a
population of engaged, honest citizens: broad-powers council + "high civic
participation", market housing with a light land tax, inspectors assumed honest,
police assumed benign. Reality: sustained voluntary participation in local governance
runs 10–20% and skews old, propertied, and organised — so "participatory" governance
is capture-prone by construction; unpriced-enough land in a desirable fixed footprint
gets financialised (every superstar city post-1990); and the historical failure mode
of building codes is the inspection desk, not the drawing board (Haiti 2010 vs Chile
2010 is a ~400:1 death-toll ratio between two similar-magnitude quakes, largely an
enforcement story). A city designed for the residents you wish you had will be
operated by the residents you actually get — including the officials.

**Fix (a bundle, because the flaw was systemic):**
- **Land**: all land into the City Land Trust; 49-year auctioned leaseholds, 5-yearly
  rent reassessment — speculation loses its object; land rent funds Universal Basics.
- **Housing**: 35–40% non-market stock *per district* with income-mix quotas — no
  poverty concentration, no gated wealth, enforced at zoning level rather than hoped for.
- **Governance against capture**: a paid, sortition-based **Citizens' Audit Jury** (99
  residents, one year) with veto-and-remand over budgets, lease rules, and police
  powers; term limits; sunset-by-default regulation; inspectors city-employed,
  randomly rotated, personally liable.
- **Labour**: Job Guarantee at a living wage as buffer stock — it staffs the hinterland
  and removes survival crime and idle-youth crime at the root.
- **Flawed-human services**: mediation before litigation, walk-in mental-health
  clinics, restorative-first justice with custody reserved for danger, kōban-style
  embedded neighbourhood policing with an armed tier held separate.

**Trade-off introduced:** several, all named. Leasehold land closes the
home-as-wealth-escalator channel — households build savings, not property fortunes,
and some people will reject that bargain outright. The Jury is slower than executive
action and can be swayed by presentation (hence veto-and-remand, not rule). The
non-market housing share plus base-isolated lifelines creates the **founding
endowment problem** — tens of billions before rent revenue flows — promoted in the
masterplan to open-problem #1. And the quota-and-audit machinery is honestly
paternalistic; the design accepts constrained choice as the price of never zoning a
ghetto into existence.

---

## Iteration 5 → v6: one uniform hazard spec cannot serve a worldwide template

**Flaw identified (and why it matters):** v5 carried a single, uniform
disaster-resistance specification — effectively "build everything to survive
everything, everywhere." That fails in both directions. It's wasteful where hazards
are absent: base-isolating a whole city on the Canadian Shield, or buying 250 km/h
glazing in a region with no cyclones, burns the founding endowment for nothing. And
it's *insufficient* where hazards are specific: a generic spec put ordinary housing in
the coastal band with no vertical evacuation — in a near-field tsunami (warning time
possibly < 15 minutes, per Tōhoku 2011), a dense district cannot evacuate horizontally,
and a wall alone is exactly the single-layer defence that failed in 2011. A "worldwide"
template with one hazard posture is either a fiction or a bankruptcy.

**Fix:** the template becomes **parameterised** — a base blueprint plus mandatory
regional hazard modules selected by site assessment:
- *Universal gate*: microzonation before siting; liquefaction/fault/floodway/slide land
  is permanently green (Christchurch/Mexico City lesson).
- *Seismic module*: base isolation for lifelines, ductile CLT/RC fabric with
  capacity design, soft-storey ban, no gas grid.
- *Coastal module*: four-layer defence — living shoreline, +15 m landscape berm,
  sacrificial non-residential waterfront band, vertical-refuge towers within a
  10-minute walk of every point in the band.
- *Cyclonic module*: Miami-Dade envelope standards, damped/chamfered towers,
  underground distribution.
- *Continental module*: the cheap baseline where none of the above trigger.
The template also now **publishes rejection criteria** — hot inland-arid sites fail the
water audit; some subduction coasts force a port-vs-safety compromise the module only
mitigates. A template that won't say "not here" isn't an engineering document.

**Trade-off introduced:** "one blueprint" is now a **family of blueprints**. Every
module multiplies the engineering, supply-chain, and code-enforcement variants that
replication has to quality-control — the thing that makes templates cheap (sameness) is
partially spent, and instances can no longer straight-swap components or crews with an
instance on a different module set. Governance must also police module *selection*
honestly (the incentive to skip an expensive module a lax assessment "didn't trigger"
is obvious), which is why the microzonation gate and inspector-liability law sit at
charter level, outside local discretion.

---

## Where it stands

v6 is the version documented in `masterplan.md` and visualised in `index.html`. It is
not finished — masterplan §10 lists eight open problems, led by the founding-endowment
financing gap, and the honest summary is: the physics and layout close; the money and
the culture are not fully solved. A further iteration 6 would attack the endowment
problem (phased single-district founding at ~143k people is the current best guess,
since one district is designed to be independently viable).
