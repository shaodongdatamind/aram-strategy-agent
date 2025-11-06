from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .state import PreGameAdviceInput, IngameQAInput, AgentInputs
from .graph import build_initial_state, run_pev, DEFAULT_PATCH


app = FastAPI(title="ARAM Coach", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def root():
    """Root endpoint providing a web UI."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ARAM Coach</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 3em;
                margin-bottom: 10px;
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 30px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .card h2 {
                color: #667eea;
                margin-bottom: 20px;
                font-size: 1.8em;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 600;
            }
            .form-group input, .form-group textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            .form-group input:focus, .form-group textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            .form-group textarea {
                resize: vertical;
                min-height: 100px;
            }
            .champion-input {
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }
            .champion-input input {
                flex: 1;
            }
            .champion-list {
                margin-top: 10px;
            }
            .champion-tag {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                margin: 5px 5px 5px 0;
                font-size: 14px;
            }
            .champion-tag .remove {
                margin-left: 8px;
                cursor: pointer;
                font-weight: bold;
            }
            .champion-tag .remove:hover {
                opacity: 0.8;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            button:active {
                transform: translateY(0);
            }
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .result {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                display: none;
            }
            .result.show {
                display: block;
            }
            .result pre {
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                font-size: 13px;
                line-height: 1.5;
            }
            .loading {
                display: none;
                text-align: center;
                margin-top: 20px;
            }
            .loading.show {
                display: block;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .help-text {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .links {
                text-align: center;
                margin-top: 30px;
            }
            .links a {
                color: white;
                text-decoration: none;
                margin: 0 15px;
                opacity: 0.9;
            }
            .links a:hover {
                opacity: 1;
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 ARAM Coach</h1>
                <p>Get strategic advice for your ARAM matches</p>
            </div>
            
            <div class="cards">
                <!-- Pre-Game Advice Card -->
                <div class="card">
                    <h2>Pre-Game Advice</h2>
                    <form id="preGameForm">
                        <div class="form-group">
                            <label>Patch (optional)</label>
                            <input type="text" id="preGamePatch" placeholder="e.g., 15.20 (defaults to latest)">
                        </div>
                        
                        <div class="form-group">
                            <label>Your Champion</label>
                            <input type="text" id="preGameMyChamp" placeholder="e.g., Jinx">
                            <div class="help-text">The champion you're playing</div>
                        </div>
                        
                        <div class="form-group">
                            <label>Ally Team Composition</label>
                            <div class="champion-input">
                                <input type="text" id="allyChampInput" placeholder="Enter champion name">
                                <button type="button" onclick="addChampion('ally')">Add</button>
                            </div>
                            <div id="allyList" class="champion-list"></div>
                            <div class="help-text">Enter champion names one at a time (e.g., "Jinx", "Thresh")</div>
                        </div>
                        
                        <div class="form-group">
                            <label>Enemy Team Composition</label>
                            <div class="champion-input">
                                <input type="text" id="enemyChampInput" placeholder="Enter champion name">
                                <button type="button" onclick="addChampion('enemy')">Add</button>
                            </div>
                            <div id="enemyList" class="champion-list"></div>
                            <div class="help-text">Enter champion names one at a time</div>
                        </div>
                        
                        <button type="submit">Get Pre-Game Advice</button>
                        <div id="preGameLoading" class="loading">
                            <div class="spinner"></div>
                            <p style="margin-top: 10px;">Processing...</p>
                        </div>
                        <div id="preGameResult" class="result"></div>
                    </form>
                </div>
                
                <!-- In-Game QA Card -->
                <div class="card">
                    <h2>In-Game Q&A</h2>
                    <form id="ingameForm">
                        <div class="form-group">
                            <label>Patch (optional)</label>
                            <input type="text" id="ingamePatch" placeholder="e.g., 15.20 (defaults to latest)">
                        </div>
                        
                        <div class="form-group">
                            <label>Your Champion</label>
                            <input type="text" id="myChamp" placeholder="e.g., Jinx" required>
                        </div>
                        
                        <div class="form-group">
                            <label>Question</label>
                            <textarea id="question" placeholder="Ask a question about strategy, items, or gameplay..." required></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Game State (optional JSON)</label>
                            <textarea id="gameState" placeholder='{"gold": 3000, "level": 8, ...}'></textarea>
                            <div class="help-text">Optional: JSON object with current game state</div>
                        </div>
                        
                        <button type="submit">Ask Question</button>
                        <div id="ingameLoading" class="loading">
                            <div class="spinner"></div>
                            <p style="margin-top: 10px;">Processing...</p>
                        </div>
                        <div id="ingameResult" class="result"></div>
                    </form>
                </div>
            </div>
            
            <div class="links">
                <a href="/docs">API Documentation</a>
                <a href="/openapi.json">OpenAPI Spec</a>
            </div>
        </div>
        
        <script>
            const allyChamps = [];
            const enemyChamps = [];
            
            function addChampion(type) {
                const input = type === 'ally' ? document.getElementById('allyChampInput') : document.getElementById('enemyChampInput');
                const list = type === 'ally' ? document.getElementById('allyList') : document.getElementById('enemyList');
                const champs = type === 'ally' ? allyChamps : enemyChamps;
                
                const champName = input.value.trim();
                if (champName && !champs.includes(champName)) {
                    champs.push(champName);
                    renderChampionList(list, champs, type);
                    input.value = '';
                }
            }
            
            function removeChampion(type, champName) {
                const champs = type === 'ally' ? allyChamps : enemyChamps;
                const index = champs.indexOf(champName);
                if (index > -1) {
                    champs.splice(index, 1);
                    const list = type === 'ally' ? document.getElementById('allyList') : document.getElementById('enemyList');
                    renderChampionList(list, champs, type);
                }
            }
            
            function renderChampionList(list, champs, type) {
                list.innerHTML = champs.map(champ => 
                    `<span class="champion-tag">${champ}<span class="remove" onclick="removeChampion('${type}', '${champ}')">×</span></span>`
                ).join('');
            }
            
            // Allow Enter key to add champions
            document.getElementById('allyChampInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addChampion('ally');
                }
            });
            
            document.getElementById('enemyChampInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addChampion('enemy');
                }
            });
            
            document.getElementById('preGameForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const loading = document.getElementById('preGameLoading');
                const result = document.getElementById('preGameResult');
                
                if (allyChamps.length === 0 || enemyChamps.length === 0) {
                    alert('Please add at least one champion to both teams');
                    return;
                }
                
                loading.classList.add('show');
                result.classList.remove('show');
                
                const patch = document.getElementById('preGamePatch').value.trim() || null;
                const myChamp = document.getElementById('preGameMyChamp').value.trim();
                const allyComp = [...allyChamps];
                // Add your champion to ally comp if provided and not already in list
                if (myChamp && !allyComp.includes(myChamp)) {
                    allyComp.unshift(myChamp); // Add at the beginning
                }
                const payload = {
                    ally_comp: allyComp,
                    enemy_comp: enemyChamps
                };
                if (patch) payload.patch = patch;
                
                try {
                    const response = await fetch('/pre_game_advice', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    
                    const data = await response.json();
                    result.innerHTML = '<h3>Result:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    result.classList.add('show');
                } catch (error) {
                    result.innerHTML = '<h3>Error:</h3><pre>' + error.message + '</pre>';
                    result.classList.add('show');
                } finally {
                    loading.classList.remove('show');
                }
            });
            
            document.getElementById('ingameForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const loading = document.getElementById('ingameLoading');
                const result = document.getElementById('ingameResult');
                
                loading.classList.add('show');
                result.classList.remove('show');
                
                const patch = document.getElementById('ingamePatch').value.trim() || null;
                const gameStateStr = document.getElementById('gameState').value.trim();
                let gameState = null;
                if (gameStateStr) {
                    try {
                        gameState = JSON.parse(gameStateStr);
                    } catch (e) {
                        alert('Invalid JSON in Game State field');
                        loading.classList.remove('show');
                        return;
                    }
                }
                
                const payload = {
                    my_champ: document.getElementById('myChamp').value.trim(),
                    question: document.getElementById('question').value.trim()
                };
                if (patch) payload.patch = patch;
                if (gameState) payload.state = gameState;
                
                try {
                    const response = await fetch('/ingame_qa', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    
                    const data = await response.json();
                    result.innerHTML = '<h3>Result:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    result.classList.add('show');
                } catch (error) {
                    result.innerHTML = '<h3>Error:</h3><pre>' + error.message + '</pre>';
                    result.classList.add('show');
                } finally {
                    loading.classList.remove('show');
                }
            });
        </script>
    </body>
    </html>
    """


@app.post("/pre_game_advice")
def pre_game_advice(body: PreGameAdviceInput):
    patch = body.patch or DEFAULT_PATCH
    if not body.ally_comp or not body.enemy_comp:
        raise HTTPException(status_code=400, detail="ally_comp and enemy_comp are required")
    inputs = AgentInputs(mode="pre_game", ally_comp=body.ally_comp, enemy_comp=body.enemy_comp)
    state = build_initial_state(patch=patch, inputs=inputs, profile=body.profile)
    state = run_pev(state)
    if not state.final:
        raise HTTPException(status_code=500, detail={"verify": state.verify.model_dump() if state.verify else None})
    return state.final.model_dump()


@app.post("/ingame_qa")
def ingame_qa(body: IngameQAInput):
    patch = body.patch or DEFAULT_PATCH
    inputs = AgentInputs(mode="ingame_qa", my_champ=body.my_champ, question=body.question, state=body.state)
    state = build_initial_state(patch=patch, inputs=inputs, profile=body.profile)
    state = run_pev(state)
    if not state.final:
        raise HTTPException(status_code=500, detail={"verify": state.verify.model_dump() if state.verify else None})
    return state.final.model_dump()


