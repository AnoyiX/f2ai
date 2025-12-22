import uvicorn
import os
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from utils.converter import process_file
from utils.file_handler import save_upload_file

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


async def verify_token(x_api_token: str | None = Header(default=None, alias="X-API-Token")):
    """
    Verify API Token from Header X-API-Token
    If API_TOKEN env var is set, request must include valid X-API-Token
    """
    env_token = os.getenv("API_TOKEN")
    if env_token:
        if not x_api_token or x_api_token != env_token:
            raise HTTPException(status_code=401, detail="Invalid or missing API Token")
    return x_api_token


@app.post("/api/process", dependencies=[Depends(verify_token)])
async def process_upload(
    file: UploadFile = File(...),
    imgH: int = Form(1024),
    imgW: int = Form(1024),
    enbaleV2I: bool = Form(True),
    videoFPS: float = Form(1.0)
):
    try:
        # 1. Save File
        file_info = await save_upload_file(file)

        # 2. Process File (Convert/Read)
        ai_data = process_file(file_info, imgW, imgH, enbaleV2I, videoFPS)

        # 3. Construct Response
        response_data = {
            "code": 200,
            "message": "success",
            "data": {
                "file": {
                    "url": file_info['url'],
                    "size": file_info['size'],
                    "name": file_info['name'],
                    "md5": file_info['md5'],
                    "contentType": file_info['contentType']
                },
                "ai": ai_data
            }
        }
        return JSONResponse(content=response_data)

    except Exception as e:
        return JSONResponse(content={
            "code": 500,
            "message": str(e),
            "data": None
        })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
