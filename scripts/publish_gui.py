"""Optional graphical publisher; uses the user's installed Git credential manager.

Never imports the studio database, asks for a token, force-pushes, or writes main.
This helper is not run by setup or by GraphPaper itself.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timezone
from uuid import uuid4
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/AronAxe/GraphPaper.git"
BROWSER_REPOSITORY = "https://github.com/AronAxe/GraphPaper"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def package_files(root: Path) -> list[Path]:
    """Verify a code-only allowlist before Git is touched."""
    data = json.loads((root / "publish-manifest.json").read_text(encoding="utf-8"))
    if data.get("repository") != "AronAxe/GraphPaper" or not isinstance(data.get("files"), dict):
        raise ValueError("Invalid GraphPaper publishing manifest.")
    files = []
    for name, expected in data["files"].items():
        pure = PurePosixPath(name)
        if pure.is_absolute() or any(x in {"..", ".git", ".venv", "__pycache__"} for x in pure.parts) or "\\" in name or ":" in name:
            raise ValueError("Unsafe path in publishing manifest.")
        path = root.joinpath(*pure.parts)
        if not path.is_file() or path.is_symlink() or root.resolve() not in path.resolve().parents:
            raise ValueError(f"Missing or unsafe package file: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Package file changed: {name}. This publisher only sends the original verified source package.")
        files.append(path)
    if not files:
        raise ValueError("The source manifest is empty.")
    return files


def locate_git() -> str:
    paths = [shutil.which("git"), os.environ.get("ProgramFiles", "C:\\Program Files") + "\\Git\\cmd\\git.exe",
             os.environ.get("LOCALAPPDATA", "") + "\\Programs\\Git\\cmd\\git.exe"]
    found = next((p for p in paths if p and Path(p).is_file()), None)
    if not found:
        raise ValueError("Install Git for Windows with Git Credential Manager, then reopen this publisher. A browser sign-in may appear when you publish.")
    return found


def publish(root: Path, notify, git: str | None = None) -> str:
    files = package_files(root)
    git = git or locate_git()
    workspace = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GraphPaper" / "publish"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
    target = workspace / stamp
    target.parent.mkdir(parents=True, exist_ok=True)
    branch = "graphpaper/studio-v0.1.0-" + stamp
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"  # Credentials belong in the installed GUI manager, not a hidden terminal.

    def run(*args, cwd=None):
        result = subprocess.run([git, *args], cwd=cwd, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=240, creationflags=NO_WINDOW)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[-2500:]
            raise RuntimeError("Git could not complete this step. Check your GitHub sign-in and repository permissions.\n\n" + detail)
        return result.stdout

    notify("Checking the source package and cloning your repository…")
    run("clone", "--depth", "1", REPOSITORY, str(target))
    run("checkout", "-b", branch, cwd=target)
    notify(f"Copying {len(files)} verified source files. No project data or keys are included…")
    for path in files:
        destination = target / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    shutil.copyfile(root / "publish-manifest.json", target / "publish-manifest.json")
    # Fresh clone contains no local user data. No unknown repository file is deleted.
    run("add", "--all", cwd=target)
    if not run("diff", "--cached", "--name-only", cwd=target).strip():
        return BROWSER_REPOSITORY
    run("-c", "user.name=Aron Bijl", "-c", "user.email=33731256+AronAxe@users.noreply.github.com",
        "commit", "-m", "Build GraphPaper: graph-guided fiction and nonfiction writing studio", cwd=target)
    notify("Publishing a new branch. Git Credential Manager may open a browser sign-in…")
    run("push", "--set-upstream", "origin", branch, cwd=target)
    return BROWSER_REPOSITORY + "/compare/main..." + branch + "?expand=1"


def main():
    root = tk.Tk();root.title("Publish GraphPaper to GitHub");root.geometry("650x455");root.configure(bg="#101714")
    frame = tk.Frame(root, bg="#101714", padx=30, pady=25);frame.pack(fill="both",expand=True)
    tk.Label(frame,text="GraphPaper → GitHub",font=("Segoe UI",23),bg="#101714",fg="#c7e1b9").pack(anchor="w")
    tk.Label(frame,text="AronAxe / GraphPaper",font=("Segoe UI",12),bg="#101714",fg="#c7e1b9").pack(anchor="w",pady=(8,18))
    tk.Label(frame,text="This optional helper publishes the included source code to a new branch.\nIt does not overwrite main or publish your manuscripts or API keys.\n\nIt uses Git for Windows and your GitHub sign-in. When finished,\nit opens a pull-request page so you can review and merge the build.\nNothing is uploaded until you press Publish source.",justify="left",font=("Segoe UI",10),bg="#101714",fg="#b9c7b8",wraplength=585).pack(anchor="w")
    status=tk.StringVar(value="Ready. Your main branch will remain untouched.")
    tk.Label(frame,textvariable=status,wraplength=580,justify="left",font=("Segoe UI",10),bg="#101714",fg="#e5e9df").pack(anchor="w",pady=(24,12))
    progress=ttk.Progressbar(frame,mode="indeterminate");progress.pack(fill="x")
    events=queue.Queue();running=False
    def worker():
        try:events.put(("done",publish(ROOT,lambda m:events.put(("status",m)))))
        except Exception as e:events.put(("error",str(e)))
    def start():
        nonlocal running
        if not messagebox.askyesno("Publish source to GitHub?","Publish the verified GraphPaper source package to a new branch of AronAxe/GraphPaper?"):
            return
        running=True;button.configure(state="disabled");progress.start(12)
        threading.Thread(target=worker,daemon=True).start()
    def poll():
        nonlocal running
        try:
            while True:
                kind,text=events.get_nowait()
                if kind=="status":status.set(text)
                else:
                    running=False;progress.stop();button.configure(state="normal")
                    if kind=="done":
                        status.set("Source published. Review and merge the pull request in your browser.")
                        webbrowser.open(text)
                        messagebox.showinfo("Published to a new branch","The source has been pushed. Review and merge it on GitHub.\n\nAfter merging, Actions → Windows desktop package → Run workflow builds the Windows executable.")
                    else:status.set("Publishing did not complete. No force-push was attempted.");messagebox.showerror("Publishing needs attention",text)
        except queue.Empty:pass
        root.after(150,poll)
    def close():
        if running:messagebox.showinfo("Publishing in progress","Please let the current Git operation finish.")
        else:root.destroy()
    button=tk.Button(frame,text="Publish source",command=start,bg="#c7e1b9",fg="#1f3225",relief="flat",font=("Segoe UI",11,"bold"),padx=18,pady=10);button.pack(anchor="e",pady=(20,0))
    root.protocol("WM_DELETE_WINDOW",close);root.after(150,poll);root.mainloop()

if __name__=="__main__":main()
