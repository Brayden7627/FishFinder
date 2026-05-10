from flask import Flask, render_template_string, jsonify
from dotenv import load_dotenv
import requests
import json
import os
import ollama
import re
import time
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

#config
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

        * { box-sizing: border-box; margin: 0; padding: 0; }

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

        .system-bar span strong { color: var(--text-secondary); font-weight: normal; }

        .app-container {
            display: grid;
            grid-template-columns: 260px 1fr;
            flex-grow: 1;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        aside.sidebar {
            border-right: 1px solid var(--border-dim);
            padding: 40px 32px 40px 24px;
            display: flex;
            flex-direction: column;
        }

        .agency-header { margin-bottom: 48px; }

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
            border-left: 2px solid transparent;
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

        /*Rotation status indicator*/
        .rotation-status {
            margin-top: 16px;
            border-top: 1px solid var(--border-dim);
            padding-top: 16px;
        }

        .rotation-label {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-tertiary);
            margin-bottom: 8px;
            letter-spacing: 0.1em;
        }

        .rotation-bar-track {
            width: 100%;
            height: 2px;
            background: var(--border-dim);
            position: relative;
            overflow: hidden;
        }

        .rotation-bar-fill {
            height: 100%;
            background: var(--accent-crit);
            width: 0%;
            transition: width 0.1s linear;
        }

        .rotation-info {
            font-family: var(--font-mono);
            font-size: 0.6rem;
            color: var(--text-tertiary);
            margin-top: 6px;
        }

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

        .feed-title { font-size: 1.5rem; font-weight: 500; letter-spacing: -0.02em; }

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

        /*Card with animation states*/
        .case-file {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-dim);
            padding: 24px;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, opacity 0.5s ease;
        }

        .case-file:hover {
            transform: translateY(-2px);
            border-color: var(--border-focus);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }

        /*Fade out animation*/
        .case-file.exiting {
            opacity: 0;
            transform: translateY(10px) scale(0.98);
            transition: opacity 0.5s ease, transform 0.5s ease;
            pointer-events: none;
        }

        /*Fade in animation*/
        .case-file.entering {
            opacity: 0;
            transform: translateY(-10px) scale(0.98);
            transition: none;
        }

        .case-file.entered {
            opacity: 1;
            transform: translateY(0) scale(1);
            transition: opacity 0.5s ease, transform 0.5s ease;
        }

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

        .case-id { letter-spacing: 0.05em; }

        .status-badge {
            background-color: rgba(215, 77, 77, 0.1);
            color: var(--accent-crit);
            padding: 2px 6px;
            border: 1px solid rgba(215, 77, 77, 0.3);
            text-transform: uppercase;
            font-size: 0.65rem;
        }

        .species-name {
            font-family: "Georgia", serif;
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

        .data-confidence span { color: var(--text-secondary); }

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

        .btn-playback:active:not(:disabled) { transform: translateY(1px); }
        .btn-playback:disabled { opacity: 0.4; cursor: wait; }

        .db-link {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--accent-link);
            text-decoration: none;
            text-transform: uppercase;
        }

        .db-link:hover { text-decoration: underline; }

        @media (max-width: 900px) {
            .app-container { grid-template-columns: 1fr; }
            aside.sidebar { border-right: none; border-bottom: 1px solid var(--border-dim); padding: 24px; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

    <div class="system-bar">
        <span>UNIT: <strong>OCEAN_INTEL_DB</strong></span>
        <span>SYS_STAT: <strong>SECURE / ONLINE</strong></span>
        <span>UPTIME: <strong>99.98%</strong></span>
    </div>

    <div class="app-container">

        <aside class="sidebar">
            <div class="agency-header">
                <h1>Endangered Species Tracking System</h1>
                <p>Global Conservation Watchlist</p>
            </div>

            <div class="filter-group">
                <div class="filter-label">DATA FILTERS</div>
                <div class="filter-btn active">ALL RECORDS</div>
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
                <div class="meta-row">
                    <span>TOTAL RECORDS</span>
                    <span id="total-count">—</span>
                </div>
                <div class="meta-row">
                    <span>DISPLAYING</span>
                    <span id="display-count">12</span>
                </div>
            </div>

            <div class="rotation-status">
                <div class="rotation-label">FEED ROTATION</div>
                <div class="rotation-bar-track">
                    <div class="rotation-bar-fill" id="rotation-bar"></div>
                </div>
                <div class="rotation-info" id="rotation-info">NEXT ROTATION IN —</div>
            </div>
        </aside>

        <main class="feed">
            <div class="feed-header">
                <h2 class="feed-title">Active Case Files</h2>
                <span class="result-count" id="feed-count">LOADING RECORDS...</span>
            </div>

            <div class="grid" id="fish-grid">
                <!-- Cards injected by JS -->
            </div>
        </main>

    </div>

    <script>
        const DISPLAY_COUNT = 12;
        const ROTATION_INTERVAL = 5000; //5 seconds per swap
        const CARDS_PER_ROTATION = 1;   //swap 1 card at a time

        let allFish = [];
        let displayedIndices = [];
        let rotationTimer = null;
        let progressTimer = null;
        let progressStart = null;

        //Fetch all fish from the API
        async function fetchFish() {
            const res = await fetch('/api/fish');
            allFish = await res.json();
            document.getElementById('total-count').textContent = allFish.length;
            document.getElementById('feed-count').textContent = `DISPLAYING ${Math.min(DISPLAY_COUNT, allFish.length)} OF ${allFish.length} RECORDS`;

            //Pick initial 12 random fish
            displayedIndices = shuffle([...Array(allFish.length).keys()]).slice(0, DISPLAY_COUNT);
            renderAllCards();
            startRotation();
        }

        function shuffle(arr) {
            for (let i = arr.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [arr[i], arr[j]] = [arr[j], arr[i]];
            }
            return arr;
        }

        function buildCard(fish, index, globalIndex) {
            const fileNum = String(globalIndex * 73).padStart(5, '0');
            const fileSeq = String(index + 1).padStart(2, '0');
            return `
                <div class="case-file" id="card-${index}">
                    <div class="case-meta-strip">
                        <span class="case-id">FILE //${fileNum}-${fileSeq}</span>
                        <span class="status-badge">CRITICAL</span>
                    </div>
                    <h3 class="species-name">${fish.name}</h3>
                    <div class="data-confidence">
                        <div>THREAT LEVEL: <span>SEVERE</span></div>
                        <div>CONFIDENCE: <span>HIGH (94%)</span></div>
                    </div>
                    <div class="report-body">
                        ${fish.summary || 'Loading intelligence summary...'}
                        <div class="trend-indicator">POPULATION TREND: ${(fish.trend || 'UNKNOWN').toUpperCase()}</div>
                    </div>
                    <div class="action-strip">
                        <button class="btn-playback" onclick="playAudio(${globalIndex}, this)">
                            [ PLAY BRIEFING ]
                        </button>
                        <a href="${fish.url}" class="db-link" target="_blank">EXT_DB_REF ↗</a>
                        <audio id="audio-${globalIndex}"></audio>
                    </div>
                </div>
            `;
        }

        function renderAllCards() {
            const grid = document.getElementById('fish-grid');
            grid.innerHTML = '';
            displayedIndices.forEach((globalIdx, slotIdx) => {
                const fish = allFish[globalIdx];
                grid.insertAdjacentHTML('beforeend', buildCard(fish, slotIdx, globalIdx));
            });
            //Trigger enter animation
            requestAnimationFrame(() => {
                document.querySelectorAll('.case-file').forEach(card => {
                    card.classList.add('entering');
                    requestAnimationFrame(() => card.classList.add('entered'));
                });
            });
        }

        function rotateCard() {
            //Find indices NOT currently displayed
            const hiddenIndices = [...Array(allFish.length).keys()].filter(i => !displayedIndices.includes(i));
            if (hiddenIndices.length === 0) return; //nothing to swap

            //Pick a random slot to replace
            const slotToReplace = Math.floor(Math.random() * displayedIndices.length);
            const cardEl = document.getElementById(`card-${slotToReplace}`);
            if (!cardEl) return;

            //Pick a random hidden fish to bring in
            const newGlobalIdx = hiddenIndices[Math.floor(Math.random() * hiddenIndices.length)];

            //Fade out
            cardEl.classList.add('exiting');

            setTimeout(() => {
                //Swap index
                displayedIndices[slotToReplace] = newGlobalIdx;

                //Replace card HTML
                const fish = allFish[newGlobalIdx];
                const newCardHTML = buildCard(fish, slotToReplace, newGlobalIdx);
                cardEl.outerHTML = newCardHTML;

                //Trigger enter animation on new card
                const newCard = document.getElementById(`card-${slotToReplace}`);
                if (newCard) {
                    newCard.classList.add('entering');
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            newCard.classList.remove('entering');
                            newCard.classList.add('entered');
                        });
                    });
                }
            }, 550); //slightly after fade out completes
        }

        function startRotation() {
            clearInterval(rotationTimer);
            rotationTimer = setInterval(rotateCard, ROTATION_INTERVAL);
            startProgressBar();
        }

        function startProgressBar() {
            clearInterval(progressTimer);
            progressStart = Date.now();
            const bar = document.getElementById('rotation-bar');
            const info = document.getElementById('rotation-info');

            progressTimer = setInterval(() => {
                const elapsed = Date.now() - progressStart;
                const pct = (elapsed % ROTATION_INTERVAL) / ROTATION_INTERVAL * 100;
                const remaining = Math.ceil((ROTATION_INTERVAL - (elapsed % ROTATION_INTERVAL)) / 1000);
                bar.style.width = pct + '%';
                info.textContent = `NEXT ROTATION IN ${remaining}S`;
            }, 100);
        }

        function playAudio(globalIndex, btn) {
            const audio = document.getElementById('audio-' + globalIndex);
            if (!audio) return;
            const originalText = '[ PLAY BRIEFING ]';

            if (!audio.src || audio.paused) {
                btn.innerHTML = '[ BUFFERING... ]';
                btn.disabled = true;
                audio.src = '/speak/' + globalIndex;
                audio.load();
                audio.play().then(() => {
                    btn.innerHTML = '[ ■ STOP PLAYBACK ]';
                    btn.disabled = false;
                }).catch(() => {
                    btn.innerHTML = '[ ERR: STREAM FAILED ]';
                    btn.disabled = false;
                });
                audio.onended = () => { btn.innerHTML = originalText; };
            } else {
                audio.pause();
                audio.currentTime = 0;
                btn.innerHTML = originalText;
            }
        }

        fetchFish();
    </script>
</body>
</html>
"""


#route - main page
@app.route("/")
def home():
    load_fish_with_summaries()  #ensure summaries are generated
    return render_template_string(HTML)


#NEW: api endpoint that returns all fish as json for the frontend
@app.route("/api/fish")
def api_fish():
    fish_list = load_fish_with_summaries()
    return jsonify(fish_list)


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