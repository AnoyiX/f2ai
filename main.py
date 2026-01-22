import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Literal

from utils.converter import process_file
from utils.file_handler import save_upload_file
from utils.vector_engine import VectorEngine

load_dotenv()

app = FastAPI(version="0.4.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = VectorEngine()

class VectorItem(BaseModel):
    type: Literal["text", "image_url"]
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

class StoreRequest(BaseModel):
    items: List[VectorItem]
    collection: str

class SearchRequest(BaseModel):
    item: VectorItem
    limit: int = 5
    collection: str

def verify_token(token: Optional[str]) -> None:
    api_token = os.getenv("API_TOKEN")
    if api_token:
        if not token or token != api_token:
            raise HTTPException(status_code=401, detail="Invalid or missing API Token")


@app.post("/api/process")
async def process_upload(
    token: str | None = Form(None),
    file: UploadFile = File(...),
    imgH: int = Form(1024),
    imgW: int = Form(1024),
    enbaleV2I: bool = Form(True),
    videoFPS: float = Form(1.0),
    enableA2T: bool = Form(True),
    audioLanguage: str | None = Form(None)
):
    api_token = os.getenv("API_TOKEN")
    if api_token:
        if not token or token != api_token:
            raise HTTPException(status_code=401, detail="Invalid or missing API Token")
    try:
        # 1. Save File
        file_info = await save_upload_file(file)

        # 2. Process File (Convert/Read)
        ai_data = process_file(file_info, imgW, imgH, enbaleV2I, videoFPS, enableA2T, audioLanguage)

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

@app.post("/api/vector/store")
async def vector_store(req: StoreRequest, token: Optional[str] = Header(None)):
    verify_token(token)
    try:
        volc_inputs: List[Dict[str, Any]] = []
        payloads: List[Dict[str, Any]] = []
        for it in req.items:
            if it.type == "text" and it.text:
                volc_inputs.append({"type": "text", "text": it.text})
                payloads.append({"type": "text", "text": it.text, **(it.metadata or {})})
            elif it.type == "image_url" and it.image_url and it.image_url.get("url"):
                volc_inputs.append({"type": "image_url", "image_url": {"url": it.image_url["url"]}})
                payloads.append({"type": "image_url", "image_url": it.image_url, **(it.metadata or {})})
        embeddings = await engine.get_embeddings(volc_inputs)
        ids = engine.upsert_vectors(embeddings, payloads, req.collection)
        return JSONResponse(content={
            "code": 200,
            "message": "success",
            "data": {"count": len(ids), "ids": ids}
        })
    except Exception as e:
        return JSONResponse(content={"code": 500, "message": str(e), "data": None})

@app.post("/api/vector/search")
async def vector_search(req: SearchRequest, token: Optional[str] = Header(None)):
    verify_token(token)
    try:
        it = req.item
        if it.type == "text" and it.text:
            volc_input = [{"type": "text", "text": it.text}]
        elif it.type == "image_url" and it.image_url and it.image_url.get("url"):
            volc_input = [{"type": "image_url", "image_url": {"url": it.image_url["url"]}}]
        else:
            raise HTTPException(status_code=400, detail="Invalid input")
        emb = await engine.get_embeddings(volc_input)
        results = engine.search_vectors(emb[0], limit=req.limit, collection_name=req.collection)
        return JSONResponse(content={"code": 200, "message": "success", "data": {"items": results}})
    except Exception as e:
        return JSONResponse(content={"code": 500, "message": str(e), "data": None})
 

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
