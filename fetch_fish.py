import requests
import json
import time

API_KEY = "HdwbDQ7tBkbi2Jaq2b76wNtHMR7ZB8ViiszS"
BASE_URL = "https://api.iucnredlist.org/api/v4"

headers = {
    "accept": "application/json",
    "Authorization": API_KEY
}

fish_classes = [
    "ACTINOPTERYGII",
    "ELASMOBRANCHII",
    "HOLOCEPHALI"
]

def get_species_details(assessment_id):
    url = f"{BASE_URL}/assessment/{assessment_id}"
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        return None
    return r.json()

results = []

for c in fish_classes:
    print(f"Scanning class: {c}")
    for page in range(1, 16):  # scan 15 pages
        if len(results) >= 50:
            break

        url = f"{BASE_URL}/taxa/class/{c}?page={page}&latest=true"
        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            print(f"  Page {page} failed: {r.status_code}")
            break

        data = r.json()
        species_list = data.get("assessments", [])

        if not species_list:
            print(f"  Page {page} empty, stopping")
            break

        print(f"  Page {page}: {len(species_list)} species found")

        for s in species_list:
            if len(results) >= 50:
                break

            category = s.get("red_list_category_code")
            assessment_id = s.get("assessment_id")

            if category != "CR" or not assessment_id:
                continue

            details = get_species_details(assessment_id)
            if not details:
                continue

            taxon = details.get("taxon") or {}
            trend = details.get("population_trend") or {}
            trend_desc = trend.get("description") or {}
            habitats = details.get("habitats") or []
            threats = details.get("threats") or []

            results.append({
                "name": taxon.get("scientific_name", "Unknown"),
                "category": category,
                "trend": trend_desc.get("en", "Unknown"),
                "habitat": habitats,
                "threats": threats,
                "url": details.get("url", "#"),
                "score": 3
            })

            print(f"    Added: {taxon.get('scientific_name')} ({len(results)}/50)")
            time.sleep(0.2)

        time.sleep(0.5)

    if len(results) >= 50:
        break

with open("cr_fish_detailed.json", "w") as f:
    json.dump(results, f, indent=4)

print(f"\nDone! Saved {len(results)} fish to cr_fish_detailed.json")