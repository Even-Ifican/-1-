import tkinter as tk
import getpass
import socket
import re
import shlex
import os

window = tk.Tk()
username = getpass.getuser()
hostname = socket.gethostname()
PROMPT = f"{username}@{hostname}:~$ "

window.geometry("800x800")
window.title(f"{username}@{hostname}")
console = tk.Text(window, bg="black", fg="white",
                  insertbackground="white", relief=tk.FLAT)


def parse_things(text: str) -> str:
    pattern = r'\$(?:{([a-zA-Z_][a-zA-Z0-9_]*)}|([a-zA-Z_][a-zA-Z0-9_]*))'

    def replace(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replace, text)


os.environ["PROJECT_DIR"] = "/var/www/app"

console.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)


class CommandError(Exception):
    pass


def cmd_ls(args: list[str]):
    return f"ls, аргументы: {args}"


def cmd_cd(args: list[str]):
    return f"cd: {args}"


def cmd_exit(args: list[str]):
    window.destroy()
    return ""


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "exit": cmd_exit,
}


def execute(line: str) -> str:
    line = parse_things(line)
    try:
        token = shlex.split(line)
    except ValueError as e:
        raise CommandError(f"ошибка: {e}")
    if not token:
        return ""

    name, args = token[0], token[1:]
    handler = COMMANDS.get(name)
    if handler is None:
        raise CommandError(f"{name}: команда не найдена")
    return handler(args)


def print_prompt():
    console.insert(tk.END, PROMPT)
    console.mark_set("input_start", "end-1c")
    console.mark_gravity("input_start", tk.LEFT)
    console.see(tk.END)


def on_enter(event):
    line = console.get("input_start", "end-1c")
    try:
        console.insert(tk.END, "\n")
        try:
            result = execute(line)
            if result:
                console.insert(tk.END, result + "\n")
        except CommandError as e:
            console.insert(tk.END, f"{e}\n")
        print_prompt()
    except tk.TclError:
        pass  # окно уже закрыто командой exit
    return "break"


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
