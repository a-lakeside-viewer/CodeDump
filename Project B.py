import os
import sys
import json
import threading
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QObject

# Optional: for listing COM ports
try:
    from serial.tools import list_ports
    import serial
    import serial.threaded
except Exception as e:
    list_ports = None
    serial = None


# ---------------------------- Data Models ----------------------------

@dataclass
class CommandItem:
    label: str
    text: str

@dataclass
class Section:
    name: str
    commands: List[CommandItem]

@dataclass
class Profile:
    name: str
    sections: Dict[str, List[CommandItem]]  # section name -> list of commands


# ---------------------------- Persistence ----------------------------

class ProfileStore:
    """
    Handles loading/saving profile JSON files. Each profile is stored as ./profiles/<name>.json
    """
    def __init__(self, base_dir: str = "profiles"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def profile_path(self, name: str) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in "-_ ").strip()
        if not safe:
            safe = "profile"
        return os.path.join(self.base_dir, f"{safe}.json")

    def list_profiles(self) -> List[str]:
        names = []
        if not os.path.isdir(self.base_dir):
            return names
        for fn in os.listdir(self.base_dir):
            if fn.lower().endswith(".json"):
                names.append(os.path.splitext(fn)[0])
        names.sort(key=lambda s: s.lower())
        return names

    def load_profile(self, name: str) -> Profile:
        path = self.profile_path(name)
        if not os.path.exists(path):
            # Create empty profile
            return Profile(name=name, sections={})
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize
        sections: Dict[str, List[CommandItem]] = {}
        for sec_name, cmds in data.get("sections", {}).items():
            items = []
            for c in cmds:
                if isinstance(c, dict):
                    label = c.get("label", "")
                    text = c.get("text", "")
                else:
                    # legacy/list form
                    label = str(c)
                    text = str(c)
                items.append(CommandItem(label=label, text=text))
            sections[sec_name] = items
        return Profile(name=name, sections=sections)

    def save_profile(self, profile: Profile) -> None:
        path = self.profile_path(profile.name)
        data = {
            "name": profile.name,
            "sections": {
                sec_name: [asdict(cmd) for cmd in cmds]
                for sec_name, cmds in profile.sections.items()
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------- Serial Backend ----------------------------

class SerialWorker(QtCore.QThread):
    """
    Background thread for reading from serial port without blocking the GUI.
    """
    data_received = pyqtSignal(bytes)
    error = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self, port: str, baud: int, parent=None):
        super().__init__(parent)
        self.port_name = port
        self.baud = baud
        self._serial = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def run(self):
        if serial is None:
            self.error.emit("pyserial is not installed. Run: pip install pyserial")
            return
        try:
            self._serial = serial.Serial(self.port_name, self.baud, timeout=0.1)
            self.connected.emit()
        except Exception as e:
            self.error.emit(f"Failed to open {self.port_name} @ {self.baud}: {e}")
            return

        try:
            while not self._stop_event.is_set():
                try:
                    data = self._serial.read(4096)
                    if data:
                        self.data_received.emit(data)
                    else:
                        # Short nap to avoid busy loop
                        time.sleep(0.01)
                except Exception as e:
                    self.error.emit(f"Serial read error: {e}")
                    break
        finally:
            try:
                if self._serial and self._serial.is_open:
                    self._serial.close()
            except Exception:
                pass
            self.disconnected.emit()

    def stop(self):
        self._stop_event.set()

    def write(self, data: bytes):
        with self._lock:
            try:
                if self._serial and self._serial.is_open:
                    self._serial.write(data)
                else:
                    self.error.emit("Serial port is not open.")
            except Exception as e:
                self.error.emit(f"Serial write error: {e}")


# ---------------------------- Profile Editor Dialog ----------------------------

class CommandEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, label: str = "", text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Command")
        self.setMinimumWidth(400)

        form = QtWidgets.QFormLayout(self)

        self.label_edit = QtWidgets.QLineEdit(label)
        self.text_edit = QtWidgets.QPlainTextEdit(text)

        form.addRow("Button label:", self.label_edit)
        form.addRow("Command text:", self.text_edit)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_values(self):
        return self.label_edit.text().strip(), self.text_edit.toPlainText()


class ProfileManagerDialog(QtWidgets.QDialog):
    """
    Create/edit profiles, sections, and commands.
    """
    profile_saved = pyqtSignal(Profile)  # emitted on save

    def __init__(self, store: ProfileStore, current_profile: Optional[Profile] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Profiles & Sections")
        self.resize(800, 500)
        self.store = store

        # Left: profiles & sections
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        self.profile_list = QtWidgets.QListWidget()
        self.profile_list.addItems(self.store.list_profiles())
        if current_profile:
            # Ensure current is in list
            items = [self.profile_list.item(i).text() for i in range(self.profile_list.count())]
            if current_profile.name not in items:
                self.profile_list.addItem(current_profile.name)
        self.profile_list.setCurrentRow(0 if self.profile_list.count() else -1)
        left_layout.addWidget(QtWidgets.QLabel("Profiles"))
        left_layout.addWidget(self.profile_list, 1)

        prof_btns = QtWidgets.QHBoxLayout()
        self.btn_add_prof = QtWidgets.QPushButton("Add")
        self.btn_rename_prof = QtWidgets.QPushButton("Rename")
        self.btn_del_prof = QtWidgets.QPushButton("Delete")
        prof_btns.addWidget(self.btn_add_prof)
        prof_btns.addWidget(self.btn_rename_prof)
        prof_btns.addWidget(self.btn_del_prof)
        left_layout.addLayout(prof_btns)

        left_layout.addSpacing(8)
        left_layout.addWidget(QtWidgets.QLabel("Sections"))

        self.section_list = QtWidgets.QListWidget()
        left_layout.addWidget(self.section_list, 1)

        sec_btns = QtWidgets.QHBoxLayout()
        self.btn_add_sec = QtWidgets.QPushButton("Add")
        self.btn_rename_sec = QtWidgets.QPushButton("Rename")
        self.btn_del_sec = QtWidgets.QPushButton("Delete")
        sec_btns.addWidget(self.btn_add_sec)
        sec_btns.addWidget(self.btn_rename_sec)
        sec_btns.addWidget(self.btn_del_sec)
        left_layout.addLayout(sec_btns)

        # Right: commands of selected section
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        self.commands_list = QtWidgets.QListWidget()
        right_layout.addWidget(QtWidgets.QLabel("Commands in Section"))
        right_layout.addWidget(self.commands_list, 1)

        cmd_btns = QtWidgets.QHBoxLayout()
        self.btn_add_cmd = QtWidgets.QPushButton("Add Command")
        self.btn_edit_cmd = QtWidgets.QPushButton("Edit")
        self.btn_del_cmd = QtWidgets.QPushButton("Delete")
        cmd_btns.addWidget(self.btn_add_cmd)
        cmd_btns.addWidget(self.btn_edit_cmd)
        cmd_btns.addWidget(self.btn_del_cmd)
        right_layout.addLayout(cmd_btns)

        # Bottom save/close
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Close)

        # Layout
        h = QtWidgets.QHBoxLayout(self)
        h.addWidget(left, 1)
        h.addWidget(right, 1)

        h2 = QtWidgets.QVBoxLayout()
        h2.addStretch(1)
        h2.addWidget(bb)
        h.addLayout(h2)

        # State
        self.current_profile: Optional[Profile] = None
        if current_profile:
            self.load_profile(current_profile.name)
        elif self.profile_list.count():
            self.load_profile(self.profile_list.item(0).text())

        # Signals
        self.profile_list.currentTextChanged.connect(self.load_profile)
        self.section_list.currentTextChanged.connect(self._refresh_commands)

        self.btn_add_prof.clicked.connect(self._add_profile)
        self.btn_rename_prof.clicked.connect(self._rename_profile)
        self.btn_del_prof.clicked.connect(self._delete_profile)

        self.btn_add_sec.clicked.connect(self._add_section)
        self.btn_rename_sec.clicked.connect(self._rename_section)
        self.btn_del_sec.clicked.connect(self._delete_section)

        self.btn_add_cmd.clicked.connect(self._add_command)
        self.btn_edit_cmd.clicked.connect(self._edit_command)
        self.btn_del_cmd.clicked.connect(self._delete_command)

        bb.accepted.connect(self._save_and_close)
        bb.rejected.connect(self.reject)

    # ---------- Helpers ----------

    def load_profile(self, name: str):
        if not name:
            self.current_profile = None
            self.section_list.clear()
            self.commands_list.clear()
            return
        prof = self.store.load_profile(name)
        self.current_profile = prof
        self._refresh_sections()

    def _refresh_sections(self):
        self.section_list.blockSignals(True)
        self.section_list.clear()
        if not self.current_profile:
            self.section_list.blockSignals(False)
            return
        secs = sorted(self.current_profile.sections.keys(), key=lambda s: s.lower())
        self.section_list.addItems(secs)
        if self.section_list.count():
            self.section_list.setCurrentRow(0)
        self.section_list.blockSignals(False)
        self._refresh_commands()

    def _refresh_commands(self):
        self.commands_list.clear()
        if not self.current_profile:
            return
        sec_name = self.section_list.currentItem().text() if self.section_list.currentItem() else None
        if not sec_name:
            return
        cmds = self.current_profile.sections.get(sec_name, [])
        for c in cmds:
            self.commands_list.addItem(f"{c.label}  —  {c.text.replace(os.linesep,' ')[:60]}")

    # ---------- Profile ops ----------

    def _add_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Profile", "Profile name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.store.list_profiles():
                QtWidgets.QMessageBox.warning(self, "Exists", "A profile with that name already exists.")
                return
            self.store.save_profile(Profile(name=name, sections={}))
            self.profile_list.addItem(name)
            self.profile_list.setCurrentRow(self.profile_list.count()-1)

    def _rename_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return
        old = item.text()
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename Profile", "New name:", text=old)
        if ok and new.strip():
            new = new.strip()
            if new == old:
                return
            if new in self.store.list_profiles():
                QtWidgets.QMessageBox.warning(self, "Exists", "A profile with that name already exists.")
                return
            # rename file
            old_path = self.store.profile_path(old)
            self.current_profile.name = new
            self.store.save_profile(self.current_profile)
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass
            item.setText(new)

    def _delete_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return
        name = item.text()
        reply = QtWidgets.QMessageBox.question(self, "Delete Profile", f"Delete profile '{name}' and its file?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            path = self.store.profile_path(name)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to delete file: {e}")
            row = self.profile_list.currentRow()
            self.profile_list.takeItem(row)
            self.current_profile = None
            self.section_list.clear()
            self.commands_list.clear()

    # ---------- Section ops ----------

    def _add_section(self):
        if not self.current_profile:
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Section", "Section name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.current_profile.sections:
                QtWidgets.QMessageBox.warning(self, "Exists", "A section with that name already exists.")
                return
            self.current_profile.sections[name] = []
            self._refresh_sections()
            # select new
            items = self.section_list.findItems(name, Qt.MatchExactly)
            if items:
                self.section_list.setCurrentItem(items[0])

    def _rename_section(self):
        if not self.current_profile or not self.section_list.currentItem():
            return
        old = self.section_list.currentItem().text()
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename Section", "New name:", text=old)
        if ok and new.strip():
            new = new.strip()
            if new == old:
                return
            if new in self.current_profile.sections:
                QtWidgets.QMessageBox.warning(self, "Exists", "A section with that name already exists.")
                return
            self.current_profile.sections[new] = self.current_profile.sections.pop(old)
            self._refresh_sections()
            items = self.section_list.findItems(new, Qt.MatchExactly)
            if items:
                self.section_list.setCurrentItem(items[0])

    def _delete_section(self):
        if not self.current_profile or not self.section_list.currentItem():
            return
        name = self.section_list.currentItem().text()
        reply = QtWidgets.QMessageBox.question(self, "Delete Section", f"Delete section '{name}'?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.current_profile.sections.pop(name, None)
            self._refresh_sections()

    # ---------- Command ops ----------

    def _add_command(self):
        if not self.current_profile or not self.section_list.currentItem():
            return
        sec = self.section_list.currentItem().text()
        dlg = CommandEditorDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            label, text = dlg.get_values()
            if label:
                self.current_profile.sections[sec].append(CommandItem(label=label, text=text))
                self._refresh_commands()

    def _edit_command(self):
        if not self.current_profile or not self.section_list.currentItem() or not self.commands_list.currentRow() >= 0:
            return
        sec = self.section_list.currentItem().text()
        idx = self.commands_list.currentRow()
        if idx < 0 or idx >= len(self.current_profile.sections[sec]):
            return
        item = self.current_profile.sections[sec][idx]
        dlg = CommandEditorDialog(self, label=item.label, text=item.text)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            label, text = dlg.get_values()
            if label:
                item.label = label
                item.text = text
                self._refresh_commands()

    def _delete_command(self):
        if not self.current_profile or not self.section_list.currentItem() or not self.commands_list.currentRow() >= 0:
            return
        sec = self.section_list.currentItem().text()
        idx = self.commands_list.currentRow()
        if idx < 0 or idx >= len(self.current_profile.sections[sec]):
            return
        reply = QtWidgets.QMessageBox.question(self, "Delete Command", "Delete selected command?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.current_profile.sections[sec].pop(idx)
            self._refresh_commands()

    def _save_and_close(self):
        if self.current_profile:
            self.store.save_profile(self.current_profile)
            self.profile_saved.emit(self.current_profile)
        self.accept()


# ---------------------------- Main Window ----------------------------

class TerminalWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project B")
        self.resize(1100, 700)

        # Persistence store
        self.store = ProfileStore()

        # Widgets
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)

        # Left: terminal area
        left_wrap = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_wrap)

        # Serial toolbar (port/baud/connect)
        serial_bar = QtWidgets.QHBoxLayout()
        self.port_combo = QtWidgets.QComboBox()
        self.refresh_ports_btn = QtWidgets.QPushButton("↻")
        self.refresh_ports_btn.setToolTip("Refresh COM ports")
        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems([
            "300","600","1200","2400","4800","9600","14400","19200","28800","38400","56000","57600","115200","128000","230400","250000","460800","921600"
        ])
        self.baud_combo.setCurrentText("115200")
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.status_lbl = QtWidgets.QLabel("Disconnected")

        serial_bar.addWidget(QtWidgets.QLabel("Port:"))
        serial_bar.addWidget(self.port_combo, 1)
        serial_bar.addWidget(self.refresh_ports_btn)
        serial_bar.addSpacing(8)
        serial_bar.addWidget(QtWidgets.QLabel("Baud:"))
        serial_bar.addWidget(self.baud_combo)
        serial_bar.addSpacing(8)
        serial_bar.addWidget(self.connect_btn)
        serial_bar.addStretch(1)
        serial_bar.addWidget(self.status_lbl)

        # Terminal display
        self.terminal = QtWidgets.QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.terminal.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 12pt;")

        # Input line
        input_bar = QtWidgets.QHBoxLayout()
        self.input_line = QtWidgets.QLineEdit()
        self.send_btn = QtWidgets.QPushButton("Send")
        self.lineend_combo = QtWidgets.QComboBox()
        self.port_combo.setEditable(True)
        self.lineend_combo.addItems(["No line end", r"\\n", r"\\r", r"\\r\\n"])
        self.lineend_combo.setCurrentIndex(3)  # default CRLF
        input_bar.addWidget(QtWidgets.QLabel("Input:"))
        input_bar.addWidget(self.input_line, 1)
        input_bar.addWidget(self.send_btn)
        input_bar.addSpacing(8)
        input_bar.addWidget(QtWidgets.QLabel("Line end:"))
        input_bar.addWidget(self.lineend_combo)

        left_layout.addLayout(serial_bar)
        left_layout.addWidget(self.terminal, 1)
        left_layout.addLayout(input_bar)

        # Right: profiles/sections/command buttons
        right_wrap = QtWidgets.QWidget()
        right_wrap.setMinimumWidth(320)
        right_layout = QtWidgets.QVBoxLayout(right_wrap)

        self.profile_combo = QtWidgets.QComboBox()
        self.section_combo = QtWidgets.QComboBox()
        self.edit_profiles_btn = QtWidgets.QPushButton("Edit Profiles…")

        right_layout.addWidget(QtWidgets.QLabel("Profile"))
        right_layout.addWidget(self.profile_combo)
        right_layout.addSpacing(6)
        right_layout.addWidget(QtWidgets.QLabel("Section"))
        right_layout.addWidget(self.section_combo)
        right_layout.addSpacing(6)
        right_layout.addWidget(self.edit_profiles_btn)

        # Scroll area for dynamic command buttons
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.buttons_container = QtWidgets.QWidget()
        self.buttons_layout = QtWidgets.QVBoxLayout(self.buttons_container)
        self.buttons_layout.addStretch(1)
        self.scroll_area.setWidget(self.buttons_container)

        right_layout.addWidget(self.scroll_area, 1)

        main_layout.addWidget(left_wrap, 1)
        main_layout.addWidget(right_wrap)

        # Serial state
        self.worker: Optional[SerialWorker] = None
        self._connected = False

        # Signals
        self.refresh_ports_btn.clicked.connect(self._refresh_ports)
        self.connect_btn.clicked.connect(self._toggle_connect)
        self.send_btn.clicked.connect(self._send_input)
        self.input_line.returnPressed.connect(self._send_input)

        self.profile_combo.currentTextChanged.connect(self._profile_changed)
        self.section_combo.currentTextChanged.connect(self._section_changed)
        self.edit_profiles_btn.clicked.connect(self._open_profile_manager)

        # Populate initial data
        self._refresh_ports()
        self._load_profiles_into_combo()

        # Shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self, activated=self.terminal.clear)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+K"), self, activated=self.terminal.clear)

    # ------------------------ Serial Methods ------------------------

    def _refresh_ports(self):
        self.port_combo.clear()
        if list_ports is None:
            self.port_combo.addItem("pyserial not installed")
            return
        ports = list(list_ports.comports())
        if not ports:
            self.port_combo.addItem("<no ports>")
        else:
            for p in ports:
                # Show like: COM3 - USB Serial Device (ttyUSB0 on Linux shown as device path)
                display = f"{p.device} — {p.description}"
                self.port_combo.addItem(display, userData=p.device)

    def _toggle_connect(self):
        if self._connected:
            self._disconnect_serial()
        else:
            self._connect_serial()

    def _connect_serial(self):
        # Determine port name
        if self.port_combo.count() == 0:
            QtWidgets.QMessageBox.warning(self, "No Port", "No COM ports available.")
            return
        data = self.port_combo.currentData()
        port_name = data if data else self.port_combo.currentText().split(" — ")[0].strip()
        try:
            baud = int(self.baud_combo.currentText())
        except ValueError:
            baud = 115200

        self.terminal.appendPlainText(f"[Connecting to {port_name} @ {baud}…]")
        self.worker = SerialWorker(port_name, baud)
        self.worker.data_received.connect(self._on_serial_data)
        self.worker.error.connect(self._on_serial_error)
        self.worker.connected.connect(self._on_serial_connected)
        self.worker.disconnected.connect(self._on_serial_disconnected)
        self.worker.start()

    def _disconnect_serial(self):
        if self.worker:
            self.terminal.appendPlainText("[Disconnecting…]")
            self.worker.stop()
            self.worker.wait(1500)
            self.worker = None

    def _on_serial_connected(self):
        self._connected = True
        self.status_lbl.setText("Connected")
        self.connect_btn.setText("Disconnect")
        self.terminal.appendPlainText("[Connected]")

    def _on_serial_disconnected(self):
        self._connected = False
        self.status_lbl.setText("Disconnected")
        self.connect_btn.setText("Connect")
        self.terminal.appendPlainText("[Disconnected]")

    def _on_serial_error(self, msg: str):
        self.terminal.appendPlainText(f"[Error] {msg}")
        # If failed to open, ensure clean state
        if not self._connected:
            self._on_serial_disconnected()

    def _on_serial_data(self, data: bytes):
        try:
            text = data.decode(errors="replace")
        except Exception:
            text = str(data)
        # Append without losing scroll
        at_bottom = self._is_scrolled_to_bottom(self.terminal)
        self.terminal.moveCursor(QtGui.QTextCursor.End)
        self.terminal.insertPlainText(text)
        if at_bottom:
            self.terminal.moveCursor(QtGui.QTextCursor.End)

    def _is_scrolled_to_bottom(self, edit: QtWidgets.QPlainTextEdit) -> bool:
        sb = edit.verticalScrollBar()
        return sb.value() == sb.maximum()

    def _send_input(self):
        text = self.input_line.text()
        if not text and self.lineend_combo.currentIndex() == 0:
            return
        suffix = self._selected_line_ending_bytes()
        payload = (text.encode() + suffix)
        if self.worker and self._connected:
            self.worker.write(payload)
        else:
            QtWidgets.QMessageBox.information(self, "Not connected", "Connect to a serial port first.")
            return
        self.input_line.clear()

    def _selected_line_ending_bytes(self) -> bytes:
        idx = self.lineend_combo.currentIndex()
        if idx == 1:
            return b"\n"
        elif idx == 2:
            return b"\r"
        elif idx == 3:
            return b"\r\n"
        return b""

    # ------------------------ Profiles / Sections ------------------------

    def _load_profiles_into_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        names = self.store.list_profiles()
        if not names:
            # create a default empty profile
            default = Profile(name="Default", sections={"Quick": []})
            self.store.save_profile(default)
            names = [default.name]
        self.profile_combo.addItems(names)
        self.profile_combo.blockSignals(False)
        # trigger load
        if names:
            self._profile_changed(names[0])

    def _profile_changed(self, name: str):
        if not name:
            return
        self.current_profile = self.store.load_profile(name)
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        secs = sorted(self.current_profile.sections.keys(), key=lambda s: s.lower())
        self.section_combo.addItems(secs)
        self.section_combo.blockSignals(False)
        if secs:
            self._section_changed(secs[0])
        else:
            self._rebuild_buttons([])

    def _section_changed(self, sec_name: str):
        if not sec_name:
            self._rebuild_buttons([])
            return
        cmds = self.current_profile.sections.get(sec_name, [])
        self._rebuild_buttons(cmds)

    def _rebuild_buttons(self, commands: List[CommandItem]):
        # Clear old widgets
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        # Build buttons
        if not commands:
            lbl = QtWidgets.QLabel("No commands in this section.\nClick 'Edit Profiles…' to add some.")
            lbl.setAlignment(Qt.AlignCenter)
            self.buttons_layout.addWidget(lbl)
            self.buttons_layout.addStretch(1)
            return

        for cmd in commands:
            btn = QtWidgets.QPushButton(cmd.label or "(no label)")
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda _, c=cmd: self._send_command(c))
            self.buttons_layout.addWidget(btn)
        self.buttons_layout.addStretch(1)

    def _send_command(self, cmd: CommandItem):
        text = cmd.text or ""
        if not text and self.lineend_combo.currentIndex() == 0:
            return
        payload = text.encode() + self._selected_line_ending_bytes()
        if self.worker and self._connected:
            self.worker.write(payload)
        else:
            QtWidgets.QMessageBox.information(self, "Not connected", "Connect to a serial port first.")

    def _open_profile_manager(self):
        # Ensure we pass currently selected profile
        current_name = self.profile_combo.currentText().strip() if self.profile_combo.currentText() else None
        prof = self.store.load_profile(current_name) if current_name else None
        dlg = ProfileManagerDialog(self.store, current_profile=prof, parent=self)
        dlg.profile_saved.connect(self._on_profile_saved)
        dlg.exec_()

    def _on_profile_saved(self, profile: Profile):
        # Refresh combos, keep selection on saved profile
        current_profile_name = profile.name
        self._load_profiles_into_combo()
        # set to saved profile
        idx = self.profile_combo.findText(current_profile_name, Qt.MatchExactly)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

    # ------------------------ Window / Close ------------------------

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(1000)
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = TerminalWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
