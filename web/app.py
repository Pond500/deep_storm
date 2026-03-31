"""
SansarnWiki Web API
FastAPI backend for STORM and Co-STORM article generation
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
from pathlib import Path
import asyncio
from typing import Optional, Dict
import json
import hashlib

# Add STORM paths
sys.path.insert(0, str(Path(__file__).parent.parent / "storm"))
sys.path.insert(0, str(Path(__file__).parent.parent / "storm" / "wiki"))

# Resolve OpenRouter API key — validate format to catch placeholder values like
# "YOUR_NEW_KEY_HERE" that users may have accidentally left in their shell env.
_FALLBACK_KEY = "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"
_env_key = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_API_KEY = _env_key if _env_key.startswith("sk-or-") else _FALLBACK_KEY
os.environ["OPENROUTER_API_KEY"] = _OPENROUTER_API_KEY  # always set the valid key
os.environ["ENCODER_API_TYPE"] = "openai"

app = FastAPI(title="SansarnWiki API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections and Co-STORM states
active_connections: Dict[str, WebSocket] = {}
costorm_states: Dict[str, dict] = {}  # Store Co-STORM conversation states

# Request/Response models
class GenerateRequest(BaseModel):
    topic: str
    mode: str = "storm"  # "storm" or "costorm"
    settings: dict = None  # Optional settings for research parameters

class UserResponseRequest(BaseModel):
    client_id: str
    response: str  # User's answer or "SKIP" or "DONE"

class GenerateResponse(BaseModel):
    topic: str
    mode: str
    article: str
    metadata: Optional[dict] = None
    client_id: str  # Add client_id to response

# Import STORM modules (lazy loading)
def get_storm_runner():
    """Import and configure STORM runner"""
    from test_storm_hybrid import setup_storm_runner
    return setup_storm_runner
    
def get_costorm_runner():
    """Import and configure Co-STORM runner"""
    from test_costorm_hybrid import setup_costorm_with_hybrid
    return setup_costorm_with_hybrid

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("index.html")

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json

# Store active connections
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    active_connections[client_id] = websocket
    print(f"🔌 WebSocket CONNECTED: client_id={client_id}")
    print(f"   Total active connections: {len(active_connections)}")
    
    try:
        while True:
            data = await websocket.receive_text()
            # Keep connection alive
            print(f"📨 Received from client: {data}")
    except WebSocketDisconnect:
        del active_connections[client_id]
        print(f"🔌 WebSocket DISCONNECTED: client_id={client_id}")
        print(f"   Total active connections: {len(active_connections)}")

async def send_progress(client_id: str, step: str, progress: int, message: str):
    """Send progress update to connected WebSocket client"""
    print(f"📤 Sending progress: client_id={client_id}, step={step}, progress={progress}%")
    if client_id in active_connections:
        try:
            await active_connections[client_id].send_json({
                "type": "progress",
                "step": step,
                "progress": progress,
                "message": message
            })
            print(f"   ✅ Sent successfully")
        except Exception as e:
            print(f"   ❌ Failed to send: {e}")
    else:
        print(f"   ⚠️ Client not connected yet")

async def send_question(client_id: str, question: str, context: str = ""):
    """Send question to user via WebSocket and wait for response"""
    print(f"❓ Sending question: client_id={client_id}")
    if client_id in active_connections:
        try:
            await active_connections[client_id].send_json({
                "type": "question",
                "question": question,
                "context": context
            })
            print(f"   ✅ Question sent, waiting for response...")
            
            # Wait for response (stored in costorm_states)
            if client_id not in costorm_states:
                costorm_states[client_id] = {"waiting": True, "response": None}
            else:
                costorm_states[client_id]["waiting"] = True
                costorm_states[client_id]["response"] = None
            
            # Wait for response with timeout (60 seconds)
            for _ in range(600):  # 60 seconds (0.1s intervals)
                await asyncio.sleep(0.1)
                if not costorm_states[client_id]["waiting"]:
                    response = costorm_states[client_id]["response"]
                    print(f"   ✅ Got response: {response[:50]}...")
                    return response
            
            # Timeout - return SKIP
            print(f"   ⏱️ Timeout - auto SKIP")
            return "SKIP"
            
        except Exception as e:
            print(f"   ❌ Failed to send question: {e}")
            return "SKIP"
    else:
        print(f"   ⚠️ Client not connected")
        return "SKIP"

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_article(request: GenerateRequest):
    """
    Generate article using STORM or Co-STORM
    
    - **topic**: The topic to generate article about
    - **mode**: Generation mode ("storm" or "costorm")
    """
    try:
        topic = request.topic.strip()
        mode = request.mode.lower()
        
        if not topic:
            raise HTTPException(status_code=400, detail="Topic is required")
        
        if mode not in ["storm", "costorm"]:
            raise HTTPException(status_code=400, detail="Mode must be 'storm' or 'costorm'")
        
        print(f"📝 Generating article: {topic} (mode: {mode})")
        
        # Generate client_id from topic (using SHA-256 to match frontend)
        import hashlib
        client_id = hashlib.sha256(topic.encode()).hexdigest()
        print(f"🔑 Generated client_id: {client_id}")
        print(f"   Active WebSocket connections: {list(active_connections.keys())}")
        
        # Extract settings from request
        settings = request.settings if hasattr(request, 'settings') else None
        
        if mode == "storm":
            # Run STORM with settings
            article, metadata = await run_storm(topic, client_id, settings)
        else:
            # Run Co-STORM with settings
            article, metadata = await run_costorm(topic, client_id, settings)
        
        return GenerateResponse(
            topic=topic,
            mode=mode,
            article=article,
            metadata=metadata,
            client_id=client_id  # Return client_id
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/respond")
async def user_respond(request: UserResponseRequest):
    """
    Receive user's response to Co-STORM question
    
    - **client_id**: The client ID from WebSocket
    - **response**: User's answer, "SKIP", or "DONE"
    """
    try:
        client_id = request.client_id
        response = request.response
        
        print(f"💬 Received user response: client_id={client_id[:16]}...")
        print(f"   Response: {response[:100]}...")
        
        if client_id in costorm_states:
            costorm_states[client_id]["response"] = response
            costorm_states[client_id]["waiting"] = False
            return {"status": "ok", "message": "Response received"}
        else:
            return {"status": "error", "message": "Client not found"}
            
    except Exception as e:
        print(f"❌ Error receiving response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_storm(topic: str, client_id: str, settings: dict = None):
    """Run STORM article generation with progress tracking"""
    try:
        # Use default settings if not provided
        if settings is None:
            settings = {
                "max_conv_turn": 5,
                "max_perspective": 4,
                "search_top_k": 5,
                "max_search_queries_per_turn": 2,
                "retrieve_top_k": 5
            }
        
        print(f"⚙️ STORM Settings: {settings}")
        
        # Step 1: Setup (5%)
        await send_progress(client_id, "setup", 5, "🔧 กำลังเตรียมระบบ...")
        
        # Import here to avoid loading on startup
        sys.path.insert(0, str(Path(__file__).parent.parent / "storm" / "wiki"))
        
        await send_progress(client_id, "setup", 10, "📚 กำลังโหลดโมเดล AI...")
        
        # Dynamic import
        from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
        from knowledge_storm.lm import LitellmModel
        from hybrid_wikipedia_rm import get_shared_instance as get_shared_rm
        
        # Setup LM configs
        lm_configs = STORMWikiLMConfigs()
        
        await send_progress(client_id, "config", 15, "⚙️ กำลังตั้งค่าโมเดล AI...")
        
        lm_configs.conv_simulator_lm = LitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=500,
            temperature=1.0,
            top_p=0.9,
            api_key=_OPENROUTER_API_KEY,
        )
        
        lm_configs.question_asker_lm = LitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=500,
            temperature=1.0,
            top_p=0.9,
            api_key=_OPENROUTER_API_KEY,
        )
        
        lm_configs.outline_gen_lm = LitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=400,
            temperature=1.0,
            top_p=0.9,
            api_key=_OPENROUTER_API_KEY,
        )
        
        lm_configs.article_gen_lm = LitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=700,
            temperature=1.0,
            top_p=0.9,
            api_key=_OPENROUTER_API_KEY,
        )
        
        lm_configs.article_polish_lm = LitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=4000,
            temperature=1.0,
            top_p=0.9,
            api_key=_OPENROUTER_API_KEY,
        )
        
        await send_progress(client_id, "retrieval", 20, "🔍 กำลังเชื่อมต่อกับฐานข้อมูล Wikipedia...")
        
        # Setup runner arguments with user settings
        runner_args = STORMWikiRunnerArguments(
            output_dir=str(Path(__file__).parent.parent / "storm" / "output" / "web_api"),
            max_conv_turn=settings.get("max_conv_turn", 5),
            max_perspective=settings.get("max_perspective", 4),
            search_top_k=settings.get("search_top_k", 5),
            max_search_queries_per_turn=settings.get("max_search_queries_per_turn", 2),
            retrieve_top_k=settings.get("retrieve_top_k", 5),
        )
        
        # Setup Hybrid Retrieval
        rm = get_shared_rm(
            vector_store_path=str(Path(__file__).parent.parent / "storm" / "wiki" / "vector_store"),
            collection_name="wikipedia_thai",
            embedding_model="BAAI/bge-m3",
            reranker_model="BAAI/bge-reranker-v2-m3",
            device="mps",
            k=5,
            use_reranking=True,
            rerank_top_k=20,
            alpha=0.5,
        )
        
        await send_progress(client_id, "init", 25, "✅ ระบบพร้อมแล้ว เริ่มสร้างบทความ...")
        
        # Create runner
        runner = STORMWikiRunner(runner_args, lm_configs, rm)
        
        # Step 2-5: Run STORM with simulated progress (25-95%)
        await send_progress(client_id, "research", 30, "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 1/4)...")
        
        # Run STORM in background while simulating progress
        loop = asyncio.get_event_loop()
        
        # Create async task for STORM execution
        async def run_storm_task():
            return await loop.run_in_executor(
                None,
                lambda: runner.run(
                    topic=topic,
                    do_research=True,
                    do_generate_outline=True,
                    do_generate_article=True,
                    do_polish_article=True,
                )
            )
        
        storm_task = asyncio.create_task(run_storm_task())
        
        # Simulate progress while STORM is running
        progress_steps = [
            (35, "research", "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 2/4, รอบที่ 1/5)..."),
            (40, "research", "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 2/4, รอบที่ 3/5)..."),
            (45, "research", "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 3/4, รอบที่ 2/5)..."),
            (50, "research", "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 3/4, รอบที่ 4/5)..."),
            (55, "research", "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 4/4, รอบที่ 3/5)..."),
            (60, "research", "📚 กำลังค้นคว้าข้อมูล (มุมมองที่ 4/4, รอบที่ 5/5)..."),
            (65, "outline", "📝 กำลังสร้างโครงร่างบทความ..."),
            (70, "outline", "📝 กำลังจัดระเบียบโครงสร้างบทความ..."),
            (75, "writing", "✍️ กำลังเขียนบทความ (ส่วนที่ 1)..."),
            (80, "writing", "✍️ กำลังเขียนบทความ (ส่วนที่ 2)..."),
            (85, "writing", "✍️ กำลังเขียนบทความ (ส่วนที่ 3)..."),
            (90, "polish", "✨ กำลังปรับปรุงบทความให้สมบูรณ์..."),
            (93, "polish", "✨ กำลังตรวจสอบและแก้ไขบทความ..."),
            (96, "polish", "✨ กำลังจัดรูปแบบบทความ..."),
        ]
        
        for progress, step, message in progress_steps:
            if storm_task.done():
                break
            await send_progress(client_id, step, progress, message)
            await asyncio.sleep(3)  # Wait 3 seconds between updates
        
        # Wait for STORM to complete
        await storm_task
        
        await send_progress(client_id, "complete", 100, "🎉 สร้างบทความเสร็จสมบูรณ์!")
        
        # Read generated article
        article_path = Path(runner.article_output_dir) / "storm_gen_article_polished.txt"
        if not article_path.exists():
            article_path = Path(runner.article_output_dir) / "storm_gen_article.txt"
        
        article = article_path.read_text(encoding='utf-8')
        
        # Read references (url_to_info.json)
        references = {}
        ref_path = Path(runner.article_output_dir) / "url_to_info.json"
        if ref_path.exists():
            try:
                ref_data = json.loads(ref_path.read_text(encoding='utf-8'))
                # Convert to frontend format: {1: {title, url, snippet}, 2: {...}}
                url_to_index = ref_data.get("url_to_unified_index", {})
                url_to_info = ref_data.get("url_to_info", {})
                
                for url, index in url_to_index.items():
                    if url in url_to_info:
                        info = url_to_info[url]
                        references[str(index)] = {
                            "title": info.get("title", ""),
                            "url": url.replace("wiki://th/", "https://th.wikipedia.org/wiki/"),
                            "snippet": info.get("snippets", [""])[0] if info.get("snippets") else ""
                        }
                print(f"   ✅ Loaded {len(references)} references")
            except Exception as e:
                print(f"   ⚠️  Could not load references: {e}")
        
        metadata = {
            "output_dir": runner.article_output_dir,
            "perspectives": 4,
            "turns": 5,
            "length": len(article),
            "references": references  # Add references to metadata
        }
        
        return article, metadata
        
    except Exception as e:
        print(f"❌ STORM Error: {e}")
        raise

async def run_costorm(topic: str, client_id: str, settings: dict = None):
    """Run Co-STORM in interactive mode"""
    from costorm_interactive import run_costorm_interactive
    
    # Use default settings if not provided
    if settings is None:
        settings = {
            "total_conv_turn": 20,
            "retrieve_top_k": 5,
            "max_search_queries": 3,
            "warmstart_max_num_experts": 2,
            "warmstart_max_turn_per_experts": 2,
            "max_num_round_table_experts": 2
        }
    
    print(f"⚙️ Co-STORM Settings: {settings}")
    
    return await run_costorm_interactive(topic, client_id, send_progress, send_question, settings)

# Mount static files
app.mount("/", StaticFiles(directory=str(Path(__file__).parent), html=True), name="static")

app.mount("/", StaticFiles(directory=str(Path(__file__).parent), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    
    print("="*80)
    print("🌩️  SansarnWiki Web Server")
    print("="*80)
    print()
    print("🚀 Starting server...")
    print("📂 Web UI: http://localhost:8000")
    print("📡 API Docs: http://localhost:8000/docs")
    print()
    print("💡 Press Ctrl+C to stop")
    print("="*80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
