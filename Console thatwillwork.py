import tkinter as tk
import getpass
import socket
import re
import shlex
import os
import argparse
from cmd import PROMPT

window = tk.Tk()
username = getpass.getuser()
hostname = socket.gethostname()
window.geometry("800x800")

window.title(f"{username}@{hostname}")
console = tk.Text(window, bg = "black", fg = "white", relief=tk.FLAT)

def parse_things(text: str)->str:
    pattern = r'\$(?:{([a-zA-Z_][a-zA-Z0-9_]*)}|([a-zA-Z_][a-zA-Z0-9_]*))'
    def replace(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, "")
    return re.sub(pattern, replace, text)
os.environ["PROJECT_DIR"] = "/var/www/app"

console.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

class CommandError(Exception):
    def cmd_lb(args: list[str]):
        return f"ls, аргументы: {args}"
    def cmd_cd(args: list[str]):
        return f"cd: {args}"
    def cmd_destroy(args: list[str]):
        return window.destroy()
        return ""

    COMMANDS = {
        "ls": cmd_lb,
        "cd": cmd_cd,
        "exit": cmd_destroy
    }

def execute(line: str)-> str:
    line = parse_things(line)
    try:
        token = shlex.split(line)
    except ValueError as e:
        raise CommandError(f'ошибка{e}')
    if not token:
        return ""

    name, args = token[0], token[1:]
    handler = COMMANDS.get(name)
    if handler is None:
        raise CommandError(f"{name}: команда не найдена")
    return handler(args)


def print_prompt(event):
    console.insert(tk.END, PROMPT)
    console.mark_set("input_start","end-1c")
    console.gravity("input_start", tk.LEFT)
    console.see(tk.END)

def on_key(event):
    if console.compare("insert", "<", "input_start"):
        console.mark_set("insert", tk.END)


def on_backspace(event):
    if console.compare("insert", "<=", "input_start"):
        return "break"


console.bind("<Return>", on_enter)
console.bind("<Key>", on_key)
console.bind("<BackSpace>", on_backspace)

print_prompt()
console.focus_set()
window.mainloop()
