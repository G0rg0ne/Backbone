import reflex as rx
import asyncio
import os
import tempfile
from unstructured.partition.pdf import partition_pdf

class State(rx.State):
    """The app state."""

    # The uploaded documents to show.
    uploaded_documents: list[str] = []
    
    # PDF processing state
    is_processing: bool = False
    processing_status: str = ""
    extracted_texts: list[tuple[str, str]] = []

    def clear_all_data(self):
        """Clear all uploaded documents and extracted texts."""
        self.uploaded_documents = []
        self.extracted_texts = []
        self.processing_status = ""
        self.is_processing = False

    async def handle_upload(
        self, files: list[rx.UploadFile]
    ):
        """Handle the upload of file(s) and extract text content.

        Args:
            files: The uploaded files.
        """
        try:
            self.is_processing = True
            self.processing_status = "Processing PDF files..."
            
            processed_count = 0
            for file in files:
                if not file.name.endswith('.pdf'):
                    continue
                
                # Read the file content
                file_content = await file.read()
                
                # Create a temporary file to save the PDF content
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                    
                
                try:
                    # Extract text using partition_pdf with file path
                    elements = partition_pdf(temp_file_path)
                    extracted_text = "\n".join([el.text for el in elements if hasattr(el, 'text') and el.text.strip()])
                    
                    # Store the extracted text
                    self.uploaded_documents.append(file.name)
                    self.extracted_texts.append((file.name, extracted_text))
                    processed_count += 1
                    
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            
            self.processing_status = f"Successfully processed {processed_count} PDF file(s)."
            
        except Exception as e:
            self.processing_status = f"Error processing files: {str(e)}"
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
                        rx.hstack(
                            rx.cond(
                                State.is_processing,
                                rx.spinner(size="1", color=color),
                                rx.icon("check-circle", size=16, color="green.600"),
                            ),
                            rx.text(
                                State.processing_status,
                                color=rx.cond(State.is_processing, "blue.600", "green.600"),
                                font_size="sm",
                                font_weight="500",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        padding="1em 1.5em",
                        bg=rx.cond(State.is_processing, "blue.50", "green.50"),
                        border="1px solid",
                        border_color=rx.cond(State.is_processing, "blue.200", "green.200"),
                        border_radius="lg",
                        width="100%",
                        max_width="600px",
                        margin="0 auto",
                        text_align="center",
                    ),
                ),
                rx.cond(
                    State.uploaded_documents.length() > 0,
                    rx.button(
                        rx.icon("trash-2", size=16),
                        "Clear All Data",
                        on_click=State.clear_all_data,
                        color="white",
                        bg="#FF5733",
                        border="1px solid",
                        border_color="red.600",
                        padding="0.5em 1em",
                        font_size="sm",
                        font_weight="500",
                        border_radius="md",
                        _hover={
                            "bg": "red.700",
                            "border_color": "red.700",
                            "transform": "translateY(-1px)",
                        },
                        transition="all 0.2s ease",
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
                rx.divider(margin="2em 0"),
                rx.heading(
                    "Extracted PDF Content", 
                    size="4", 
                    color="gray.700",
                    font_weight="600",
                ),
                rx.foreach(
                    State.extracted_texts,
                    lambda item: rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("file-text", size=20, color=color),
                                rx.text(
                                    f"Document: {item[0]}",
                                    font_weight="bold",
                                    color="gray.700",
                                    font_size="md",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            rx.box(
                                rx.text(
                                    item[1],
                                    font_size="sm",
                                    line_height="1.6",
                                    color="gray.600",
                                ),
                                max_height="300px",
                                overflow_y="auto",
                                padding="1.5em",
                                border="1px solid",
                                border_color="gray.200",
                                border_radius="lg",
                                box_shadow="0 2px 4px rgba(0, 0, 0, 0.05)",
                                width="100%",
                            ),
                            spacing="3",
                            align="start",
                        ),
                        padding="1.5em",
                        border="1px solid",
                        border_color="gray.200",
                        border_radius="xl",
                        bg="gray.50",
                        box_shadow="0 4px 6px rgba(0, 0, 0, 0.05)",
                        width="100%",
                        max_width="800px",
                        margin="0 auto",
                    ),
                ),
                spacing="4",
                align="center",
                width="100%",
            ),
        ),
        padding="5em",
    )


# Create the app
app = rx.App()
app.add_page(index, route="/")
