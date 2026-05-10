import ollama
import json
import time

with open("cr_fish_detailed.json", "r") as f:
    data = json.load(f)

for i, fish in enumerate(data):
    if "summary" in fish:
        print(f"Skipping {fish['name']} (already has summary)")
        continue

    threats = [t["description"]["en"] for t in fish.get("threats", []) if t.get("description")]
    habitats = [h["description"]["en"] for h in fish.get("habitat", []) if h.get("description")]

    prompt = f"""
You are a marine conservation expert writing for a general audience.
Write a clear 2-3 sentence summary. Mention where it lives, main threats, and one way people can help.

Fish: {fish['name']}
Status: Critically Endangered
Trend: {fish.get('trend', 'Unknown')}
Habitats: {', '.join(habitats) or 'Unknown'}
Threats: {', '.join(threats) or 'Unknown'}
"""

    try:
        response = ollama.chat(
            model="gemma3",
            messages=[{"role": "user", "content": prompt}]
        )
        import re
        text = response["message"]["content"].strip()
        # Remove any intro sentence that ends with a colon
        text = re.sub(r'^.*?:\s*', '', text, count=1) if ':' in text.split('\n')[0] else text
        fish["summary"] = text.strip()
        print(f"Added ({i+1}/{len(data)}) {fish['name']}")
    except Exception as e:
        print(f"Failed {fish['name']}: {e}")
        break

    with open("cr_fish_detailed.json", "w") as f:
        json.dump(data, f, indent=4)

print("Done!")