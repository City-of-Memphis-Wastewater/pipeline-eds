# src/frontend_kivy/gui_kivy.py

import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock

from pipeline_eds.gui_starlette_msgspec_plotly import run_plot, DummyBuffer

class EDSTrendForm(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 10

        # Title
        self.add_widget(Label(text="EDS Trend Controls", font_size='20sp', size_hint_y=None, height=40))

        # 1. IDCS Input
        self.add_widget(Label(text="1. Sensor Selection (IDCS):", size_hint_y=None, height=25))
        self.idcs_input = TextInput(
            text="M100FI M310LI FI8001", 
            multiline=False, 
            size_hint_y=None, 
            height=40
        )
        self.add_widget(self.idcs_input)

        # 2. Time Range (Days)
        self.add_widget(Label(text="2. Days to Plot:", size_hint_y=None, height=25))
        self.days_input = TextInput(text="2.0", multiline=False, size_hint_y=None, height=40)
        self.add_widget(self.days_input)

        # Mock Data Checkbox
        mock_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
        self.mock_checkbox = CheckBox(active=True, size_hint_x=None, width=40)
        mock_box.add_widget(self.mock_checkbox)
        mock_box.add_widget(Label(text="Use Mock Data (No VPN)"))
        self.add_widget(mock_box)

        # Status Label
        self.status_label = Label(text="Ready", size_hint_y=None, height=30)
        self.add_widget(self.status_label)

        # Action Buttons
        btn_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        
        plot_btn = Button(text="Fetch & Plot Trend", background_color=(0.13, 0.77, 0.36, 1))
        plot_btn.bind(on_press=self.on_fetch_and_plot)
        btn_box.add_widget(plot_btn)

        excel_btn = Button(text="Download XLSX", background_color=(0.61, 0.15, 0.69, 1))
        excel_btn.bind(on_press=self.on_download_excel)
        btn_box.add_widget(excel_btn)

        self.add_widget(btn_box)

    def set_status(self, text: str):
        self.status_label.text = text

    def on_fetch_and_plot(self, instance):
        self.set_status("Fetching data...")

        def _worker():
            # 1. Gather data (Extracting from EDS backend or DummyBuffer)
            if self.mock_checkbox.active:
                buffer = DummyBuffer().mock_data()
            else:
                # Place real ClientEdsRest query here
                buffer = DummyBuffer().mock_data()

            Clock.schedule_once(lambda dt: self.set_status("Launching Plotly Server..."))

            # 2. Spin up Starlette Plotly server (opens browser automatically via pyhabitat)
            run_plot(buffer, port=8000)

        threading.Thread(target=_worker, daemon=True).start()

    def on_download_excel(self, instance):
        self.set_status("Generating Excel export...")
        # Add openpyxl / pandas export logic here

class EDSTrendKivyApp(App):
    def build(self):
        self.title = "Pipeline EDS - Input Control Panel"
        return EDSTrendForm()


def launch_kivy_app() -> None:
    """Entry point callable from CLI."""
    EDSTrendKivyApp().run()

main = launch_kivy_app

if __name__ == "__main__":
    launch_kivy_app()
