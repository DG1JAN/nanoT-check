"""
T-Check GUI  –  Tkinter front-end for tcheck.py
"""

import csv
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import tcheck as tc

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
BTN_BG    = ACCENT
BTN_FG    = "#ffffff"
BTN_ACT   = "#0d47a1"

# ── plot band colours (darker, solid) ───────────────────────────────────────
PLOT_GREEN  = "#388e3c"   # dark green
PLOT_YELLOW = "#f9a825"   # dark amber
PLOT_RED    = "#c62828"   # dark red
PLOT_BG     = "#fafafa"   # plot area background


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



class TCheckApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("nanoT-check  –  NanoVNA Accuracy Test")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(720, 520)

        # start maximized
        self.attributes("-zoomed", True)

        self._source = tk.StringVar(value="nanovna")
        self._lang   = tk.StringVar(value="en")
        self._port   = tk.StringVar(value="")
        self._start  = tk.StringVar(value="")
        self._stop   = tk.StringVar(value="")
        self._average = tk.BooleanVar(value=False)
        self._repeats = tk.StringVar(value="4")
        self._csv_out = tk.BooleanVar(value=False)

        self._build_ui()
        # position sash after layout is realised: plot ~70 %, table ~30 %
        self.after(100, self._set_sash)
        self._toggle_source()

    def _tr(self, key: str, *args) -> str:
        """Return translated string for current language."""
        s = STRINGS[self._lang.get()].get(key, key)
        return s.format(*args) if args else s

    # ── layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── menu bar ─────────────────────────────────────────────────────────
        menubar = tk.Menu(self, bg=PANEL, fg=FG, activebackground=ACCENT,
                          activeforeground="#ffffff", relief="flat")
        self.configure(menu=menubar)

        self._menu_settings = tk.Menu(menubar, tearoff=False,
                                      bg=PANEL, fg=FG,
                                      activebackground=ACCENT,
                                      activeforeground="#ffffff")
        menubar.add_cascade(label=self._tr("menu_settings"),
                            menu=self._menu_settings)
        self._menubar     = menubar
        self._menubar_idx = 0          # index of "Settings" entry in menubar

        # Data source sub-menu
        self._menu_src = tk.Menu(self._menu_settings, tearoff=False,
                                 bg=PANEL, fg=FG,
                                 activebackground=ACCENT,
                                 activeforeground="#ffffff")
        self._menu_src.add_radiobutton(label=self._tr("src_example"),
                                       variable=self._source, value="example",
                                       command=self._toggle_source)
        self._menu_src.add_radiobutton(label=self._tr("src_nanovna"),
                                       variable=self._source, value="nanovna",
                                       command=self._toggle_source)
        self._menu_settings.add_cascade(label=self._tr("menu_source"),
                                        menu=self._menu_src)

        self._menu_settings.add_separator()

        # Language sub-menu
        self._menu_lang = tk.Menu(self._menu_settings, tearoff=False,
                                  bg=PANEL, fg=FG,
                                  activebackground=ACCENT,
                                  activeforeground="#ffffff")
        self._menu_lang.add_radiobutton(label="English",
                                        variable=self._lang, value="en",
                                        command=self._apply_language)
        self._menu_lang.add_radiobutton(label="Deutsch",
                                        variable=self._lang, value="de",
                                        command=self._apply_language)
        self._menu_settings.add_cascade(label=self._tr("menu_language"),
                                        menu=self._menu_lang)

        self._menu_settings.add_separator()
        self._menu_settings.add_checkbutton(label=self._tr("menu_csv"),
                                            variable=self._csv_out,
                                            selectcolor=ACCENT)
        self._menu_csv_idx = 4

        # Info menu
        self._menu_info = tk.Menu(menubar, tearoff=False,
                                  bg=PANEL, fg=FG,
                                  activebackground=ACCENT,
                                  activeforeground="#ffffff")
        menubar.add_cascade(label=self._tr("menu_info"), menu=self._menu_info)
        self._menubar_info_idx = 1     # index of "Info" entry in menubar
        self._menu_info.add_command(label=self._tr("menu_credits"),
                                    command=self._show_credits)

        # ── title bar (accent stripe only) ─────────────────────────────────
        hdr = tk.Frame(self, bg=ACCENT, height=4)
        hdr.pack(fill="x")

        # ── NanoVNA settings ─────────────────────────────────────────────────
        self._nvna_frame = tk.LabelFrame(self, text=self._tr("nvna_frame"),
                                         bg=BG, fg=FG_DIM,
                                         font=("Helvetica", 9), bd=1, relief="solid")
        self._nvna_frame.pack(fill="x", padx=20, pady=(0, 8))

        self._nvna_widgets = []
        grid = self._nvna_frame

        # field rows — store label/hint widgets for language updates
        field_keys = [("lbl_port", self._port, "hint_port")]
        self._field_lbls  = []   # (label_widget, lbl_key)
        self._field_hints = []   # (hint_widget,  hint_key)

        for row, (lbl_key, var, hint_key) in enumerate(field_keys):
            lbl_w = tk.Label(grid, text=self._tr(lbl_key),
                             bg=BG, fg=FG, width=16, anchor="e")
            lbl_w.grid(row=row, column=0, padx=(10, 4), pady=4, sticky="e")
            ent = tk.Entry(grid, textvariable=var, bg=ENTRY_BG, fg=FG,
                           insertbackground=FG, relief="flat", width=26,
                           font=("Courier", 10))
            ent.grid(row=row, column=1, padx=4, pady=4, sticky="w")
            hint_w = tk.Label(grid, text=self._tr(hint_key),
                              bg=BG, fg=FG_DIM, font=("Helvetica", 8))
            hint_w.grid(row=row, column=2, padx=(2, 10), pady=4, sticky="w")
            self._nvna_widgets += [lbl_w, ent, hint_w]
            self._field_lbls.append((lbl_w,   lbl_key))
            self._field_hints.append((hint_w, hint_key))

        for row, (lbl_key, var) in enumerate((
                ("lbl_start", self._start), ("lbl_stop", self._stop)),
                start=len(field_keys)):
            lbl_w = tk.Label(grid, text=self._tr(lbl_key),
                             bg=BG, fg=FG, width=16, anchor="e")
            lbl_w.grid(row=row, column=0, padx=(10, 4), pady=4, sticky="e")
            value_w = tk.Label(grid, textvariable=var, bg=BG, fg=FG_DIM,
                               font=("Courier", 10), anchor="w", width=26)
            value_w.grid(row=row, column=1, padx=4, pady=4, sticky="w")
            self._field_lbls.append((lbl_w, lbl_key))

        pts_row = len(field_keys) + 2

        # Averaging controls appear below the data-points row.
        average_row = pts_row + 1
        self._average_check = tk.Checkbutton(
            grid, text=self._tr("lbl_average"), variable=self._average,
            bg=BG, fg=FG, activebackground=BG, activeforeground=FG,
            selectcolor=ENTRY_BG, command=self._toggle_average)
        self._average_check.grid(row=average_row, column=0, columnspan=2,
                                 padx=(10, 4), pady=4, sticky="w")
        self._nvna_widgets.append(self._average_check)

        self._repeats_menu = ttk.Combobox(
            grid, textvariable=self._repeats,
            values=[str(value) for value in range(2, 11)],
            state="disabled", width=4)
        self._repeats_menu.grid(row=average_row, column=2, padx=4, pady=4,
                                sticky="w")
        self._nvna_widgets.append(self._repeats_menu)

        # data-points info label
        self._pts_lbl_w = tk.Label(grid, text=self._tr("lbl_points"),
                                   bg=BG, fg=FG, width=16, anchor="e")
        self._pts_lbl_w.grid(row=pts_row, column=0, padx=(10, 4), pady=4, sticky="e")
        self._pts_info = tk.Label(grid, text="", bg=BG, fg=FG_DIM,
                                  font=("Courier", 10), anchor="w")
        self._pts_info.grid(row=pts_row, column=1, padx=4, pady=4, sticky="w")
        self._nvna_widgets.append(self._pts_info)

        self._detect_btn = tk.Button(grid, text=self._tr("btn_detect"),
                                     command=self._auto_detect,
                                     bg=PANEL, fg=FG, activebackground=BTN_ACT,
                                     relief="flat", padx=8, cursor="hand2")
        self._detect_btn.grid(row=0, column=3, padx=8)
        self._nvna_widgets.append(self._detect_btn)

        # ── run button ───────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 8))
        self._run_btn = tk.Button(btn_row, text=self._tr("btn_run"),
                                  command=self._run,
                                  bg=BTN_BG, fg=BTN_FG,
                                  activebackground=BTN_ACT, activeforeground=BTN_FG,
                                  relief="flat", font=("Helvetica", 11, "bold"),
                                  padx=20, pady=6, cursor="hand2")
        self._run_btn.pack(side="left")
        self._status = tk.Label(btn_row, text="", bg=BG, fg=FG_DIM,
                                font=("Helvetica", 9))
        self._status.pack(side="left", padx=16)

        # ── paned container (plot top, table bottom) ──────────────────────────
        self._pane = tk.PanedWindow(self, orient="vertical", bg=BG,
                              sashwidth=6, sashrelief="flat",
                              sashpad=2)
        self._pane.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # ── plot ─────────────────────────────────────────────────────────────
        plot_frame = tk.Frame(self._pane, bg=BG)
        self._pane.add(plot_frame, minsize=260, stretch="always")
        self._build_plot(plot_frame)

        # ── results table ────────────────────────────────────────────────────
        tbl_outer = tk.Frame(self._pane, bg=BG)
        self._pane.add(tbl_outer, minsize=60, stretch="middle")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Results.Treeview",
                        background=PANEL, foreground=FG,
                        fieldbackground=PANEL, rowheight=24,
                        font=("Courier", 10))
        style.configure("Results.Treeview.Heading",
                        background=ACCENT, foreground="#ffffff",
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Results.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        cols = ("freq", "ct", "deviation", "quality")
        self._tree = ttk.Treeview(tbl_outer, columns=cols, show="headings",
                                  style="Results.Treeview")
        self._tree_col_keys = {
            "freq":      "col_freq",
            "ct":        "col_ct",
            "deviation": "col_dev",
            "quality":   "col_quality",
        }
        col_widths = {"freq": 160, "ct": 100, "deviation": 110, "quality": 200}
        for col, key in self._tree_col_keys.items():
            self._tree.heading(col, text=self._tr(key))
            self._tree.column(col, width=col_widths[col], anchor="center")

        sb = ttk.Scrollbar(tbl_outer, orient="vertical",
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._tree.tag_configure("green",  background=GREEN_BG,  foreground=GREEN_FG)
        self._tree.tag_configure("yellow", background=YELLOW_BG, foreground=YELLOW_FG)
        self._tree.tag_configure("red",    background=RED_BG,    foreground=RED_FG)

        # ── legend ───────────────────────────────────────────────────────────
        leg = tk.Frame(self, bg=BG)
        leg.pack(fill="x", padx=20, pady=(0, 8))
        leg_defs = [
            (GREEN_BG,  GREEN_FG,  "leg_green"),
            (YELLOW_BG, YELLOW_FG, "leg_yellow"),
            (RED_BG,    RED_FG,    "leg_red"),
        ]
        self._leg_labels = []
        for bg, fg, key in leg_defs:
            lbl = tk.Label(leg, text=self._tr(key), bg=bg, fg=fg,
                           font=("Helvetica", 9), padx=8, pady=2)
            lbl.pack(side="left", padx=4)
            self._leg_labels.append((lbl, key))

        tk.Label(leg, text="DG1JAN", bg=BG, fg=FG_DIM,
                 font=("Helvetica", 9)).pack(side="right", padx=4)

    # ── plot ─────────────────────────────────────────────────────────────────

    def _build_plot(self, parent: tk.Frame):
        """Create an empty matplotlib figure inside *parent*."""
        self._fig = Figure(figsize=(6, 3), dpi=96, facecolor=BG)
        self._ax  = self._fig.add_subplot(111, facecolor=PLOT_BG)
        self._ax.set_xlabel("Frequency (MHz)", color=FG, fontsize=20)
        self._ax.set_ylabel("cT  (%)",         color=FG, fontsize=20)
        self._ax.tick_params(colors=FG, which="both", labelsize=15)
        for spine in self._ax.spines.values():
            spine.set_edgecolor(FG_DIM)
        self._ax.grid(color=FG_DIM, linewidth=0.4, linestyle="--", alpha=0.4)
        self._fig.tight_layout(pad=1.6)

        self._canvas = FigureCanvasTkAgg(self._fig, master=parent)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def _update_plot(self, freqs_mhz: list, ct_values: list):
        """Redraw the cT-vs-frequency chart."""
        ax = self._ax
        ax.cla()

        ax.set_facecolor(PLOT_BG)
        ax.set_xlabel("Frequency (MHz)", color=FG, fontsize=20)
        ax.set_ylabel("cT  (%)",         color=FG, fontsize=20)
        ax.tick_params(colors=FG, which="both", labelsize=15)
        for spine in ax.spines.values():
            spine.set_edgecolor(FG_DIM)

        if freqs_mhz:
            margin = max(20.0, max(abs(v - 100) for v in ct_values) + 5)
            y_lo = 100 - margin
            y_hi = 100 + margin

            # ── coloured quality bands (darker, semi-transparent) ─────────────
            ax.axhspan(y_lo,  85,  color=PLOT_RED,    alpha=0.25, zorder=0)
            ax.axhspan(85,    90,  color=PLOT_YELLOW,  alpha=0.25, zorder=0)
            ax.axhspan(90,   110,  color=PLOT_GREEN,   alpha=0.20, zorder=0)
            ax.axhspan(110,  115,  color=PLOT_YELLOW,  alpha=0.25, zorder=0)
            ax.axhspan(115,  y_hi, color=PLOT_RED,    alpha=0.25, zorder=0)

            # band border lines
            for y, col in ((85,  PLOT_RED),    (90,  PLOT_YELLOW),
                           (110, PLOT_YELLOW), (115, PLOT_RED)):
                ax.axhline(y, color=col, linewidth=1.2, linestyle="-",
                           alpha=0.8, zorder=1)

            # 100 % reference line
            ax.axhline(100, color="#000000", linewidth=1.4,
                       linestyle="--", alpha=0.6, zorder=2, label="100 %")

            # ── cT curve — black line, coloured markers ───────────────────────
            ax.plot(freqs_mhz, ct_values,
                    color="#000000", linewidth=1.8, zorder=3)

            for x, y in zip(freqs_mhz, ct_values):
                dev = abs(y - 100.0)
                mc  = (PLOT_GREEN if dev <= 10 else
                       PLOT_YELLOW if dev <= 15 else PLOT_RED)
                ax.plot(x, y, marker="o", markersize=8,
                        markerfacecolor=mc, markeredgecolor="#000000",
                        markeredgewidth=1.2, zorder=4)

            # grid on top of bands
            ax.grid(color=FG_DIM, linewidth=0.4, linestyle="--",
                    alpha=0.45, zorder=2)

            ax.set_ylim(80, 120)
            ax.set_xlim(freqs_mhz[0], freqs_mhz[-1])

        self._fig.tight_layout(pad=1.6)
        self._canvas.draw()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_sash(self):
        """Place the sash so the plot takes ~70 % of the paned area."""
        total = self._pane.winfo_height()
        if total > 10:
            self._pane.sash_place(0, 0, int(total * 0.70))

    def _apply_language(self):
        """Update every translatable widget to the current language."""
        # window title stays in English regardless of language setting
        self._nvna_frame.configure(text=self._tr("nvna_frame"))
        for lbl_w, key in self._field_lbls:
            lbl_w.configure(text=self._tr(key))
        for hint_w, key in self._field_hints:
            hint_w.configure(text=self._tr(key))
        self._pts_lbl_w.configure(text=self._tr("lbl_points"))
        self._average_check.configure(text=self._tr("lbl_average"))
        self._detect_btn.configure(text=self._tr("btn_detect"))
        if self._run_btn["state"] == "normal":
            self._run_btn.configure(text=self._tr("btn_run"))
        for col, key in self._tree_col_keys.items():
            self._tree.heading(col, text=self._tr(key))
        for lbl, key in self._leg_labels:
            lbl.configure(text=self._tr(key))
        # update menus
        self._menubar.entryconfig(self._menubar_idx,
                                  label=self._tr("menu_settings"))
        self._menubar.entryconfig(self._menubar_info_idx,
                                  label=self._tr("menu_info"))
        self._menu_info.entryconfig(0, label=self._tr("menu_credits"))
        self._menu_settings.entryconfig(0, label=self._tr("menu_source"))
        self._menu_src.entryconfig(0, label=self._tr("src_example"))
        self._menu_src.entryconfig(1, label=self._tr("src_nanovna"))
        self._menu_settings.entryconfig(2, label=self._tr("menu_language"))
        self._menu_settings.entryconfig(self._menu_csv_idx,
                                        label=self._tr("menu_csv"))
        # update plot axis labels
        self._ax.set_xlabel(self._tr("axis_freq"), color=FG)
        self._ax.set_ylabel(self._tr("axis_ct"),   color=FG)
        self._canvas.draw_idle()

    def _show_credits(self):
        """Open a modal credits popup."""
        win = tk.Toplevel(self)
        win.title(self._tr("credits_title"))
        win.configure(bg=PANEL)
        win.resizable(False, False)
        win.grab_set()          # modal

        # centre over main window
        win.update_idletasks()
        w, h = 600, 480
        rx = self.winfo_rootx() + (self.winfo_width()  - w) // 2
        ry = self.winfo_rooty() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{rx}+{ry}")

        tk.Frame(win, bg=ACCENT, height=4).pack(fill="x")

        tk.Label(win, text="nanoT-check",
                 font=("Helvetica", 16, "bold"), bg=PANEL, fg=ACCENT).pack(pady=(14, 2))

        txt = tk.Text(win, wrap="word", font=("Helvetica", 9),
                      bg=PANEL, fg=FG, relief="flat",
                      width=72, height=22, cursor="arrow",
                      padx=16, pady=6)
        txt.insert("1.0", self._tr("credits_text"))
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=10)

        tk.Button(win, text="OK", command=win.destroy,
                  bg=ACCENT, fg="#ffffff", activebackground=BTN_ACT,
                  relief="flat", padx=24, pady=4, cursor="hand2",
                  font=("Helvetica", 10, "bold")).pack(pady=10)

    def _toggle_source(self):
        use_nvna = self._source.get() == "nanovna"
        state = "normal" if use_nvna else "disabled"
        self._start.set("")
        self._stop.set("")
        self._pts_info.configure(text="")
        for w in self._nvna_widgets:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass

        self._toggle_average()

    def _toggle_average(self):
        state = "normal" if self._source.get() == "nanovna" and self._average.get() else "disabled"
        self._repeats_menu.configure(state=state)
        if state == "normal":
            self._repeats_menu.configure(state="readonly")

    def _auto_detect(self):
        try:
            _, list_ports = tc._require_serial()
        except SystemExit:
            self._set_status(self._tr("serial_unavailable"), RED_FG)
            return
        port = tc._find_nanovna_port(list_ports)
        if port:
            self._port.set(port)
            self._set_status(self._tr("detected", port), FG)
        else:
            all_ports = [p.device for p in list_ports.comports()]
            if all_ports:
                self._port.set(all_ports[0])
                self._set_status(self._tr("no_nvna", ", ".join(all_ports)), YELLOW_FG)
            else:
                self._set_status(self._tr("no_ports"), RED_FG)

    def _set_status(self, msg: str, color=FG_DIM):
        self._status.configure(text=msg, fg=color)

    # ── run ───────────────────────────────────────────────────────────────────

    def _run(self):
        self._run_btn.configure(state="disabled", text=self._tr("btn_running"))
        self._set_status(self._tr("st_acquiring"), FG_DIM)
        self._start.set("")
        self._stop.set("")
        self._pts_info.configure(text="")
        for item in self._tree.get_children():
            self._tree.delete(item)
        source = self._source.get()
        average = self._average.get()
        repeats = max(2, min(10, int(self._repeats.get()))) if average else 1
        threading.Thread(target=self._worker, args=(source, average, repeats),
                         daemon=True).start()

    def _worker(self, source, average, repeats):
        try:
            if source == "nanovna":
                measurements = self._acquire_nanovna(average, repeats)
            else:
                measurements = tc.EXAMPLE_MEASUREMENTS

            self.after(0, self._show_results, measurements)
        except SystemExit:
            self.after(0, self._reset_btn)
        except Exception as exc:
            self.after(0, messagebox.showerror, "Error", str(exc))
            self.after(0, self._reset_btn)

    def _acquire_nanovna(self, average=False, repeats=1):
        serial, list_ports = tc._require_serial()

        port = self._port.get().strip()
        if not port:
            raise ValueError(self._tr("no_port"))

        self.after(0, self._set_status, self._tr("st_connecting", port), FG_DIM)

        import time
        try:
            ser = serial.Serial(port, baudrate=115200, timeout=1)
        except serial.SerialException as exc:
            raise RuntimeError(f"Cannot open {port}: {exc}") from exc

        time.sleep(0.3)
        freq_lines = tc._send_cmd(ser, "frequencies", timeout=5.0)
        repeat_values = []
        import time
        for repeat in range(repeats):
            if average:
                self.after(0, self._set_status,
                           self._tr("st_average", repeat + 1, repeats), FG_DIM)
            else:
                self.after(0, self._set_status, self._tr("st_s11"), FG_DIM)
            s11_lines = tc._send_cmd(ser, "data 0", timeout=5.0)
            self.after(0, self._set_status, self._tr("st_s21"), FG_DIM)
            s21_lines = tc._send_cmd(ser, "data 1", timeout=5.0)
            repeat_values.append((tc._parse_complex_lines(s11_lines),
                                 tc._parse_complex_lines(s21_lines)))
            if repeat + 1 < repeats:
                time.sleep(2.0)
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

        self.after(0, self._set_frequency_labels, freqs[0], freqs[n - 1])
        self.after(0, self._pts_info.configure,
                   {"text": self._tr("pts_label", n), "fg": FG})
        return list(zip(freqs[:n], s11_vals[:n], s21_vals[:n]))

    def _set_frequency_labels(self, start_hz: float, stop_hz: float):
        self._start.set(f"{start_hz / 1e6:.6g} MHz")
        self._stop.set(f"{stop_hz / 1e6:.6g} MHz")

    def _show_results(self, measurements):
        freqs_mhz, ct_values, csv_rows = [], [], []

        if measurements and self._source.get() == "example":
            self._set_frequency_labels(measurements[0][0], measurements[-1][0])

        for freq_hz, s11, s21 in measurements:
            try:
                ct = tc.tcheck(s11, s21)
                ct_pct = ct * 100.0
                deviation = ct_pct - 100.0
                dev_str = f"{deviation:+.3f} %"
                dev = abs(deviation)
                tag = ("green"  if dev <= 10.0 else
                       "yellow" if dev <= 15.0 else "red")
                q_key = ("q_good" if dev <= 10.0 else
                         "q_border" if dev <= 15.0 else "q_issue")
                self._tree.insert("", "end", tags=(tag,),
                                  values=(f"{freq_hz/1e6:.4f}",
                                          f"{ct_pct:.3f}",
                                          dev_str,
                                          self._tr(q_key)))
                freqs_mhz.append(freq_hz / 1e6)
                ct_values.append(ct_pct)
                csv_rows.append((freq_hz, s11, s21, ct_pct))
            except ValueError as exc:
                self._tree.insert("", "end", tags=("red",),
                                  values=(f"{freq_hz/1e6:.4f}", "---", "---",
                                          str(exc)[:40]))

        self._update_plot(freqs_mhz, ct_values)
        if self._csv_out.get():
            self._print_csv(csv_rows)
        count = len(self._tree.get_children())
        self._pts_info.configure(text=self._tr("pts_label", count), fg=FG)
        self._set_status(self._tr("st_done", count), GREEN_FG)
        self._reset_btn()

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
        self._run_btn.configure(state="normal", text=self._tr("btn_run"))


if __name__ == "__main__":
    app = TCheckApp()
    app.mainloop()
