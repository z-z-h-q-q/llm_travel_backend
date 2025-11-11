from fastapi import APIRouter, UploadFile, File, HTTPException
from ..providers.speech_provider import transcribe_and_extract_basicinfo

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post('/recognize')
async def recognize_audio(file: UploadFile = File(...)):
    content = await file.read()
    try:
        result = await transcribe_and_extract_basicinfo(content, fmt=file.filename.split('.')[-1])
        # result: { text: str, basic_info: dict }
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
