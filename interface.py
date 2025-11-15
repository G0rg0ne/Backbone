import gradio as gr
import os
import time
from loguru import logger
import requests
from dotenv import load_dotenv
from datetime import datetime

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

def process_pdf_file(file, progress: gr.Progress = gr.Progress()):
    """
    Process uploaded PDF file and return information about it.
    Returns: (report_markdown, report_file_path, metadata_html, status_message)
    """
    if file is None:
        return "", None, "", "⚠️ Please upload a PDF file first."
    
    try:
        progress(0, desc="📤 Uploading PDF to backend...")
        # Gradio passes a file path string when type="filepath"
        with open(file, "rb") as f:
            files = {"file": (os.path.basename(file), f, "application/pdf")}
            progress(0.2, desc="🔄 Processing PDF with backend...")
            response = requests.post(f"{BACKEND_URL}/process_pdf_file", files=files, timeout=300)
        
        progress(0.8, desc="📊 Generating report...")
        if response.status_code == 200:
            data = response.json()
            num_elements = data.get("num_elements", 0)
            file_size_mb = data.get("file_size_mb", 0)
            status = data.get("status", "unknown")
            report = data.get("report", "")
            
            # Create a temporary file for the report
            report_file_path = None
            if report:
                # Create reports directory if it doesn't exist
                os.makedirs("reports", exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(file) if file else "document"
                filename_base = os.path.splitext(filename)[0]
                report_filename = f"{filename_base}_report_{timestamp}.md"
                report_file_path = os.path.join("reports", report_filename)
                
                # Save report to file
                with open(report_file_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Report saved to {report_file_path}")
            
            # Create metadata HTML with dark mode support using semi-transparent backgrounds
            metadata_html = f"""
            <div class="metadata-card" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); border: 2px solid rgba(102, 126, 234, 0.4);">
                <h3 style="margin-top: 0; font-weight: 600; color: inherit;">📄 Document Information</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div class="metadata-item" style="background: rgba(102, 126, 234, 0.15); padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid rgba(102, 126, 234, 0.3);">
                        <strong style="display: block; margin-bottom: 8px; opacity: 0.8;">📊 Elements Extracted</strong>
                        <span style="font-size: 28px; font-weight: bold; color: #667eea;">{num_elements:,}</span>
                    </div>
                    <div class="metadata-item" style="background: rgba(102, 126, 234, 0.15); padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid rgba(102, 126, 234, 0.3);">
                        <strong style="display: block; margin-bottom: 8px; opacity: 0.8;">💾 File Size</strong>
                        <span style="font-size: 28px; font-weight: bold; color: #667eea;">{file_size_mb:.2f} MB</span>
                    </div>
                    <div class="metadata-item" style="background: rgba(102, 126, 234, 0.15); padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid rgba(102, 126, 234, 0.3);">
                        <strong style="display: block; margin-bottom: 8px; opacity: 0.8;">✅ Status</strong>
                        <span style="font-size: 22px; font-weight: bold; color: #4caf50;">{status.title()}</span>
                    </div>
                </div>
            </div>
            """
            
            progress(1.0, desc="✅ Complete!")
            status_message = "✅ **Processing complete!** Report generated successfully."
            
            return report if report else "No report available.", report_file_path, metadata_html, status_message
        else:
            error_msg = f"Error processing PDF file: {response.status_code} {response.text}"
            logger.error(error_msg)
            return "", None, "", f"❌ **Processing failed!** Error: {response.status_code}"
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        return "", None, "", f"❌ **Processing failed!** Error: {str(e)}"


# Create Gradio interface with improved design
with gr.Blocks(
    title="AI Document Analyzer",
    theme=gr.themes.Soft(
        primary_hue="purple",
        secondary_hue="blue",
        font=("ui-sans-serif", "system-ui", "sans-serif")
    )
) as app:
    
    # Header
    with gr.Row():
        gr.Markdown(
            """
            <div style="text-align: center; padding: 20px;">
                <h1 style="margin-bottom: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🤖 Scientific Paper Agent
                </h1>
                <p style="font-size: 16px; color: #666;">
                    Upload a scietific paper and get an AI-generated report.
                </p>
            </div>
            """
        )
    
    # Status indicator
    status_indicator = gr.Markdown(
        value="🟢 **Backend Status:** Ready" if backend_ready else "🔴 **Backend Status:** Not Ready - Please wait...",
        visible=True,
        elem_classes=["status-indicator"]
    )
    
    # Main content area
    with gr.Row():
        # Left column - Upload section
        with gr.Column(scale=1):
            gr.Markdown("### 📤 Upload Document")
            file_input = gr.File(
                label="Select PDF File",
                file_types=[".pdf"],
                type="filepath",
                interactive=backend_ready,
                height=100
            )
            upload_btn = gr.Button(
                "🚀 Process Document", 
                variant="primary",
                interactive=backend_ready,
                size="lg",
                scale=1
            )
            processing_status = gr.Markdown(
                value="",
                visible=True
            )
        
        # Right column - Metadata (will be populated after processing)
        with gr.Column(scale=2):
            metadata_display = gr.HTML(
                value="<div style='text-align: center; padding: 40px; color: #999;'>Upload a PDF file to see document information here.</div>",
                label="Document Information"
            )
    
    # Report section
    gr.Markdown("---")
    gr.Markdown("### 📊 Generated Report")
    
    with gr.Row():
        with gr.Column(scale=3):
            report_output = gr.Markdown(
                label="Report Preview",
                value="*Your generated report will appear here after processing...*",
                elem_classes=["report-preview"]
            )
        
        with gr.Column(scale=1):
            gr.Markdown("### 💾 Download")
            download_btn = gr.File(
                label="Download Report",
                interactive=False,
                visible=True
            )
            gr.Markdown(
                """
                <div style="padding: 15px; background: var(--background-fill-secondary, rgba(0,0,0,0.05)); border-radius: 8px; margin-top: 10px; border: 1px solid var(--border-color-primary, rgba(0,0,0,0.1));">
                    <small style="color: var(--body-text-color, inherit);">
                    <strong>📝 Note:</strong> The report is generated using AI analysis of your document. 
                    It includes key insights, summaries, and structured information extracted from the PDF.
                    </small>
                </div>
                """
            )
    
    # Event handlers
    def show_processing_status():
        """Show processing status when button is clicked"""
        return "🔄 **Processing document...** This may take a few moments. Please wait."
    
    def process_and_update(file):
        """Process file and return all outputs"""
        report_md, report_file, metadata_html, status_msg = process_pdf_file(file)
        
        # Update download button with the report file
        return report_md, report_file, metadata_html, status_msg
    
    upload_btn.click(
        fn=show_processing_status,
        inputs=None,
        outputs=processing_status
    ).then(
        fn=process_and_update,
        inputs=file_input,
        outputs=[report_output, download_btn, metadata_display, processing_status]
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
    
    # Custom CSS for better styling with dark mode support
    app.css = """
    .status-indicator {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .report-preview {
        max-height: 600px;
        overflow-y: auto;
        padding: 20px;
        background: var(--background-fill-secondary, rgba(0,0,0,0.05)) !important;
        border-radius: 8px;
        border: 1px solid var(--border-color-primary, rgba(0,0,0,0.1)) !important;
        color: var(--body-text-color, inherit) !important;
    }
    .report-preview * {
        color: var(--body-text-color, inherit) !important;
    }
    .report-preview h1,
    .report-preview h2,
    .report-preview h3,
    .report-preview h4,
    .report-preview h5,
    .report-preview h6 {
        color: var(--body-text-color, inherit) !important;
    }
    .report-preview p,
    .report-preview li,
    .report-preview span,
    .report-preview div {
        color: var(--body-text-color, inherit) !important;
    }
    
    /* Dark mode support for HTML content */
    .dark .prose,
    .dark .prose *,
    [data-theme="dark"] .prose,
    [data-theme="dark"] .prose * {
        color: var(--body-text-color) !important;
    }
    
    /* Style HTML content in dark mode */
    .dark div[style*="background"],
    [data-theme="dark"] div[style*="background"] {
        background: rgba(255, 255, 255, 0.05) !important;
        color: var(--body-text-color) !important;
    }
    
    /* Override white backgrounds in dark mode */
    .dark div[style*="background: white"],
    .dark div[style*="background: #fff"],
    .dark div[style*="background: #ffffff"],
    [data-theme="dark"] div[style*="background: white"],
    [data-theme="dark"] div[style*="background: #fff"],
    [data-theme="dark"] div[style*="background: #ffffff"] {
        background: var(--background-fill-secondary) !important;
        color: var(--body-text-color) !important;
    }
    
    /* Make sure text is visible in dark mode */
    .dark span,
    .dark strong,
    .dark div,
    [data-theme="dark"] span,
    [data-theme="dark"] strong,
    [data-theme="dark"] div {
        color: var(--body-text-color) !important;
    }
    
    /* Metadata card styling for dark mode */
    .metadata-card,
    .metadata-card * {
        color: inherit !important;
    }
    
    .dark .metadata-card,
    [data-theme="dark"] .metadata-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%) !important;
        color: var(--body-text-color) !important;
    }
    
    .dark .metadata-item,
    [data-theme="dark"] .metadata-item {
        background: rgba(102, 126, 234, 0.2) !important;
        color: var(--body-text-color) !important;
    }
    
    .dark .metadata-item strong,
    [data-theme="dark"] .metadata-item strong {
        color: var(--body-text-color) !important;
        opacity: 0.9 !important;
    }
    """
    
if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )