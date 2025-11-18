import tkinter as tk
from tkinter import ttk
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

root = tk.Tk()
root.title("Phigros 曲目筛选")

search_frame = ttk.LabelFrame(root, text="搜索曲目")
search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
ttk.Label(search_frame, text="曲目名称/ID: ").grid(row=0, column=0, sticky="w")
id_entry = ttk.Entry(search_frame)
id_entry.grid(row=0, column=1, sticky="ew")
ttk.Label(search_frame, text="筛选难度: ").grid(row=1, column=0, sticky="w")
level_frame = ttk.Frame(search_frame)
level_frame.grid(row=1, column=1, sticky="w")
levels = ["EZ", "HD", "IN", "AT", "Legacy"]
level_vars = {level: tk.BooleanVar(value=False) for level in levels}
for index,level in enumerate(levels):
    ttk.Checkbutton(level_frame, text=level, variable=level_vars[level]).grid(row=0, column=index, sticky="w")
search_frame.columnconfigure(1, weight=1)

candidates_frame = ttk.LabelFrame(root, text="候选曲目")
candidates_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
candidates_listbox = tk.Listbox(candidates_frame, height=6)
candidates_listbox.grid(row=0, column=0, sticky="nsew")
candidates_scrollbar = ttk.Scrollbar(candidates_frame, orient="vertical", command=candidates_listbox.yview)
candidates_scrollbar.grid(row=0, column=1, sticky="ns")
candidates_listbox.config(yscrollcommand=candidates_scrollbar.set)
candidates_frame.columnconfigure(0, weight=1)
candidates_frame.rowconfigure(0, weight=1)

root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)

root.mainloop()