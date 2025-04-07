"""
Example FastAPI server that uses YPY SQLite for document persistence.

To run this example:
1. Install dependencies: pip install fastapi uvicorn websockets
2. Run the server: uvicorn web_server:app --reload
3. Open a browser to http://localhost:8000
"""

import asyncio
import json
import y_py as Y
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import base64
from ypy_sqlite import SQLitePersistence

app = FastAPI()

# Database setup
DB_PATH = "web_server_example.db"
persistence = None

# Connected clients by document name
connected_clients = {}


async def get_persistence():
    global persistence
    if persistence is None:
        persistence = await SQLitePersistence.build(DB_PATH)
    return persistence


async def encode_update_for_client(update):
    """Encode an update as base64 for sending over websocket"""
    return base64.b64encode(update).decode('utf-8')


async def decode_update_from_client(b64_update):
    """Decode base64 update from client"""
    return base64.b64decode(b64_update)


@app.on_event("startup")
async def startup_event():
    # Initialize persistence
    await get_persistence()


@app.on_event("shutdown")
async def shutdown_event():
    global persistence
    if persistence:
        await persistence.destroy()


@app.websocket("/ws/{doc_name}")
async def websocket_endpoint(websocket: WebSocket, doc_name: str):
    await websocket.accept()
    
    # Add client to connected clients for this document
    if doc_name not in connected_clients:
        connected_clients[doc_name] = []
    connected_clients[doc_name].append(websocket)
    
    # Get document persistence
    db = await get_persistence()
    
    try:
        # Get the current document
        ydoc = await db.get_ydoc(doc_name)
        
        # Send the initial state to the client
        initial_update = Y.encode_state_as_update(ydoc)
        await websocket.send_json({
            "type": "sync",
            "update": await encode_update_for_client(initial_update)
        })
        
        # Process messages from this client
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "update":
                # Client sent an update
                update = await decode_update_from_client(data["update"])
                
                # Apply to YDoc
                Y.apply_update(ydoc, update)
                
                # Store in database
                await db.store_update(doc_name, update)
                
                # Broadcast to other clients
                for client in connected_clients[doc_name]:
                    if client != websocket:
                        await client.send_json({
                            "type": "update",
                            "update": data["update"]  # Forward as-is
                        })
            
            elif data["type"] == "sync":
                # Client requests sync (sends its state vector)
                state_vector = await decode_update_from_client(data["stateVector"])
                
                # Get the differences
                diff = Y.encode_state_as_update(ydoc, state_vector)
                
                # Send back the differences
                await websocket.send_json({
                    "type": "sync",
                    "update": await encode_update_for_client(diff)
                })
    
    except WebSocketDisconnect:
        # Remove from connected clients
        connected_clients[doc_name].remove(websocket)
        if not connected_clients[doc_name]:
            del connected_clients[doc_name]


@app.get("/", response_class=HTMLResponse)
async def get_root():
    """Serve a simple demo HTML page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YPY SQLite Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            textarea { width: 100%; height: 200px; margin-bottom: 10px; }
            #status { margin-bottom: 20px; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/yjs@13.5.0/dist/y.js"></script>
    </head>
    <body>
        <h1>YPY SQLite Demo</h1>
        <div id="status">Status: Disconnected</div>
        <div>
            <label for="docName">Document Name:</label>
            <input type="text" id="docName" value="example-doc">
            <button id="connect">Connect</button>
        </div>
        <h2>Shared Text:</h2>
        <textarea id="editor" disabled></textarea>
        
        <script>
            const statusEl = document.getElementById('status');
            const editorEl = document.getElementById('editor');
            const docNameEl = document.getElementById('docName');
            const connectBtn = document.getElementById('connect');
            
            let ws = null;
            let ydoc = null;
            let ytext = null;
            
            // Base64 utility functions
            function base64ToUint8Array(base64) {
                const binary = atob(base64);
                const len = binary.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {
                    bytes[i] = binary.charCodeAt(i);
                }
                return bytes;
            }
            
            function uint8ArrayToBase64(bytes) {
                const binary = String.fromCharCode.apply(null, bytes);
                return btoa(binary);
            }
            
            connectBtn.addEventListener('click', () => {
                const docName = docNameEl.value.trim();
                if (!docName) return;
                
                // Disconnect if already connected
                if (ws) {
                    ws.close();
                    ws = null;
                    ydoc = null;
                    ytext = null;
                    editorEl.disabled = true;
                    editorEl.value = '';
                    statusEl.textContent = 'Status: Disconnected';
                }
                
                // Create a new Yjs document
                ydoc = new Y.Doc();
                ytext = ydoc.getText('text');
                
                // Connect to WebSocket
                const wsUrl = `ws://${window.location.host}/ws/${docName}`;
                ws = new WebSocket(wsUrl);
                
                // Handle connection events
                ws.onopen = () => {
                    statusEl.textContent = `Status: Connected to ${docName}`;
                    editorEl.disabled = false;
                    
                    // Send initial sync request
                    const stateVector = Y.encodeStateVector(ydoc);
                    ws.send(JSON.stringify({
                        type: 'sync',
                        stateVector: uint8ArrayToBase64(stateVector)
                    }));
                };
                
                ws.onclose = () => {
                    statusEl.textContent = 'Status: Disconnected';
                    editorEl.disabled = true;
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    statusEl.textContent = 'Status: Error';
                };
                
                // Handle incoming messages
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'sync' || data.type === 'update') {
                        const update = base64ToUint8Array(data.update);
                        Y.applyUpdate(ydoc, update);
                    }
                };
                
                // Set up editor binding
                ytext.observe(event => {
                    // Update the textarea when the ytext changes
                    editorEl.value = ytext.toString();
                });
                
                // Listen to textarea changes
                editorEl.addEventListener('input', () => {
                    const currentValue = editorEl.value;
                    ydoc.transact(() => {
                        ytext.delete(0, ytext.length);
                        ytext.insert(0, currentValue);
                    });
                    
                    // Send update to server
                    const update = Y.encodeStateAsUpdate(ydoc);
                    ws.send(JSON.stringify({
                        type: 'update',
                        update: uint8ArrayToBase64(update)
                    }));
                });
            });
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)