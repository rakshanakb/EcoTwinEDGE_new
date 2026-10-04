# EcoTwin-EDGE — Edge-AI Digital Twins for Climate-Zone-Aware Building Efficiency

## 1. The Problem, Precisely Stated

India's buildings consume ~33% of national electricity, and this is rising because of three compounding forces: rapid growth in commercial floor space, rising incomes driving AC penetration, and a warming climate increasing cooling-degree-days. 
The actual failure isn't "buildings use energy" — it's that the vast majority of India's building stock operates blind: no real-time visibility into where energy goes, equipment runs on fixed schedules rather than actual need, and facility managers make decisions on gut feel or monthly utility bills, not data. ECBC and BEE set a compliance bar, but compliance ≠ optimization — a building can be code-compliant on paper and still waste 20-30% of its energy through poor scheduling, oversized HVAC, and no feedback loop with occupants or the grid.

So the problem has four layers, and a winning solution needs to visibly address all four, not just one:
* **Visibility gap** — no real-time data
* **Control gap** — even where data exists, systems don't act on it intelligently
* **Occupant gap** — comfort and energy are treated as opposed, not linked
* **Grid gap** — buildings are passive consumers, not flexible, grid-responsive assets

## 2. What Already Exists (The Landscape)

1. **Traditional BMS (Building Management Systems) — e.g., Siemens Desigo, Honeywell, Schneider EcoStruxure Building**
   * **Pros:** Mature, reliable, industry-standard.
   * **Cons:** Expensive, wired sensor networks + licensed software. Retrofit-hostile (running new wiring through an existing occupied building is disruptive). Not intelligent — it's rule-based, not adaptive.

2. **Cloud-Based Occupancy/ML Smart-Thermostat Systems**
   * **Pros:** Cheaper and faster to install than a full BMS. Genuinely adaptive.
   * **Cons:** Cloud-dependent. In buildings with unreliable internet, control decisions lag or fail. A cloud round-trip can take seconds, which is too slow. Raw occupancy data is transmitted centrally, creating privacy concerns.

3. **Digital Twin Platforms (BIM-based)**
   * **Pros:** Extremely powerful for scenario testing.
   * **Cons:** Requires detailed BIM data, which most existing Indian buildings simply don't have. Unusable for the retrofit market, which is where most of India's savings potential actually is.

4. **Solar Self-Consumption / Battery Optimization Systems**
   * **Pros:** Directly reduces peak grid draw.
   * **Cons:** Only addresses the supply side, not building demand behavior. Requires solar + battery capex already in place.

## 3. How EcoTwin-EDGE Is Different

EcoTwin-EDGE isn't just another occupancy ML dashboard. The differentiation is structural:

* **On-device inference (Edge AI) vs. Cloud ML:** Works with poor connectivity, preserves occupant privacy, cuts bandwidth cost — fits India's retrofit reality, not just premium new-builds. Raw data never leaves the room.
* **Occupant comfort feedback is a literal training signal — and it is direction-aware:** Directly defuses the "you're just making people uncomfortable to save energy" objection. Each 1-tap vote ("Too Warm / Fine / Too Cold") is a labeled sample that retrains the building's local model in real time. The model is given the vote's *direction* (heat excess vs. cold excess) as features, so rather than learning only "comfort is low here" it learns an implicit **comfort band** — low comfort when the space is too warm *or* too cold, high comfort in between. That model lives on a single building's gateway: it is local to that building, not shared across buildings and not federated with any other site.
* **Lightweight RC-thermal-model twin:** Usable on existing/retrofit buildings without BIM, benchmarked against real BEE/ECBC EPI data.
* **Grid responsiveness built-in:** Matches exactly what the brief asks for (shift flexible loads off-peak) rather than bolting it on.

## 4. The Full Solution Architecture

A 4-layer edge-AI building intelligence system:

1. **Sense (Edge Sensor Node):** Low-cost RISC-V-based sensor nodes (occupancy, CO₂, temp/RH, lux, sub-metering) run on-device inference using tinyML. They transmit only derived comfort/occupancy scores, not raw data.
2. **Learn (Building Gateway):** A local edge gateway trains a comfort/energy model continuously on that building's own data (in the prototype, a small online linear model warm-started from a synthetic comfort-band prior and refined by replayed occupant votes). It handles BACnet/Modbus bridging to existing HVAC/lighting hardware.
3. **Model (Digital Twin):** A lightweight digital twin per building benchmarks real consumption against BEE/ECBC EPI baselines for that climate zone. It ranks retrofit interventions by ₹-per-kWh-saved.
4. **Act (Grid-Responsive Controller):** Uses the comfort-aware model output plus DISCOM tariff/DR signals to shift flexible loads (pre-cooling, battery dispatch, non-critical lighting) off-peak, within occupant-comfort bounds. A 1-tap feedback loop ("Too Warm / Fine / Too Cold") provides labeled training data for the model.

### 4.1 Scope of This Prototype

The architecture above is the full per-building design. This hackathon prototype instantiates it **end-to-end for one building** — Coimbatore Block A, a warm-humid IT/ITES campus — with a single local model running on one gateway. Climate-zone awareness is a property of the *platform* (the same sensor stack is retuned per zone); the prototype deliberately demonstrates one zone completely and honestly rather than simulating many shallowly. The comfort model is the piece shown live; the energy/twin and DR optimisation layers are represented in the dashboard's analytics, retrofit and Grid-DR views.

**What the live demo shows on screen:**

* Live sensor gauges (occupancy, CO₂, temperature, comfort) refreshed every 2 s, with the comfort score predicted by the on-device model.
* Occupant vote buttons that retrain the local model on each click, with a visible **"Model updates: N"** counter so the learning loop is observable rather than hidden.
* A comfort score that visibly reshapes as votes arrive: warm votes pull the prediction down at high temperature, cold votes pull it down at low temperature, and fine votes raise the comfortable middle — an implicit comfort band learned from feedback, not hard-coded.
* Grid-DR, retrofit-ranking and retrofit-deployment views over the same building's data.

## 5. Why It's Sustainable (Electricity 4.0 Alignment)

Schneider Electric's sustainability thesis (Electricity 4.0) rests on three pillars:

* **Electrify:** EcoTwin-EDGE makes existing electrified loads (HVAC, lighting) run at genuinely necessary levels instead of oversized/always-on defaults — the efficiency half of decarbonization.
* **Digitize:** EcoTwin-EDGE mirrors Schneider's EcoStruxure 3-layer model (connected products → edge control → apps/analytics) with a cheaper, retrofit-friendly implementation.
* **Decarbonize:** The grid-responsive controller turns buildings into active, flexible grid participants that actively balance supply and demand, shifting load away from dirty peak generation.

**Quantified Estimate:** 
15-25% reduction in building energy intensity (defensible, literature-supported range for occupancy-driven control) against BEE EPI baselines. Commercial payback is typically 12-24 months for occupancy-based controls retrofits.
