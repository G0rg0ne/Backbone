import reflex as rx
import httpx
import asyncio
import os
import json

# Document processor API configuration
DOCUMENT_PROCESSOR_URL = os.getenv("DOCUMENT_PROCESSOR_URL", "http://localhost:8000")

class State(rx.State):
    """The app state."""

    # The uploaded documents to show.
    uploaded_documents: list[str] = []
    
    # PDF processing state
    is_processing: bool = False
    processing_status: str = ""
    extracted_texts: dict[str, str] = {}

    async def handle_upload(
        self, files: list[rx.UploadFile]
    ):
        """Handle the upload of file(s) by sending to backend API.

        Args:
            files: The uploaded files.
        """
        try:
            # Prepare files for API upload
            files_data = []
            for file in files:
                upload_data = await file.read()
                files_data.append(("files", (file.name, upload_data, "application/pdf")))
            
            # Send files to backend API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DOCUMENT_PROCESSOR_URL}/upload",
                    files=files_data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Update the uploaded_documents list
                self.uploaded_documents.extend(result["files"])
                self.processing_status = f"Successfully uploaded {len(result['files'])} file(s)."
                
        except httpx.HTTPError as e:
            self.processing_status = f"Error uploading files: {str(e)}"
        except Exception as e:
            self.processing_status = f"Unexpected error: {str(e)}"

    async def clear_files(self):
        """Clear all uploaded files from backend and state."""
        try:
            if not self.uploaded_documents:
                return
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "DELETE",
                    f"{DOCUMENT_PROCESSOR_URL}/files",
                    json=self.uploaded_documents,
                    timeout=10.0
                )
                response.raise_for_status()
                
            # Clear local state
            self.uploaded_documents = []
            self.extracted_texts = {}
            self.processing_status = "All files cleared successfully."
            
        except httpx.HTTPError as e:
            self.processing_status = f"Error clearing files: {str(e)}"
        except Exception as e:
            self.processing_status = f"Unexpected error: {str(e)}"

    async def process_pdfs(self):
        """Process all uploaded PDF files via backend API."""
        self.is_processing = True
        self.processing_status = "Processing PDFs..."
        
        try:
            pdf_files = [doc for doc in self.uploaded_documents if doc.endswith('.pdf')]
            
            if not pdf_files:
                self.processing_status = "No PDF files found to process."
                self.is_processing = False
                return
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DOCUMENT_PROCESSOR_URL}/process-pdfs",
                    json=pdf_files,
                    timeout=60.0  # Longer timeout for processing
                )
                response.raise_for_status()
                result = response.json()
                
                # Update extracted texts
                self.extracted_texts = result["extracted_texts"]
                
                if result["errors"]:
                    self.processing_status = f"Processed {result['processed_count']} files. Errors: {', '.join(result['errors'])}"
                else:
                    self.processing_status = f"Successfully processed {result['processed_count']} PDF file(s)."
            
        except httpx.HTTPError as e:
            self.processing_status = f"Error processing PDFs: {str(e)}"
        except Exception as e:
            self.processing_status = f"Unexpected error: {str(e)}"
        finally:
            self.is_processing = False


color = "rgb(107,99,246)"


def index():
    """The main view."""
    return rx.vstack(
        # Upload Section with improved UI
        rx.box(
            rx.upload(
                rx.vstack(
                    rx.icon(
                        "upload-cloud",
                        size=64,
                        color=color,
                        opacity=0.8,
                    ),
                    rx.heading(
                        "Upload PDF Documents",
                        size="5",
                        color="gray.700",
                        font_weight="600",
                    ),
                    rx.text(
                        "Drag and drop your PDF files here, or click to browse",
                        color="gray.500",
                        font_size="md",
                        text_align="center",
                    ),
                    rx.button(
                        rx.icon("plus", size=20),
                        "Choose Files",
                        color="white",
                        bg=color,
                        border=f"2px solid {color}",
                        padding="1em 2em",
                        font_size="md",
                        font_weight="600",
                        border_radius="lg",
                        _hover={
                            "bg": "rgb(87, 89, 246)",
                            "transform": "translateY(-2px)",
                            "box_shadow": f"0 8px 25px {color}40",
                        },
                        transition="all 0.2s ease",
                    ),
                    rx.text(
                        "Supports PDF files up to 10MB each",
                        color="gray.400",
                        font_size="sm",
                    ),
                    spacing="4",
                    align="center",
                ),
                id="upload2",
                multiple=True,
                accept={
                    "application/pdf": [".pdf"],
                },
                max_files=5,
                disabled=False,
                no_keyboard=True,
                on_drop=State.handle_upload(
                    rx.upload_files(upload_id="upload2")
                ),
                border=f"2px dashed {color}",
                border_radius="xl",
                padding="4em 2em",
                bg="gray.50",
                _hover={
                    "bg": "gray.100",
                    "border_color": "rgb(87, 89, 246)",
                    "transform": "translateY(-2px)",
                    "box_shadow": f"0 10px 30px {color}20",
                },
                transition="all 0.3s ease",
                width="100%",
                max_width="600px",
                margin="0 auto",
            ),
            width="100%",
            display="flex",
            justify="center",
            padding="2em 0",
        ),
        # Action Buttons Section
        rx.cond(
            State.uploaded_documents.length() > 0,
            rx.vstack(
                rx.box(
                    rx.hstack(
                        rx.button(
                            rx.icon("trash-2", size=16),
                            "Clear All Files",
                            on_click=State.clear_files,
                            bg="red.500",
                            color="white",
                            border="2px solid red.500",
                            padding="0.75em 1.5em",
                            font_weight="600",
                            border_radius="lg",
                            _hover={
                                "bg": "red.600",
                                "transform": "translateY(-2px)",
                                "box_shadow": "0 8px 25px rgba(239, 68, 68, 0.4)",
                            },
                            transition="all 0.2s ease",
                        ),
                        rx.button(
                            rx.icon("zap", size=16),
                            "Process PDFs",
                            on_click=State.process_pdfs,
                            bg=color,
                            color="white",
                            border=f"2px solid {color}",
                            padding="0.75em 1.5em",
                            font_weight="600",
                            border_radius="lg",
                            _hover={
                                "bg": "rgb(87, 89, 246)",
                                "transform": "translateY(-2px)",
                                "box_shadow": f"0 8px 25px {color}40",
                            },
                            disabled=State.is_processing,
                            transition="all 0.2s ease",
                        ),
                        rx.box(
                            rx.text(
                                f"{State.uploaded_documents.length()} file(s) uploaded",
                                color="gray.600",
                                font_weight="500",
                                font_size="sm",
                            ),
                            padding="0.75em 1.5em",
                            bg="gray.100",
                            border_radius="lg",
                        ),
                        spacing="4",
                        align="center",
                        wrap="wrap",
                    ),
                    padding="1.5em",
                    bg="black",
                    border="1px solid",
                    border_color="gray.200",
                    border_radius="xl",
                    box_shadow="0 4px 6px rgba(0, 0, 0, 0.05)",
                    width="100%",
                    max_width="600px",
                    margin="0 auto",
                ),
                rx.cond(
                    State.processing_status != "",
                    rx.box(
                        rx.text(
                            State.processing_status,
                            color="blue.600",
                            font_size="sm",
                            font_weight="500",
                        ),
                        padding="1em 1.5em",
                        bg="blue.50",
                        border="1px solid",
                        border_color="blue.200",
                        border_radius="lg",
                        width="100%",
                        max_width="600px",
                        margin="0 auto",
                        text_align="center",
                    ),
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
        ),
        # File Preview Section
        rx.cond(
            State.uploaded_documents.length() > 0,
            rx.vstack(
                rx.divider(margin="2em 0"),
                rx.heading(
                    "Uploaded Files",
                    size="4",
                    color="gray.700",
                    font_weight="600",
                ),
                rx.grid(
                    rx.foreach(
                        State.uploaded_documents,
                        lambda doc: rx.box(
                            rx.vstack(
                                rx.cond(
                                    doc.endswith(".pdf"),
                                    rx.link(
                                        rx.vstack(
                                            rx.box(
                                                rx.icon("file-text", size=40, color="white"),
                                                bg=color,
                                                padding="1em",
                                                border_radius="lg",
                                                _hover={
                                                    "bg": "rgb(87, 89, 246)",
                                                    "transform": "scale(1.05)",
                                                },
                                                transition="all 0.2s ease",
                                            ),
                                            rx.text(
                                                "PDF Document",
                                                font_size="sm",
                                                font_weight="600",
                                                color="gray.700",
                                            ),
                                        ),
                                        href=rx.get_upload_url(doc),
                                        is_external=True,
                                        text_decoration="none",
                                    ),
                                ),
                                rx.text(
                                    doc,
                                    font_size="xs",
                                    color="gray.500",
                                    text_align="center",
                                    max_width="120px",
                                    overflow="hidden",
                                    text_overflow="ellipsis",
                                    white_space="nowrap",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="1em",
                            border_radius="lg",
                            bg="black",
                            _hover={
                                "border_color": color,
                                "box_shadow": f"0 4px 12px {color}20",
                                "transform": "translateY(-2px)",
                            },
                            transition="all 0.2s ease",
                            width="100%",
                        ),
                    ),
                    columns="4",
                    spacing="4",
                    width="100%",
                    max_width="800px",
                    margin="0 auto",
                ),
                spacing="4",
                align="center",
                width="100%",
            ),
        ),
        rx.cond(
            State.extracted_texts.length() > 0,
            rx.vstack(
                rx.divider(),
                rx.heading("Extracted Text", size="4", color=color),
                rx.foreach(
                    State.extracted_texts,
                    lambda item: rx.vstack(
                        rx.text(
                            f"From: {item[0]}",
                            font_weight="bold",
                            color="gray",
                            font_size="sm",
                        ),
                        rx.text(
                            item[1],
                            font_size="sm",
                            max_height="200px",
                            overflow_y="auto",
                            padding="1em",
                            border=f"1px solid {color}",
                            border_radius="md",
                            bg="gray.50",
                        ),
                        spacing="2",
                        align="start",
                    ),
                ),
                spacing="4",
                align="start",
            ),
        ),
        padding="5em",
    )


# Create the app
app = rx.App()
app.add_page(index, route="/")
