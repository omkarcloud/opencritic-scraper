"""Use the scraper straight from Python — no server needed.

    python main.py

Every function returns the same JSON the API does; results are written to
output/*.json. The full function list is in routes.py (ENDPOINTS).
"""
import json
import os

from opencritic.games import browse, details
from opencritic.reviews import game_reviews_all

os.makedirs("output", exist_ok=True)


def save(name, data):
    path = os.path.join("output", name)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"saved {path}")


if __name__ == "__main__":
    # a game id or any opencritic.com game link
    save("game_12090_elden_ring.json", details(12090))

    # every critic review of a game in one call
    save("reviews_12090_elden_ring.json", game_reviews_all(12090))

    # the best-reviewed PC games of 2025, 20 per page
    save("best_pc_games_2025.json", browse(platforms=["pc"], year=2025, sort="score"))
