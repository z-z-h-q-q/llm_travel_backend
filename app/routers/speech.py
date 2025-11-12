from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Request
from ..providers.speech_provider import transcribe_and_extract_basicinfo
from ..providers.iflytek_provider import make_iflytek_ws_url
import asyncio
import json
import base64

router = APIRouter(prefix="/speech", tags=["speech"]) 


@router.post('/recognize')
async def recognize_audio(request: Request):
    """Accept multipart/form-data with either 'file' or 'audio' field for compatibility with different clients.

    Returns { text, basic_info } on success.
    """
    # Support JSON body with base64 audio for clients that send application/json
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        body = await request.json()
        # accept fields: audio (base64), audio_base64, audio_b64
        audio_b64 = body.get('audio') or body.get('audio_base64') or body.get('audio_b64')
        if not audio_b64:
            raise HTTPException(status_code=422, detail="Missing 'audio' (base64) in JSON body")
        try:
            content = base64.b64decode(audio_b64)
        except Exception:
            raise HTTPException(status_code=400, detail='audio field is not valid base64')
        fmt = (body.get('format') or body.get('fmt') or body.get('filename') or 'wav').split('.')[-1]
        try:
            result = await transcribe_and_extract_basicinfo(content, fmt=fmt)
            return result
        except RuntimeError as e:
            msg = str(e)
            # If it's an upstream iFlyTek/httpx error, surface as 502 Bad Gateway
            if any(k in msg.lower() for k in ("upstream", "iflytek", "http error", "request failed", "client error")):
                raise HTTPException(status_code=502, detail=msg)
            raise HTTPException(status_code=400, detail=msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Otherwise expect multipart/form-data with either 'file' or 'audio' field
    form = await request.form()
    upload = form.get('file') or form.get('audio')
    if not upload:
        raise HTTPException(status_code=422, detail="Missing 'file' or 'audio' form field")

    # upload is an UploadFile-like object
    content = await upload.read()
    try:
        filename = getattr(upload, 'filename', '') or 'recording.wav'
        result = await transcribe_and_extract_basicinfo(content, fmt=filename.split('.')[-1])
        return result
    except RuntimeError as e:
        msg = str(e)
        if any(k in msg.lower() for k in ("upstream", "iflytek", "http error", "request failed", "client error")):
            raise HTTPException(status_code=502, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket('/stream')
async def stream_proxy(websocket: WebSocket):
    """Proxy WebSocket between frontend and iFlyTek IAT service.

    Frontend protocol (simple):
      - send binary frames for audio data (raw PCM/16k/16bit mono)
      - send the text message 'EOS' to indicate end of stream
      - server will forward recognition updates as JSON messages:
          {"type":"partial","text":"..."}
          {"type":"final","text":"..."}
          or raw detailed payload under {"type":"raw","data": ...}

    Note: this proxy doesn't implement authentication for clients. Use HTTPS/WSS and deploy behind auth in production.
    """
    await websocket.accept()

    # Build iFlyTek wss URL using configured keys
    from ..config import settings
    if not settings.XUNFEI_API_KEY or not settings.XUNFEI_API_SECRET:
        await websocket.send_text(json.dumps({"error": "iFlyTek API key/secret not configured on server"}))
        await websocket.close()
        return

    iat_url = make_iflytek_ws_url(settings.XUNFEI_API_KEY, settings.XUNFEI_API_SECRET, None)

    # Use websockets client to connect to iFlyTek
    import websockets

    try:
        async with websockets.connect(iat_url, ping_interval=20, ping_timeout=20) as ws:

            async def frontend_to_iflytek():
                """Read binary frames from frontend and send JSON frames to iFlyTek.
                We'll number seq starting at 1.
                """
                seq = 1
                first = True
                try:
                    while True:
                        msg = await websocket.receive()
                        if msg.get("type") == "websocket.receive":
                            if "bytes" in msg:
                                chunk = msg["bytes"]
                                audio_b64 = base64.b64encode(chunk).decode()
                                status = 0 if first else 1
                                first = False
                                body = {
                                    "header": {"app_id": settings.XUNFEI_APPID, "status": status},
                                    "parameter": {
                                        "iat": {
                                            "domain": "slm",
                                            "language": "zh_cn",
                                            "accent": "mandarin",
                                            "eos": 6000,
                                            "vinfo": 1,
                                            "dwa": "wpgs",
                                            "result": {"encoding": "utf8", "compress": "raw", "format": "json"},
                                        }
                                    },
                                    "payload": {
                                        "audio": {
                                            "encoding": "raw",
                                            "sample_rate": 16000,
                                            "channels": 1,
                                            "bit_depth": 16,
                                            "seq": seq,
                                            "status": status,
                                            "audio": audio_b64,
                                        }
                                    },
                                }
                                await ws.send(json.dumps(body))
                                seq += 1
                            elif "text" in msg:
                                text = msg["text"]
                                if isinstance(text, str) and text.strip().upper() == "EOS":
                                    # send final empty frame with status=2
                                    body = {
                                        "header": {"app_id": settings.XUNFEI_APPID, "status": 2},
                                        "payload": {"audio": {"encoding": "raw", "sample_rate": 16000, "channels": 1, "bit_depth": 16, "seq": seq, "status": 2, "audio": ""}}
                                    }
                                    await ws.send(json.dumps(body))
                                    return
                                else:
                                    # ignore other text messages for now
                                    continue
                        else:
                            # other types (disconnect)
                            return
                except WebSocketDisconnect:
                    return

            async def iflytek_to_frontend():
                """Receive messages from iFlyTek, decode and forward to frontend."""
                try:
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                        except Exception:
                            # non-json message, forward raw
                            await websocket.send_text(json.dumps({"type": "raw", "data": msg}))
                            continue

                        # forward basic fields
                        header = data.get("header", {})
                        payload = data.get("payload", {})
                        result = payload.get("result") or {}

                        text_b64 = result.get("text")
                        if text_b64:
                            try:
                                decoded = base64.b64decode(text_b64)
                                try:
                                    inner = json.loads(decoded)
                                except Exception:
                                    # plain text
                                    t = decoded.decode("utf-8", errors="ignore")
                                    await websocket.send_text(json.dumps({"type": "partial", "text": t}))
                                    continue

                                # assemble text from ws->cw->w
                                result_words = []
                                for seg in inner.get("ws", []):
                                    for cw in seg.get("cw", []):
                                        w = cw.get("w")
                                        if w:
                                            result_words.append(w)

                                joined = "".join(result_words)

                                # detect last-frame status
                                status = result.get("status")  # 0/1/2
                                if status == 2 or header.get("status") == 2 or inner.get("ls"):
                                    await websocket.send_text(json.dumps({"type": "final", "text": joined, "raw": inner}))
                                else:
                                    await websocket.send_text(json.dumps({"type": "partial", "text": joined, "raw": inner}))
                            except Exception as e:
                                await websocket.send_text(json.dumps({"type": "error", "error": str(e)}))
                        else:
                            # forward raw payload for debugging
                            await websocket.send_text(json.dumps({"type": "raw", "data": data}))
                except websockets.exceptions.ConnectionClosed:
                    return

            # run both tasks concurrently until completion
            tasks = [asyncio.create_task(frontend_to_iflytek()), asyncio.create_task(iflytek_to_frontend())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()

    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
    
