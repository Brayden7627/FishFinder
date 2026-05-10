from flask import Flask, render_template_string
from dotenv import load_dotenv
import requests
import json
import os
import ollama
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

# config
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

IUCN_API_KEY = os.getenv("IUCN_API_KEY")

BASE_URL = "https://api.iucnredlist.org/api/v4"

headers = {
    "accept": "application/json",
    "Authorization": IUCN_API_KEY
}


#load local json
def load_fish_data():
    with open("cr_fish_detailed.json", "r") as f:
        return json.load(f)


def get_summary(fish: dict) -> str:
    threats = [t["description"]["en"] for t in fish.get("threats", []) if t.get("description")]
    habitats = [h["description"]["en"] for h in fish.get("habitat", []) if h.get("description")]

    prompt = f"""
You are a marine conservation expert writing for a general audience.

Given this data about a critically endangered fish, write a clear 2-3 sentence summary.
Mention where it lives, the main threats it faces, and one thing people can do to help.
Keep it engaging and accessible — no jargon.
IMPORTANT: Do NOT start with any introduction, preamble, heading, or phrase like "Here is", "Here's", "This is", or "Sure". Your response must begin directly with the first sentence about the fish. No intro whatsoever.

Fish name: {fish['name']}
Conservation status: Critically Endangered (CR)
Population trend: {fish.get('trend', 'Unknown')}
Habitats: {', '.join(habitats) if habitats else 'Unknown'}
Threats: {', '.join(threats) if threats else 'Unknown'}
"""

    try:
        response = ollama.chat(
            model="gemma3",
            messages=[{"role": "user", "content": prompt}]
        )
        import re
        text = response["message"]["content"].strip()
        text = re.sub(r'^.*?:\s*', '', text, count=1) if ':' in text.split('\n')[0] else text
        return text.strip()
    except Exception as e:
        return f"Summary unavailable: {e}"


#save summaries back to json
def load_fish_with_summaries():
    fish_list = load_fish_data()
    changed = False

    for fish in fish_list:
        if "summary" not in fish: 
            fish["summary"] = get_summary(fish)
            changed = True

    if changed:
        with open("cr_fish_detailed.json", "w") as f:
            json.dump(fish_list, f, indent=4)

    return fish_list


#html
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ocean Intelligence Unit | Terminal</title>
    <style>
        /*Typography & Color Palette*/
        :root {
            --bg-base: #0a0c10;
            --bg-surface: #11141a;
            --bg-surface-hover: #161a22;
            --border-dim: #252a34;
            --border-focus: #3d4658;
            --text-primary: #e0e5eb;
            --text-secondary: #8492a6;
            --text-tertiary: #546175;
            --accent-crit: #d74d4d;
            --accent-link: #6294d1;
            
            --font-sans: "Helvetica Neue", Helvetica, Arial, sans-serif;
            --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
        }

        /*Base Reset & Grain Texture*/
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--font-sans);
            background-color: var(--bg-base);
            color: var(--text-primary);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        body::after {
            content: "";
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            opacity: 0.03;
            pointer-events: none;
            z-index: 999;
            background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
        }

        /*Top Status Bar*/
        .system-bar {
            background-color: var(--bg-base);
            border-bottom: 1px solid var(--border-dim);
            padding: 6px 24px;
            display: flex;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-tertiary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .system-bar span strong {
            color: var(--text-secondary);
            font-weight: normal;
        }

        /*Main Application Layout*/
        .app-container {
            display: grid;
            grid-template-columns: 260px 1fr;
            flex-grow: 1;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        /*Sidebar Sidebar*/
        aside.sidebar {
            border-right: 1px solid var(--border-dim);
            padding: 40px 32px 40px 24px;
            display: flex;
            flex-direction: column;
        }

        .agency-header {
            margin-bottom: 48px;
        }

        .agency-header h1 {
            font-size: 1.25rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin-bottom: 8px;
        }

        .agency-header p {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: auto;
        }

        .filter-label {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-tertiary);
            margin-bottom: 8px;
            letter-spacing: 0.1em;
        }

        .filter-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            text-align: left;
            padding: 8px 12px;
            font-family: var(--font-sans);
            font-size: 0.85rem;
            cursor: pointer;
            border-left: 2px solid transparent;
            transition: all 0.2s ease;
        }

        .filter-btn:hover {
            color: var(--text-primary);
            background-color: var(--bg-surface);
        }

        .filter-btn.active {
            color: var(--text-primary);
            border-left-color: var(--text-primary);
            background-color: var(--bg-surface);
            font-weight: 500;
        }

        .meta-data-block {
            margin-top: 60px;
            border-top: 1px solid var(--border-dim);
            padding-top: 24px;
        }

        .meta-row {
            display: flex;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        /*Main Content / Case File Feed*/
        main.feed {
            padding: 40px;
            overflow-y: auto;
            background-color: var(--bg-base);
        }

        .feed-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-dim);
        }

        .feed-title {
            font-size: 1.5rem;
            font-weight: 500;
            letter-spacing: -0.02em;
        }

        .result-count {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 24px;
        }

        /*Dossier Card Styling*/
        .case-file {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-dim);
            padding: 24px;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
        }

        .case-file:hover {
            transform: translateY(-2px);
            border-color: var(--border-focus);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }

        /*Case File Header*/
        .case-meta-strip {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-dim);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }

        .case-id {
            letter-spacing: 0.05em;
        }

        .status-badge {
            background-color: rgba(215, 77, 77, 0.1);
            color: var(--accent-crit);
            padding: 2px 6px;
            border: 1px solid rgba(215, 77, 77, 0.3);
            text-transform: uppercase;
        }

        /*Editorial Typography*/
        .species-name {
            font-family: "Georgia", serif; /*Adds an editorial investigative feel*/
            font-size: 1.6rem;
            font-weight: normal;
            color: #ffffff;
            margin-bottom: 6px;
            line-height: 1.2;
        }

        .data-confidence {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-tertiary);
            margin-bottom: 20px;
            display: flex;
            gap: 12px;
        }

        .data-confidence span {
            color: var(--text-secondary);
        }

        /*Intelligence Summary*/
        .report-body {
            font-size: 0.85rem;
            line-height: 1.6;
            color: var(--text-primary);
            flex-grow: 1;
            margin-bottom: 24px;
        }

        .trend-indicator {
            display: inline-block;
            margin-top: 12px;
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--text-secondary);
            background: var(--bg-base);
            padding: 4px 8px;
            border: 1px solid var(--border-dim);
        }

        /*Functional Actions*/
        .action-strip {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 16px;
            border-top: 1px dotted var(--border-dim);
        }

        .btn-playback {
            background-color: var(--bg-base);
            color: var(--text-primary);
            border: 1px solid var(--border-focus);
            padding: 6px 12px;
            font-family: var(--font-mono);
            font-size: 0.7rem;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.1s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-playback:hover:not(:disabled) {
            background-color: var(--text-primary);
            color: var(--bg-base);
        }

        .btn-playback:active:not(:disabled) {
            transform: translateY(1px);
        }

        .btn-playback:disabled {
            opacity: 0.4;
            cursor: wait;
        }

        .db-link {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--accent-link);
            text-decoration: none;
            text-transform: uppercase;
        }

        .db-link:hover {
            text-decoration: underline;
        }
        
        /*Responsive*/
        @media (max-width: 900px) {
            .app-container {
                grid-template-columns: 1fr;
            }
            aside.sidebar {
                border-right: none;
                border-bottom: 1px solid var(--border-dim);
                padding: 24px;
            }
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
    function playAudio(index, btn) {
        const audio = document.getElementById('audio-' + index);
        const originalText = '[ PLAY BRIEFING ]';
        
        if (!audio.src || audio.paused) {
            btn.innerHTML = '[ BUFFERING... ]';
            btn.disabled = true;
            audio.src = '/speak/' + index;
            audio.load();
            audio.play().then(() => {
                btn.innerHTML = '[ ■ STOP PLAYBACK ]';
                btn.disabled = false;
            }).catch(e => {
                btn.innerHTML = '[ ERR: STREAM FAILED ]';
                btn.disabled = false;
            });
            audio.onended = () => {
                btn.innerHTML = originalText;
            };
        } else {
            audio.pause();
            audio.currentTime = 0;
            btn.innerHTML = originalText;
        }
    }
    </script>
</head>
<body>

    <!-- System Status Bar -->
    <div class="system-bar">
        <span>UNIT: <strong>OCEAN_INTEL_DB</strong></span>
        <span>SYS_STAT: <strong>SECURE / ONLINE</strong></span>
        <span>UPTIME: <strong>99.98%</strong></span>
    </div>

    <div class="app-container">
        
        <!-- Left Sidebar / Filters -->
        <aside class="sidebar">
            <div class="agency-header">
                <h1>Endangered Species Tracking System</h1>
                <p>Global Conservation Watchlist</p>
            </div>

            <div class="filter-group">
                <div class="filter-label">DATA FILTERS</div>
                <button class="filter-btn active">ALL RECORDS</button>
                <div class="filter-btn">STATUS: CRITICAL (CR)</div>
                <div class="filter-btn">STATUS: ENDANGERED (EN)</div>
                <div class="filter-btn">STATUS: VULNERABLE (VU)</div>
            </div>

            <div class="meta-data-block">
                <div class="meta-row">
                    <span>DATA SOURCE</span>
                    <span>IUCN API v4</span>
                </div>
                <div class="meta-row">
                    <span>LAST SYNC</span>
                    <span>14 MINS AGO</span>
                </div>
                <div class="meta-row">
                    <span>COVERAGE</span>
                    <span>GLOBAL</span>
                </div>
            </div>
        </aside>

        <!-- Main Feed -->
        <main class="feed">
            <div class="feed-header">
                <h2 class="feed-title">Active Case Files</h2>
                <span class="result-count">DISPLAYING {{ fish|length }} RECORDS</span>
            </div>

            <div class="grid">
                {% for f in fish %}
                <div class="case-file">
                    
                    <div class="case-meta-strip">
                        <span class="case-id">FILE // {{ "%05d" | format(loop.index * 73) }}-{{ "%02d" | format(loop.index) }}</span>
                        <span class="status-badge">CRITICAL</span>
                    </div>

                    <h3 class="species-name">{{ f.name }}</h3>
                    
                    <div class="data-confidence">
                        <div>THREAT LEVEL: <span>SEVERE</span></div>
                        <div>CONFIDENCE: <span>HIGH (94%)</span></div>
                    </div>

                    <div class="report-body">
                        {{ f.summary }}
                        <div class="trend-indicator">POPULATION TREND: {{ f.trend | upper }}</div>
                    </div>

                    <div class="action-strip">
                        <button class="btn-playback" onclick="playAudio({{ loop.index0 }}, this)">
                            [ PLAY BRIEFING ]
                        </button>
                        <a href="{{ f.url }}" class="db-link" target="_blank">EXT_DB_REF ↗</a>
                        <audio id="audio-{{ loop.index0 }}"></audio>
                    </div>

                </div>
                {% endfor %}
            </div>
        </main>

    </div>

</body>
</html>
"""


#route
@app.route("/")
def home():
    fish = load_fish_with_summaries()
    return render_template_string(HTML, fish=fish)

@app.route("/speak/<int:fish_index>")
def speak(fish_index):
    fish_list = load_fish_data()
    
    if fish_index >= len(fish_list):
        return "Not found", 404
    
    fish = fish_list[fish_index]
    summary = fish.get("summary", "No summary available.")
    text = f"{fish['name']}. {summary}"

    audio = el_client.text_to_speech.convert(
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        text=text,
        model_id="eleven_multilingual_v2"
    )

    audio_bytes = b"".join(audio)

    from flask import Response
    return Response(audio_bytes, mimetype="audio/mpeg")


#run
if __name__ == "__main__":
    app.run(debug=True)