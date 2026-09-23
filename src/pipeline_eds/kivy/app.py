# src/pipeline_eds/kivy/gui_kivy.py

import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock

from pipeline_eds.gui_starlette_msgspec_plotly import run_plot, DummyBuffer
from pipeline_eds.gui_plotly_static import MockBuffer, show_static
from pipeline_eds.gui_plotly_static import show_static
from pipeline_eds.api.eds.core import fetch_trend_data

class EDSTrendForm(BoxLayout):
    def dead(self, **kwargs):
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

        self.start_input = TextInput(
            text="", multiline=False, size_hint_y=None, height=40
        )
        self.add_widget(self.start_input)

        # 3. End Time Input
        self.add_widget(
            Label(
                text="3. End Time (e.g. 2026-09-22 15:00 or empty):",
                size_hint_y=None,
                height=25,
            )
        )
        self.end_input = TextInput(
            text="", multiline=False, size_hint_y=None, height=40
        )
        self.add_widget(self.end_input)

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 10

        # Title
        self.add_widget(
            Label(
                text="EDS Trend Controls",
                font_size='20sp',
                size_hint_y=None,
                height=40,
            )
        )

        # 1. IDCS Input
        self.add_widget(
            Label(
                text="1. Sensor Selection (IDCS):", size_hint_y=None, height=25
            )
        )
        self.idcs_input = TextInput(
            text="M100FI M310LI FI8001",
            multiline=False,
            size_hint_y=None,
            height=40,
        )
        self.add_widget(self.idcs_input)

        # 2. Start Time Input
        self.add_widget(
            Label(
                text="2. Start Time (e.g. 2026-09-20 08:00 or empty):",
                size_hint_y=None,
                height=25,
            )
        )
        self.start_input = TextInput(
            text="", multiline=False, size_hint_y=None, height=40
        )
        self.add_widget(self.start_input)

        # 3. End Time Input
        self.add_widget(
            Label(
                text="3. End Time (e.g. 2026-09-22 15:00 or empty):",
                size_hint_y=None,
                height=25,
            )
        )
        self.end_input = TextInput(
            text="", multiline=False, size_hint_y=None, height=40
        )
        self.add_widget(self.end_input)

        # 4. Time Range (Days)
        self.add_widget(
            Label(
                text="4. Days to Plot (used if Start/End empty):",
                size_hint_y=None,
                height=25,
            )
        )
        self.days_input = TextInput(
            text="2.0", multiline=False, size_hint_y=None, height=40
        )
        self.add_widget(self.days_input)

        # Mock Data Checkbox
        mock_box = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=30
        )
        self.mock_checkbox = CheckBox(active=True, size_hint_x=None, width=40)
        mock_box.add_widget(self.mock_checkbox)
        mock_box.add_widget(Label(text="Use Mock Data (No VPN)"))
        self.add_widget(mock_box)

        # Status Label
        self.status_label = Label(text="Ready", size_hint_y=None, height=30)
        self.add_widget(self.status_label)

        # Action Buttons
        btn_box = BoxLayout(
            orientation='horizontal', spacing=10, size_hint_y=None, height=50
        )

        plot_btn = Button(
            text="Fetch & Plot Trend", background_color=(0.13, 0.77, 0.36, 1)
        )
        plot_btn.bind(on_press=self.on_fetch_and_plot)
        btn_box.add_widget(plot_btn)

        excel_btn = Button(
            text="Download XLSX", background_color=(0.61, 0.15, 0.69, 1)
        )
        excel_btn.bind(on_press=self.on_download_excel)
        btn_box.add_widget(excel_btn)

        self.add_widget(btn_box)

    def set_status(self, text: str):
        self.status_label.text = text


    def on_fetch_and_plot(self, instance):
        self.set_status("Fetching data...")

        # Extract user inputs from Kivy GUI fields (adjust widget names as needed)
        selected_idcs = self.idcs_input.text.strip().split()  # e.g., ["M100FI", "FI8001"]
        start_time = self.start_input.text.strip() or None
        end_time = self.end_input.text.strip() or None
        days_val = float(self.days_input.text) if self.days_input.text.strip() else None

        def _worker():
            if self.mock_checkbox.active:
                from pipeline_eds.gui_plotly_static import MockBuffer
                buffer = MockBuffer()
            else:
                # Live REST query using core fetch pipeline
                buffer, results, resolved_idcs, plant = fetch_trend_data(
                    idcs=selected_idcs,
                    starttime=start_time,
                    endtime=end_time,
                    days=days_val,
                    use_mock=False,
                )

            if buffer.is_empty():
                self.set_status("No data returned for selected sensors.")
                return

            self.set_status("Rendering plot...")
            show_static(buffer)
            self.set_status("Done.")

        # Execute fetch/plot pipeline off the Kivy main UI thread
        import threading
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
