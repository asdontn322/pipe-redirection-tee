import os
import re
import subprocess
from datetime import datetime, timedelta
from importlib.util import spec_from_file_location, module_from_spec
import psutil
from textual.app import App, ComposeResult
from textual.widgets import Static, Input
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.binding import Binding

# Infinity UI Theme System
THEMES = {
    "obsidian": {"bg": "#000000", "fg": "#FFFFFF", "highlight": "#800080"},
    "cosmic": {"bg": "#0F0F23", "fg": "#00FFCC", "highlight": "#FF00FF"},
    "nebula": {"bg": "#1A1A40", "fg": "#FFD700", "highlight": "#FF1493"}
}

class TopBar(Static):
    """Displays the terminal's top bar with time and uptime."""
    def on_mount(self):
        self.set_interval(1, self.refresh)
    
    def refresh(self):
        self.update(f"🧠 ButterTerm | {datetime.now().strftime('%H:%M:%S')} | ⬆️ {timedelta(seconds=int(time.time() - psutil.boot_time()))}")

class AsciiLogo(Static):
    """Displays the ButterTerm ASCII logo."""
    def on_mount(self):
        self.update(r"""
██████╗ ██╗   ██╗████████╗████████╗███████╗██████╗ ███╗   ███╗
██╔══██╗██║   ██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
██████╔╝██║   ██║   ██║      ██║   █████╗  ██████╔╝██╔████╔██║
██╔═══╝ ██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
██║     ╚██████╔╝   ██║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║
╚═╝      ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝
""")

class SystemStats(Static):
    """Displays real-time system statistics (CPU, RAM, temp, network)."""
    def on_mount(self):
        self.set_interval(1, self.refresh)
    
    def refresh(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        net = psutil.net_io_counters()
        temp = psutil.sensors_temperatures().get("k10temp", [{}])[0].get("current", 0)
        self.update(f"🧠 CPU: {cpu}%\n💾 RAM: {ram}%\n🌡️ Temp: {temp}°C\n📡 ↓ {net.bytes_recv//1024}KB ↑ {net.bytes_sent//1024}KB")

class ShellInput(Input):
    """Input field for entering terminal commands."""
    pass

class ButterTerm(App):
    """ButterTerm: Cosmic Edition terminal application."""
    BINDINGS = [
        Binding("ctrl+l", "clear_output", "Clear"),
        Binding("ctrl+s", "save_output", "Save"),
        Binding("ctrl+t", "toggle_theme", "Theme")
    ]
    output_text = reactive("")
    theme_index = reactive(0)
    themes = list(THEMES.keys())

    def compose(self) -> ComposeResult:
        """Compose the terminal UI layout."""
        yield TopBar()
        with Horizontal():
            yield AsciiLogo()
            yield SystemStats()
        yield Static(id="output")
        yield ShellInput(placeholder="Type command...")

    def on_mount(self):
        """Initialize the terminal on startup."""
        self.output = self.query_one("#output", Static)
        self.input = self.query_one(ShellInput)
        self.history, self.history_index = [], -1
        self.set_theme(self.themes[self.theme_index])

    def on_input_submitted(self, msg: Input.Submitted):
        """Handle user-entered commands."""
        cmd = msg.value.strip()
        if not cmd:
            return
        self.history.append(cmd)
        self.history_index = len(self.history)
        
        # Log command to command_history.log
        try:
            os.makedirs(os.path.dirname("command_history.log") or ".", exist_ok=True)
            safe_cmd = re.sub(r"[\n\r\t]", " ", cmd)  # Sanitize command
            with open("command_history.log", "a") as log:
                log.write(f"{datetime.now()}: {safe_cmd}\n")
        except IOError as e:
            self.output_text += f"\n[ERROR] Failed to log command: {e}\n"
        
        # Handle plugin command
        if cmd.startswith("run plugin "):
            name = cmd.split("run plugin ", 1)[-1].strip()
            output = self.load_plugin_dynamic(name)
        # Handle git clone command
        elif cmd.startswith("gitclone "):
            repo = cmd.split("gitclone ", 1)[-1].strip()
            try:
                result = subprocess.run(f"git clone {repo}", shell=True, capture_output=True, text=True)
                output = result.stdout + result.stderr
            except Exception as e:
                output = f"Error: {e}"
        # Handle other shell commands
        else:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                output = result.stdout + result.stderr
            except Exception as e:
                output = f"Error: {e}"
        
        self.output_text += f"\n$ {cmd}\n{output}"
        self.output.update(self.output_text)
        self.input.value = ""

    def on_key(self, event):
        """Handle arrow key navigation for command history."""
        if event.key == "up" and self.history:
            self.history_index = max(0, self.history_index - 1)
            self.input.value = self.history[self.history_index]
        elif event.key == "down" and self.history:
            self.history_index = min(len(self.history) - 1, self.history_index + 1)
            self.input.value = self.history[self.history_index]

    def action_clear_output(self):
        """Clear the terminal output."""
        self.output_text = ""
        self.output.update("")

    def action_save_output(self):
        """Save terminal output and command history to a log file."""
        os.makedirs("logs", exist_ok=True)
        log_file = f"logs/output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_file, "w") as f:
            f.write(f"Commands:\n{'-'*50}\n")
            try:
                with open("command_history.log", "r") as log:
                    f.write(log.read())
            except FileNotFoundError:
                f.write("No command history available.\n")
            f.write(f"\nOutput:\n{'-'*50}\n{self.output_text}")

    def action_toggle_theme(self):
        """Cycle through available themes."""
        self.theme_index = (self.theme_index + 1) % len(self.themes)
        self.set_theme(self.themes[self.theme_index])

    def set_theme(self, theme: str):
        """Apply a theme to the UI."""
        theme_colors = THEMES.get(theme, THEMES["obsidian"])
        required_keys = ["bg", "fg", "highlight"]
        if not all(k in theme_colors for k in required_keys):
            theme_colors = THEMES["obsidian"]
        self.stylesheet = f"""
        TopBar {{ background: {theme_colors["bg"]}; color: {theme_colors["fg"]}; border: round {theme_colors["highlight"]}; padding: 1; }}
        AsciiLogo {{ background: {theme_colors["bg"]}; color: {theme_colors["fg"]}; border: round {theme_colors["highlight"]}; padding: 2; }}
        SystemStats {{ background: {theme_colors["bg"]}; color: {theme_colors["fg"]}; border: round {theme_colors["highlight"]}; padding: 2; }}
        ShellInput {{ background: {theme_colors["bg"]}; color: {theme_colors["fg"]}; border: round {theme_colors["highlight"]}; padding: 1; }}
        #output {{ background: {theme_colors["bg"]}; color: {theme_colors["fg"]}; border: round {theme_colors["highlight"]}; padding: 1; }}
        """
        with open("temp_theme.css", "w") as f:
            f.write(self.stylesheet)
        self.app.set_css_path("temp_theme.css")

    def load_plugin_dynamic(self, plugin_name: str) -> str:
        """Dynamically load a plugin from the plugins directory."""
        if not plugin_name.endswith(".py"):
            plugin_name += ".py"
        plugin_dir = "plugins"
        os.makedirs(plugin_dir, exist_ok=True)
        plugin_path = os.path.join(plugin_dir, plugin_name)
        if not os.path.exists(plugin_path):
            return f"Plugin {plugin_name} not found."
        try:
            spec = spec_from_file_location("plugin", plugin_path)
            if spec is None:
                return f"Failed to create spec for {plugin_name}"
            plugin = module_from_spec(spec)
            spec.loader.exec_module(plugin)
            if not hasattr(plugin, "main"):
                return f"Plugin {plugin_name} has no main() function"
            return plugin.main()
        except Exception as e:
            return f"⚠️ Error in {plugin_name}: {e}"

if __name__ == "__main__":
    ButterTerm().run()
