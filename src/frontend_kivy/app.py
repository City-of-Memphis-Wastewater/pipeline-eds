import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout

from pathlib import Path

class DashboardScreen(Screen):
    """Main landing screen for the pipeline interface."""
    pass


class SettingsScreen(Screen):
    """Configuration and credentials setup screen."""
    pass


class RootLayout(BoxLayout):
    """Main container binding layout and screen navigation."""
    def switch_screen(self, screen_name: str) -> None:
        if self.ids.screen_manager.has_screen(screen_name):
            self.ids.screen_manager.current = screen_name


class KivyApp(App):
    """Kivy application entry point."""
    def build(self):
        self.title = "App"
        kv_file = os.path.join(os.path.dirname(__file__), "main.kv")
        if os.path.exists(kv_file):
            Builder.load_file(kv_file)
        return RootLayout()


def launch_app() -> None:
    """Entry point callable from CLI."""
    KivyApp().run()


if __name__ == "__main__":
    launch_app()