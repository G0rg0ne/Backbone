from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from unstructured.partition.pdf import partition_pdf
import os
import tempfile
import shutil
from typing import Dict, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI(title="Backbone PDF Processing API", version="1.0.0")

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using unstructured library."""
    try:
        elements = partition_pdf(filename=pdf_path)
        text = "\n".join([el.text for el in elements if hasattr(el, 'text')])
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload PDF files to the server."""
    uploaded_files = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
        
        # Save file to uploads directory
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_files.append(file.filename)
    
    return {"message": f"Successfully uploaded {len(uploaded_files)} files", "files": uploaded_files}

@app.post("/process-pdfs")
async def process_pdfs(filenames: List[str]):
    """Process uploaded PDF files and extract text."""
    extracted_texts = {}
    errors = []
    
    for filename in filenames:
        if not filename.endswith('.pdf'):
            continue
            
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            errors.append(f"File {filename} not found")
            continue
        
        try:
            # Run PDF processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            extracted_text = await loop.run_in_executor(
                executor, extract_text_from_pdf, file_path
            )
            extracted_texts[filename] = extracted_text
        except Exception as e:
            errors.append(f"Error processing {filename}: {str(e)}")
    
    return {
        "extracted_texts": extracted_texts,
        "errors": errors,
        "processed_count": len(extracted_texts)
    }

@app.get("/files")
async def list_uploaded_files():
    """List all uploaded files."""
    files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if filename.endswith('.pdf'):
                file_path = os.path.join(UPLOAD_DIR, filename)
                file_size = os.path.getsize(file_path)
                files.append({
                    "filename": filename,
                    "size": file_size,
                    "path": file_path
                })
    return {"files": files}

@app.delete("/files")
async def delete_files(filenames: List[str]):
    """Delete specified files from the server."""
    deleted_files = []
    errors = []
    
    for filename in filenames:
        file_path = os.path.join(UPLOAD_DIR, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(filename)
            else:
                errors.append(f"File {filename} not found")
        except Exception as e:
            errors.append(f"Error deleting {filename}: {str(e)}")
    
    return {
        "deleted_files": deleted_files,
        "errors": errors
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Backbone PDF Processing API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
