import tkinter as tk
import getpass
import socket
import os

window = tk.Tk()
username = getpass.getuser()
hostname = socket.gethostname()
window.geometry("800x800")

window.title(f"{username}@{hostname}")
console = tk.Text(window, bg = "black", fg = "white", relief=tk.FLAT)

console.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

window.mainloop()