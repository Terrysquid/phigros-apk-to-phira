import os, json, base64, struct, UnityPy, io, yaml, re
from math import floor, ceil
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass
print("Info: Modules loaded")

songs = {}
output_indexes = [] # saved as list, to get corresponding index with candidates_listbox

def i32(b,p): return struct.unpack_from("<i",b,p)[0], p+4 # int32
def u32(b,p): return struct.unpack_from("<I",b,p)[0], p+4 # unsigned int32
def f32(b,p): return struct.unpack_from("<f",b,p)[0], p+4 # float32
def utf8(b,p): length, p = u32(b,p); return b[p:p+length].decode("utf-8"), p+length
def utf16(b,p): length, p = u32(b,p); return b[p:p+length].decode("utf-16"), p+length

class Song:
    def __init__(self):
        self.key = ""
        self.name = ""
        self.music = None
        self.composer = ""
        self.previewTime = 0.0
        self.previewEndTime = 0.0
        self.illustration = None
        self.illustration_lowres = None
        self.illustration_blur = None
        self.illustrator = ""
        self.levels = []
        self.difficulty = []
        self.charts = []
        self.charter = []

def sanitize_windows(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)

def generate_yaml(song, index):
    data = {
        "name": song.name,
        "difficulty": song.difficulty[index],
        "level": song.levels[index] + f" Lv.{floor(song.difficulty[index])}",
        "charter": song.charter[index],
        "composer": song.composer,
        "illustrator": song.illustrator,
        "chart": "chart.json",
        "format": "pgr",
        "music": "music.wav",
        "illustration": "illustration.jpg",
        "previewStart": song.previewTime,
        "previewEnd": song.previewEndTime
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

def load_assets():
    with ZipFile(path_var.get()) as zf:
        with zf.open("assets/aa/catalog.json") as f:
            j = json.load(f)
        with zf.open("assets/bin/Data/level0") as f:
            env = UnityPy.load(f.read())
        with zf.open("assets/bin/Data/globalgamemanagers.assets") as src:
            with open("globalgamemanagers.assets","wb") as dst:
                dst.write(src.read()) # Important: PPtr.py in UnityPy will use this for data.m_Script.read()
    data_key = base64.b64decode(j["m_KeyDataString"])
    data_bucket = base64.b64decode(j["m_BucketDataString"])
    data_entry = base64.b64decode(j["m_EntryDataString"])
    with open("typetree.json") as f: # extracted using Il2CppDumper and TypeTreeGenerator
        typetree = json.load(f)
    print("Info: Input files found")

    game_information = None
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour": continue
        data = obj.read(check_read=False)
        if data.m_Script.read().m_Name == "GameInformation":
            game_information = obj.read_typetree(typetree["GameInformation"])
            break
    assert game_information != None
    for k,v in game_information["song"].items():
        if k == "otherSongs": continue
        for i in v:
            song = songs.setdefault(i["songsId"], Song())
            song.key = i["songsKey"]
            song.name = i["songsName"]
            song.difficulty = [round(j,1) for j in i["difficulty"]]
            song.illustrator = i["illustrator"]
            song.charter = i["charter"]
            song.composer = i["composer"]
            song.levels = i["levels"]
            song.previewTime = i["previewTime"]
            song.previewEndTime = i["previewEndTime"]
            assert len(song.difficulty) == len(song.charter) == len(song.levels)
            song.charts = [""] * len(song.levels)
    print(f"Info: Total number of songs: {len(songs)}")

    output = []
    p_bucket = 0x0 # pointer
    count, p_bucket = u32(data_bucket, p_bucket)
    for i in range(count):
        p_key, p_bucket = u32(data_bucket, p_bucket)
        typ = data_key[p_key]; p_key += 1
        assert typ in [0,1,4]
        if typ == 0: # ascii
            key, p_key = utf8(data_key, p_key)
        elif typ == 1: # mixed
            key, p_key = utf16(data_key, p_key)
        elif typ == 4: # integer
            key, p_key = u32(data_key, p_key)
        length, p_bucket = u32(data_bucket, p_bucket)
        for ii in range(length): # this length seems useless, the two entries are always referring to the same entry
            p_entry, p_bucket = u32(data_bucket, p_bucket)
            p_entry = 4 + 28 * p_entry + 8
            if ii == 0: entry = i32(data_entry, p_entry)[0]
            if ii > 0: assert entry == i32(data_entry, p_entry)[0]
        output.append((key,entry))
    for i, j in enumerate(output):
        key, entry = j
        if entry == -1: # a key
            pass
        if entry != -1: # a value
            output[i] = (key, output[entry][0])

    # remove keys with non-bundle values
    output = [i for i in output if isinstance(i[1], str) and i[1].endswith(".bundle")]
    temp = len(output)
    # remove unity GUIDs (half of them are GUIDs)
    output = [i for i in output if not (len(i[0]) == 32 and all(c in "0123456789abcdef" for c in i[0]))]
    assert len(output) * 2 == temp
    # remove non-assets
    output = [(i[0][14:],i[1]) for i in output if i[0].startswith("Assets/Tracks/") and not i[0].startswith("Assets/Tracks/#")]

    for key, value in output:
        song_id, file_name = key.split("/")
        if song_id not in songs:
            continue
        song = songs[song_id]
        path = "assets/aa/Android/" + value
        suffix = Path(file_name).suffix
        assert suffix in [".wav",".json",".jpg"]
        if suffix == ".wav":
            assert file_name == "music.wav"
            song.music = path
        elif suffix == ".json":
            assert file_name[:6] == "Chart_"
            level = file_name[6:-5] # Chart_IN.json -> IN
            if level not in song.levels:
                continue
            song.charts[song.levels.index(level)] = path
        elif suffix == ".jpg":
            assert file_name in ["Illustration.jpg","IllustrationLowRes.jpg","IllustrationBlur.jpg"]
            if file_name == "Illustration.jpg": song.illustration = path
            elif file_name == "IllustrationLowRes.jpg": song.illustration_lowres = path # will not be used
            elif file_name == "IllustrationBlur.jpg": song.illustration_blur = path # will not be used
    print("Info: Asset files located")

    return songs

def search():
    output_id = id_var.get()
    output_levels = [level for level in level_vars if level_vars[level].get()]
    output_difficulty_min = difficulty_min_var.get()
    output_difficulty_max = difficulty_max_var.get()
    try: output_difficulty_min = ceil(float(output_difficulty_min)*10)/10
    except:
        output_difficulty_min = -float("inf")
        difficulty_min_var.set("")
    try: output_difficulty_max = floor(float(output_difficulty_max)*10)/10
    except:
        output_difficulty_max = float("inf")
        difficulty_max_var.set("")

    song_count = 0
    output_indexes.clear()
    candidates_listbox.delete(0, tk.END)
    for song_id in songs:
        song = songs[song_id]
        if output_id in songs and song_id != output_id: continue # if has exact match, skip all non-exact matches
        if not (output_id.lower() in song_id.lower() or output_id.lower() in song.name.lower()): continue # if output_id is "", it will always return True
        trigger = 0
        for index in range(len(song.levels)):
            level = song.levels[index]
            if not (level in output_levels or len(output_levels) == 0): continue
            if not (output_difficulty_min <= song.difficulty[index] <= output_difficulty_max and song.difficulty[index] != 0): continue
            output_indexes.append((song_id,index))
            candidates_listbox.insert(tk.END, f"[{song.levels[index]} {song.difficulty[index]:.1f}] {song.name} ({song_id})")
            if level not in level_vars:
                level_vars[level] = tk.BooleanVar(value=False)
                ttk.Checkbutton(level_frame, text=level, variable=level_vars[level]).grid(row=0, column=len(level_vars)-1, sticky="w")
            trigger = 1
        song_count += trigger
    print(f"Info: {song_count} song(s) ({len(output_indexes)} chart(s)) found")
    set_info(f"找到 {song_count} 首曲目 ({len(output_indexes)} 张谱面)")

def clear_search():
    id_var.set("")
    for l in level_vars: level_vars[l].set(False)
    difficulty_min_var.set("")
    difficulty_max_var.set("")
    search()

def export():
    if not path_var.get():
        set_info("导出失败: 无 APK 文件")
        return
    if not output_indexes:
        set_info("导出失败: 无候选曲目")
        return
    output_indexes_ = list(output_indexes) # copy of output_indexes, will not be modified
    apk_path = path_var.get()
    path_button.config(state="disabled")
    clear_button.config(state="disabled")
    search_button.config(state="disabled")
    candidates_listbox.config(state="disabled")
    export_button.config(state="disabled")
    progress_bar.config(maximum=len(output_indexes_), value=0)
    set_info(f"正在导出: 0/{len(output_indexes_)}")
    print("Info: Starting to export")

    def worker():
        os.makedirs("output", exist_ok=True)
        for output_count,(song_id,index) in enumerate(output_indexes_, start=1):
            song = songs[song_id]
            with ZipFile(apk_path) as zf:
                with zf.open(song.music) as f:
                    objs = [obj for obj in UnityPy.load(f.read()).objects if obj.type.name not in ["AssetBundle","Sprite"]]
                    assert len(objs) == 1
                    data = objs[0].read()
                    assert len(data.samples) == 1
                    (output_music,) = data.samples.values()
                with zf.open(song.charts[index]) as f:
                    objs = [obj for obj in UnityPy.load(f.read()).objects if obj.type.name not in ["AssetBundle","Sprite"]]
                    assert len(objs) == 1
                    data = objs[0].read()
                    output_chart = bytes(data.m_Script.encode("utf-8"))
                with zf.open(song.illustration) as f:
                    objs = [obj for obj in UnityPy.load(f.read()).objects if obj.type.name not in ["AssetBundle","Sprite"]]
                    assert len(objs) == 1
                    data = objs[0].read()
                    buf = io.BytesIO()
                    data.image.save(buf, "JPEG")
                    output_illustration = buf.getvalue()
            with ZipFile(f"output/[{song.levels[index]} {song.difficulty[index]:.1f}] {sanitize_windows(song.name)} ({song_id}).zip", "w", compression=ZIP_DEFLATED) as zf:
                zf.writestr("music.wav", output_music)
                zf.writestr("chart.json", output_chart)
                zf.writestr("illustration.jpg", output_illustration)
                zf.writestr("info.yml", generate_yaml(song, index))
            root.after(0, lambda cnt=output_count: progress_bar.config(value=cnt))
            root.after(0, lambda cnt=output_count: set_info(f"正在导出: {cnt}/{len(output_indexes_)}"))
        print(f"Info: {len(output_indexes_)} zip file(s) written to output/ directory")
        root.after(0, lambda: set_info(f"已导出 {len(output_indexes_)} 张谱面至 output/ 文件夹"))
        root.after(0, lambda: path_button.config(state="normal"))
        root.after(0, lambda: clear_button.config(state="normal"))
        root.after(0, lambda: search_button.config(state="normal"))
        root.after(0, lambda: candidates_listbox.config(state="normal"))
        root.after(0, lambda: export_button.config(state="normal"))
    Thread(target=worker, daemon=True).start()

def select_path():
    path_button.config(state="disabled")
    apk_path = filedialog.askopenfilename(title="选择 APK 文件", filetypes=[("APK 文件", "*.apk")])
    if not apk_path:
        path_button.config(state="normal")
        return
    path_var.set(apk_path)
    songs.clear()
    for child in level_frame.winfo_children(): child.destroy()
    level_vars.clear()
    try:
        load_assets()
    except Exception as e:
        print(f"Error: Failed to load assets: {e}")
        set_info(f"加载资源失败")
        path_button.config(state="normal")
        return
    clear_search() # to load level_frame
    path_button.config(state="normal")

def select_candidate(event):
    selection = event.widget.curselection()
    if selection:
        song_id,index = output_indexes[selection[0]]
        id_var.set(song_id)

def double_click_candidate(event):
    selection = event.widget.curselection()
    if not selection: return
    song_id,index = output_indexes[selection[0]]
    song = songs[song_id]
    id_var.set(song_id)
    level = song.levels[index]
    for l in level_vars: level_vars[l].set(l == level)
    search()

def set_info(info):
    info_var.set(info)

root = tk.Tk()
root.title("Phigros 谱面提取")
root.columnconfigure(0, weight=1)
root.rowconfigure(2, weight=1)

path_frame = ttk.LabelFrame(root, text="选择文件")
path_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
path_frame.columnconfigure(0, weight=1)
#
path_var = tk.StringVar()
path_entry = ttk.Entry(path_frame, width=40, textvariable=path_var, state="readonly")
path_entry.grid(row=0, column=0, sticky="ew")
#
path_button = ttk.Button(path_frame, text="选择 APK", width=8, command=select_path)
path_button.grid(row=0, column=1, sticky="w")

search_frame = ttk.LabelFrame(root, text="搜索曲目")
search_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
search_frame.columnconfigure(1, weight=1)
#
ttk.Label(search_frame, text="曲目名称/ID: ").grid(row=0, column=0, sticky="w")
id_var = tk.StringVar()
id_entry = ttk.Entry(search_frame, width=40, textvariable=id_var)
id_entry.grid(row=0, column=1, columnspan=3, sticky="ew")
#
ttk.Label(search_frame, text="筛选难度: ").grid(row=1, column=0, sticky="w")
level_frame = ttk.Frame(search_frame)
level_frame.grid(row=1, column=1, columnspan=3, sticky="w")
level_vars = {}
#
ttk.Label(search_frame, text="筛选定数: ").grid(row=2, column=0, sticky="w")
difficulty_frame = ttk.Frame(search_frame)
difficulty_frame.grid(row=2, column=1, sticky="w")
difficulty_min_var = tk.StringVar()
difficulty_min_entry = ttk.Entry(difficulty_frame, justify="center", width=4, textvariable=difficulty_min_var)
difficulty_min_entry.grid(row=0, column=0, sticky="w")
ttk.Label(difficulty_frame, text="~").grid(row=0, column=1, sticky="w")
difficulty_max_var = tk.StringVar()
difficulty_max_entry = ttk.Entry(difficulty_frame, justify="center", width=4, textvariable=difficulty_max_var)
difficulty_max_entry.grid(row=0, column=2, sticky="w")
#
clear_button = ttk.Button(search_frame, text="清空", width=8, command=clear_search)
clear_button.grid(row=2, column=2, sticky="e")
search_button = ttk.Button(search_frame, text="搜索", width=8, command=search)
search_button.grid(row=2, column=3, sticky="e")

candidates_frame = ttk.LabelFrame(root, text="候选曲目")
candidates_frame.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")
candidates_frame.columnconfigure(0, weight=1)
candidates_frame.rowconfigure(0, weight=1)
#
candidates_listbox = tk.Listbox(candidates_frame, height=10)
candidates_listbox.grid(row=0, column=0, sticky="nsew")
candidates_listbox.bind("<<ListboxSelect>>", select_candidate)
candidates_listbox.bind("<Double-Button-1>", double_click_candidate)
candidates_scrollbar = ttk.Scrollbar(candidates_frame, orient="vertical", command=candidates_listbox.yview)
candidates_scrollbar.grid(row=0, column=1, sticky="ns")
candidates_listbox.config(yscrollcommand=candidates_scrollbar.set)

progress_bar = ttk.Progressbar(root)
progress_bar.grid(row=3, column=0, padx=10, pady=(0,10), sticky="ew")

bottom_frame = ttk.Frame(root)
bottom_frame.grid(row=4, column=0, padx=10, pady=(0,10), sticky="ew")
bottom_frame.columnconfigure(1, weight=1)
#
info_var = tk.StringVar()
info_label = ttk.Label(bottom_frame, textvariable=info_var)
info_label.grid(row=0, column=0, sticky="w")
export_button = ttk.Button(bottom_frame, text="导出", width=8, command=export)
export_button.grid(row=0, column=1, sticky="e")

root.mainloop()