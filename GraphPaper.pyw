"""Double-click Windows launcher and first-run graphical setup. No terminal needed."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GraphPaper"
RUNTIME = HOME / "runtime" / f"py{sys.version_info.major}{sys.version_info.minor}"
PYTHON = RUNTIME / ("Scripts/pythonw.exe" if os.name == "nt" else "bin/python")
CONSOLE_PYTHON = RUNTIME / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
STAMP = RUNTIME / "graphpaper-requirements.sha256"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
requirements = ROOT / "requirements-desktop.txt"
fingerprint = hashlib.sha256(requirements.read_bytes() + (ROOT / "requirements.txt").read_bytes() + ((ROOT / "requirements-graphify.txt").read_bytes() if (ROOT / "requirements-graphify.txt").exists() else b"")).hexdigest()


def launch():
    subprocess.Popen([str(PYTHON), "-m", "graphpaper.desktop"], cwd=str(ROOT), creationflags=NO_WINDOW)


def main():
    if PYTHON.exists() and STAMP.exists() and STAMP.read_text() == fingerprint:
        launch()
        return
    root = tk.Tk()
    root.title("Welcome to GraphPaper")
    root.geometry("550x405")
    root.resizable(False, False)
    root.configure(bg="#101714")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("GP.Horizontal.TProgressbar", troughcolor="#223227", background="#c7e1b9", bordercolor="#223227", lightcolor="#c7e1b9", darkcolor="#c7e1b9")
    frame = tk.Frame(root, bg="#101714", padx=32, pady=27);frame.pack(fill="both", expand=True)
    tk.Label(frame, text="GraphPaper", bg="#101714", fg="#c7e1b9", font=("Segoe UI", 27)).pack(anchor="w")
    tk.Label(frame, text="A studio for connected thought.", bg="#101714", fg="#dce7d7", font=("Segoe UI", 12)).pack(anchor="w", pady=(3,20))
    tk.Label(frame, text="A one-time setup will install the desktop components into\nyour private GraphPaper folder. It needs an internet connection.\n\nYour existing Python installation will not be changed.\nNo manuscripts or API keys are sent during setup.", justify="left", bg="#101714", fg="#a6b6a8", font=("Segoe UI", 10), wraplength=475).pack(anchor="w")
    status = tk.StringVar(value="Ready when you are.")
    tk.Label(frame, textvariable=status, bg="#101714", fg="#c7e1b9", font=("Segoe UI", 10),wraplength=470,justify="left").pack(anchor="w",pady=(20,10))
    bar = ttk.Progressbar(frame, mode="indeterminate", style="GP.Horizontal.TProgressbar");bar.pack(fill="x")
    actions = tk.Frame(frame,bg="#101714");actions.pack(fill="x",pady=(20,0))
    events = queue.Queue()
    running = False

    def work():
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            with (HOME / "setup.log").open("w",encoding="utf-8") as log:
                events.put(("status","Preparing an isolated Python environment…"))
                subprocess.run([sys.executable,"-m","venv",str(RUNTIME)],check=True,stdout=log,stderr=subprocess.STDOUT,creationflags=NO_WINDOW,timeout=240)
                events.put(("status","Installing desktop components. This can take a few minutes…"))
                subprocess.run([str(CONSOLE_PYTHON),"-m","pip","install","--disable-pip-version-check","-r",str(requirements)],cwd=str(ROOT),check=True,stdout=log,stderr=subprocess.STDOUT,creationflags=NO_WINDOW,timeout=1200)
            STAMP.write_text(fingerprint)
            events.put(("done",""))
        except Exception:
            events.put(("error",f"Setup did not finish. Check your internet connection.\nDetails: {HOME / 'setup.log'}"))

    def start():
        nonlocal running
        if sys.version_info < (3,11):
            messagebox.showerror("Python update needed", "GraphPaper needs Python 3.11 or newer. Install Python, then reopen this launcher.");return
        running=True;button.configure(state="disabled");bar.start(12)
        threading.Thread(target=work,daemon=True).start()

    def check_events():
        nonlocal running
        try:
            while True:
                kind,text=events.get_nowait()
                if kind=="status":status.set(text)
                elif kind=="done":
                    running=False;bar.stop();launch();root.destroy();return
                elif kind=="error":
                    running=False;bar.stop();status.set("Setup needs attention.");button.configure(state="normal",text="Try again");messagebox.showerror("GraphPaper setup",text)
        except queue.Empty:pass
        root.after(120,check_events)

    def close():
        if running:
            messagebox.showinfo("Setup in progress", "Please let setup finish. Closing now could leave an incomplete environment.")
        else:root.destroy()

    button=tk.Button(actions,text="Install and open",command=start,bg="#c7e1b9",fg="#213722",activebackground="#d8ebce",font=("Segoe UI",11,"bold"),relief="flat",padx=17,pady=8);button.pack(side="right")
    tk.Button(actions,text="Not now",command=close,bg="#1d2a22",fg="#a6b6a8",relief="flat",padx=14,pady=9).pack(side="left")
    root.protocol("WM_DELETE_WINDOW",close);root.after(120,check_events);root.mainloop()


if __name__ == "__main__":
    main()
