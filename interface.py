import gradio as gr
import os
from pathlib import Path
import tempfile

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
        
        # Read PDF metadata if possible
        try:
            import PyPDF2
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                
                # Try to get metadata
                metadata = pdf_reader.metadata
                title = metadata.get('/Title', 'N/A') if metadata else 'N/A'
                author = metadata.get('/Author', 'N/A') if metadata else 'N/A'
                
                info = f"""
                **PDF File Information:**
                - **File Name:** {os.path.basename(file_path)}
                - **File Size:** {file_size_mb:.2f} MB ({file_size:,} bytes)
                - **Number of Pages:** {num_pages}
                - **Title:** {title}
                - **Author:** {author}

                **Status:** ✅ PDF file uploaded and processed successfully!
                """
        except Exception as e:
            info = f"""
                **PDF File Information:**
                - **File Name:** {os.path.basename(file_path)}
                - **File Size:** {file_size_mb:.2f} MB ({file_size:,} bytes)

                **Status:** ✅ PDF file uploaded successfully!
                **Note:** Could not read PDF metadata: {str(e)}
                """
        
        return info, file_path
        
    except Exception as e:
        return f"Error processing PDF: {str(e)}", None

def download_pdf(file_path):
    """
    Return the file path for download.
    """
    if file_path and os.path.exists(file_path):
        return file_path
    return None

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
            download_output = gr.File(label="Download Uploaded File")
    
    # Event handlers
    upload_btn.click(
        fn=process_pdf,
        inputs=file_input,
        outputs=[info_output, download_output]
    )
    
if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )

