import os
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils.converter import process_file
from utils.file_handler import save_upload_file
from utils.vector_engine import VectorEngine

load_dotenv()

app = FastAPI(version="0.4.1")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = VectorEngine()


class StoreRequest(BaseModel):
    items: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    collection: str


class SearchRequest(BaseModel):
    items: List[Dict[str, Any]]
    limit: int = 5
    collection: str


class ClearRequest(BaseModel):
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
    audioLanguage: str | None = Form(None),
    h_token: str | None = Header(None, alias="token")
):
    verify_token(token or h_token)
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
        types = []
        for item in {x['type'] for x in req.items}:
            if 'text' in item:
                types.append("text")
            elif 'image' in item:
                types.append("image")
            elif 'video' in item:
                types.append("video")
        instructions = f"Instruction:Compress the {'/'.join(types)} into one word.\nQuery:"
        embedding = await engine.get_embedding(req.items, instructions)
        payload = {
            'items': req.items,
            **(req.metadata or {})
        }
        id = engine.upsert_vector(embedding, payload, req.collection)
        return JSONResponse(content={
            "code": 200,
            "message": "success",
            "data": {"id": id}
        })
    except Exception as e:
        return JSONResponse(content={"code": 500, "message": str(e), "data": None})


@app.post("/api/vector/search")
async def vector_search(req: SearchRequest, token: Optional[str] = Header(None)):
    verify_token(token)
    try:
        types = []
        for item in {x['type'] for x in req.items}:
            if 'text' in item:
                types.append("text")
            elif 'image' in item:
                types.append("image")
            elif 'video' in item:
                types.append("video")
        instructions = f"Target_modality: {' and '.join(types)}.\nInstruction:Compress the {'/'.join(types)} into one word.\nQuery:"
        embedding = await engine.get_embedding(req.items, instructions)
        results = engine.search_vectors(embedding, limit=req.limit, collection_name=req.collection)
        return JSONResponse(content={"code": 200, "message": "success", "data": {"items": results}})
    except Exception as e:
        return JSONResponse(content={"code": 500, "message": str(e), "data": None})


@app.post("/api/vector/clear")
async def vector_clear(req: ClearRequest, token: Optional[str] = Header(None)):
    verify_token(token)
    try:
        success = engine.delete_collection(req.collection)
        return JSONResponse(content={
            "code": 200,
            "message": "success" if success else "collection not found",
            "data": {"deleted": success}
        })
    except Exception as e:
        return JSONResponse(content={"code": 500, "message": str(e), "data": None})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
