import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Agents"))

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.connections import connections

app = FastAPI(title="Prospera API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "linkedin-assistant-6quz1j1jp-tredips-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared WebSocket store — defined before router import ─────


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connections[session_id] = websocket
    print(f"  [WS] ✓ Connected: {session_id[:8]}...")
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connections.pop(session_id, None)
        print(f"  [WS] ✗ Disconnected: {session_id[:8]}...")

# ── Router imported AFTER connections defined ─────────────────
from backend.routes.pipeline import router
app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    print("🚀 Backend is running...")