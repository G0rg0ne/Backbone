import gradio as gr
import os
import time
from loguru import logger
import requests
from dotenv import load_dotenv
from datetime import datetime
from typing import Tuple, Optional

load_dotenv()

# Get environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://backbone-backend:8000")

def check_backend_health(max_retries=30, retry_delay=2) -> bool:
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

def process_pdf_file(file: Optional[str], progress: gr.Progress = gr.Progress()) -> Tuple[str, Optional[str], str, str]:
    """
    Process uploaded PDF file and return information about it.
    Returns: (report_markdown, report_file_path, metadata_html, status_message)
    """
    if file is None:
        return "", None, "", "⚠️ **Please upload a PDF file first.**"
    
    try:
        progress(0.05, desc="📤 Uploading PDF to backend...")
        
        # Get file info
        file_size = os.path.getsize(file) if os.path.exists(file) else 0
        file_size_mb = file_size / (1024 * 1024)
        filename = os.path.basename(file) if file else "document.pdf"
        
        # Upload file
        with open(file, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            progress(0.15, desc="🔄 Processing PDF with backend...")
            response = requests.post(f"{BACKEND_URL}/process_pdf_file", files=files, timeout=300)
        
        progress(0.85, desc="📊 Generating AI report...")
        
        if response.status_code == 200:
            data = response.json()
            num_elements = data.get("num_elements", 0)
            file_size_mb = data.get("file_size_mb", file_size_mb)
            status = data.get("status", "unknown")
            report = data.get("report", "")
            content_length = len(data.get("content", ""))
            
            # Create report file
            report_file_path = None
            if report:
                os.makedirs("reports", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_base = os.path.splitext(filename)[0]
                report_filename = f"{filename_base}_report_{timestamp}.md"
                report_file_path = os.path.join("reports", report_filename)
                
                with open(report_file_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Report saved to {report_file_path}")
            
            # Enhanced metadata HTML with better design
            metadata_html = f"""
            <div class="metadata-container">
                <div class="metadata-header">
                    <h3>📄 Document Analysis Results</h3>
                    <span class="status-badge status-{status.lower()}">{status.title()}</span>
                </div>
                <div class="metadata-grid">
                    <div class="metadata-card stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-content">
                            <div class="stat-label">Elements Extracted</div>
                            <div class="stat-value">{num_elements:,}</div>
                            <div class="stat-description">Text blocks, tables, and structures</div>
                        </div>
                    </div>
                    <div class="metadata-card stat-card">
                        <div class="stat-icon">💾</div>
                        <div class="stat-content">
                            <div class="stat-label">File Size</div>
                            <div class="stat-value">{file_size_mb:.2f} <span class="stat-unit">MB</span></div>
                            <div class="stat-description">Original document size</div>
                        </div>
                    </div>
                    <div class="metadata-card stat-card">
                        <div class="stat-icon">📝</div>
                        <div class="stat-content">
                            <div class="stat-label">Content Length</div>
                            <div class="stat-value">{content_length:,} <span class="stat-unit">chars</span></div>
                            <div class="stat-description">Extracted text content</div>
                        </div>
                    </div>
                    <div class="metadata-card stat-card">
                        <div class="stat-icon">📄</div>
                        <div class="stat-content">
                            <div class="stat-label">Report Length</div>
                            <div class="stat-value">{len(report):,} <span class="stat-unit">chars</span></div>
                            <div class="stat-description">Generated report size</div>
                        </div>
                    </div>
                </div>
                <div class="metadata-footer">
                    <small>📅 Processed on {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}</small>
                </div>
            </div>
            """
            
            progress(1.0, desc="✅ Complete!")
            status_message = f"✅ **Processing complete!** Successfully analyzed `{filename}` and generated report."
            
            return report if report else "No report available.", report_file_path, metadata_html, status_message
        else:
            error_msg = f"Error processing PDF file: {response.status_code} {response.text}"
            logger.error(error_msg)
            error_detail = response.text[:200] if response.text else "Unknown error"
            return "", None, "", f"❌ **Processing failed!**\n\n**Error Code:** {response.status_code}\n**Details:** {error_detail}"
    except requests.exceptions.Timeout:
        logger.error("Request timeout while processing PDF")
        return "", None, "", "⏱️ **Request timeout!** The processing took too long. Please try again with a smaller file."
    except requests.exceptions.ConnectionError:
        logger.error("Connection error while processing PDF")
        return "", None, "", "🔌 **Connection error!** Cannot reach the backend service. Please check if the backend is running."
    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        return "", None, "", f"❌ **Processing failed!**\n\n**Error:** {str(e)}\n\nPlease try again or contact support if the issue persists."


# Create Gradio interface with modern, improved design
with gr.Blocks(
    title=" Backbone | Dynamic Summarization of Scientific Papers Using Profile-Aware AI",
    theme=gr.themes.Soft(
        primary_hue="purple",
        secondary_hue="blue",
        spacing_size="md",
        radius_size="lg"
    ),
    css="""
    /* Custom CSS for enhanced UI */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border-radius: 16px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    .main-header h1 {
        margin: 0 0 0.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .main-header p {
        font-size: 1.1rem;
        color: var(--body-text-color);
        opacity: 0.8;
        margin: 0;
    }
    .status-indicator {
        padding: 12px 20px;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        font-weight: 500;
        text-align: center;
        background: var(--background-fill-secondary);
        border: 2px solid var(--border-color-primary);
    }
    .status-indicator.ready {
        background: rgba(76, 175, 80, 0.1);
        border-color: rgba(76, 175, 80, 0.3);
        color: #4caf50;
    }
    .status-indicator.not-ready {
        background: rgba(244, 67, 54, 0.1);
        border-color: rgba(244, 67, 54, 0.3);
        color: #f44336;
    }
    .upload-section {
        background: var(--background-fill-secondary);
        padding: 1.5rem;
        border-radius: 16px;
        border: 2px dashed var(--border-color-primary);
        transition: all 0.3s ease;
    }
    .upload-section:hover {
        border-color: var(--primary-color);
        background: var(--background-fill-primary);
    }
    /* Make upload button full width */
    .upload-section + button,
    button[data-testid*="Process Document"] {
        width: 100%;
    }
    .metadata-container {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    .metadata-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid rgba(102, 126, 234, 0.2);
    }
    .metadata-header h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--body-text-color);
    }
    .status-badge {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .status-badge.status-success {
        background: rgba(76, 175, 80, 0.2);
        color: #4caf50;
        border: 1px solid rgba(76, 175, 80, 0.4);
    }
    .metadata-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .stat-card {
        background: rgba(255, 255, 255, 0.5);
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border-color: rgba(102, 126, 234, 0.4);
    }
    .stat-icon {
        font-size: 2rem;
        line-height: 1;
    }
    .stat-content {
        flex: 1;
    }
    .stat-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--body-text-color);
        opacity: 0.7;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--primary-color);
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }
    .stat-unit {
        font-size: 1rem;
        font-weight: 500;
        opacity: 0.7;
    }
    .stat-description {
        font-size: 0.75rem;
        color: var(--body-text-color);
        opacity: 0.6;
        margin-top: 0.25rem;
    }
    .metadata-footer {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(102, 126, 234, 0.2);
        text-align: center;
    }
    .metadata-footer small {
        color: var(--body-text-color);
        opacity: 0.6;
    }
    .report-section {
        margin-top: 2rem;
    }
    .report-preview {
        max-height: 70vh;
        overflow-y: auto;
        padding: 1.5rem;
        background: var(--background-fill-secondary);
        border-radius: 12px;
        border: 1px solid var(--border-color-primary);
        line-height: 1.7;
    }
    .report-preview * {
        color: var(--body-text-color) !important;
    }
    .report-preview h1,
    .report-preview h2,
    .report-preview h3,
    .report-preview h4,
    .report-preview h5,
    .report-preview h6 {
        color: var(--body-text-color) !important;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }
    .download-section {
        background: var(--background-fill-secondary);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid var(--border-color-primary);
    }
    .info-box {
        padding: 1rem;
        background: var(--background-fill-secondary);
        border-radius: 8px;
        margin-top: 1rem;
        border: 1px solid var(--border-color-primary);
    }
    .info-box small {
        color: var(--body-text-color);
        opacity: 0.8;
        line-height: 1.6;
    }
    .processing-status {
        padding: 1rem;
        border-radius: 8px;
        background: var(--background-fill-secondary);
        border: 1px solid var(--border-color-primary);
        margin-top: 1rem;
    }
    /* Dark mode enhancements */
    .dark .stat-card,
    [data-theme="dark"] .stat-card {
        background: rgba(255, 255, 255, 0.05);
    }
    .dark .metadata-container,
    [data-theme="dark"] .metadata-container {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
    }
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .metadata-grid {
            grid-template-columns: 1fr;
        }
        .main-header h1 {
            font-size: 2rem;
        }
    }
    """
) as app:
    
    # Enhanced Header
    with gr.Row():
        gr.HTML(
            """
            <div class="main-header">
                <h1>🤖 Backbone </h1>
                <p>Upload a scientific paper and get an AI-generated comprehensive analysis report</p>
            </div>
            """
        )
    
    # Status indicator with better styling
    status_indicator = gr.HTML(
        value=f"""
        <div class="status-indicator {'ready' if backend_ready else 'not-ready'}">
            {'🟢 <strong>Backend Status:</strong> Ready - System operational' if backend_ready else '🔴 <strong>Backend Status:</strong> Not Ready - Please wait for the backend to initialize...'}
        </div>
        """,
        visible=True
    )
    
    # Main content area with improved layout
    with gr.Row():
        # Left column - Upload section
        with gr.Column(scale=1, min_width=300):
            with gr.Group():
                gr.Markdown("### 📤 Upload Document")
                file_input = gr.File(
                    label="Select PDF File",
                    file_types=[".pdf"],
                    type="filepath",
                    interactive=backend_ready,
                    height=120,
                    elem_classes=["upload-section"]
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
                    visible=True,
                    elem_classes=["processing-status"]
                )
        
        # Right column - Metadata (will be populated after processing)
        with gr.Column(scale=2, min_width=400):
            metadata_display = gr.HTML(
                value="""
                <div class="metadata-container">
                    <div style="text-align: center; padding: 3rem 2rem; color: var(--body-text-color); opacity: 0.6;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
                        <div style="font-size: 1.1rem; font-weight: 500;">Upload a PDF file to see document analysis results here</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.7;">The system will extract and analyze your document</div>
                    </div>
                </div>
                """,
                label="Document Information"
            )
    
    # Report section with improved layout
    with gr.Group():
        gr.Markdown("---")
        gr.Markdown("### 📊 Generated Report")
        
        with gr.Row():
            with gr.Column(scale=3, min_width=500):
                report_output = gr.Markdown(
                    label="Report Preview",
                    value="""
                    <div style="text-align: center; padding: 3rem; color: var(--body-text-color); opacity: 0.6;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">📝</div>
                        <div style="font-size: 1.1rem; font-weight: 500;">Your generated report will appear here after processing</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.7;">The AI will analyze your document and create a comprehensive report</div>
                    </div>
                    """,
                    elem_classes=["report-preview"]
                )
            
            with gr.Column(scale=1, min_width=250):
                with gr.Group(elem_classes=["download-section"]):
                    gr.Markdown("### 💾 Download")
                    download_btn = gr.File(
                        label="Download Report",
                        interactive=False,
                        visible=True
                    )
                    gr.HTML(
                        """
                        <div class="info-box">
                            <small>
                                <strong>📝 About the Report:</strong><br>
                                The report is generated using advanced AI analysis of your document. 
                                It includes key insights, summaries, and structured information extracted from the PDF.
                                <br><br>
                                <strong>💡 Tip:</strong> You can download the report as a Markdown file for further use.
                            </small>
                        </div>
                        """
                    )
    
    # Event handlers
    def show_processing_status():
        """Show processing status when button is clicked"""
        return "🔄 **Processing document...**\n\nThis may take a few moments depending on the document size. Please wait while we analyze your PDF and generate the report."
    
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
                    return f"""
                    <div class="status-indicator ready">
                        🟢 <strong>Backend Status:</strong> Ready - System operational
                    </div>
                    """
                else:
                    return f"""
                    <div class="status-indicator not-ready">
                        🔴 <strong>Backend Status:</strong> Not Ready - Please wait...
                    </div>
                    """
            except:
                return f"""
                <div class="status-indicator not-ready">
                    🔴 <strong>Backend Status:</strong> Not Ready - Please wait...
                </div>
                """
        
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