"""Quick API smoke test."""
import urllib.request
import json
import time

BASE = "http://localhost:8000"

# Test health
resp = urllib.request.urlopen(f"{BASE}/")
print("Health:", json.loads(resp.read()))

# Test simulation
start = time.perf_counter()
resp = urllib.request.urlopen(f"{BASE}/simulate?simulations=1000")
data = json.loads(resp.read())
elapsed = time.perf_counter() - start

print(f"\n{'Team':<35} {'Top4':>8} {'Top2':>8} {'AvgPos':>8} {'Pts':>5} {'NRR':>7}")
print("-" * 75)
for t in data["teams"]:
    print(
        f"{t['name']:<35} {t['top4_probability']:>7.1%} {t['top2_probability']:>7.1%} "
        f"{t['avg_position']:>7.1f} {t['current_points']:>5} {t['current_nrr']:>+7.3f}"
    )

print(f"\nSimulations: {data['simulations_run']}")
print(f"Remaining matches: {data['remaining_matches']}")
print(f"Time: {elapsed:.2f}s")
