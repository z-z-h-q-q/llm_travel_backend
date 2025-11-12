from fastapi import APIRouter, Request, HTTPException, WebSocket

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post('/recognize')
async def recognize_audio(request: Request):
    """Speech recognition via server-side providers has been removed.

    Clients should perform speech-to-text in the browser (Web Speech API)
    and send text to the AI parsing endpoints. This endpoint now returns
    501 Not Implemented to avoid accidental use.
    """
    raise HTTPException(status_code=501, detail=(
        "Server-side speech recognition has been disabled and removed. "
        "Please use client-side Web Speech API and send recognized text to the AI parsing endpoint."
    ))


@router.websocket('/stream')
async def stream_proxy(websocket: WebSocket):
    """Streaming proxy has been removed. Accept connection and inform client."""
    await websocket.accept()
    await websocket.send_text('{"error": "Server-side streaming speech proxy has been removed. Use client-side recording."}')
    await websocket.close()
    
