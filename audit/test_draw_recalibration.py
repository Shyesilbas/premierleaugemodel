"""
Test effect of draw bias adjustment on all 10 Gameweek 7 fixtures.
"""
import requests
import json
import numpy as np

# Let's get the raw GW7 predictions from the API
url = "http://127.0.0.1:8000/api/fixtures/grouped?season=2026_27"
resp = requests.get(url).json()
gw7 = [g for g in resp["gameweeks"] if g["gameweek"] == 7][0]

matches = []
for d in gw7["days"]:
    for m in d["matches"]:
        matches.append(m)

# Current Calibrator 1x2_ensemble parameters:
# temperature: 0.8923
# bias: [-0.09854, +0.13458, -0.03604]

# Let's see: in apply_probability_calibrator:
# logits = log(p) / temperature + bias
# If we invert the current calibrator to get pre-calibrated logits:
# logits_raw = (logits_cal - bias) * temperature
temp = 0.892345
bias_curr = np.array([-0.098542, 0.134582, -0.036039])

def recalibrate(p_curr, new_bias, new_temp=0.92):
    # Recover logit before current bias
    # p_curr = softmax(logits_cal)
    l_cal = np.log(np.clip(p_curr, 1e-12, 1.0))
    # Unbias and untemp to get back pre-calibrated blend logits:
    l_raw = (l_cal - bias_curr) * temp
    # Apply new temp and new bias:
    l_new = l_raw / new_temp + new_bias
    l_new -= l_new.max()
    p_new = np.exp(l_new)
    return p_new / p_new.sum()

print("Comparing Current vs Balanced Draw Calibration:")
print(f"{'#':2s} {'Match':30s} {'Current 1X2 (%)':22s} {'Balanced 1X2 (Draw in 30-32% band)':30s}")
print("-" * 90)

# We want Draw to sit comfortably in the 28-32% band for close matches,
# allowing the slight favorite (Liverpool / Man Utd) to edge out Draw as argmax!
# Let's test new_bias = [-0.03, -0.02, 0.05] (slight shift from draw to away/home):
new_bias = np.array([-0.02, -0.02, 0.04])

for i, m in enumerate(matches, 1):
    pred = m["prediction"]
    p_curr = np.array([pred["home_win_pct"], pred["draw_pct"], pred["away_win_pct"]]) / 100.0
    p_new = recalibrate(p_curr, new_bias)
    
    cur_str = f"{p_curr[0]*100:.1f} - {p_curr[1]*100:.1f} - {p_curr[2]*100:.1f}"
    new_str = f"{p_new[0]*100:.1f} - {p_new[1]*100:.1f} - {p_new[2]*100:.1f}"
    
    name = f"{m['home_name']} vs {m['away_name']}"
    print(f"{i:<2d} {name:30s} {cur_str:22s} {new_str:30s}")
