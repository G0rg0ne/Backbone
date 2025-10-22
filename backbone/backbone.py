import reflex as rx

class State(rx.State):
    """The app state."""

    # The uploaded documents to show.
    uploaded_documents: list[str]

    async def handle_upload(
        self, files: list[rx.UploadFile]
    ):
        """Handle the upload of file(s).

        Args:
            files: The uploaded files.
        """
        for file in files:
            upload_data = await file.read()
            outfile = rx.get_upload_dir() / file.name

            # Save the file.
            with outfile.open("wb") as file_object:
                file_object.write(upload_data)

            # Update the uploaded_documents list.
            self.uploaded_documents.append(file.name)

    def clear_files(self):
        """Clear all uploaded files from disk and state."""
        import os
        for filename in self.uploaded_documents:
            file_path = rx.get_upload_dir() / filename
            if file_path.exists():
                os.remove(file_path)
        self.uploaded_documents = []


color = "rgb(107,99,246)"


def index():
    """The main view."""
    return rx.vstack(
        rx.upload(
            rx.vstack(
                rx.button(
                    "Select File",
                    color=color,
                    bg="white",
                    border=f"1px solid {color}",
                ),
                rx.text(
                    "Drag and drop files here or click to select files"
                ),
            ),
            id="upload2",
            multiple=True,
            accept={
                "application/pdf": [".pdf"],
                "text/html": [".html", ".htm"],
                "text/plain": [".txt"],
                "application/msword": [".doc"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
            },
            max_files=5,
            disabled=False,
            no_keyboard=True,
            on_drop=State.handle_upload(
                rx.upload_files(upload_id="upload2")
            ),
            border=f"1px dotted {color}",
            padding="5em",
        ),
        rx.cond(
            State.uploaded_documents.length() > 0,
            rx.hstack(
                rx.button(
                    "Clear All Files",
                    on_click=State.clear_files,
                    bg="red",
                    color="white",
                    border="1px solid red",
                    _hover={"bg": "darkred"},
                ),
                rx.text(f"{State.uploaded_documents.length()} file(s) uploaded", color="gray"),
                spacing="4",
                align="center",
            ),
        ),
        rx.grid(
            rx.foreach(
                State.uploaded_documents,
                lambda doc: rx.vstack(
                    rx.cond(
                        doc.endswith(".pdf"),
                        rx.link(
                            rx.vstack(
                                rx.icon("file-text", size=48, color=color),
                                rx.text("PDF Document", font_size="sm"),
                            ),
                            href=rx.get_upload_url(doc),
                            is_external=True,
                            text_decoration="none",
                        ),
                        rx.cond(
                            doc.endswith(".txt"),
                            rx.link(
                                rx.vstack(
                                    rx.icon("file-text", size=48, color=color),
                                    rx.text("Text Document", font_size="sm"),
                                ),
                                href=rx.get_upload_url(doc),
                                is_external=True,
                                text_decoration="none",
                            ),
                            rx.cond(
                                doc.endswith(".html") | doc.endswith(".htm"),
                                rx.link(
                                    rx.vstack(
                                        rx.icon("globe", size=48, color=color),
                                        rx.text("HTML Document", font_size="sm"),
                                    ),
                                    href=rx.get_upload_url(doc),
                                    is_external=True,
                                    text_decoration="none",
                                ),
                                rx.link(
                                    rx.vstack(
                                        rx.icon("file", size=48, color=color),
                                        rx.text("Word Document", font_size="sm"),
                                    ),
                                    href=rx.get_upload_url(doc),
                                    is_external=True,
                                    text_decoration="none",
                                ),
                            ),
                        ),
                    ),
                    rx.text(doc, font_size="xs", color="gray"),
                ),
            ),
            columns="3",
            spacing="4",
        ),
        padding="5em",
    )


# Create the app
app = rx.App()
app.add_page(index, route="/")
