# nanoT-check
NanoVNA Accuracy Tester using the T-Check Method

***!!! This Project is heavily Vibe Coded using GitHub Copilot with Claude Sonnet 4.6 !!!***

The nanoT-check Tool can be used to perform a accuracy test of a calibrated (SOLT) NanoVNA according the Method described by Rhode & Schwarz in their Application Note 1EZ43_0E : "T-Check Accuracy Test for Vector Network Analyzers utilizing a Tee-junction"
(see  https://www.rohde-schwarz.com/us/applications/t-check-accuracy-test-for-vector-network-analyzers-utilizing-a-tee-junction_56280-15519.html )

Tested only under Debian 13 with NanoVNA-F v2 and NanoVNA H2
![screenshot of the Application](nanoT-check.png)

## Setup
Install python modules (via pip):
- matplotlib
- pyserial 

Install Tk/Tcl runtime for tkinter (e.g. python3-tk on Debian/Ubuntu)

The tcheck.py must be in the path (or same folder) as tcheck_ui.py

## Run
Performe SOLT Calibration (for a selected frequency range) on your NanoVNA
- Connect your NanoVNA to the PC via USB
- Start tcheck_ui.py (e.g. #python3 tcheck_ui.py)
- Enter Serial Port or (better) run auto detection by clicking
- connect a T-Junction with a 50 Ohm Calibration resistor to PORT1 and PORT2 of your NanoVNA
- Run the T-Check





