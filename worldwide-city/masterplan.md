# MERIDIAN — a replicable blueprint for a self-sufficient city

*Design document, version 6 (final). See [`iteration_log.md`](iteration_log.md) for how it got here,
[`response_model.py`](response_model.py) for the emergency-response calculations, and
[`index.html`](index.html) for the interactive 3D visualisation.*

Meridian is not a city; it is a **template for cities** — a parameterised kit meant to be
instantiated anywhere on Earth with local hazard, climate, and culture modules swapped in.
One million residents per instance, on a compact 54.5 km² urban core surrounded by a
~1,250 km² productive hinterland that closes the food, water, energy, and materials loops.

This document is honest about what it doesn't solve. Section 10 lists the open problems.

---

## 1. Form: the hex flower

The urban core is **seven hexagonal districts** — one core, six petals — each 3.0 km
flat-to-flat (~7.8 km², ~143,000 people), tangent to its neighbours. Total: 54.5 km²,
1,000,000 people, **~18,300/km² gross density** — denser than Barcelona citywide
(~16,000/km²), just under central Paris (~20,000/km²), and achieved without towers.

Why hexagons, and why seven:

- **Polycentric by construction.** Every district has its own centre with a transit hub,
  market hall, clinic, and civic hall. No single point of failure, no single point of
  congestion. Trips distribute across seven centres instead of converging on one.
- **Every district is edge.** No district is more than one district away from open land —
  critical for evacuation, food logistics, and psychological access to landscape.
- **Replication is literal.** A district is the unit of construction phasing: an instance
  is viable at one district (~143k people) and grows petal by petal. It is also the unit
  of governance and of emergency-services planning.

The dominant building type is the **perimeter block**: 6–8 storey buildings enclosing a
quiet courtyard, on a ~130 m grid with narrow (20 m) streets. This is the Barcelona
Eixample / Vienna Gründerzeit / Paris Haussmann typology — the only form that has
repeatedly delivered >30,000/km² net residential density that people *choose* and pay
premiums to live in a century later. Each district centre adds a small cluster of
12–20 storey buildings within 400 m of the transit hub; the core district holds the
university, main hospital campus, and inter-city rail station.

Between the petals sit six **green wedges** — parks, sports grounds, allotments, and
stormwater basins — so every home is near landscape without lowering density where
people actually live. The wedges double as firebreaks, floodways, and post-disaster
staging areas.

## 2. Structural resilience

The template is parameterised by a mandatory **hazard module** chosen at siting. Four are
specified: *seismic*, *coastal* (tsunami/storm surge), *cyclonic*, and *continental*
(the low-hazard baseline). A site takes every module its hazard assessment triggers.
Before any module applies, one universal gate:

**Microzonation first.** No construction until a geotechnical map at ≤200 m resolution
identifies liquefiable soils, soft basins, fault traces, and landslide slopes. Housing is
forbidden on them; they become the green wedges. Christchurch (2011) demonstrated the
cost of building suburbs on liquefiable ground; Mexico City (1985, 2017) the cost of
soft lake-bed amplification. Geology, not road access, dictates where the hexagons land.

### Seismic module (design basis: MCE for the site, e.g. M8+ subduction or M7 crustal)

- **Base isolation for everything that must work the day after**: hospitals, the 33
  emergency micro-stations, water and energy control nodes, and the district civic halls
  (which double as shelters). Friction-pendulum or lead-rubber bearings decouple the
  structure from ground motion, cutting accelerations 3–5×. Precedents: Japan operates
  thousands of isolated buildings and hospitals that rode out Tōhoku 2011 functional;
  Istanbul's Sabiha Gökçen terminal (the world's largest isolated building at completion);
  USC University Hospital, undamaged in Northridge 1994.
- **Ductile capacity design for ordinary fabric.** The 6–8 storey blocks are engineered
  mass timber (CLT) or reinforced concrete with strong-column/weak-beam detailing, so
  yielding happens where it's planned. Chile's strict enforcement of this held the death
  toll of the 2010 M8.8 Maule quake to ~500 — versus >200,000 in Haiti's M7.0 weeks
  earlier. Codes save lives only when enforced; see §7 for the enforcement law.
  Mass timber's seismic case is now empirical: the 10-storey NHERI TallWood building
  survived simulated M6.7 and M7.7 records on UC San Diego's shake table (2023) with
  its rocking-wall system essentially undamaged.
- **Soft storeys are banned outright** (the dominant collapse mode in Kobe 1995 and
  Izmit 1999). Ground-floor retail gets the same lateral system as the floors above.
- Gas grids are omitted entirely (the city is all-electric), removing the post-quake
  fire-ignition source that destroyed much of Kobe.

### Coastal module (design basis: 1-in-1000-year tsunami / surge for the site)

Japan's post-2011 doctrine, adopted wholesale: **layered defence, not a single wall**,
because Tōhoku overtopped walls designed for the 1-in-100 event.

- Layer 1: living shoreline — reefs, mangroves or dune fields where climate allows —
  to shave energy off the wave.
- Layer 2: a continuous **landscape berm at +15 m** carrying the coastal linear park;
  a dike that reads as topography (precedent: Sendai's reconstructed coast, the
  Netherlands' "dike-in-dune" at Katwijk).
- Layer 3: the waterfront band (first ~400 m) is **sacrificial by design** — port,
  parks, markets, workshops; no ground-floor housing. Buildings there are engineered
  for scour and impact, with habitable floors above +15 m.
- Layer 4: **vertical evacuation towers within a 10-minute walk of every point** in the
  band — hardened, ramped structures precedented by Japan's tsunami towers and the
  Ocosta Elementary School gym in Washington State (the first US purpose-built vertical
  refuge). Warning time from a near-field subduction source can be under 15 minutes;
  horizontal evacuation of a dense district in that window is a fantasy, so refuge
  must be vertical and everywhere.

### Cyclonic module (design basis: 250 km/h 3-second gust, Saffir-Simpson 5)

- The perimeter-block fabric is inherently good in wind: 6–8 storey continuous street
  walls give no isolated towers for vortex shedding to punish. The few 12–20 storey
  buildings get chamfered or rounded corners and, where slenderness demands, tuned mass
  dampers (Taipei 101's 660 t sphere is the canonical precedent).
- Envelope over structure: most cyclone damage starts when the envelope fails. Glazing
  and roofing to Miami-Dade large-missile impact standards; roof geometries hipped or
  parapeted; no lightweight overhangs.
- The entire distribution grid is underground; the tram catenary is the accepted
  sacrificial element (buses substitute during repair).

### All modules

Critical lifelines are **N+1 per district**: each district can be islanded with its own
substation, water storage (72 h), and micro-station coverage (§4). The green wedges are
sized as staging/relief areas. Every building code in §7 carries the *enforcement* law,
because the historical record is unambiguous: hazard engineering fails at the inspection
desk, not the drawing board.

## 3. Self-sufficiency: closing the loops

Assumption taken literally: **nothing can be imported**. Meridian treats autarky as a
*resilience floor* — the city trades happily in normal times, but every essential loop
must close within the city-region. The urban core cannot do this alone; the honest unit
of self-sufficiency is the core **plus a ~20 km-radius hinterland (~1,250 km²)** under
city stewardship. (Iteration 3 exists because the arithmetic of "the towers will feed
us" does not survive contact with a calculator — see the log.)

### Food (~2,300 kcal/person/day, 1M people)

- **Staples come from fields, not buildings.** Growing grain indoors costs orders of
  magnitude more energy than the sun provides for free; an indoor loaf of wheat bread
  carries an electricity bill that makes it a luxury good. Vertical farming is reserved
  for what it is actually good at: leafy greens, herbs, and seedlings — high value, low
  calorie, water-efficient (~95% less than field), fresh year-round. ~200 ha of rooftop
  greenhouses and farm towers supply most of the city's leafy vegetables and ~2% of its
  calories. The other 98% comes from the hinterland.
- **Land budget:** a plant-forward diet (meat as garnish; legumes, grains, tubers,
  dairy/eggs, aquaculture) needs roughly 800–1,000 m²/person of productive land under
  intensive mixed farming — call it 1,000 km² for 1M people, which is what the
  hinterland annulus provides. A US-style beef-heavy diet needs 2–3× that and simply
  does not fit; diet policy is therefore load-bearing infrastructure, not lifestyle
  advice. Precedents for the intensity: Dutch horticulture, Cuban organopónicos
  (urban agriculture under a genuine import cut-off, post-1991), East Asian rice-fish
  polyculture.
- **Nutrient loop:** all organic waste and treated biosolids return to the fields;
  phosphorus is recovered from wastewater (struvite reactors, as at Amsterdam West).
  A city that exports its sewage to the sea imports its fertiliser forever.
- **Buffer:** 18 months of staple grain storage per district, rotated through the
  market halls (the Swiss federal grain reserve as precedent).

### Water (~130 L/person/day municipal + irrigation)

- Municipal demand ~47 Mm³/yr. Sources stack: rainfall capture on every roof (mandated,
  §7), hinterland reservoirs in the stormwater wedges, and **closed-loop reuse of ~40%
  of wastewater** to potable standard — Singapore's NEWater and Windhoek's 50 years of
  direct potable reuse prove the engineering and, harder, the public-acceptance path.
- Irrigation is the real budget (10× municipal in a dry year) and is served by rainfed
  farming first, drip systems, and treated-effluent reuse.
- Coastal-arid instances add solar-powered desalination; **hot inland-arid sites fail
  the water audit and should not be built** — the template refuses some geographies
  (§10).

### Energy (all-electric city, ~5.5 MWh/person/yr → ~630 MW average, ~1.5 GW peak)

- **Generation:** rooftop PV across the urban core (~1 GWp on the perimeter blocks'
  large flat roofs), utility PV on ~25 km² of hinterland (co-located with grazing and
  horticulture — agrivoltaics), wind where the resource exists, and a firm block sized
  by geography: geothermal where available, otherwise two small modular reactors or a
  biomass CHP plant fed by the hinterland forestry belt. The firm block is deliberately
  boring, proven technology; a self-sufficient city cannot bet its winters on a
  technology that doesn't exist yet.
- **Storage:** ~4 GWh of batteries for diurnal shifting, plus **seasonal thermal
  storage** for heat: sand/water pit stores of the kind operating in Vantaa and
  Meridian's district-heating loops (Drake Landing, Canada, has covered >90% of a
  community's winter heat from summer sun since 2007).
- **Demand is the secret weapon:** compact mid-rise fabric, district heating/cooling,
  heat pumps, and a modal split where cars are rare (§5) put per-capita demand at
  roughly half of a sprawled equivalent. The cheapest megawatt is the one the urban
  form never asks for.

### Materials

- **Steady-state, not construction-phase.** Honesty first: the *initial build* of any
  instance imports cement, steel, and glass like every city ever built. Self-sufficiency
  is the steady state the city converges on: a ~300 km² managed forestry belt yields
  150–240k m³ of structural timber per year (maintenance + slow growth for the CLT
  fabric); steel circulates through a scrap-fed electric-arc mini-mill; glass and
  ceramics from regional sand and clay; cement use is minimised by the timber-first
  code and met by one small electrified kiln with local limestone where geology allows.
- **Demolition is harvest:** buildings are designed for disassembly (bolted CLT
  connections), and the §7 code treats demolition waste as city property routed through
  materials-recovery yards.

## 4. Emergency services — calculated, not asserted

The layout question was settled by computation, not intuition; `response_model.py`
models the street network as a 100 m grid (Manhattan/BFS distances, which track real
street-network detour factors), assumes NFPA-style 75 s turnout and a 36 km/h average
emergency speed, and evaluates station strategies against the whole urban footprint:

| Config | Stations | Mean | Median | p90 | Max |
|---|---|---|---|---|---|
| A — 3 consolidated campuses | 3 | 5.3 min | 5.1 | 8.1 | 11.1 |
| B — 7 district stations | 7 | 3.5 min | 3.6 | 4.4 | 5.1 |
| **C — micro-station lattice (adopted)** | **33** | **2.3 min** | **2.4** | **2.8** | **3.9** |
| C after quake, 25% stations lost | 24 | 2.6 min | 2.6 | 3.6 | 4.9 |
| Hospital transport (4 hospitals, travel only) | 4 | 3.6 min | 3.2 | 6.5 | 9.7 |

The NFPA 1710 benchmark — first engine on scene in 5:20 for 90% of calls — is *failed*
by the consolidated option (p90 = 8.1 min) and met by the adopted lattice with a 2.5-minute
margin (p90 = 2.8 min). More importantly for a hazard-exposed city: **with a quarter of
all stations destroyed, the lattice still outperforms the intact 7-station design.**
Redundancy, not size, is what survives an earthquake.

Design consequences:

- **33 resilience micro-stations** on a ~1.4 km triangular lattice: each houses one
  pumper, one ambulance, and a cross-trained fire/EMS/community-police crew of 6–8 on
  shift. Cross-training is what makes small stations staffable (precedent: the fire
  service *is* the ambulance service across much of Germany and Japan).
- Stations are base-isolated, solar+battery islanded, and double as neighbourhood civic
  rooms in peacetime — the crews are *known* to their 30,000 residents, which §6 relies on.
- **4 hospitals** (core + 3 alternating petals) so no dwelling is >10 min transport even
  at the p99 tail; each pair can absorb the other's load (N+1 again).
- The 20 m street grid gives emergency vehicles two independent approach paths to every
  block; the green wedges take helicopter medevac and mass-casualty staging.

The cost of this choice is real and stated in the iteration log: ~33 small stations cost
roughly twice the staffing of 7 big ones per capita. Meridian pays it knowingly — it is
the single largest line item bought with the land-rent dividend (§6) after transit.

## 5. Density with contentment — defined, measured, enforced

"Content" is defined as a **measurable standard-of-living floor**, written into the
charter (§7) and audited annually. A resident is deemed adequately served when all of
the following hold:

| Dimension | Floor (charter minimum) | Precedent / basis |
|---|---|---|
| Dwelling space | ≥ 35 m² net per person; ≥ 2 rooms per household | Vienna social housing norms |
| Daylight | ≥ 2 h direct sun in main room at equinox | Chinese & Nordic daylight codes |
| Green access | "3–30–300": 3 trees visible from home, 30% canopy per neighbourhood, park ≥ 0.5 ha within 300 m | Konijnendijk rule, ratified by several EU cities |
| Noise | ≤ 55 dB(A) day / 45 night at every façade; every dwelling has a quiet side | WHO Environmental Noise Guidelines |
| Daily needs | ≥ 90% of residents reach school, clinic, groceries, park, transit within a 15-minute walk | Paris "ville du quart d'heure" |
| Commute | Median door-to-door ≤ 22 min; p90 ≤ 35 min | Marchetti's constant; kept by polycentricity |
| Climate comfort | Continuous shaded/arcaded routes; summer surface temps managed by canopy + water | Sevilla, Singapore GreenUP |

The perimeter block is what lets density and these floors coexist: street-side liveliness
and courtyard-side silence in the same building, which a tower-in-a-park cannot offer
(every façade equally exposed) and a townhouse suburb cannot densify. The quiet-side rule
is the single most anti-“housed but miserable” regulation in the charter.

The floors are audited by the annual **Resident Wellbeing Survey** (participation
incentivised, results public by block) plus churn tracking: if a neighbourhood's
out-migration exceeds the city mean by 50% for two years, a design review is triggered
automatically. Contentment is treated as an SLO with an error budget, not a slogan.

**The trade-off named:** the 35 m² floor and daylight rules cap achievable density.
Meridian deliberately leaves ~30–40% of theoretical maximum density on the table
(Kowloon Walled City proved humans *can* be stored at 1.2M/km²) because the goal is
retention, not warehousing. 18,300/km² is the chosen point on that curve.

## 6. Economy: market Georgism with a universal floor

Neither pure model survives its own failure mode. Central planning fails on the
information problem — no bureau can price a million people's shifting needs (the
socialist calculation debate was settled empirically by 1989). Laissez-faire fails on
land: in a fixed, desirable footprint, unpriced land rent is captured by whoever got
there first, and the density-contentment bargain of §5 is bid away into asset prices —
see every superstar city since 1990. Meridian's hybrid targets both failure modes:

1. **All land is held by the City Land Trust.** Users hold 49-year renewable leaseholds,
   auctioned openly, with rents reassessed every 5 years to current land value. This is
   Singapore's land regime crossed with Georgist tax logic: you keep 100% of what you
   build and earn; the community keeps the value of *location*, which the community
   created. Land rent is the city's primary revenue — there is no income or sales tax
   at city level.
2. **Markets allocate goods, services, and labour.** Private firms, worker co-ops
   (favoured in city procurement, precedent Mondragón/Emilia-Romagna), and sole traders
   compete freely. Prices are not controlled. Natural monopolies — grid, water, transit,
   fibre — are city-owned utilities at cost.
3. **Universal Basics, funded by land rent:** healthcare, education, childcare, transit,
   connectivity, and the §5 housing floor are unconditional. Vienna is the proof that
   a city can be a landlord at scale and remain one of Earth's most liveable cities for
   a century.
4. **Housing: ~38% of the stock is non-market** (city-built, cost-rent, allocated by
   waitlist with income mix quotas per block — no poverty towers, no gated districts),
   ~50% market leasehold, ~12% limited-equity co-ops. Speculative vacancy is punished
   by the lease terms themselves (rent accrues whether occupied or not).
5. **Labour: a Job Guarantee as buffer stock.** Anyone can work at a living wage on the
   city's standing needs — farm belt, forestry, care, maintenance, disaster corps. It
   sets a de-facto wage floor, staffs exactly the unglamorous work autarky requires
   (the farm labour question is where most self-sufficiency fantasies die), and expands
   counter-cyclically. Private employers must beat the guarantee's wage+conditions,
   which is the point.

**Named trade-offs:** leasehold land weakens the main wealth-building collateral channel
households have historically used (the mortgage escalator) — Meridian accepts a
lower-asset, higher-service equilibrium, and this will not suit everyone. The Job
Guarantee compresses low-end wage differentials and irritates labour-intensive private
employers. The 38% non-market stock requires a **founding endowment measured in tens of
billions** — replication's hardest constraint, stated plainly in §10.

## 7. The Charter — laws and policies (concise form)

*The full legal code is beyond scope; these are the charter-level laws every instance
adopts. All regulation below charter level sunsets after 10 years unless renewed (L24).*

**Economy**
- L1. All land is held in perpetuity by the City Land Trust; use rights are auctioned as
  49-year renewable leaseholds, rent reassessed 5-yearly to market land value.
- L2. Land rent funds Universal Basics: healthcare, education, childcare, transit,
  connectivity, and the housing floor. No municipal income or sales tax.
- L3. Grid, water, transit, and fibre are city-owned, operated at cost, with public
  real-time performance dashboards.
- L4. Any resident may invoke the Job Guarantee: city work at the living wage, defined
  annually by the Wage Board from the §5 basket.
- L5. Essential stocks (18 months staple grain, 72 h water per district, strategic
  materials) are audited quarterly and published.

**Housing**
- L6. The §5 floors (space, daylight, noise, green access) are enforceable individual
  rights; a dwelling failing them generates automatic rent abatement until cured.
- L7. Non-market housing shall be 35–40% of stock in every district — measured per
  district, so no district becomes a ghetto of either poverty or wealth.
- L8. Every block mixes at least three dwelling sizes; ground floors on designated
  streets must be active uses (retail, workshops, civic), never blank walls
  or parking.
- L9. Vacancy incurs full lease rent; short-term letting of entire dwellings is capped
  at 60 nights/year.

**Safety & resilience**
- L10. Construction requires licensed independent inspection at foundation, frame, and
  completion; inspectors are city-employed, rotated randomly between sites, and
  personally liable for sign-offs (the Chile/Haiti lesson codified).
- L11. Soft-storey configurations are prohibited; critical facilities (hospitals,
  micro-stations, civic halls, lifeline nodes) must be base-isolated or performance-
  equivalent and islandable for 72 h.
- L12. No habitable construction on mapped liquefaction, fault-trace, floodway, or
  slide zones; those lands are permanently zoned green.
- L13. Every resident shall be within 10 minutes' walk of hardened refuge (vertical
  evacuation in coastal band, civic halls elsewhere); refuge capacity is audited yearly.
- L14. Each district must independently hold: 72 h water, 7 d food distribution
  capacity, an islandable power node, and ≥ 4 micro-stations.

**Environment**
- L15. The city operates on current energy income: no fossil combustion within the
  city-region except declared emergencies; the firm-power block must be non-fossil.
- L16. All organic waste and biosolids return to the food system; phosphorus recovery
  is mandatory at the wastewater works.
- L17. Buildings are designed for disassembly; demolition material is city property
  routed through recovery yards.
- L18. The hinterland is zoned in perpetuity: food, forestry, energy, and wild belts;
  urban expansion happens by founding a new instance, not by eating the farm belt.
- L19. Potable reuse, rooftop catchment, and metered pricing above the free basic
  allowance apply city-wide.

**Civic participation & governance**
- L20. The Council (one member per district + six at-large, 4-year terms, two-term
  lifetime limit) legislates; the Executive administers.
- L21. A **Citizens' Audit Jury** — 99 residents drawn by lot for one year, paid, with
  professional staff — may remand any law or budget line for public revision, and its
  approval is required for charter amendments, lease-auction rules, and police-powers
  changes. (Sortition as anti-capture: the jury cannot be lobbied in advance because
  it cannot be predicted.)
- L22. All non-personal city data — budgets, contracts, sensor networks, survey
  results — is public by default; personal data is private by default and may not be
  sold. Surveillance requires Audit Jury renewal every 24 months (see §8 trade-off).
- L23. Voting is by ranked ballot; participation is maximised by default enrolment,
  mobile/advance voting, and a civic holiday — but is not compulsory.
- L24. Every regulation below charter level expires after 10 years unless renewed
  ("sunset by default").
- L25. The Charter Court, whose judges are appointed by the Audit Jury from a
  professional list, adjudicates charter conflicts; its proceedings are public.

## 8. Designing for flawed humans

Meridian assumes people are self-interested, occasionally malicious, frequently
irrational, and that **institutions must fail safe against their own operators.**

**Crime.** Target, stated honestly: **homicide < 0.5/100k/yr, overall victimisation
< 50% of host-nation baseline — never zero.** Zero is not a target because passion,
pathology, and organised predation survive any urban form. The levers, in order of
expected effect:

1. *Inequality compression* (§6): the Gini-violence gradient is one of criminology's
   most robust cross-national findings. Universal Basics remove survival crime;
   the Job Guarantee removes the idle-young-men problem that no police force has
   ever out-patrolled.
2. *Urban form as guardianship*: perimeter blocks put "eyes on the street"
   (Jacobs) on every street — active ground floors, no leftover spaces, courtyards
   with clear ownership (Newman's defensible space — the inverse of the
   towers-in-park estates whose failure iteration 1 corrected). Lighting, sight
   lines, and maintenance follow CPTED practice; broken things are fixed in 72 h
   because disorder signals compound.
3. *Social integration by quota* (L7, L8): no district of concentrated poverty ever
   forms, so no district is written off — the single strongest predictor of
   neighbourhood violence is removed at zoning level.
4. *Policing*: neighbourhood officers embedded in the micro-stations (§4), on foot,
   known by name — the Japanese kōban model, which pairs with the highest
   clearance-by-cooperation rates on record. Routine patrol is unarmed; a small
   armed-response tier exists per district (UK/NZ split). Every use of force is
   reviewed by the Audit Jury's policing panel.
5. *Restorative justice first* for non-violent offences — victim-offender mediation
   with teeth (restitution enforced), custody reserved for danger, not poverty.
   Norway's recidivism (~20% at 2 years vs ~60% in punitive systems) is the
   benchmark. Ports and markets get a dedicated organised-crime unit, because
   trade nodes attract predation regardless of local virtue.

**Conflict resolution.** Free, fast mediation is a Universal Basic; civil suits require
a mediation certificate first (precedent: mandatory mediation tiers in Singapore and
Italy). District ombudsmen handle resident-vs-city disputes with public dockets.

**Mental health.** One walk-in, no-referral clinic per district; crisis response is a
mental-health team, not an armed one (Trieste's community model; CAHOOTS in Eugene,
Oregon). Loneliness is treated as infrastructure failure: every block lease includes a
funded common room, and the market halls, baths, and libraries are deliberately
over-programmed as third places. Suicide means restriction is designed in (bridge and
platform barriers work; the evidence is strong and cheap).

**Governance against its operators.** Term limits (L20), sortition veto (L21), sunset
laws (L24), random rotation of inspectors (L10), radical budget transparency (L22),
and asset disclosure for every official. Assume every office will eventually be held
by someone who shouldn't hold it; limit the blast radius.

**Named trade-off:** the transparency-and-quota machinery is paternalistic. Income-mix
quotas constrain where people live; data-rich audits sit one bad amendment away from
surveillance overreach — which is why L22 makes surveillance powers expire by default
every 24 months and puts renewal in the Jury's hands, not the police's.

## 9. Movement (supporting system)

No point minimising commutes by assertion: the polycentric form does the work. ~70% of
residents work within their own or an adjacent district (jobs are distributed by the
leasehold zoning mix). The tram network is two nested loops plus six radials (every
district centre ≤ 2 stops from two other centres); headways ≤ 5 min. The 20 m streets
carry trams, bikes, and freight; private cars exist (car-share pools at district edges)
but get no through-routes and no free land — the mode share design point is
40% walk / 30% bike / 25% transit / 5% motor. Freight consolidates at the rail port and
moves by cargo tram overnight (precedent: Zurich's Cargo-Tram, Dresden's former
CarGoTram) with last-400 m e-cargo bikes.

## 10. What this design does not solve — read before replicating

1. **The founding endowment.** 38% non-market housing, base-isolated lifelines, and a
   full tram network before rent revenue flows means tens of billions up front. Vienna
   took a century; Singapore took an authoritarian land acquisition act. A replicable
   financing instrument is *not designed here* and is the template's largest open hole.
2. **Autarky is a floor with a construction-phase exception.** The initial build imports
   materials at global scale. A cynic may call the self-sufficiency claim "steady-state
   only"; the cynic is right, and the claim is made only for the steady state.
3. **Some geographies are refused.** Hot inland-arid sites fail the water audit;
   near-field subduction coasts with no high ground force a port-vs-safety choice the
   coastal module only mitigates. A template that claims to fit everywhere is lying;
   this one publishes its rejection criteria.
4. **Diet is constrained by physics.** No imports means no coffee, chocolate, or
   out-of-region luxuries, and a plant-forward diet is structural, not optional. In
   practice instances will trade for luxuries — the design guarantees survival, not
   cosmopolitan abundance, under blockade.
5. **The wellbeing floors are period-bound.** 35 m² and 2 h of sun encode this era's
   preferences; L24's sunset mechanism is the hedge, but a charter can still ossify.
6. **Sortition is not magic.** A 99-person jury can be swayed by presentation quality
   and staff framing; its power is a veto-and-remand, not rule, for exactly that reason
   — but capture risk is reduced, not eliminated.
7. **One million is an assumption.** The template's economics (hospital tiers, tram
   viability, mini-mill scale) are tuned to ~1M ± 300k. It does not scale down to a
   town or up to a megacity without re-derivation.
8. **Culture cannot be templated.** Everything above is the hardware. Whether an
   instance becomes somewhere people love is decided by things no masterplan
   controls — and pretending otherwise is how planned cities have failed before
   (Brasília's superquadras were also, on paper, complete).
