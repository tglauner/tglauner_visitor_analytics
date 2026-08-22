#!/usr/bin/env python3
"""Create and open a one-slide Beamer status PDF for agent workflows."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import urllib.request
import urllib.parse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load .env file if present (no external dependencies)
def _load_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_load_dotenv()

# Telegram notification settings
TELEGRAM_ENABLED = os.environ.get("STATUS_TELEGRAM_ENABLED", "true").lower() in ("1", "true", "yes")
STATUS_DIR = PROJECT_ROOT / "status"
STATUS_TEX = STATUS_DIR / "status_slide.tex"
STATUS_PDF = STATUS_DIR / "status_slide.pdf"
STATUS_STATE = STATUS_DIR / "status_slide_state.json"


WORKING_BULLETS = [
    "Work is in progress.",
    "This agent is not done yet.",
    "Success or issue slide will replace this.",
]

FALLBACK_ISSUE_BULLETS = [
    "Turn ended without a recorded final status.",
    "The stop hook replaced the stale working slide.",
    "Review the Codex response before relying on the result.",
]

STATUS_STYLES = {
    "working": {
        "label": "Status: Working",
        "symbol": r"\(\blacktriangleright\)",
        "accent": "6DB7FF",
        "bg": "191D24",
        "ink": "F3F7FF",
        "muted": "AEB8C6",
    },
    "success": {
        "label": "Status: Success",
        "symbol": r"\checkmark",
        "accent": "1F8A4C",
        "bg": "F7F8F3",
        "ink": "20231F",
        "muted": "687069",
    },
    "issue": {
        "label": "Status: Issue",
        "symbol": r"!",
        "accent": "B45F06",
        "bg": "F7F8F3",
        "ink": "20231F",
        "muted": "687069",
    },
}

FINAL_STATUSES = ("success", "issue")


def send_telegram_notification(project: str, status: str, bullets: list[str]) -> bool:
    """Send Telegram notification when status is finalized.

    Requires environment variables:
      - TELEGRAM_BOT_TOKEN (from @BotFather)
      - TELEGRAM_CHAT_ID (your chat ID with the bot)
      - STATUS_TELEGRAM_ENABLED (defaults to true)

    To get your chat ID:
      1. Message your bot
      2. Visit https://api.telegram.org/bot<TOKEN>/getUpdates
      3. Find "chat":{"id": YOUR_CHAT_ID}
    """
    if not TELEGRAM_ENABLED:
        print("status slide: Telegram notifications disabled")
        return False

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("status slide: Telegram skipped - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return False

    # Build message
    emoji = "✅" if status == "success" else "⚠️"
    bullet_text = "\n".join(f"• {b}" for b in bullets[:3])
    message = f"{emoji} *{project}* — {status.upper()}\n{bullet_text}"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"status slide: Telegram notification sent")
                return True
            else:
                print(f"status slide: Telegram failed - HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"status slide: Telegram failed - {e}")
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Generate and open a dark working status slide")
    start.add_argument("--project", default=PROJECT_ROOT.name)
    start.add_argument("--bullet", action="append", default=[], help="Brief working bullet; defaults are explicit")
    start.add_argument("--no-open", action="store_true", help="Compile without opening the PDF in VS Code")

    sub.add_parser("close", help="Best-effort close of the current status PDF editor")

    hook_start = sub.add_parser("hook-start", help="Hook entrypoint: start a working slide for a new prompt")
    hook_start.add_argument("--project", default=PROJECT_ROOT.name)
    hook_start.add_argument("--no-open", action="store_true", help="Compile without opening the PDF in VS Code")

    hook_finish = sub.add_parser("hook-finish", help="Hook entrypoint: preserve a final slide or replace stale working status with Issue")
    hook_finish.add_argument("--project", default=PROJECT_ROOT.name)
    hook_finish.add_argument("--no-open", action="store_true", help="Compile without opening the PDF in VS Code")

    finish = sub.add_parser("finish", help="Generate, compile, and open a final status slide")
    finish.add_argument("--status", choices=FINAL_STATUSES, required=True)
    finish.add_argument("--project", default=PROJECT_ROOT.name)
    finish.add_argument("--bullet", action="append", default=[], help="Brief completion bullet; use three")
    finish.add_argument("--no-open", action="store_true", help="Compile without opening the PDF in VS Code")
    finish.add_argument("--no-notify", action="store_true", help="Skip Telegram notification")

    args = parser.parse_args(argv)
    if args.command == "start":
        bullets = normalize_bullets(args.bullet, defaults=WORKING_BULLETS)
        write_status_tex(args.project, "working", bullets, source="manual")
        compile_status_pdf()
        if not args.no_open:
            open_status_pdf()
        return 0
    if args.command == "close":
        return close_status_editor()
    if args.command == "hook-start":
        bullets = normalize_bullets(
            [
                "Codex is handling the latest prompt.",
                "A final status slide should replace this.",
                "Project hook started this workflow automatically.",
            ],
            defaults=WORKING_BULLETS,
        )
        write_status_tex(args.project, "working", bullets, source="hook")
        compile_status_pdf()
        if not args.no_open:
            open_status_pdf()
        return 0
    if args.command == "hook-finish":
        return hook_finish_status(args.project, no_open=args.no_open)
    if args.command == "finish":
        bullets = normalize_bullets(args.bullet)
        write_status_tex(args.project, args.status, bullets, source="manual")
        compile_status_pdf()
        if not args.no_notify:
            send_telegram_notification(args.project, args.status, bullets)
        if not args.no_open:
            open_status_pdf()
        return 0
    parser.error("unknown command")
    return 2


def hook_finish_status(project: str, no_open: bool = False) -> int:
    state = read_status_state()
    if state.get("status") in FINAL_STATUSES and STATUS_PDF.exists():
        print(f"status slide: final status already recorded as {state['status']}")
        if not no_open:
            open_status_pdf()
        return 0

    write_status_tex(project, "issue", FALLBACK_ISSUE_BULLETS, source="hook-fallback")
    compile_status_pdf()
    send_telegram_notification(project, "issue", FALLBACK_ISSUE_BULLETS)
    if not no_open:
        open_status_pdf()
    print("status slide: no final status recorded; generated fallback issue status")
    return 0


def close_status_editor() -> int:
    """Best-effort close of the status PDF tab in VS Code."""
    if not STATUS_PDF.exists():
        print("status slide: no previous PDF to close")
        return 0
    code = shutil.which("code")
    if not code:
        print("status slide: VS Code CLI not found; cannot focus/close PDF")
        return 0

    subprocess.run([code, "-r", str(STATUS_PDF)], check=False)
    if platform.system() != "Darwin" or not shutil.which("osascript"):
        print("status slide: focused previous PDF; close it manually if needed")
        return 0

    script = textwrap.dedent(
        """
        tell application "Visual Studio Code" to activate
        delay 0.4
        tell application "System Events"
            keystroke "w" using command down
        end tell
        """
    )
    result = subprocess.run(["osascript", "-e", script], check=False, capture_output=True, text=True)
    if result.returncode == 0:
        print("status slide: requested VS Code to close previous PDF editor")
        return 0
    print("status slide: could not automate VS Code close; close the previous PDF manually if it remains")
    if result.stderr.strip():
        print(result.stderr.strip())
    return 0


def normalize_bullets(raw_bullets: list[str], defaults: list[str] | None = None) -> list[str]:
    bullets = [bullet.strip() for bullet in raw_bullets if bullet.strip()]
    if not bullets:
        bullets = list(defaults or ["Completed requested work.", "Ran relevant validation.", "Updated the project status slide."])
    while len(bullets) < 3:
        bullets.append("No additional issue reported.")
    return bullets[:3]


def write_status_tex(project: str, status: str, bullets: list[str], source: str = "manual") -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    style = STATUS_STYLES[status]
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bullet_text = "\n".join(rf"\item {latex_escape(bullet)}" for bullet in bullets)
    tex = rf"""
\documentclass[aspectratio=169]{{beamer}}
\usepackage{{amssymb}}
\usepackage{{xcolor}}
\setbeamertemplate{{navigation symbols}}{{}}
\setbeamertemplate{{footline}}{{}}
\definecolor{{StatusAccent}}{{HTML}}{{{style["accent"]}}}
\definecolor{{StatusInk}}{{HTML}}{{{style["ink"]}}}
\definecolor{{StatusMuted}}{{HTML}}{{{style["muted"]}}}
\definecolor{{StatusLine}}{{HTML}}{{DADFD7}}
\definecolor{{StatusPaper}}{{HTML}}{{{style["bg"]}}}
\setbeamercolor{{normal text}}{{fg=StatusInk,bg=StatusPaper}}
\setbeamercolor{{itemize item}}{{fg=StatusAccent}}
\setbeamercolor{{itemize subitem}}{{fg=StatusAccent}}
\begin{{document}}
\begin{{frame}}[plain]
\vspace{{0.30cm}}
{{\Large\bfseries {latex_escape(project)}\par}}
\vspace{{0.45cm}}
\begin{{center}}
{{\fontsize{{58}}{{64}}\selectfont\textcolor{{StatusAccent}}{{{style["symbol"]}}}\par}}
\vspace{{0.18cm}}
{{\Huge\bfseries\textcolor{{StatusAccent}}{{{latex_escape(style["label"])}}}\par}}
\end{{center}}
\vspace{{0.35cm}}
\begin{{minipage}}{{0.84\paperwidth}}
\Large
\begin{{itemize}}
{bullet_text}
\end{{itemize}}
\end{{minipage}}
\vfill
{{\small\textcolor{{StatusMuted}}{{Generated {latex_escape(generated_at)}}}\par}}
\end{{frame}}
\end{{document}}
"""
    STATUS_TEX.write_text(textwrap.dedent(tex).strip() + "\n", encoding="utf-8")
    write_status_state(project, status, bullets, source)


def write_status_state(project: str, status: str, bullets: list[str], source: str) -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "project": project,
        "status": status,
        "source": source,
        "bullets": bullets[:3],
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    STATUS_STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_status_state() -> dict[str, object]:
    if not STATUS_STATE.exists():
        return {}
    try:
        return json.loads(STATUS_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def compile_status_pdf() -> None:
    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    if latexmk:
        command = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", STATUS_TEX.name]
        result = subprocess.run(command, cwd=STATUS_DIR, text=True, capture_output=True)
    elif pdflatex:
        command = [pdflatex, "-interaction=nonstopmode", "-halt-on-error", STATUS_TEX.name]
        first = subprocess.run(command, cwd=STATUS_DIR, text=True, capture_output=True)
        result = first if first.returncode else subprocess.run(command, cwd=STATUS_DIR, text=True, capture_output=True)
    else:
        raise SystemExit("status slide: neither latexmk nor pdflatex is available")

    if result.returncode != 0 or not STATUS_PDF.exists():
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit("status slide: LaTeX build failed")
    print(f"status slide: compiled {STATUS_PDF}")


def open_status_pdf() -> None:
    code = shutil.which("code")
    if not code:
        print(f"status slide: open manually: {STATUS_PDF}")
        return
    subprocess.run([code, "-r", str(STATUS_PDF)], check=False)
    print(f"status slide: opened {STATUS_PDF}")


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


if __name__ == "__main__":
    raise SystemExit(main())
