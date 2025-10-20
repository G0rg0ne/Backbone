import reflex as rx

class State(rx.State):
    """The app state."""
    count: int = 0

    def increment(self):
        self.count += 1

    def decrement(self):
        self.count -= 1

def index():
    """The main view."""
    return rx.container(
        rx.vstack(
            rx.heading("Simple Button Counter", size="8"),
            rx.text(f"Count: {State.count}", size="6"),
            rx.hstack(
                rx.button("Increment", on_click=State.increment, color_scheme="green"),
                rx.button("Decrement", on_click=State.decrement, color_scheme="red"),
                spacing="4",
            ),
            spacing="6",
            align="center",
        ),
        padding="2rem",
        max_width="600px",
        margin="auto",
    )

# Create the app
app = rx.App()
app.add_page(index, route="/")
