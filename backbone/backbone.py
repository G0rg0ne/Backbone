import reflex as rx

class State(rx.State):
    """The app state."""

    # The images to show.
    img: list[str]

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

            # Update the img var.
            self.img.append(file.name)


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
                "image/png": [".png"],
                "image/jpeg": [".jpg", ".jpeg"],
                "image/gif": [".gif"],
                "image/webp": [".webp"],
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
        rx.grid(
            rx.foreach(
                State.img,
                lambda img: rx.vstack(
                    rx.cond(
                        img.endswith(".pdf"),
                        rx.link(
                            rx.vstack(
                                rx.icon("file-text", size=48, color=color),
                                rx.text("PDF Document", font_size="sm"),
                            ),
                            href=rx.get_upload_url(img),
                            is_external=True,
                            text_decoration="none",
                        ),
                        rx.cond(
                            img.endswith(".txt"),
                            rx.link(
                                rx.vstack(
                                    rx.icon("file-text", size=48, color=color),
                                    rx.text("Text Document", font_size="sm"),
                                ),
                                href=rx.get_upload_url(img),
                                is_external=True,
                                text_decoration="none",
                            ),
                            rx.link(
                                rx.vstack(
                                    rx.icon("file", size=48, color=color),
                                    rx.text("Word Document", font_size="sm"),
                                ),
                                href=rx.get_upload_url(img),
                                is_external=True,
                                text_decoration="none",
                            ),
                        ),
                    ),
                    rx.text(img, font_size="xs", color="gray"),
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
