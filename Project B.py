# Jermz wuz hir

import os
import sys
import json
import glob
import threading
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal

# Attempt to import pyserial; the app will still run without it but serial I/O won't work
try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None

PROFILES_DIR = "profiles"

# ---------------------------- Data models ----------------------------
@dataclass
class CommandItem:
    label: str
    text: str

@dataclass
class Profile:
    name: str
    sections: Dict[str, List[CommandItem]]

# ---------------------------- Profile persistence ----------------------------
class ProfileStore:
    def __init__(self, base_dir: str = PROFILES_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, profile_name: str) -> str:
        safe = "".join(c for c in profile_name if c.isalnum() or c in "-_ ").strip()
        if not safe:
            safe = "profile"
        return os.path.join(self.base_dir, f"{safe}.json")

    def list_profiles(self) -> List[str]:
        names = []
        if not os.path.isdir(self.base_dir):
            return names
        for fn in os.listdir(self.base_dir):
            if fn.lower().endswith('.json'):
                names.append(os.path.splitext(fn)[0])
        names.sort(key=lambda s: s.lower())
        return names

    def load_profile(self, name: str) -> Profile:
        path = self._path(name)
        if not os.path.exists(path):
            return Profile(name=name, sections={})
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sections = {}
        for sec_name, cmds in data.get('sections', {}).items():
            items = []
            for c in cmds:
                if isinstance(c, dict):
                    items.append(CommandItem(label=c.get('label',''), text=c.get('text','')))
                else:
                    items.append(CommandItem(label=str(c), text=str(c)))
            sections[sec_name] = items
        return Profile(name=name, sections=sections)

    def save_profile(self, profile: Profile) -> None:
        path = self._path(profile.name)
        data = {
            'name': profile.name,
            'sections': {sec: [asdict(cmd) for cmd in cmds] for sec, cmds in profile.sections.items()}
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------------------- Serial worker ----------------------------
class SerialWorker(QtCore.QThread):
    data_received = pyqtSignal(bytes)
    error = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self, port: str, baud: int, parent=None):
        super().__init__(parent)
        self.port = port
        self.baud = baud
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._serial = None

    def run(self):
        if serial is None:
            self.error.emit("pyserial is not installed. Install with: pip install pyserial")
            return
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.1)
            self.connected.emit()
        except Exception as e:
            self.error.emit(f"Failed to open {self.port} @ {self.baud}: {e}")
            return

        try:
            while not self._stop.is_set():
                try:
                    data = self._serial.read(4096)
                    if data:
                        self.data_received.emit(data)
                    else:
                        # small sleep to avoid busy loop
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
        self._stop.set()

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
class ProfileEditorDialog(QtWidgets.QDialog):
    """
    Advanced editor with drag-and-drop ordering and inline editing.
    Left: profiles (QListWidget)
    Middle: sections (QListWidget, reorderable)
    Right: commands (QListWidget with label stored in text and command in userData)
    """

    profile_saved = pyqtSignal(str)  # emits profile name when saved

    def __init__(self, store: ProfileStore, current_profile: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Profiles")
        self.resize(1000, 520)
        self.store = store

        # Layout
        main = QtWidgets.QHBoxLayout(self)

        # Profiles list
        pframe = QtWidgets.QFrame()
        pv = QtWidgets.QVBoxLayout(pframe)
        pv.addWidget(QtWidgets.QLabel("Profiles"))
        self.profiles_list = QtWidgets.QListWidget()
        self.profiles_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        pv.addWidget(self.profiles_list)
        ph = QtWidgets.QHBoxLayout()
        self.add_profile_btn = QtWidgets.QPushButton("Add")
        self.rename_profile_btn = QtWidgets.QPushButton("Rename")
        self.del_profile_btn = QtWidgets.QPushButton("Delete")
        ph.addWidget(self.add_profile_btn)
        ph.addWidget(self.rename_profile_btn)
        ph.addWidget(self.del_profile_btn)
        pv.addLayout(ph)
        main.addWidget(pframe, 1)

        # Sections list (middle)
        sframe = QtWidgets.QFrame()
        sv = QtWidgets.QVBoxLayout(sframe)
        sv.addWidget(QtWidgets.QLabel("Sections (drag to reorder)"))
        self.sections_list = QtWidgets.QListWidget()
        self.sections_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.sections_list.setDefaultDropAction(Qt.MoveAction)
        sv.addWidget(self.sections_list)
        sh = QtWidgets.QHBoxLayout()
        self.add_section_btn = QtWidgets.QPushButton("Add")
        self.rename_section_btn = QtWidgets.QPushButton("Rename")
        self.del_section_btn = QtWidgets.QPushButton("Delete")
        sh.addWidget(self.add_section_btn)
        sh.addWidget(self.rename_section_btn)
        sh.addWidget(self.del_section_btn)
        sv.addLayout(sh)
        main.addWidget(sframe, 1)

        # Commands list (right)
        cframe = QtWidgets.QFrame()
        cv = QtWidgets.QVBoxLayout(cframe)
        cv.addWidget(QtWidgets.QLabel("Commands (double-click to edit, drag to reorder)"))
        self.commands_list = QtWidgets.QListWidget()
        self.commands_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.commands_list.setDefaultDropAction(Qt.MoveAction)
        cv.addWidget(self.commands_list)
        ch = QtWidgets.QHBoxLayout()
        self.add_cmd_btn = QtWidgets.QPushButton("Add")
        self.edit_cmd_btn = QtWidgets.QPushButton("Edit")
        self.del_cmd_btn = QtWidgets.QPushButton("Delete")
        ch.addWidget(self.add_cmd_btn)
        ch.addWidget(self.edit_cmd_btn)
        ch.addWidget(self.del_cmd_btn)
        cv.addLayout(ch)
        main.addWidget(cframe, 2)

        # Bottom save/cancel
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Close)
        bb.accepted.connect(self._save_and_close)
        bb.rejected.connect(self.reject)

        vwrap = QtWidgets.QVBoxLayout()
        vwrap.addLayout(main)
        vwrap.addWidget(bb)
        self.setLayout(vwrap)

        # Signals
        self.add_profile_btn.clicked.connect(self._add_profile)
        self.rename_profile_btn.clicked.connect(self._rename_profile)
        self.del_profile_btn.clicked.connect(self._delete_profile)

        self.add_section_btn.clicked.connect(self._add_section)
        self.rename_section_btn.clicked.connect(self._rename_section)
        self.del_section_btn.clicked.connect(self._delete_section)

        self.add_cmd_btn.clicked.connect(self._add_command)
        self.edit_cmd_btn.clicked.connect(self._edit_command)
        self.del_cmd_btn.clicked.connect(self._delete_command)

        self.profiles_list.currentTextChanged.connect(self._load_profile_into_editor)
        self.sections_list.currentTextChanged.connect(self._load_section_commands)
        self.commands_list.itemDoubleClicked.connect(self._edit_command_item)

        # internal state
        self.current_profile_name: Optional[str] = None
        self._load_profiles_into_list()
        if current_profile and current_profile in [self.profiles_list.item(i).text() for i in range(self.profiles_list.count())]:
            items = self.profiles_list.findItems(current_profile, Qt.MatchExactly)
            if items:
                self.profiles_list.setCurrentItem(items[0])
        elif self.profiles_list.count():
            self.profiles_list.setCurrentRow(0)

    # ---------- profile list ----------
    def _load_profiles_into_list(self):
        self.profiles_list.clear()
        for name in self.store.list_profiles():
            self.profiles_list.addItem(name)

    def _add_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Profile", "Profile name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.store.list_profiles():
                QtWidgets.QMessageBox.warning(self, "Exists", "Profile already exists")
                return
            p = Profile(name=name, sections={})
            self.store.save_profile(p)
            self._load_profiles_into_list()
            items = self.profiles_list.findItems(name, Qt.MatchExactly)
            if items:
                self.profiles_list.setCurrentItem(items[0])

    def _rename_profile(self):
        it = self.profiles_list.currentItem()
        if not it:
            return
        old = it.text()
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename Profile", "New name:", text=old)
        if ok and new.strip():
            new = new.strip()
            if new == old:
                return
            if new in self.store.list_profiles():
                QtWidgets.QMessageBox.warning(self, "Exists", "Profile already exists")
                return
            # load, save as new, delete old file
            p = self.store.load_profile(old)
            p.name = new
            self.store.save_profile(p)
            try:
                os.remove(self.store._path(old))
            except Exception:
                pass
            self._load_profiles_into_list()
            items = self.profiles_list.findItems(new, Qt.MatchExactly)
            if items:
                self.profiles_list.setCurrentItem(items[0])

    def _delete_profile(self):
        it = self.profiles_list.currentItem()
        if not it:
            return
        name = it.text()
        if QtWidgets.QMessageBox.question(self, "Delete Profile", f"Delete profile '{name}'? This will remove its file.") != QtWidgets.QMessageBox.Yes:
            return
        try:
            os.remove(self.store._path(name))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to delete profile file: {e}")
        self._load_profiles_into_list()

    # ---------- sections ----------
    def _load_profile_into_editor(self, profile_name: str):
        self.current_profile_name = profile_name
        self.sections_list.clear()
        if not profile_name:
            return
        p = self.store.load_profile(profile_name)
        for sec in p.sections.keys():
            self.sections_list.addItem(sec)
        if self.sections_list.count():
            self.sections_list.setCurrentRow(0)

    def _add_section(self):
        if not self.current_profile_name:
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Section", "Section name:")
        if ok and name.strip():
            p = self.store.load_profile(self.current_profile_name)
            if name in p.sections:
                QtWidgets.QMessageBox.warning(self, "Exists", "Section already exists")
                return
            p.sections[name] = []
            self.store.save_profile(p)
            self._load_profile_into_editor(self.current_profile_name)
            items = self.sections_list.findItems(name, Qt.MatchExactly)
            if items:
                self.sections_list.setCurrentItem(items[0])

    def _rename_section(self):
        if not self.current_profile_name:
            return
        it = self.sections_list.currentItem()
        if not it:
            return
        old = it.text()
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename Section", "New name:", text=old)
        if ok and new.strip():
            p = self.store.load_profile(self.current_profile_name)
            if new in p.sections:
                QtWidgets.QMessageBox.warning(self, "Exists", "Section already exists")
                return
            p.sections[new] = p.sections.pop(old)
            self.store.save_profile(p)
            self._load_profile_into_editor(self.current_profile_name)
            items = self.sections_list.findItems(new, Qt.MatchExactly)
            if items:
                self.sections_list.setCurrentItem(items[0])

    def _delete_section(self):
        if not self.current_profile_name:
            return
        it = self.sections_list.currentItem()
        if not it:
            return
        name = it.text()
        if QtWidgets.QMessageBox.question(self, "Delete Section", f"Delete section '{name}'?") != QtWidgets.QMessageBox.Yes:
            return
        p = self.store.load_profile(self.current_profile_name)
        p.sections.pop(name, None)
        self.store.save_profile(p)
        self._load_profile_into_editor(self.current_profile_name)

    # ---------- commands ----------
    def _load_section_commands(self, section_name: str):
        self.commands_list.clear()
        if not self.current_profile_name or not section_name:
            return
        p = self.store.load_profile(self.current_profile_name)
        cmds = p.sections.get(section_name, [])
        for cmd in cmds:
            item = QtWidgets.QListWidgetItem(cmd.label)
            item.setData(Qt.UserRole, cmd.text)
            self.commands_list.addItem(item)

    def _add_command(self):
        if not self.current_profile_name:
            return
        sec_item = self.sections_list.currentItem()
        if not sec_item:
            return
        label, ok = QtWidgets.QInputDialog.getText(self, "Command label", "Label:")
        if not ok or not label.strip():
            return
        text, ok = QtWidgets.QInputDialog.getMultiLineText(self, "Command text", "Command to send:")
        if not ok:
            return
        p = self.store.load_profile(self.current_profile_name)
        p.sections.setdefault(sec_item.text(), []).append(CommandItem(label=label.strip(), text=text))
        self.store.save_profile(p)
        self._load_section_commands(sec_item.text())

    def _edit_command(self):
        it = self.commands_list.currentItem()
        sec_item = self.sections_list.currentItem()
        if not it or not sec_item or not self.current_profile_name:
            return
        label = it.text()
        text = it.data(Qt.UserRole)
        new_label, ok = QtWidgets.QInputDialog.getText(self, "Edit label", "Label:", text=label)
        if not ok:
            return
        new_text, ok = QtWidgets.QInputDialog.getMultiLineText(self, "Edit command", "Command to send:", text=text)
        if not ok:
            return
        p = self.store.load_profile(self.current_profile_name)
        cmds = p.sections.get(sec_item.text(), [])
        # find item by matching label and text; use current row index instead
        idx = self.commands_list.currentRow()
        if 0 <= idx < len(cmds):
            cmds[idx].label = new_label.strip()
            cmds[idx].text = new_text
            self.store.save_profile(p)
            self._load_section_commands(sec_item.text())
            # restore selection
            self.commands_list.setCurrentRow(idx)

    def _edit_command_item(self, item: QtWidgets.QListWidgetItem):
        # convenience: double click
        self._edit_command()

    def _delete_command(self):
        it = self.commands_list.currentItem()
        sec_item = self.sections_list.currentItem()
        if not it or not sec_item or not self.current_profile_name:
            return
        if QtWidgets.QMessageBox.question(self, "Delete Command", f"Delete '{it.text()}'?") != QtWidgets.QMessageBox.Yes:
            return
        p = self.store.load_profile(self.current_profile_name)
        idx = self.commands_list.currentRow()
        if idx >= 0:
            p.sections[sec_item.text()].pop(idx)
            self.store.save_profile(p)
            self._load_section_commands(sec_item.text())

    # ---------- save and close (also handle reordered lists) ----------
    def _save_and_close(self):
        # For the current profile, we need to capture sections order and commands order
        if not self.current_profile_name:
            self.accept()
            return
        p = self.store.load_profile(self.current_profile_name)
        # sections order: take items from sections_list
        new_sections = {}
        for i in range(self.sections_list.count()):
            sec_name = self.sections_list.item(i).text()
            # if previously existed, keep its commands, else create empty
            new_sections[sec_name] = p.sections.get(sec_name, [])
        p.sections = new_sections
        # commands order and content: rebuild for each section from commands_list widgets only for the selected section
        # We assume user moved commands within a selected section; to fully persist drag across sections we'd need more complexity.
        # So reload commands for the currently selected section from the UI list
        sel_sec_item = self.sections_list.currentItem()
        if sel_sec_item:
            sec = sel_sec_item.text()
            new_cmds = []
            for i in range(self.commands_list.count()):
                it = self.commands_list.item(i)
                new_cmds.append(CommandItem(label=it.text(), text=it.data(Qt.UserRole)))
            p.sections[sec] = new_cmds
        self.store.save_profile(p)
        self.profile_saved.emit(self.current_profile_name)
        self.accept()

# ---------------------------- Main Window ----------------------------
class TerminalWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQt TeraTerm-like (Advanced)')
        self.resize(1200, 760)

        self.store = ProfileStore()
        self.worker: Optional[SerialWorker] = None
        self._connected = False

        self.last_command: Optional[str] = None
        self._result_start_offset = 0  # position in terminal text where result started

        self._build_ui()
        self._load_profiles()
        self._refresh_ports()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)

        # Left (terminal)
        left = QtWidgets.QVBoxLayout()
        h.addLayout(left, 3)

        topbar = QtWidgets.QHBoxLayout()
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setEditable(True)
        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems(["300","600","1200","2400","4800","9600","14400","19200","38400","57600","115200"])
        self.baud_combo.setCurrentText("115200")
        self.refresh_ports_btn = QtWidgets.QPushButton("↻")
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.status_lbl = QtWidgets.QLabel("Disconnected")

        self.refresh_ports_btn.setToolTip("Refresh serial ports")
        self.refresh_ports_btn.clicked.connect(self._refresh_ports)
        self.connect_btn.clicked.connect(self._toggle_connect)

        topbar.addWidget(QtWidgets.QLabel("Port:"))
        topbar.addWidget(self.port_combo, 1)
        topbar.addWidget(self.refresh_ports_btn)
        topbar.addSpacing(8)
        topbar.addWidget(QtWidgets.QLabel("Baud:"))
        topbar.addWidget(self.baud_combo)
        topbar.addWidget(self.connect_btn)
        topbar.addStretch(1)
        topbar.addWidget(self.status_lbl)

        left.addLayout(topbar)

        self.terminal = QtWidgets.QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.terminal.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 11pt;")
        left.addWidget(self.terminal, 1)

        # input row
        input_row = QtWidgets.QHBoxLayout()
        self.input_line = QtWidgets.QLineEdit()
        self.send_btn = QtWidgets.QPushButton("Send")
        self.ctrlc_btn = QtWidgets.QPushButton("Ctrl+C")
        self.lineend_combo = QtWidgets.QComboBox()
        self.lineend_combo.addItems(["No line end","\\n","\\r","\\r\\n"])
        self.lineend_combo.setCurrentIndex(3)

        input_row.addWidget(QtWidgets.QLabel("Input:"))
        input_row.addWidget(self.input_line, 1)
        input_row.addWidget(self.send_btn)
        input_row.addWidget(self.ctrlc_btn)
        input_row.addSpacing(6)
        input_row.addWidget(QtWidgets.QLabel("Line end:"))
        input_row.addWidget(self.lineend_combo)

        left.addLayout(input_row)

        # log/copy/search row (below input)
        action_row = QtWidgets.QHBoxLayout()
        self.save_log_btn = QtWidgets.QPushButton("Save Log")
        self.copy_last_btn = QtWidgets.QPushButton("Copy Last Result")
        self.edit_profiles_btn = QtWidgets.QPushButton("Edit Profiles…")
        action_row.addWidget(self.save_log_btn)
        action_row.addWidget(self.copy_last_btn)
        action_row.addStretch(1)
        action_row.addWidget(self.edit_profiles_btn)
        left.addLayout(action_row)

        # Right (profiles, sections, buttons)
        right = QtWidgets.QVBoxLayout()
        h.addLayout(right, 1)

        right.addWidget(QtWidgets.QLabel("Profile"))
        self.profile_combo = QtWidgets.QComboBox()
        right.addWidget(self.profile_combo)
        right.addWidget(QtWidgets.QLabel("Section"))
        self.section_combo = QtWidgets.QComboBox()
        right.addWidget(self.section_combo)

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search commands in current profile…")
        right.addWidget(self.search_bar)

        # Scroll area for buttons
        self.buttons_scroll = QtWidgets.QScrollArea()
        self.buttons_scroll.setWidgetResizable(True)
        scroll_content = QtWidgets.QWidget()
        self.buttons_layout = QtWidgets.QVBoxLayout(scroll_content)
        self.buttons_layout.setContentsMargins(6,6,6,6)
        self.buttons_layout.setSpacing(6)
        self.buttons_layout.addStretch(1)
        self.buttons_scroll.setWidget(scroll_content)
        right.addWidget(self.buttons_scroll, 1)

        # Status at bottom-right
        right_bottom = QtWidgets.QHBoxLayout()
        self.profile_info_lbl = QtWidgets.QLabel("")
        right_bottom.addWidget(self.profile_info_lbl)
        right.addLayout(right_bottom)

        # Signals
        self.send_btn.clicked.connect(self._send_input)
        self.input_line.returnPressed.connect(self._send_input)
        self.ctrlc_btn.clicked.connect(self._send_ctrl_c)
        # keyboard shortcut: Ctrl+C to send ctrl-c (when not in text field copying)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, activated=self._send_ctrl_c)

        self.save_log_btn.clicked.connect(self._save_log)
        self.copy_last_btn.clicked.connect(self._copy_last_result)
        self.edit_profiles_btn.clicked.connect(self._open_profile_editor)

        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        self.section_combo.currentTextChanged.connect(self._on_section_changed)
        self.search_bar.textChanged.connect(self._on_search_changed)

        # populate initial UI
        self._wire_shortcuts()

    def _wire_shortcuts(self):
        # Ctrl+L to clear terminal
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self, activated=self.terminal.clear)

    # ---------------------- Ports ----------------------
    def _refresh_ports(self):
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        if list_ports is None:
            self.port_combo.addItem("pyserial not installed")
            self.port_combo.setEditable(True)
            self.port_combo.blockSignals(False)
            return
        ports = list(list_ports.comports())
        pts_ports = glob.glob('/dev/pts/*') + glob.glob('/dev/tty.*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        added = set()
        for p in ports:
            display = f"{p.device} — {p.description}"
            self.port_combo.addItem(display, userData=p.device)
            added.add(p.device)
        for p in pts_ports:
            if p not in added:
                self.port_combo.addItem(p, userData=p)
                added.add(p)
        self.port_combo.setEditable(True)
        self.port_combo.blockSignals(False)

    def _toggle_connect(self):
        if self._connected:
            self._disconnect_serial()
        else:
            self._connect_serial()

    def _connect_serial(self):
        port_data = self.port_combo.currentData()
        port = port_data if port_data else self.port_combo.currentText().split(' — ')[0].strip()
        try:
            baud = int(self.baud_combo.currentText())
        except Exception:
            baud = 115200

        self._append_line(f"[Connecting to {port} @ {baud}…]\n")
        self.worker = SerialWorker(port, baud)
        self.worker.data_received.connect(self._on_serial_data)
        self.worker.error.connect(self._on_serial_error)
        self.worker.connected.connect(self._on_serial_connected)
        self.worker.disconnected.connect(self._on_serial_disconnected)
        self.worker.start()

    def _disconnect_serial(self):
        if hasattr(self, 'worker') and self.worker:
            self._append_line("[Disconnecting…]\n")
            self.worker.stop()
            self.worker.wait(1500)
            self.worker = None

    def _on_serial_connected(self):
        self._connected = True
        self.status_lbl.setText('Connected')
        self.connect_btn.setText('Disconnect')
        self._append_line('[Connected]\n')

    def _on_serial_disconnected(self):
        self._connected = False
        self.status_lbl.setText('Disconnected')
        self.connect_btn.setText('Connect')
        self._append_line('[Disconnected]\n')

    def _on_serial_error(self, msg: str):
        self._append_line(f"[Error] {msg}\n")
        if not self._connected:
            self._on_serial_disconnected()

    def _on_serial_data(self, data: bytes):
        try:
            text = data.decode(errors='replace')
        except Exception:
            text = str(data)
        at_bottom = self._is_scrolled_to_bottom()
        # Append preserving cursor
        self.terminal.moveCursor(QtGui.QTextCursor.End)
        self.terminal.insertPlainText(text)
        if at_bottom:
            self.terminal.moveCursor(QtGui.QTextCursor.End)

    def _is_scrolled_to_bottom(self) -> bool:
        sb = self.terminal.verticalScrollBar()
        return sb.value() == sb.maximum()

    # ---------------------- Terminal helpers ----------------------
    def _append_line(self, s: str):
        self.terminal.appendPlainText(s)

    # ---------------------- Sending commands ----------------------
    def _selected_line_ending_bytes(self) -> bytes:
        idx = self.lineend_combo.currentIndex()
        if idx == 1:
            return b"\n"
        elif idx == 2:
            return b"\r"
        elif idx == 3:
            return b"\r\n"
        return b""

    def _send_input(self):
        text = self.input_line.text()
        if text == "" and self.lineend_combo.currentIndex() == 0:
            return
        payload = text.encode() + self._selected_line_ending_bytes()
        if self.worker and self._connected:
            self.worker.write(payload)
            # capture for last result
            self.last_command = text
            self._result_start_offset = len(self.terminal.toPlainText())
        else:
            QtWidgets.QMessageBox.information(self, 'Not connected', 'Connect to a serial port first.')
            return
        self.input_line.clear()

    def _send_ctrl_c(self):
        # send ASCII ETX
        payload = b"\x03"
        if self.worker and self._connected:
            self.worker.write(payload)
            self.last_command = 'Ctrl+C'
            self._result_start_offset = len(self.terminal.toPlainText())
        else:
            # If user tries to copy (Ctrl+C) within a text field, we don't want to override native copy.
            # But the QShortcut is bound globally; we still try to send when possible.
            pass

    def _send_command(self, cmd_text: str):
        if not cmd_text:
            return
        payload = cmd_text.encode() + self._selected_line_ending_bytes()
        if self.worker and self._connected:
            self.worker.write(payload)
            self.last_command = cmd_text
            self._result_start_offset = len(self.terminal.toPlainText())
        else:
            QtWidgets.QMessageBox.information(self, 'Not connected', 'Connect to a serial port first.')

    # ---------------------- Log & copy ----------------------
    def _save_log(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Log', '', 'Text Files (*.txt);;All Files (*)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.terminal.toPlainText())
            QtWidgets.QMessageBox.information(self, 'Saved', f'Log saved to {path}')
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', f'Failed to save: {e}')

    def _copy_last_result(self):
        if not self.last_command:
            QtWidgets.QMessageBox.information(self, 'No command', 'No command has been sent yet.')
            return
        full = self.terminal.toPlainText()
        if self._result_start_offset <= 0 or self._result_start_offset > len(full):
            result = ''
        else:
            result = full[self._result_start_offset:]
        # trim leading/trailing whitespace
        result = result.strip('\n\r ')
        QtWidgets.QApplication.clipboard().setText(result)
        QtWidgets.QMessageBox.information(self, 'Copied', 'Last result copied to clipboard')

    # ---------------------- Profiles / Sections / Buttons ----------------------
    def _load_profiles(self):
        names = self.store.list_profiles()
        if not names:
            # create default sample
            p = Profile(name='Default', sections={'Quick': [CommandItem(label='AT', text='AT'), CommandItem(label='Reset', text='reset')]})
            self.store.save_profile(p)
            names = [p.name]
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(names)
        self.profile_combo.blockSignals(False)
        if names:
            self._on_profile_changed(names[0])

    def _on_profile_changed(self, name: str):
        if not name:
            return
        self.current_profile = self.store.load_profile(name)
        # populate sections
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        secs = list(self.current_profile.sections.keys())
        self.section_combo.addItems(secs)
        self.section_combo.blockSignals(False)
        if secs:
            self._on_section_changed(secs[0])
        else:
            self._rebuild_buttons([])
        self.profile_info_lbl.setText(f"{self.current_profile.name} — {len(secs)} section(s)")

    def _on_section_changed(self, sec: str):
        if not sec:
            self._rebuild_buttons([])
            return
        cmds = self.current_profile.sections.get(sec, [])
        self._rebuild_buttons(cmds)

    def _rebuild_buttons(self, commands: List[CommandItem]):
        # clear layout children except the final stretch
        content = self.buttons_scroll.widget()
        layout = self.buttons_layout
        # remove everything
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        # build new
        if not commands:
            lbl = QtWidgets.QLabel('No commands in this section. Click Edit Profiles to add.')
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
            layout.addStretch(1)
            return
        for cmd in commands:
            btn = QtWidgets.QPushButton(cmd.label or '(no label)')
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda _, c=cmd: self._send_command(c.text))
            layout.addWidget(btn)
        layout.addStretch(1)

    def _on_search_changed(self, text: str):
        # Global search across current profile
        query = text.strip().lower()
        if not query:
            # restore to current section
            cur_sec = self.section_combo.currentText()
            if cur_sec:
                self._on_section_changed(cur_sec)
            return
        # collect matches across profile
        matches: List[tuple] = []  # (section, CommandItem)
        for sec_name, cmds in self.current_profile.sections.items():
            for cmd in cmds:
                if query in (cmd.label or '').lower() or query in (cmd.text or '').lower():
                    matches.append((sec_name, cmd))
        # rebuild buttons area with matches
        layout = self.buttons_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not matches:
            lbl = QtWidgets.QLabel('No matching commands')
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
            layout.addStretch(1)
            return
        for sec_name, cmd in matches:
            btn = QtWidgets.QPushButton(f"{sec_name}: {cmd.label}")
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda _, c=cmd: self._send_command(c.text))
            layout.addWidget(btn)
        layout.addStretch(1)

    # ---------------------- Profile editor ----------------------
    def _open_profile_editor(self):
        dlg = ProfileEditorDialog(self.store, current_profile=self.profile_combo.currentText(), parent=self)
        dlg.profile_saved.connect(self._on_profile_editor_saved)
        dlg.exec_()

    def _on_profile_editor_saved(self, prof_name: str):
        # reload profiles and select
        self._load_profiles()
        idx = self.profile_combo.findText(prof_name, Qt.MatchExactly)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

# ---------------------------- App entry ----------------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = TerminalWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
