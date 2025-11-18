import tkinter as tk
from tkinter import ttk, filedialog
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

def select_path():
    file_path = filedialog.askopenfilename()
    if file_path:
        path_entry.delete(0, tk.END)
        path_entry.insert(0, file_path)

root = tk.Tk()
root.title("Phigros 谱面提取")
root.columnconfigure(0, weight=1)
root.rowconfigure(2, weight=1)

path_frame = ttk.LabelFrame(root, text="选择文件")
path_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
path_frame.columnconfigure(0, weight=1)
#
path_entry = ttk.Entry(path_frame, width=40)
path_entry.grid(row=0, column=0, sticky="ew")
#
path_button = ttk.Button(path_frame, text="选择.apk", width=8, command=select_path)
path_button.grid(row=0, column=1, sticky="w")

search_frame = ttk.LabelFrame(root, text="搜索曲目")
search_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
search_frame.columnconfigure(1, weight=1)
#
ttk.Label(search_frame, text="曲目名称/ID: ").grid(row=0, column=0, sticky="w")
id_entry = ttk.Entry(search_frame, width=40)
id_entry.grid(row=0, column=1, sticky="ew")
#
ttk.Label(search_frame, text="筛选难度: ").grid(row=1, column=0, sticky="w")
level_frame = ttk.Frame(search_frame)
level_frame.grid(row=1, column=1, sticky="w")
levels = ["EZ", "HD", "IN", "AT", "Legacy"]
level_vars = {level: tk.BooleanVar(value=False) for level in levels}
for index,level in enumerate(levels):
    ttk.Checkbutton(level_frame, text=level, variable=level_vars[level]).grid(row=0, column=index, sticky="w")
#
ttk.Label(search_frame, text="筛选定数: ").grid(row=2, column=0, sticky="w")
difficulty_frame = ttk.Frame(search_frame)
difficulty_frame.grid(row=2, column=1, sticky="w")
difficulty_min_entry = ttk.Entry(difficulty_frame, justify="center", width=4)
difficulty_min_entry.grid(row=0, column=0, sticky="w")
ttk.Label(difficulty_frame, text="~").grid(row=0, column=1, sticky="w")
difficulty_max_entry = ttk.Entry(difficulty_frame, justify="center", width=4)
difficulty_max_entry.grid(row=0, column=2, sticky="w")

candidates_frame = ttk.LabelFrame(root, text="候选曲目")
candidates_frame.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")
candidates_frame.columnconfigure(0, weight=1)
candidates_frame.rowconfigure(0, weight=1)
#
candidates_listbox = tk.Listbox(candidates_frame, height=6)
candidates_listbox.grid(row=0, column=0, sticky="nsew")
candidates_scrollbar = ttk.Scrollbar(candidates_frame, orient="vertical", command=candidates_listbox.yview)
candidates_scrollbar.grid(row=0, column=1, sticky="ns")
candidates_listbox.config(yscrollcommand=candidates_scrollbar.set)

bottom_frame = ttk.Frame(root)
bottom_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="ew")
bottom_frame.columnconfigure(1, weight=1)
#
status_label = ttk.Label(bottom_frame, text="就绪")
status_label.grid(row=0, column=0, sticky="w")
export_button = ttk.Button(bottom_frame, text="导出", width=8, command=lambda: None)
export_button.grid(row=0, column=1, sticky="e")

root.mainloop()