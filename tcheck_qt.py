"""
T-Check GUI  –  Qt (PyQt5) front-end (self-contained)

Accuracy test for Vector Network Analyzers using a Tee-junction, based on
Rohde & Schwarz Application Note 1EZ43_0E (Olaf Ostwald, 1998).
"""

import cmath
import csv
import math
import random
import sys
import time
from datetime import datetime

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QActionGroup, QApplication, QCheckBox, QComboBox,
    QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


# ═══ T-Check core ═══════════════════════════════════════════════════════════

def tcheck(s11: complex, s21: complex) -> float:
    """
    Compute the T-Check parameter cT for a single frequency point.

        cT = |S11·S21* + S21·S11*| / (1 - |S11|² - |S21|²)

    Returns cT as a fraction (1.0 = 100 %).
    """
    numerator = abs(s11 * s21.conjugate() + s21 * s11.conjugate())
    denominator = 1.0 - abs(s11) ** 2 - abs(s21) ** 2

    if denominator <= 0:
        raise ValueError(
            f"Denominator ≤ 0 ({denominator:.6f}): "
            "|S11|² + |S21|² ≥ 1 — DUT violates losslessness assumption."
        )

    return numerator / denominator


def db_deg_to_complex(db: float, deg: float) -> complex:
    """Convert (magnitude in dB, phase in degrees) to a complex number."""
    mag = 10 ** (db / 20.0)
    rad = math.radians(deg)
    return cmath.rect(mag, rad)


def _require_serial():
    """Import pyserial, giving a helpful message if it is missing."""
    try:
        import serial
        import serial.tools.list_ports
        return serial, serial.tools.list_ports
    except ImportError:
        print("ERROR: pyserial is not installed.")
        print("       Run:  pip install pyserial")
        sys.exit(1)


def _find_nanovna_port(list_ports):
    """Auto-detect a NanoVNA among the available serial ports."""
    candidates = []
    for port in list_ports.comports():
        desc = (port.description or "").lower()
        mfg  = (port.manufacturer or "").lower()
        if any(k in desc or k in mfg for k in ("nanovna", "cdc", "stm32", "hugen")):
            candidates.append(port.device)
    return candidates[0] if candidates else None


def _send_cmd(ser, cmd: str, timeout: float = 2.0) -> list:
    """Send a command and collect response lines until the 'ch>' prompt."""
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode())

    lines = []
    deadline = time.monotonic() + timeout
    buf = ""
    while time.monotonic() < deadline:
        chunk = ser.read(ser.in_waiting or 1).decode(errors="replace")
        buf += chunk
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.strip("\r")
            if line and line != cmd.strip():   # skip command echo
                lines.append(line)
        if "ch>" in buf:
            break
    return lines


def _parse_complex_lines(lines: list) -> list:
    """Parse NanoVNA data lines of the form 'real imag'."""
    values = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("ch>"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                values.append(complex(float(parts[0]), float(parts[1])))
            except ValueError:
                pass
    return values


def _generate_example(n: int = 101,
                      f_start: float = 10e6,
                      f_stop:  float = 4e9) -> list:
    """Simulate a realistic NanoVNA sweep of a symmetric tee-junction."""
    rng = random.Random(42)          # fixed seed → reproducible

    pts = []
    for i in range(n):
        f = f_start + i * (f_stop - f_start) / (n - 1)
        t = f / f_stop               # 0 … 1

        s11_db  = -9.54 - 0.40 * t          # mild roll-off
        s11_deg = 180.0 - 6.0  * t          # small phase rotation
        s21_db  = -3.52 - 0.22 * t
        s21_deg =   0.0 + 5.0  * t

        s11_db  += rng.gauss(0, 0.04)
        s11_deg += rng.gauss(0, 0.3)
        s21_db  += rng.gauss(0, 0.02)
        s21_deg += rng.gauss(0, 0.2)

        pts.append((f,
                    db_deg_to_complex(s11_db, s11_deg),
                    db_deg_to_complex(s21_db, s21_deg)))
    return pts


EXAMPLE_MEASUREMENTS = _generate_example(101)


# ── colour theme (bright) ───────────────────────────────────────────────────
BG        = "#f5f5f5"
PANEL     = "#ffffff"
ACCENT    = "#1565c0"
FG        = "#1a1a1a"
FG_DIM    = "#555555"
GREEN_BG  = "#c8e6c9"
GREEN_FG  = "#1b5e20"
YELLOW_BG = "#fff9c4"
YELLOW_FG = "#f57f17"
RED_BG    = "#ffcdd2"
RED_FG    = "#b71c1c"
ENTRY_BG  = "#e8eaf6"
BTN_ACT   = "#0d47a1"

# ── plot band colours (darker, solid) ───────────────────────────────────────
PLOT_GREEN  = "#388e3c"
PLOT_YELLOW = "#f9a825"
PLOT_RED    = "#c62828"
PLOT_BG     = "#fafafa"


# ── translations ────────────────────────────────────────────────────────────
STRINGS = {
    "en": {
        "win_title":       "T-Check  –  VNA Accuracy Test",
        "subtitle":        "  VNA Accuracy Test  ·  Tee-junction method",
        "menu_settings":   "Settings",
        "menu_source":     "Data Source",
        "src_example":     "Built-in example data",
        "src_nanovna":     "NanoVNA  (serial)",
        "menu_language":   "Language",
        "menu_csv":        "CSV output on console",
        "nvna_frame":      " NanoVNA settings ",
        "lbl_port":        "Serial port",
        "lbl_start":       "Start frequency",
        "lbl_stop":        "Stop  frequency",
        "lbl_points":      "Data points",
        "lbl_average":     "Average measurements",
        "lbl_repeats":     "No of Measurements",
        "hint_port":       "e.g. /dev/ttyACM0 or COM3",
        "hint_start":      "e.g. 100kHz  1MHz  500000Hz",
        "hint_stop":       "e.g. 900MHz  1.5GHz",
        "btn_detect":      "Auto-detect port",
        "btn_run":         "▶  Run T-Check",
        "btn_running":     "⏳  Running…",
        "col_freq":        "Frequency (MHz)",
        "col_ct":          "cT (%)",
        "col_dev":         "Deviation",
        "col_quality":     "Quality",
        "leg_green":       "● ≤ ±10 %  good",
        "leg_yellow":      "● 10–15 %  borderline",
        "leg_red":         "● > 15 %   calibration issue",
        "axis_freq":       "Frequency (MHz)",
        "axis_ct":         "cT  (%)",
        "st_acquiring":    "Acquiring data…",
        "st_connecting":   "Connecting to {}…",
        "st_sweep":        "Configuring sweep…",
        "st_s11":          "Reading S11…",
        "st_s21":          "Reading S21…",
        "st_average":      "Averaging measurement {} of {}…",
        "st_done":         "{} points evaluated.",
        "pts_label":       "{} points",
        "no_port":         "No serial port specified.",
        "stop_gt_start":   "Stop frequency must be greater than start frequency.",
        "no_data":         "No data received from NanoVNA.",
        "no_ports":        "No serial ports found.",
        "no_nvna":         "No NanoVNA found. Available: {}",
        "detected":        "Auto-detected: {}",
        "serial_unavailable": "pyserial is not installed.",
        "q_good":          "good",
        "q_border":        "borderline",
        "q_issue":         "calibration issue",
        "menu_info":       "Info",
        "menu_credits":    "Credits",
        "credits_title":   "Credits",
        "credits_text":    (
            "nanoT-check\n"
            "NanoVNA Accuracy Test using the Tee-junction method\n\n"
            "Based on:\n"
            "  Rohde & Schwarz Application Note 1EZ43_0E\n"
            "  \u2018T-Check – Accuracy Test for Vector Network\n"
            "   Analyzers utilizing a Tee-junction\u2019\n"
            "  Olaf Ostwald, Rohde & Schwarz, 3 June 1998\n\n"
            "Software developed by:\n"
            "  DG1JAN\n\n"
            "Coding assistant:\n"
            "  GitHub Copilot  –  Claude Sonnet 4.6\n"
        ),
    },
    "de": {
        "win_title":       "T-Check  –  VNA-Genauigkeitstest",
        "subtitle":        "  VNA-Genauigkeitstest  ·  T-Leitungs-Methode",
        "menu_settings":   "Einstellungen",
        "menu_source":     "Datenquelle",
        "src_example":     "Eingebaute Beispieldaten",
        "src_nanovna":     "NanoVNA  (seriell)",
        "menu_language":   "Sprache",
        "menu_csv":        "CSV-Ausgabe auf der Konsole",
        "nvna_frame":      " NanoVNA-Einstellungen ",
        "lbl_port":        "Serieller Port",
        "lbl_start":       "Startfrequenz",
        "lbl_stop":        "Stoppfrequenz",
        "lbl_points":      "Datenpunkte",
        "lbl_average":     "Messungen mitteln",
        "lbl_repeats":     "Anzahl der Messungen",
        "hint_port":       "z.B. /dev/ttyACM0 oder COM3",
        "hint_start":      "z.B. 100kHz  1MHz  500000Hz",
        "hint_stop":       "z.B. 900MHz  1.5GHz",
        "btn_detect":      "Port erkennen",
        "btn_run":         "▶  T-Check starten",
        "btn_running":     "⏳  Läuft…",
        "col_freq":        "Frequenz (MHz)",
        "col_ct":          "cT (%)",
        "col_dev":         "Abweichung",
        "col_quality":     "Bewertung",
        "leg_green":       "● ≤ ±10 %  gut",
        "leg_yellow":      "● 10–15 %  grenzwertig",
        "leg_red":         "● > 15 %   Kalibrierungsproblem",
        "axis_freq":       "Frequenz (MHz)",
        "axis_ct":         "cT  (%)",
        "st_acquiring":    "Daten werden erfasst…",
        "st_connecting":   "Verbinde mit {}…",
        "st_sweep":        "Sweep wird konfiguriert…",
        "st_s11":          "S11 wird gelesen…",
        "st_s21":          "S21 wird gelesen…",
        "st_average":      "Messung {} von {} wird gemittelt…",
        "st_done":         "{} Punkte ausgewertet.",
        "pts_label":       "{} Punkte",
        "no_port":         "Kein serieller Port angegeben.",
        "stop_gt_start":   "Stoppfrequenz muss größer als Startfrequenz sein.",
        "no_data":         "Keine Daten vom NanoVNA empfangen.",
        "no_ports":        "Keine seriellen Ports gefunden.",
        "no_nvna":         "Kein NanoVNA gefunden. Verfügbar: {}",
        "detected":        "Erkannt: {}",
        "serial_unavailable": "pyserial ist nicht installiert.",
        "q_good":          "gut",
        "q_border":        "grenzwertig",
        "q_issue":         "Kalibrierungsproblem",
        "menu_info":       "Info",
        "menu_credits":    "Impressum",
        "credits_title":   "Impressum",
        "credits_text":    (
            "nanoT-check\n"
            "NanoVNA-Genauigkeitstest mit der T-Leitungs-Methode\n\n"
            "Basierend auf:\n"
            "  Rohde & Schwarz Applikationsschrift 1EZ43_0E\n"
            "  \u2018T-Check – Genauigkeitstest f\u00fcr Vektornetzwerk-\n"
            "   analysatoren mit T-Leitungsverbindung\u2019\n"
            "  Olaf Ostwald, Rohde & Schwarz, 3. Juni 1998\n\n"
            "Software entwickelt von:\n"
            "  DG1JAN\n\n"
            "Programmierassistent:\n"
            "  GitHub Copilot  –  Claude Sonnet 4.6\n"
        ),
    },
}


class AcquireWorker(QThread):
    """Background acquisition so the GUI stays responsive."""

    status      = pyqtSignal(str, str)          # message, colour
    freq_labels = pyqtSignal(float, float)
    points      = pyqtSignal(int)
    finished_ok = pyqtSignal(object)
    failed      = pyqtSignal(str)

    def __init__(self, app, source, port, average, repeats):
        super().__init__()
        self._app     = app
        self._source  = source
        self._port    = port
        self._average = average
        self._repeats = repeats

    def _tr(self, key, *args):
        return self._app._tr(key, *args)

    def run(self):
        try:
            if self._source == "nanovna":
                measurements = self._acquire_nanovna()
            else:
                measurements = EXAMPLE_MEASUREMENTS
            self.finished_ok.emit(measurements)
        except SystemExit:
            self.failed.emit(self._tr("serial_unavailable"))
        except Exception as exc:
            self.failed.emit(str(exc))

    def _acquire_nanovna(self):
        serial, _list_ports = _require_serial()

        port = self._port
        if not port:
            raise ValueError(self._tr("no_port"))

        self.status.emit(self._tr("st_connecting", port), FG_DIM)

        try:
            ser = serial.Serial(port, baudrate=115200, timeout=1)
        except serial.SerialException as exc:
            raise RuntimeError(f"Cannot open {port}: {exc}") from exc

        time.sleep(0.3)
        freq_lines = _send_cmd(ser, "frequencies", timeout=5.0)
        repeats = self._repeats
        repeat_values = []
        for repeat in range(repeats):
            if self._average:
                self.status.emit(self._tr("st_average", repeat + 1, repeats),
                                 FG_DIM)
            else:
                self.status.emit(self._tr("st_s11"), FG_DIM)
            s11_lines = _send_cmd(ser, "data 0", timeout=5.0)
            self.status.emit(self._tr("st_s21"), FG_DIM)
            s21_lines = _send_cmd(ser, "data 1", timeout=5.0)
            repeat_values.append((_parse_complex_lines(s11_lines),
                                  _parse_complex_lines(s21_lines)))
            if repeat + 1 < repeats:
                time.sleep(3.0)
        ser.close()

        freqs = []
        for line in freq_lines:
            line = line.strip()
            if line and not line.startswith("ch>"):
                try:
                    freqs.append(float(line))
                except ValueError:
                    pass

        s11_lengths = {len(s11) for s11, _ in repeat_values}
        s21_lengths = {len(s21) for _, s21 in repeat_values}
        if len(s11_lengths) != 1 or len(s21_lengths) != 1:
            raise RuntimeError(self._tr("no_data"))
        s11_vals = [sum(values[index] for values, _ in repeat_values) / repeats
                    for index in range(len(repeat_values[0][0]))]
        s21_vals = [sum(values[index] for _, values in repeat_values) / repeats
                    for index in range(len(repeat_values[0][1]))]

        n = min(len(freqs), len(s11_vals), len(s21_vals))
        if n == 0:
            raise RuntimeError(self._tr("no_data"))

        self.freq_labels.emit(freqs[0], freqs[n - 1])
        self.points.emit(n)
        return list(zip(freqs[:n], s11_vals[:n], s21_vals[:n]))


class CreditsDialog(QDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(600, 480)
        self.setStyleSheet(f"background-color: {PANEL};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)

        stripe = QFrame()
        stripe.setFixedHeight(4)
        stripe.setStyleSheet(f"background-color: {ACCENT};")
        layout.addWidget(stripe)

        heading = QLabel("nanoT-check")
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont("Helvetica", 16, QFont.Bold))
        heading.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(heading)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setFrameShape(QFrame.NoFrame)
        body.setPlainText(text)
        body.setStyleSheet(f"background-color: {PANEL}; color: {FG};")
        layout.addWidget(body, 1)

        ok = QPushButton("OK")
        ok.setCursor(Qt.PointingHandCursor)
        ok.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #ffffff;"
            f" border: none; padding: 6px 24px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {BTN_ACT}; }}")
        ok.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(ok)
        row.addStretch(1)
        layout.addLayout(row)


class TCheckWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("nanoT-check  –  NanoVNA Accuracy Test")
        self.setMinimumSize(720, 520)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG}; }}")

        self._lang    = "en"
        self._source  = "nanovna"
        self._worker  = None

        self._build_ui()
        self._toggle_source()
        self.showMaximized()

    # ── translation ─────────────────────────────────────────────────────────

    def _tr(self, key: str, *args) -> str:
        s = STRINGS[self._lang].get(key, key)
        return s.format(*args) if args else s

    # ── layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        stripe = QFrame()
        stripe.setFixedHeight(4)
        stripe.setStyleSheet(f"background-color: {ACCENT};")
        root.addWidget(stripe)

        root.addWidget(self._build_settings_group())
        root.addLayout(self._build_run_row())
        root.addWidget(self._build_splitter(), 1)
        root.addLayout(self._build_legend())

    def _build_menu(self):
        bar = self.menuBar()
        bar.setStyleSheet(
            f"QMenuBar {{ background-color: {PANEL}; color: {FG}; }}"
            f"QMenuBar::item:selected {{ background-color: {ACCENT};"
            f" color: #ffffff; }}"
            f"QMenu {{ background-color: {PANEL}; color: {FG}; }}"
            f"QMenu::item:selected {{ background-color: {ACCENT};"
            f" color: #ffffff; }}")

        self._menu_settings = bar.addMenu(self._tr("menu_settings"))

        self._menu_src = self._menu_settings.addMenu(self._tr("menu_source"))
        src_group = QActionGroup(self)
        self._act_example = self._menu_src.addAction(self._tr("src_example"))
        self._act_nanovna = self._menu_src.addAction(self._tr("src_nanovna"))
        for act, value in ((self._act_example, "example"),
                           (self._act_nanovna, "nanovna")):
            act.setCheckable(True)
            src_group.addAction(act)
            act.triggered.connect(lambda _checked, v=value: self._set_source(v))
        self._act_nanovna.setChecked(True)

        self._menu_settings.addSeparator()

        self._menu_lang = self._menu_settings.addMenu(self._tr("menu_language"))
        lang_group = QActionGroup(self)
        for label, code in (("English", "en"), ("Deutsch", "de")):
            act = self._menu_lang.addAction(label)
            act.setCheckable(True)
            act.setChecked(code == self._lang)
            lang_group.addAction(act)
            act.triggered.connect(lambda _checked, c=code: self._set_language(c))

        self._menu_settings.addSeparator()
        self._act_csv = self._menu_settings.addAction(self._tr("menu_csv"))
        self._act_csv.setCheckable(True)

        self._menu_info = bar.addMenu(self._tr("menu_info"))
        self._act_credits = self._menu_info.addAction(self._tr("menu_credits"))
        self._act_credits.triggered.connect(self._show_credits)

    def _build_settings_group(self):
        self._nvna_group = QGroupBox(self._tr("nvna_frame"))
        self._nvna_group.setStyleSheet(
            f"QGroupBox {{ color: {FG_DIM}; border: 1px solid #cccccc;"
            f" margin-top: 8px; padding-top: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; }}")
        grid = QGridLayout(self._nvna_group)
        grid.setContentsMargins(10, 8, 10, 8)

        mono = QFont("Courier", 10)
        hint_font = QFont("Helvetica", 8)

        self._lbl_port = QLabel(self._tr("lbl_port"))
        self._lbl_port.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._port_edit = QLineEdit()
        self._port_edit.setFont(mono)
        self._port_edit.setFixedWidth(220)
        self._port_edit.setStyleSheet(
            f"background-color: {ENTRY_BG}; color: {FG}; border: none;"
            f" padding: 3px;")
        self._hint_port = QLabel(self._tr("hint_port"))
        self._hint_port.setFont(hint_font)
        self._hint_port.setStyleSheet(f"color: {FG_DIM};")
        self._detect_btn = QPushButton(self._tr("btn_detect"))
        self._detect_btn.setCursor(Qt.PointingHandCursor)
        self._detect_btn.clicked.connect(self._auto_detect)

        grid.addWidget(self._lbl_port,   0, 0)
        grid.addWidget(self._port_edit,  0, 1)
        grid.addWidget(self._hint_port,  0, 2)
        grid.addWidget(self._detect_btn, 0, 3)

        self._lbl_start = QLabel(self._tr("lbl_start"))
        self._lbl_start.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._start_val = QLabel("")
        self._start_val.setFont(mono)
        self._start_val.setStyleSheet(f"color: {FG_DIM};")
        grid.addWidget(self._lbl_start, 1, 0)
        grid.addWidget(self._start_val, 1, 1)

        self._lbl_stop = QLabel(self._tr("lbl_stop"))
        self._lbl_stop.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._stop_val = QLabel("")
        self._stop_val.setFont(mono)
        self._stop_val.setStyleSheet(f"color: {FG_DIM};")
        grid.addWidget(self._lbl_stop, 2, 0)
        grid.addWidget(self._stop_val, 2, 1)

        self._lbl_points = QLabel(self._tr("lbl_points"))
        self._lbl_points.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._pts_info = QLabel("")
        self._pts_info.setFont(mono)
        self._pts_info.setStyleSheet(f"color: {FG_DIM};")
        grid.addWidget(self._lbl_points, 3, 0)
        grid.addWidget(self._pts_info,   3, 1)

        self._average_check = QCheckBox(self._tr("lbl_average"))
        self._average_check.toggled.connect(self._toggle_average)
        self._repeats_combo = QComboBox()
        self._repeats_combo.addItems([str(v) for v in range(2, 11)])
        self._repeats_combo.setCurrentText("4")
        self._repeats_combo.setFixedWidth(60)
        grid.addWidget(self._average_check, 4, 0, 1, 2)
        grid.addWidget(self._repeats_combo, 4, 2)

        grid.setColumnStretch(4, 1)

        self._nvna_widgets = [self._port_edit, self._detect_btn,
                              self._average_check, self._repeats_combo]
        return self._nvna_group

    def _build_run_row(self):
        row = QHBoxLayout()
        row.setContentsMargins(20, 0, 20, 0)
        self._run_btn = QPushButton(self._tr("btn_run"))
        self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.setFont(QFont("Helvetica", 11, QFont.Bold))
        self._run_btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #ffffff;"
            f" border: none; padding: 6px 20px; }}"
            f"QPushButton:hover {{ background-color: {BTN_ACT}; }}"
            f"QPushButton:disabled {{ background-color: #90a4ae; }}")
        self._run_btn.clicked.connect(self._run)
        row.addWidget(self._run_btn)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {FG_DIM};")
        row.addSpacing(16)
        row.addWidget(self._status)
        row.addStretch(1)
        return row

    def _build_splitter(self):
        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.setContentsMargins(20, 0, 20, 0)

        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self._build_plot(plot_layout)
        self._splitter.addWidget(plot_widget)

        self._splitter.addWidget(self._build_table())
        self._splitter.setStretchFactor(0, 7)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setSizes([700, 300])
        return self._splitter

    def _build_table(self):
        self._col_keys = ["col_freq", "col_ct", "col_dev", "col_quality"]
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [self._tr(k) for k in self._col_keys])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setFont(QFont("Courier", 10))
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._table.setStyleSheet(
            f"QTableWidget {{ background-color: {PANEL}; color: {FG};"
            f" gridline-color: #dddddd; }}"
            f"QHeaderView::section {{ background-color: {ACCENT};"
            f" color: #ffffff; font-weight: bold; border: none;"
            f" padding: 4px; }}")
        return self._table

    def _build_legend(self):
        row = QHBoxLayout()
        row.setContentsMargins(20, 0, 20, 8)
        self._leg_labels = []
        for bg, fg, key in ((GREEN_BG,  GREEN_FG,  "leg_green"),
                            (YELLOW_BG, YELLOW_FG, "leg_yellow"),
                            (RED_BG,    RED_FG,    "leg_red")):
            lbl = QLabel(self._tr(key))
            lbl.setStyleSheet(
                f"background-color: {bg}; color: {fg}; padding: 2px 8px;")
            row.addWidget(lbl)
            self._leg_labels.append((lbl, key))
        row.addStretch(1)
        author = QLabel("DG1JAN")
        author.setStyleSheet(f"color: {FG_DIM};")
        row.addWidget(author)
        return row

    # ── plot ────────────────────────────────────────────────────────────────

    def _build_plot(self, layout):
        self._fig = Figure(figsize=(6, 3), dpi=96, facecolor=BG)
        self._ax  = self._fig.add_subplot(111, facecolor=PLOT_BG)
        self._style_axes()
        self._ax.grid(color=FG_DIM, linewidth=0.4, linestyle="--", alpha=0.4)
        self._fig.tight_layout(pad=1.6)

        self._canvas = FigureCanvasQTAgg(self._fig)
        layout.addWidget(self._canvas)

    def _style_axes(self):
        ax = self._ax
        ax.set_facecolor(PLOT_BG)
        ax.set_xlabel(self._tr("axis_freq"), color=FG, fontsize=10)
        ax.set_ylabel(self._tr("axis_ct"),   color=FG, fontsize=10)
        ax.tick_params(colors=FG, which="both", labelsize=10)
        for spine in ax.spines.values():
            spine.set_edgecolor(FG_DIM)

    def _update_plot(self, freqs_mhz: list, ct_values: list):
        ax = self._ax
        ax.cla()
        self._style_axes()

        if freqs_mhz:
            margin = max(20.0, max(abs(v - 100) for v in ct_values) + 5)
            y_lo = 100 - margin
            y_hi = 100 + margin

            ax.axhspan(y_lo,  85,  color=PLOT_RED,    alpha=0.25, zorder=0)
            ax.axhspan(85,    90,  color=PLOT_YELLOW, alpha=0.25, zorder=0)
            ax.axhspan(90,   110,  color=PLOT_GREEN,  alpha=0.20, zorder=0)
            ax.axhspan(110,  115,  color=PLOT_YELLOW, alpha=0.25, zorder=0)
            ax.axhspan(115,  y_hi, color=PLOT_RED,    alpha=0.25, zorder=0)

            for y, col in ((85,  PLOT_RED),    (90,  PLOT_YELLOW),
                           (110, PLOT_YELLOW), (115, PLOT_RED)):
                ax.axhline(y, color=col, linewidth=1.2, linestyle="-",
                           alpha=0.8, zorder=1)

            ax.axhline(100, color="#000000", linewidth=1.4,
                       linestyle="--", alpha=0.6, zorder=2, label="100 %")

            ax.plot(freqs_mhz, ct_values,
                    color="#000000", linewidth=1.8, zorder=3)

            for x, y in zip(freqs_mhz, ct_values):
                dev = abs(y - 100.0)
                mc  = (PLOT_GREEN if dev <= 10 else
                       PLOT_YELLOW if dev <= 15 else PLOT_RED)
                ax.plot(x, y, marker="o", markersize=8,
                        markerfacecolor=mc, markeredgecolor="#000000",
                        markeredgewidth=1.2, zorder=4)

            ax.grid(color=FG_DIM, linewidth=0.4, linestyle="--",
                    alpha=0.45, zorder=2)

            ax.set_ylim(80, 120)
            ax.set_xlim(freqs_mhz[0], freqs_mhz[-1])

        self._fig.tight_layout(pad=1.6)
        self._canvas.draw()

    # ── helpers ─────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, color: str = FG_DIM):
        self._status.setText(msg)
        self._status.setStyleSheet(f"color: {color};")

    def _set_language(self, code: str):
        self._lang = code
        self._apply_language()

    def _apply_language(self):
        self._nvna_group.setTitle(self._tr("nvna_frame"))
        self._lbl_port.setText(self._tr("lbl_port"))
        self._hint_port.setText(self._tr("hint_port"))
        self._lbl_start.setText(self._tr("lbl_start"))
        self._lbl_stop.setText(self._tr("lbl_stop"))
        self._lbl_points.setText(self._tr("lbl_points"))
        self._average_check.setText(self._tr("lbl_average"))
        self._detect_btn.setText(self._tr("btn_detect"))
        if self._run_btn.isEnabled():
            self._run_btn.setText(self._tr("btn_run"))
        self._table.setHorizontalHeaderLabels(
            [self._tr(k) for k in self._col_keys])
        for lbl, key in self._leg_labels:
            lbl.setText(self._tr(key))

        self._menu_settings.setTitle(self._tr("menu_settings"))
        self._menu_src.setTitle(self._tr("menu_source"))
        self._act_example.setText(self._tr("src_example"))
        self._act_nanovna.setText(self._tr("src_nanovna"))
        self._menu_lang.setTitle(self._tr("menu_language"))
        self._act_csv.setText(self._tr("menu_csv"))
        self._menu_info.setTitle(self._tr("menu_info"))
        self._act_credits.setText(self._tr("menu_credits"))

        self._style_axes()
        self._canvas.draw_idle()

    def _show_credits(self):
        CreditsDialog(self, self._tr("credits_title"),
                      self._tr("credits_text")).exec_()

    def _set_source(self, value: str):
        self._source = value
        self._toggle_source()

    def _toggle_source(self):
        enabled = self._source == "nanovna"
        self._start_val.setText("")
        self._stop_val.setText("")
        self._pts_info.setText("")
        for w in self._nvna_widgets:
            w.setEnabled(enabled)
        self._toggle_average()

    def _toggle_average(self):
        self._repeats_combo.setEnabled(
            self._source == "nanovna" and self._average_check.isChecked())

    def _auto_detect(self):
        try:
            _, list_ports = _require_serial()
        except SystemExit:
            self._set_status(self._tr("serial_unavailable"), RED_FG)
            return
        port = _find_nanovna_port(list_ports)
        if port:
            self._port_edit.setText(port)
            self._set_status(self._tr("detected", port), FG)
        else:
            all_ports = [p.device for p in list_ports.comports()]
            if all_ports:
                self._port_edit.setText(all_ports[0])
                self._set_status(self._tr("no_nvna", ", ".join(all_ports)),
                                 YELLOW_FG)
            else:
                self._set_status(self._tr("no_ports"), RED_FG)

    def _set_frequency_labels(self, start_hz: float, stop_hz: float):
        self._start_val.setText(f"{start_hz / 1e6:.6g} MHz")
        self._stop_val.setText(f"{stop_hz / 1e6:.6g} MHz")

    # ── run ─────────────────────────────────────────────────────────────────

    def _run(self):
        self._run_btn.setEnabled(False)
        self._run_btn.setText(self._tr("btn_running"))
        self._set_status(self._tr("st_acquiring"), FG_DIM)
        self._start_val.setText("")
        self._stop_val.setText("")
        self._pts_info.setText("")
        self._table.setRowCount(0)

        average = self._average_check.isChecked()
        repeats = int(self._repeats_combo.currentText()) if average else 1

        self._worker = AcquireWorker(self, self._source,
                                     self._port_edit.text().strip(),
                                     average, repeats)
        self._worker.status.connect(self._set_status)
        self._worker.freq_labels.connect(self._set_frequency_labels)
        self._worker.points.connect(
            lambda n: self._pts_info.setText(self._tr("pts_label", n)))
        self._worker.finished_ok.connect(self._show_results)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _on_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
        self._reset_btn()

    def _show_results(self, measurements):
        freqs_mhz, ct_values, csv_rows = [], [], []

        if measurements and self._source == "example":
            self._set_frequency_labels(measurements[0][0], measurements[-1][0])

        for freq_hz, s11, s21 in measurements:
            try:
                ct_pct = tcheck(s11, s21) * 100.0
                deviation = ct_pct - 100.0
                dev = abs(deviation)
                colors = ((GREEN_BG, GREEN_FG)  if dev <= 10.0 else
                          (YELLOW_BG, YELLOW_FG) if dev <= 15.0 else
                          (RED_BG, RED_FG))
                q_key = ("q_good" if dev <= 10.0 else
                         "q_border" if dev <= 15.0 else "q_issue")
                self._add_row((f"{freq_hz/1e6:.4f}", f"{ct_pct:.3f}",
                               f"{deviation:+.3f} %", self._tr(q_key)),
                              colors)
                freqs_mhz.append(freq_hz / 1e6)
                ct_values.append(ct_pct)
                csv_rows.append((freq_hz, s11, s21, ct_pct))
            except ValueError as exc:
                self._add_row((f"{freq_hz/1e6:.4f}", "---", "---",
                               str(exc)[:40]), (RED_BG, RED_FG))

        self._update_plot(freqs_mhz, ct_values)
        if self._act_csv.isChecked():
            self._print_csv(csv_rows)
        count = self._table.rowCount()
        self._pts_info.setText(self._tr("pts_label", count))
        self._set_status(self._tr("st_done", count), GREEN_FG)
        self._reset_btn()

    def _add_row(self, values, colors):
        bg, fg = colors
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor(bg))
            item.setForeground(QColor(fg))
            self._table.setItem(row, col, item)

    @staticmethod
    def _print_csv(rows):
        print(f"# measurement {datetime.now():%Y-%m-%d %H:%M:%S}")
        writer = csv.writer(sys.stdout)
        writer.writerow(["frequency_hz",
                         "s11_real", "s11_imag",
                         "s21_real", "s21_imag",
                         "ct_percent"])
        for freq_hz, s11, s21, ct_pct in rows:
            writer.writerow([f"{freq_hz:.0f}",
                             f"{s11.real:.9g}", f"{s11.imag:.9g}",
                             f"{s21.real:.9g}", f"{s21.imag:.9g}",
                             f"{ct_pct:.3f}"])
        print("-" * 40)
        sys.stdout.flush()

    def _reset_btn(self):
        self._run_btn.setEnabled(True)
        self._run_btn.setText(self._tr("btn_run"))


def main():
    app = QApplication(sys.argv)
    win = TCheckWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
