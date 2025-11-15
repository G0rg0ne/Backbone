from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from unstructured.partition.pdf import partition_pdf
from loguru import logger
import tempfile
import os
from typing import Dict, Any
from pydantic import BaseModel

class ProcessPDFRequest(BaseModel):
    file: UploadFile = File(...)

class ProcessPDFResponse(BaseModel):
    status: str
    content: str
    num_elements: int
    file_size_mb: float

#define logger file for logging in the /logs folder add also the date and time format add the info level
logger.add("logs/document_processor.log", rotation="100 MB", retention="10 days", format="{time} {level} {message}", level="INFO")


#Define FastAPI app
app = FastAPI(title="PDF Document Processor", version="1.0.0")

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "healthy"}

@app.post("/process_pdf_file", response_model=ProcessPDFResponse)
async def process_pdf_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Process a PDF file and return its content using unstructured.
    
    Args:
        file: The uploaded PDF file
        
    Returns:
        Dictionary containing the extracted content and metadata
    """
    # Create a temporary file to save the uploaded PDF
    temp_file_path = None
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        file_size_mb = file_size / (1024 * 1024)
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing PDF file: {file.filename}")
        
        # Use unstructured to partition the PDF
        elements = partition_pdf(
            filename=temp_file_path,
            strategy="auto",
            infer_table_structure=True,
        )
        
        # Extract text content from elements
        extracted_text = "\n\n".join([str(element) for element in elements])
        
        logger.info(f"Successfully processed PDF: {file.filename}, extracted {len(elements)} elements")
        
        return {
            "status": "success",
            "content": extracted_text,
            "num_elements": len(elements),
            "file_size_mb": file_size_mb,
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF file {file.filename if hasattr(file, 'filename') else 'unknown'}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

