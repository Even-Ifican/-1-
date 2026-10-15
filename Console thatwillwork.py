import tkinter as tk
import getpass
import socket
import re
import shlex
import argparse
import os
import base64
import binascii
import xml.etree.ElementTree as ET

window = tk.Tk()
username = getpass.getuser()
hostname = socket.gethostname()
PROMPT = f"{username}@{hostname}:~$ "

def parse_args():
    p = argparse.ArgumentParser(description="Эмулятор оболочки")
    p.add_argument("--vfs", help="путь к физическому расположению VFS")
    p.add_argument("--script", help="путь к стартовому скрипту")
    return p.parse_args()

window.geometry("800x800")
window.title(f"{username}@{hostname}")
console = tk.Text(window, bg="black", fg="white", insertbackground="white", relief=tk.FLAT)


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

class VNode:
    def __init__(self, name, is_dir, data=b"", parent=None):
        self.name = name
        self.is_dir = is_dir
        self.data = data
        self.parent = parent
        self.children = {}

def build_tree(element, parent):
    for child in element:
        name = child.get("name")
        if not name or "/" in name:
            raise CommandError(f"неверное имя узла: {name!r}")
        if name in parent.children:
            raise CommandError(f"повторяющееся имя: {name}")

        if child.tag == "dir":
            node = VNode(name, True, parent=parent)
            build_tree(child, node)
        elif child.tag == "file":
            text = child.text or ""
            if child.get("encoding") == "base64":
                try:
                    data = base64.b64decode("".join(text.split()), validate=True)
                except (binascii.Error, ValueError):
                    raise CommandError(f"файл {name}: неверный base64")
            else:
                data = text.encode("utf-8")
            node = VNode(name, False, data, parent)
        else:
            raise CommandError(f"неизвестный тег <{child.tag}>")
        parent.children[name] = node

def load_vfs(path):
    try:
        tree = ET.parse(path)
    except FileNotFoundError:
        raise CommandError(f"файл не найден: {path}")
    except ET.ParseError as e:
        raise CommandError(f"неверный формат XML: {e}")
    except OSError as e:
        raise CommandError(f"не удалось прочитать файл: {e}")

    xml_root = tree.getroot()
    if xml_root.tag != "vfs":
        raise CommandError("корневой элемент должен быть <vfs>")
    root = VNode("", True)
    build_tree(xml_root, root)
    return root

def cwd_path():
    parts, node = [], cwd
    while node.parent is not None:
        parts.append(node.name)
        node = node.parent
    return "/" + "/".join(reversed(parts))


def resolve(path):
    node = vfs_root if path.startswith("/") else cwd
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            node = node.parent or node
            continue
        if not node.is_dir or part not in node.children:
            raise CommandError(f"{path}: нет такого файла или каталога")
        node = node.children[part]
    return node


def get_prompt():
    return f"{username}@{hostname}:{cwd_path()}$ "

vfs_root = VNode("", True)
cwd = vfs_root


def cmd_ls(args):
    for a in args:
        if a.startswith("-"):
            raise CommandError(f"ls: неизвестная опция {a}")
    if len(args) > 1:
        raise CommandError("ls: слишком много аргументов")

    node = resolve(args[0]) if args else cwd
    if not node.is_dir:
        return node.name
    names = sorted(n + "/" if c.is_dir else n for n, c in node.children.items())
    return "  ".join(names)


def cmd_cd(args):
    global cwd
    if len(args) > 1:
        raise CommandError("cd: слишком много аргументов")
    target = resolve(args[0]) if args else vfs_root
    if not target.is_dir:
        raise CommandError(f"cd: {args[0]}: не каталог")
    cwd = target
    return ""


def cmd_exit(args):
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

def write(text):
    console.insert(tk.END, text)
    console.see(tk.END)

def print_prompt():
    console.insert(tk.END, get_prompt())
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
        pass
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

def run_script(path):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        write(f"Не удалось открыть скрипт: {e}\n")
        return
    try:
        for line in lines:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            write(get_prompt() + line + "\n")
            run_line(line)
    except tk.TclError:
        pass

def run_line(line):
    try:
        out = execute(line)
        if out:
            write(out + "\n")
        return True
    except CommandError as e:
        write(f"{e}\n")
        return False

args = parse_args()

write("[отладка] параметры запуска:\n")
write(f"  vfs    = {args.vfs}\n")
write(f"  script = {args.script}\n\n")

if args.vfs:
    try:
        vfs_root = load_vfs(args.vfs)
        cwd = vfs_root
        write("VFS загружена\n\n")
    except CommandError as e:
        write(f"Ошибка загрузки VFS: {e}\nРабота с пустой VFS\n\n")

if args.script:
    run_script(args.script)

try:
    print_prompt()
    console.focus_set()
    window.mainloop()
except tk.TclError:
    pass
