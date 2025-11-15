import gradio as gr
import os
import time
from loguru import logger
import requests
from dotenv import load_dotenv

load_dotenv()

# Get environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://backbone-backend:8000")

def check_backend_health(max_retries=30, retry_delay=2):
    """
    Check if backend is healthy before starting the frontend.
    """
    logger.info("Waiting for backend to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code == 200:
                logger.info("Backend is healthy and ready!")
                return True
        except Exception as e:
            logger.warning(f"Backend not ready yet (attempt {i+1}/{max_retries}): {e}")
        
        if i < max_retries - 1:
            time.sleep(retry_delay)
    
    logger.error("Backend failed to become healthy. Starting frontend anyway, but it may not work.")
    return False

# Wait for backend to be ready before starting
backend_ready = check_backend_health()

def process_pdf_file(file):
    """
    Process uploaded PDF file and return information about it.
    """
    if file is None:
        return "No file uploaded.", "", "", ""
    
    try:
        # Gradio passes a file path string when type="filepath"
        with open(file, "rb") as f:
            files = {"file": (os.path.basename(file), f, "application/pdf")}
            response = requests.post(f"{BACKEND_URL}/process_pdf_file", files=files, timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            num_elements = data.get("num_elements", 0)
            file_size_mb = data.get("file_size_mb", 0)
            status = data.get("status", "unknown")
            
            return (
                f"**Content:**\n\n{content[:1000]}..." if len(content) > 1000 else f"**Content:**\n\n{content}",
                f"**Number of Elements:** {num_elements}",
                f"**File Size:** {file_size_mb:.2f} MB",
                f"**Status:** {status}"
            )
        else:
            error_msg = f"Error processing PDF file: {response.status_code} {response.text}"
            logger.error(error_msg)
            return error_msg, "", "", ""
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        return f"Error processing PDF file: {e}", "", "", ""


# Create Gradio interface
with gr.Blocks(title="PDF File Uploader", theme=gr.themes.Soft()) as app:
    status_indicator = gr.Markdown(
        value="🟢 **Backend Status:** Ready" if backend_ready else "🔴 **Backend Status:** Not Ready - Please wait...",
        visible=True
    )
    
    gr.Markdown(
        """
        # 📄 PDF File Uploader
        
        Upload a PDF file to view its information and metadata.
        """
    )
    
    with gr.Row():
        with gr.Column():
            file_input = gr.File(
                label="Upload PDF File",
                file_types=[".pdf"],
                type="filepath",
                interactive=backend_ready
            )
            upload_btn = gr.Button(
                "Process PDF", 
                variant="primary",
                interactive=backend_ready
            )
        with gr.Column():
            num_elements_output = gr.Markdown(label="Number of Elements")
            file_size_output = gr.Markdown(label="File Size (MB)")
            status_output = gr.Markdown(label="Status")
            content_output = gr.Markdown(label="Content")
    
    # Event handlers
    upload_btn.click(
        fn=process_pdf_file,
        inputs=file_input,
        outputs=[content_output, num_elements_output, file_size_output, status_output]
    )
    
    # Update status indicator periodically if backend wasn't ready initially
    if not backend_ready:
        def update_status():
            try:
                response = requests.get(f"{BACKEND_URL}/health", timeout=5)
                if response.status_code == 200:
                    # Enable UI components when backend is ready
                    file_input.interactive = True
                    upload_btn.interactive = True
                    return "🟢 **Backend Status:** Ready"
                else:
                    return "🔴 **Backend Status:** Not Ready - Please wait..."
            except:
                return "🔴 **Backend Status:** Not Ready - Please wait..."
        
        app.load(
            fn=update_status,
            outputs=status_indicator,
            every=5  # Check every 5 seconds
        )
    
if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )