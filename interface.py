import gradio as gr
import os
from loguru import logger

def process_pdf(file):
    """
    Process uploaded PDF file and return information about it.
    """
    if file is None:
        return "No file uploaded."
    
    try:
        # Get file information
        file_path = file.name
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        return file_path
    except Exception as e:
        return f"Error processing PDF: {str(e)}", None

# Create Gradio interface
with gr.Blocks(title="PDF File Uploader", theme=gr.themes.Soft()) as app:
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
                type="filepath"
            )
            upload_btn = gr.Button("Process PDF", variant="primary")
        
        with gr.Column():
            info_output = gr.Markdown(label="File Information")

    # Event handlers
    upload_btn.click(
        fn=process_pdf,
        inputs=file_input,
        outputs=[info_output]
    )
    
if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )