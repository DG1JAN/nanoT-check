"""
T-Check: Accuracy test for Vector Network Analyzers using a Tee-junction.

Based on Rohde & Schwarz Application Note 1EZ43_0E (Olaf Ostwald, 1998).

For a symmetric tee-junction (S11 = S22, S21 = S12), the T-Check parameter
reduces to equation (12):

    cT = |S11·S21* + S21·S11*| / (1 - |S11|² - |S21|²)

Interpretation:
    cT ≈ 100%          ideal
    deviation ≤ ±10%   green  (minor, acceptable)
    deviation  10–15%  yellow (borderline)
    deviation  > 15%   red    (calibration issue)

NanoVNA serial protocol (USB CDC, 115200 baud):
    sweep <start_hz> <stop_hz> <points>  – configure sweep
    frequencies                          – read frequency list
    data 0                               – read S11 as real/imag pairs
    data 1                               – read S21 as real/imag pairs
"""

import cmath
import math
import sys
import time


# ---------------------------------------------------------------------------
# Core T-Check math
# ---------------------------------------------------------------------------

def tcheck(s11: complex, s21: complex) -> float:
    """
    Compute the T-Check parameter cT for a single frequency point.

    Parameters
    ----------
    s11 : complex  Reflection coefficient at port 1 (linear, not dB).
    s21 : complex  Transmission coefficient from port 1 to port 2 (linear).

    Returns
    -------
    float  cT as a fraction (1.0 = 100 %).
    """
    numerator = abs(s11 * s21.conjugate() + s21 * s11.conjugate())
    denominator = 1.0 - abs(s11) ** 2 - abs(s21) ** 2

    if denominator <= 0:
        raise ValueError(
            f"Denominator ≤ 0 ({denominator:.6f}): "
            "|S11|² + |S21|² ≥ 1 — DUT violates losslessness assumption."
        )

    return numerator / denominator


def quality_label(ct_percent: float) -> str:
    deviation = abs(ct_percent - 100.0)
    if deviation <= 10.0:
        return "GREEN  (good)"
    if deviation <= 15.0:
        return "YELLOW (borderline)"
    return "RED    (calibration issue)"


def db_deg_to_complex(db: float, deg: float) -> complex:
    """Convert (magnitude in dB, phase in degrees) to a complex number."""
    mag = 10 ** (db / 20.0)
    rad = math.radians(deg)
    return cmath.rect(mag, rad)


# ---------------------------------------------------------------------------
# NanoVNA serial interface
# ---------------------------------------------------------------------------

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


def _find_nanovna_port(list_ports) -> str:
    """
    Auto-detect a NanoVNA by scanning available serial ports.
    NanoVNA typically shows up as a USB CDC device.
    Returns the port name, or None if not found.
    """
    candidates = []
    for port in list_ports.comports():
        desc = (port.description or "").lower()
        mfg  = (port.manufacturer or "").lower()
        if any(k in desc or k in mfg for k in ("nanovna", "cdc", "stm32", "hugen")):
            candidates.append(port.device)
    return candidates[0] if candidates else None


def _send_cmd(ser, cmd: str, timeout: float = 2.0) -> list[str]:
    """
    Send a command to the NanoVNA and collect response lines until the
    'ch>' prompt is received (or timeout).
    """
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


def _parse_complex_lines(lines: list[str]) -> list[complex]:
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


def _ask_frequency(prompt: str, default_hz: float) -> float:
    """Prompt the user for a frequency; accept Hz, kHz, MHz, GHz suffixes."""
    suffix_map = {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
    while True:
        raw = input(f"{prompt} [{default_hz/1e6:.3g} MHz]: ").strip()
        if raw == "":
            return default_hz
        # try to parse a number with optional suffix
        raw_lower = raw.lower()
        factor = 1.0
        for suffix, mult in suffix_map.items():
            if raw_lower.endswith(suffix):
                raw_lower = raw_lower[: -len(suffix)].strip()
                factor = mult
                break
        try:
            return float(raw_lower) * factor
        except ValueError:
            print(f"  Cannot parse '{raw}'. Use e.g. 100MHz, 1.5GHz, 500000Hz.")


def read_from_nanovna() -> list[tuple[float, complex, complex]]:
    """
    Interactive acquisition from a NanoVNA via serial.

    Asks the user for:
      - Serial port (auto-detected if possible)
      - Start frequency
      - Stop  frequency
      - Number of sweep points (default 101)

    Returns a list of (frequency_Hz, S11_complex, S21_complex).
    """
    serial, list_ports = _require_serial()

    # --- port selection -------------------------------------------------------
    auto_port = _find_nanovna_port(list_ports)
    if auto_port:
        print(f"  NanoVNA detected on {auto_port}")
        port_input = input(f"  Serial port [{auto_port}]: ").strip()
        port = port_input if port_input else auto_port
    else:
        print("  No NanoVNA auto-detected. Available ports:")
        for p in list_ports.comports():
            print(f"    {p.device}  –  {p.description}")
        port = input("  Serial port: ").strip()
        if not port:
            print("ERROR: No port specified.")
            sys.exit(1)

    # --- frequency range ------------------------------------------------------
    print()
    start_hz  = _ask_frequency("  Start frequency", 1e6)
    stop_hz   = _ask_frequency("  Stop  frequency", 900e6)
    if stop_hz <= start_hz:
        print("ERROR: Stop frequency must be greater than start frequency.")
        sys.exit(1)

    pts_raw = input("  Sweep points [101]: ").strip()
    try:
        points = int(pts_raw) if pts_raw else 101
    except ValueError:
        print(f"  Invalid number '{pts_raw}', using 101.")
        points = 101
    points = max(2, min(points, 201))   # NanoVNA supports up to 201 points

    # --- connect & sweep ------------------------------------------------------
    print(f"\n  Connecting to {port} …", end=" ", flush=True)
    try:
        ser = serial.Serial(port, baudrate=115200, timeout=1)
    except serial.SerialException as exc:
        print(f"\nERROR opening {port}: {exc}")
        sys.exit(1)
    time.sleep(0.3)
    print("connected.")

    print(f"  Configuring sweep: {start_hz/1e6:.3f} MHz – {stop_hz/1e6:.3f} MHz, "
          f"{points} points …", end=" ", flush=True)
    _send_cmd(ser, f"sweep {int(start_hz)} {int(stop_hz)} {points}")
    time.sleep(0.2)
    print("done.")

    print("  Reading frequencies …", end=" ", flush=True)
    freq_lines  = _send_cmd(ser, "frequencies", timeout=5.0)
    print("  Reading S11 …",         end=" ", flush=True)
    s11_lines   = _send_cmd(ser, "data 0",       timeout=5.0)
    print("  Reading S21 …",         end=" ", flush=True)
    s21_lines   = _send_cmd(ser, "data 1",       timeout=5.0)
    print()

    ser.close()

    # --- parse ----------------------------------------------------------------
    freqs = []
    for line in freq_lines:
        line = line.strip()
        if line and not line.startswith("ch>"):
            try:
                freqs.append(float(line))
            except ValueError:
                pass

    s11_values = _parse_complex_lines(s11_lines)
    s21_values = _parse_complex_lines(s21_lines)

    n = min(len(freqs), len(s11_values), len(s21_values))
    if n == 0:
        print("ERROR: No data received from NanoVNA. Check connection and port.")
        sys.exit(1)

    print(f"  Received {n} data points.")
    return list(zip(freqs[:n], s11_values[:n], s21_values[:n]))


# ---------------------------------------------------------------------------
# Example data  (101 points, 10 MHz – 4 GHz, simulated tee-junction + noise)
# ---------------------------------------------------------------------------
def _generate_example(n: int = 101,
                       f_start: float = 10e6,
                       f_stop:  float = 4e9) -> list:
    """
    Simulate a realistic NanoVNA sweep of a tee-junction.

    Model (symmetric tee, Z = Z0 = 50 Ω):
        S11_ideal = -1/3  (-9.54 dB, 180°)
        S21_ideal =  2/3  (-3.52 dB,   0°)

    Frequency-dependent effects added:
      • mild attenuation increase at high frequencies (skin effect)
      • small phase rotation proportional to frequency
      • tiny random noise to mimic real measurement scatter
    """
    import random
    rng = random.Random(42)          # fixed seed → reproducible

    pts = []
    for i in range(n):
        f = f_start + i * (f_stop - f_start) / (n - 1)
        t = f / f_stop               # 0 … 1

        # ideal values
        s11_db  = -9.54 - 0.40 * t          # mild roll-off
        s11_deg = 180.0 - 6.0  * t          # small phase rotation
        s21_db  = -3.52 - 0.22 * t
        s21_deg =   0.0 + 5.0  * t

        # add small measurement noise
        s11_db  += rng.gauss(0, 0.04)
        s11_deg += rng.gauss(0, 0.3)
        s21_db  += rng.gauss(0, 0.02)
        s21_deg += rng.gauss(0, 0.2)

        pts.append((f,
                    db_deg_to_complex(s11_db, s11_deg),
                    db_deg_to_complex(s21_db, s21_deg)))
    return pts


EXAMPLE_MEASUREMENTS = _generate_example(101)


# ---------------------------------------------------------------------------
# Result display
# ---------------------------------------------------------------------------

def print_results(measurements: list[tuple[float, complex, complex]]) -> None:
    print()
    print(f"{'Freq (MHz)':>12}  {'cT (%)':>8}  {'Deviation':>10}  Quality")
    print("-" * 62)
    for freq_hz, s11, s21 in measurements:
        try:
            ct = tcheck(s11, s21)
            ct_pct = ct * 100.0
            deviation = ct_pct - 100.0
            label = quality_label(ct_pct)
            print(f"{freq_hz / 1e6:>12.4f}  {ct_pct:>8.3f}  {deviation:>+10.3f}  {label}")
        except ValueError as exc:
            print(f"{freq_hz / 1e6:>12.4f}  {'---':>8}  {'---':>10}  ERROR: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=== T-Check VNA Accuracy Test ===\n")
    print("Data source:")
    print("  1  NanoVNA (serial)")
    print("  2  Built-in example data")
    choice = input("Select [1/2]: ").strip()

    if choice == "1":
        print()
        measurements = read_from_nanovna()
    else:
        print("\nUsing built-in example data.")
        measurements = EXAMPLE_MEASUREMENTS

    print_results(measurements)


if __name__ == "__main__":
    main()
