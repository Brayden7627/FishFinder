from flask import Flask, render_template_string
from google import genai
from dotenv import load_dotenv
import requests
import json
import os

load_dotenv()

app = Flask(__name__)

# -------------------------
# CONFIG
# -------------------------
IUCN_API_KEY = os.getenv("IUCN_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

BASE_URL = "https://api.iucnredlist.org/api/v4"

headers = {
    "accept": "application/json",
    "Authorization": IUCN_API_KEY
}


# -------------------------
# LOAD LOCAL JSON
# -------------------------
def load_fish_data():
    with open("cr_fish_detailed.json", "r") as f:
        return json.load(f)


# -------------------------
# GEMINI SUMMARY
# -------------------------
def get_gemini_summary(fish: dict) -> str:
    threats = [t["description"]["en"] for t in fish.get("threats", []) if t.get("description")]
    habitats = [h["description"]["en"] for h in fish.get("habitat", []) if h.get("description")]

    prompt = f"""
You are a marine conservation expert writing for a general audience.

Given this data about a critically endangered fish, write a clear 2-3 sentence summary.
Mention where it lives, the main threats it faces, and one thing people can do to help.
Keep it engaging and accessible — no jargon.

Fish name: {fish['name']}
Conservation status: Critically Endangered (CR)
Population trend: {fish.get('trend', 'Unknown')}
Habitats: {', '.join(habitats) if habitats else 'Unknown'}
Threats: {', '.join(threats) if threats else 'Unknown'}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Summary unavailable: {e}"


# -------------------------
# SAVE SUMMARIES BACK TO JSON
# -------------------------
def load_fish_with_summaries():
    fish_list = load_fish_data()
    changed = False

    for fish in fish_list:
        if "summary" not in fish:  # only call Gemini if no summary yet
            fish["summary"] = get_gemini_summary(fish)
            changed = True

    if changed:  # only re-save if something was added
        with open("cr_fish_detailed.json", "w") as f:
            json.dump(fish_list, f, indent=4)

    return fish_list


# -------------------------
# HTML
# -------------------------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Critically Endangered Fish</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #1a1a2e; }
        .fish-card { border: 1px solid #ccc; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
        .fish-name { font-size: 1.3em; font-weight: bold; }
        .badge { background: #c0392b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
        .summary { background: #f0f7f0; border-left: 4px solid #2ecc71; padding: 10px 14px; margin-top: 10px; border-radius: 4px; }
        .meta { color: #555; font-size: 0.9em; margin-top: 6px; }
    </style>
</head>
<body>

<h1>🐟 Critically Endangered Fish</h1>
<p>Data from IUCN Red List · Summaries powered by Gemini AI</p>

{% for f in fish %}
<div class="fish-card">
    <div class="fish-name">{{ f.name }} <span class="badge">CR</span></div>
    <div class="meta">
        Population Trend: {{ f.trend }} ·
        <a href="{{ f.url }}" target="_blank">View on IUCN ↗</a>
    </div>
    <div class="summary">{{ f.summary }}</div>
</div>
{% endfor %}

</body>
</html>
"""


# -------------------------
# ROUTE
# -------------------------
@app.route("/")
def home():
    fish = load_fish_with_summaries()
    return render_template_string(HTML, fish=fish)


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)