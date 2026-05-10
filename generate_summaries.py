from google import genai
from dotenv import load_dotenv
import json, os, time

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        fish["summary"] = response.text.strip()
        print(f"✓ ({i+1}/{len(data)}) {fish['name']}")
    except Exception as e:
        print(f"✗ {fish['name']}: {e}")
        break  # stop if quota hit, don't waste more

    # Save after every fish so progress isn't lost
    with open("cr_fish_detailed.json", "w") as f:
        json.dump(data, f, indent=4)

    time.sleep(6)  # wait 6 seconds between each call

print("Done!")