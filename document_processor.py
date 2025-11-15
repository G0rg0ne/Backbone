from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from unstructured.partition.pdf import partition_pdf
from loguru import logger
import tempfile
import os
import time
from typing import Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from report_builder import build_report

# Load .env file with error handling for parsing issues
try:
    load_dotenv()
except Exception as e:
    logger.warning(f"Warning loading .env file: {e}. Continuing with environment variables...")

class ProcessPDFRequest(BaseModel):
    file: UploadFile = File(...)

class ProcessPDFResponse(BaseModel):
    status: str
    content: str
    num_elements: int
    file_size_mb: float
    report: str

class GetReportRequest(BaseModel):
    content: str

class GetReportResponse(BaseModel):
    status: str
    report: str

# Configure logger file for logging in the /logs folder with date and time format at INFO level
# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)
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
    # Track overall processing time
    processing_start_time = time.time()
    temp_file_path = None
    filename = file.filename if hasattr(file, 'filename') else 'unknown'
    
    try:
        logger.info(f"=== Starting PDF processing for file: {filename} ===")
        
        # Step 1: Read file content
        logger.info(f"[Step 1/5] Reading uploaded file content: {filename}")
        read_start_time = time.time()
        content = await file.read()
        read_time = time.time() - read_start_time
        file_size = len(content)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"[Step 1/5] ✓ File read complete - Size: {file_size_mb:.2f} MB ({file_size:,} bytes) in {read_time:.2f}s")
        
        # Step 2: Save to temporary file
        logger.info(f"[Step 2/5] Saving file to temporary location")
        temp_start_time = time.time()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        temp_time = time.time() - temp_start_time
        logger.info(f"[Step 2/5] ✓ Temporary file created: {temp_file_path} in {temp_time:.2f}s")
        
        # Step 3: Partition PDF using unstructured
        logger.info(f"[Step 3/5] Starting PDF partitioning with unstructured library")
        logger.info(f"[Step 3/5] Configuration: strategy=auto, infer_table_structure=True, languages=['eng']")
        partition_start_time = time.time()
        elements = partition_pdf(
            filename=temp_file_path,
            strategy="auto",
            infer_table_structure=True,
            languages=["eng"],
        )
        partition_time = time.time() - partition_start_time
        logger.info(f"[Step 3/5] ✓ PDF partitioning complete - Extracted {len(elements)} elements in {partition_time:.2f}s")
        logger.info(f"[Step 3/5] Average time per element: {partition_time/len(elements)*1000:.2f}ms" if len(elements) > 0 else "[Step 3/5] No elements extracted")
        
        # Step 4: Extract text content from elements
        logger.info(f"[Step 4/5] Extracting text content from {len(elements)} elements")
        extraction_start_time = time.time()
        extracted_text = "\n\n".join([str(element) for element in elements])
        extraction_time = time.time() - extraction_start_time
        extracted_text_length = len(extracted_text)
        logger.info(f"[Step 4/5] ✓ Text extraction complete - {extracted_text_length:,} characters extracted in {extraction_time:.2f}s")
        logger.info(f"[Step 4/5] Average characters per element: {extracted_text_length/len(elements):.0f}" if len(elements) > 0 else "[Step 4/5] No text extracted")
        
        # Step 5: Build report
        logger.info(f"[Step 5/5] Starting report generation from extracted content")
        logger.info(f"[Step 5/5] Content length: {extracted_text_length:,} characters")
        report_start_time = time.time()
        report = build_report(extracted_text)
        # Ensure report is always a string
        if report is None:
            logger.warning("[Step 5/5] Report generation returned None, using empty string")
            report = ""
        else:
            report = str(report)
        report_time = time.time() - report_start_time
        report_length = len(report) if report else 0
        logger.info(f"[Step 5/5] ✓ Report generation complete - Generated {report_length:,} characters in {report_time:.2f}s")
        
        # Calculate total processing time
        total_processing_time = time.time() - processing_start_time
        logger.info(f"=== PDF processing complete for {filename} ===")
        logger.info(f"Total processing time: {total_processing_time:.2f}s")
        logger.info(f"Breakdown - Read: {read_time:.2f}s, Temp: {temp_time:.2f}s, Partition: {partition_time:.2f}s, Extract: {extraction_time:.2f}s, Report: {report_time:.2f}s")
        logger.info(f"Final results - Elements: {len(elements)}, Content: {extracted_text_length:,} chars, Report: {report_length:,} chars, File size: {file_size_mb:.2f} MB")

        return {
            "status": "success",
            "content": extracted_text,
            "num_elements": len(elements),
            "file_size_mb": file_size_mb,
            "report": report,
        }
        
    except Exception as e:
        processing_time = time.time() - processing_start_time
        logger.error(f"=== ERROR processing PDF file {filename} ===")
        logger.error(f"Error occurred after {processing_time:.2f}s of processing")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                cleanup_start = time.time()
                os.unlink(temp_file_path)
                cleanup_time = time.time() - cleanup_start
                logger.debug(f"Temporary file {temp_file_path} deleted in {cleanup_time:.3f}s")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
                logger.warning(f"Temporary file may need manual cleanup: {temp_file_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

