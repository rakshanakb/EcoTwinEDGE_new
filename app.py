import json
import random
import threading
import time
from flask import Flask, jsonify, request, send_from_directory
from sklearn.linear_model import SGDRegressor
import numpy as np
import os

app = Flask(__name__, static_folder='.')

# Single virtual building — the pitch's lead example (Coimbatore, warm-humid ECBC zone).
# The dashboard demonstrates the full Sense -> Learn -> Model -> Act loop on one
# building instead of diluting the story across five.
BLDGS = [
    {"id":0,"city":"Coimbatore","tag":"Block A","zone":"Warm-Humid","zc":"wh","area":8500,"epiB":165,"epiT":132},
]

# Initial sensor state
sensor_states = [
    {"occ": 0.7, "co2": 650, "tmp": 24.5, "lux": 400, "cft": 85, "eng": b["epiB"]*b["area"]/8760*0.8}
    for b in BLDGS
]

# Live comfort votes. Starts empty so every number shown during the demo was
# produced by the demo itself, not seeded with fake history.
votes_stats = [
    {"warm": 0, "fine": 0, "cold": 0}
    for _ in BLDGS
]

# ─────────────────────────────────────────────────────────────────────────────
#  Comfort model — LOCAL to this one building's gateway.
#  It is not shared across buildings and not federated with any other site.
# ─────────────────────────────────────────────────────────────────────────────

# Comfort band (matches the dashboard's "Comfort Band" indicator).
T_LO, T_HI = 22.0, 26.0
COMFORT_MIN, COMFORT_MAX = 10.0, 98.0


def comfort_features(tmp, co2, occ, vote=None):
    """Feature vector for the comfort model.

    Features: [temperature, CO2, occupancy, heat_excess, cold_excess]

    The two one-sided excess terms give the model a *direction*: comfort is low
    when the space is too warm (heat_excess > 0) OR too cold (cold_excess > 0),
    and high inside the band. A single signed temperature feature cannot express
    that V-shaped relationship, which is why warm and cold votes used to collapse
    into the same direction-blind target.

    Values are scaled to comparable ranges so the constant-learning-rate SGD
    stays stable (raw CO2 values in the hundreds otherwise dominate the gradient).
    """
    heat = max(0.0, tmp - T_HI)
    cold = max(0.0, T_LO - tmp)
    if vote == 'warm':
        # Occupant reports discomfort even when we're nominally in-band; keep a
        # small positive signal so the direction is always learned.
        heat = max(0.5, heat)
    elif vote == 'cold':
        cold = max(0.5, cold)
    return np.array([[
        (tmp - 24.0) / 6.0,
        (co2 - 700.0) / 400.0,
        occ,
        heat / 4.0,
        cold / 4.0,
    ]])


def _prior_comfort(tmp, co2, occ):
    """Synthetic cold-start prior: a simple comfort band, so the model boots
    with sensible readings instead of a flat average. Occupant votes then
    reshape this prior live."""
    heat = max(0.0, tmp - T_HI)
    cold = max(0.0, T_LO - tmp)
    return float(np.clip(90.0 - 7.0*heat - 7.0*cold, COMFORT_MIN, COMFORT_MAX))


comfort_model = SGDRegressor(max_iter=8, learning_rate='constant', eta0=0.05, random_state=0)

# Labelled occupant samples replayed on every vote. A growing, replayed buffer
# keeps earlier votes in view, so a burst of warm votes followed by cold votes
# refines a band instead of overwriting it (constant-LR SGD forgets otherwise).
_vote_X = []
_vote_y = []
VOTE_BUFFER_CAP = 60
REPLAY_PASSES = 3
_fit_lock = threading.Lock()


def _warm_start():
    """Fit the cold-start prior across a grid of conditions."""
    xs, ys = [], []
    for tmp in np.arange(15.0, 35.0, 1.0):
        for occ in (0.2, 0.5, 0.8):
            for co2 in (500.0, 800.0, 1100.0):
                xs.append(comfort_features(tmp, co2, occ)[0])
                ys.append(_prior_comfort(tmp, co2, occ))
    comfort_model.partial_fit(np.vstack(xs), np.array(ys))


def _learn(features, target):
    """Online update: store the labelled sample and replay the vote buffer."""
    with _fit_lock:
        _vote_X.append(features[0])
        _vote_y.append(target)
        if len(_vote_y) > VOTE_BUFFER_CAP:
            _vote_X.pop(0)
            _vote_y.pop(0)
        X = np.vstack(_vote_X)
        y = np.array(_vote_y)
        for _ in range(REPLAY_PASSES):
            comfort_model.partial_fit(X, y)


_warm_start()

# Number of occupant votes that have retrained the model (surfaced in the dashboard).
model_updates = 0


def simulation_loop():
    """Background thread to simulate sensor data updates and ML inference."""
    global sensor_states
    while True:
        time.sleep(2)  # Update every 2 seconds

        hour = (time.localtime().tm_hour + time.localtime().tm_min/60.0)
        is_working_hour = 8.5 < hour < 19

        for i, state in enumerate(sensor_states):
            # Simulate physical changes
            target_occ = 0.65 if is_working_hour else 0.1
            state["occ"] = max(0, min(1, state["occ"] + (target_occ - state["occ"])*0.08 + (random.random()-0.5)*0.07))
            state["co2"] = max(400, min(1400, state["co2"] + (state["occ"]*600 - (state["co2"]-400))*0.05 + (random.random()-0.5)*20))
            state["tmp"] = max(18, min(34, state["tmp"] + (random.random()-0.5)*0.4))
            state["lux"] = max(50, min(800, state["lux"] + (random.random()-0.5)*30))
            state["eng"] = max(0.5, state["eng"] + (random.random()-0.5)*0.2)

            # Edge-AI Inference: Predict comfort score based on current readings
            features = comfort_features(state["tmp"], state["co2"], state["occ"])
            pred_cft = comfort_model.predict(features)[0]

            # Bound the prediction and add a tiny bit of noise for realism
            state["cft"] = max(0, min(100, pred_cft + (random.random()-0.5)*2))


@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'index.html')


@app.route('/api/sensors')
def get_sensors():
    return jsonify({
        "buildings": BLDGS,
        "sensors": sensor_states,
        "votes": votes_stats,
        "model_updates": model_updates,
    })


@app.route('/api/vote', methods=['POST'])
def handle_vote():
    """Endpoint for Occupant Feedback Loop."""
    global model_updates
    data = request.json or {}
    bldg_id = data.get('bldg_id', 0)
    vote = data.get('vote')  # 'warm', 'fine', 'cold'

    if vote not in ('warm', 'fine', 'cold') or not (0 <= bldg_id < len(sensor_states)):
        return jsonify({"status": "error", "message": "invalid vote"}), 400

    state = sensor_states[bldg_id]
    features = comfort_features(state["tmp"], state["co2"], state["occ"], vote=vote)

    # Direction-aware targets. The heat_excess / cold_excess feature columns
    # already tell the model *which way* the space is off, so both discomfort
    # votes can share a low target without becoming direction-blind.
    if vote == 'fine':
        target = 95.0  # High comfort
    else:
        target = 30.0  # Low comfort, direction carried by the excess features
    votes_stats[bldg_id][vote] += 1

    # Online learning step (Edge learning simulation)
    _learn(features, target)
    model_updates += 1

    return jsonify({
        "status": "success",
        "message": "Model updated with occupant feedback",
        "votes": votes_stats,
        "model_updates": model_updates,
    })


if __name__ == '__main__':
    # Start the simulation thread
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)
