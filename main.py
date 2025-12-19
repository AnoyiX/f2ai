import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from utils.converter import process_file
from utils.file_handler import save_upload_file

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/process")
async def process_upload(file: UploadFile = File(...)):
    try:
        # 1. Save File
        file_info = await save_upload_file(file)
        
        # 2. Process File (Convert/Read)
        ai_data = process_file(file_info)
        
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
