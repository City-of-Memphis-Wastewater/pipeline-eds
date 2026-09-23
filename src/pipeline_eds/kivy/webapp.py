import threading
import webbrowser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
import uvicorn

# Import the existing Starlette app
from pipeline_eds.interface.webapp.server import app as web_app


class ServerThread(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8082):
        super().__init__(daemon=True)
        self.config = uvicorn.Config(web_app, host=host, port=port, log_level="info")
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


class ServerControlApp(App):
    def build(self):
        self.server_thread = None

        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        self.btn_start = Button(text="Start Server", on_press=self.start_server)
        self.btn_open = Button(text="Open in Browser", on_press=self.open_browser, disabled=True)

        layout.add_widget(self.btn_start)
        layout.add_widget(self.btn_open)
        return layout

    def start_server(self, instance):
        if not self.server_thread or not self.server_thread.is_alive():
            self.server_thread = ServerThread(host="127.0.0.1", port=8082)
            self.server_thread.start()
            self.btn_start.text = "Server Running"
            self.btn_start.disabled = True
            self.btn_open.disabled = False

    def open_browser(self, instance):
        webbrowser.open("http://127.0.0.1:8082")


if __name__ == "__main__":
    ServerControlApp().run()
