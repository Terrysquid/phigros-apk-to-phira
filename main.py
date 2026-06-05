import os, json, base64, struct, UnityPy, io, yaml, re, hashlib
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
song_ids = [] # recorded song IDs, used to check for new songs
if os.path.exists("song_ids.json"):
    with open("song_ids.json", "r", encoding="utf-8") as f:
        song_ids = json.load(f)
asset_hashes = {}
if os.path.exists("asset_hashes.json"):
    with open("asset_hashes.json", "r", encoding="utf-8") as f:
        asset_hashes = json.load(f)
output_indexes = [] # saved as list, to get corresponding index with candidates_listbox

def i32(b,p): return struct.unpack_from("<i",b,p)[0], p+4 # int32
def u32(b,p): return struct.unpack_from("<I",b,p)[0], p+4 # unsigned int32
def f32(b,p): return struct.unpack_from("<f",b,p)[0], p+4 # float32
def utf8(b,p): length, p = u32(b,p); return b[p:p+length].decode("utf-8"), p+length
def utf16(b,p): length, p = u32(b,p); return b[p:p+length].decode("utf-16"), p+length

def sanitize_windows(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)
def plural(n): return "s" if n != 1 else ""
def level_group(level):
    return level if level in ["EZ", "HD", "IN", "AT"] else "Other"

class GameZip:
    def __init__(self, path):
        self.zips = []
        self.files = {}
        outer = ZipFile(path)
        self.add_zip(outer)
        if Path(path).suffix.lower() == ".xapk":
            for name in outer.namelist():
                if Path(name).suffix.lower() in [".apk", ".obb"]:
                    data = outer.read(name)
                    self.add_zip(ZipFile(io.BytesIO(data)))
    def add_zip(self, zf):
        self.zips.append(zf)
        for name in zf.namelist():
            self.files[name] = zf
    def open(self, path):
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path].open(path)
    def close(self):
        for zf in self.zips:
            zf.close()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class Song:
    def __init__(self):
        self.key = "" # will not be used
        self.name = ""
        self.default_music = ""
        self.music = []
        self.composer = ""
        self.preview_time = 0.0
        self.preview_end_time = 0.0
        self.illustration = ""
        self.illustration_lowres = ""
        self.illustration_blur = ""
        self.illustrator = ""
        self.levels = []
        self.difficulty = []
        self.charts = []
        self.charter = []

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
    def show(self, event=None):
        if self.window:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.window, text=self.text, relief="solid")
        label.grid()
    def hide(self, event=None):
        if self.window:
            self.window.destroy()
            self.window = None

def generate_yaml(song, index):
    data = {
        "name": song.name,
        "difficulty": song.difficulty[index],
        "level": song.levels[index] + "  " + ("Lv.?" if song.difficulty[index] == 0 else f"Lv.{floor(song.difficulty[index])}"),
        "charter": song.charter[index],
        "composer": song.composer,
        "illustrator": song.illustrator,
        "chart": "chart.json",
        "format": "pgr",
        "music": "music.wav",
        "illustration": "illustration.jpg",
        "illustrationLowRes": "illustrationLowRes.jpg",
        "illustrationBlur": "illustrationBlur.jpg",
        "previewStart": song.preview_time,
        "previewEnd": song.preview_end_time
    }
    data = {k: v for k, v in data.items() if v != ""}
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

def get_song(song_id):
    if song_id in songs:
        return songs[song_id]
    m = re.match(r"^(.*)\.(\d+)$", song_id)
    if m and m.group(1) + ".0" in songs:
        return clone_song(songs[m.group(1) + ".0"], song_id)
    return clone_song(None, song_id)

def clone_song(src, song_id):
    song = Song()
    song.name = song_id.split(".")[0]
    if src:
        song.name = src.name
        song.illustration = src.illustration
        song.illustration_lowres = src.illustration_lowres
        song.illustration_blur = src.illustration_blur
        song.illustrator = src.illustrator
    songs[song_id] = song
    return song

def add_level(song, level):
    if level not in song.levels:
        song.levels.append(level)
        song.difficulty.append(0.0)
        song.charter.append("")
        song.music.append(song.default_music)
        song.charts.append("")

def get_data(zf, path, description):
    assert path != "", f"Missing {description}"
    with zf.open(path) as f:
        objs = [obj for obj in UnityPy.load(f.read()).objects if obj.type.name not in ["AssetBundle","Sprite"]]
        assert len(objs) == 1, f"Expected 1 object in {path}, got {len(objs)}"
        data = objs[0].read()
    return data

def get_content(data, suffix):
    assert suffix in [".wav",".json",".jpg"], f"Unknown suffix {suffix}"
    if suffix == ".wav":
        assert len(data.samples) == 1, f"Expected 1 sample, got {len(data.samples)}"
        return next(iter(data.samples.values()))
    if suffix == ".json":
        return data.m_Script.encode()
    if suffix == ".jpg":
        buf = io.BytesIO()
        data.image.save(buf, "JPEG")
        return buf.getvalue()

def load_assets(apk_path, check_changes=False):
    with GameZip(apk_path) as zf:
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
        with open("typetree.json") as f: # extracted using Il2CppDumper and TypeTreeGenerator, from libil2cpp.so and global-metadata.dat
            typetree = json.load(f)
        print("Info: Input files found")

        game_information = None
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour": continue
            data = obj.read(check_read=False)
            if data.m_Script.read().m_Name == "GameInformation":
                game_information = obj.read_typetree(typetree["GameInformation"])
                break
        assert game_information != None, "GameInformation not found"
        for k,v in game_information["song"].items():
            for i in v:
                song_id = i["songsId"]
                if check_changes and song_id not in song_ids:
                    print(f"Info: New song ID found (GameInformation): {song_id}")
                    song_ids.append(song_id)
                song = songs.setdefault(song_id, Song())
                song.key = i["songsKey"]
                song.name = i["songsName"]
                song.difficulty = [round(j,1) for j in i["difficulty"]]
                song.illustrator = i["illustrator"]
                song.charter = i["charter"]
                song.composer = i["composer"]
                song.levels = i["levels"]
                song.preview_time = i["previewTime"]
                song.preview_end_time = i["previewEndTime"]
                assert len(song.difficulty) == len(song.charter) == len(song.levels), f"List length inconsistency with {len(song.difficulty)} {len(song.charter)} {len(song.levels)}"
                song.music = [""] * len(song.levels)
                song.charts = [""] * len(song.levels)
        print(f"Info: {len(songs)} songs found in GameInformation")

        output = []
        p_bucket = 0x0 # pointer
        count, p_bucket = u32(data_bucket, p_bucket)
        for i in range(count):
            p_key, p_bucket = u32(data_bucket, p_bucket)
            typ = data_key[p_key]; p_key += 1
            assert typ in [0,1,4], f"Unknown typ = {typ}"
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
                if ii > 0: assert entry == i32(data_entry, p_entry)[0], "Different entries referred error"
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
        assert len(output) * 2 == temp, f"GUID removal error/inconsistency with {temp} -> {len(output)}"
        # remove non-assets
        output = [(i[0][14:],i[1]) for i in output if i[0].startswith("Assets/Tracks/") and not i[0].startswith("Assets/Tracks/#")]
        # sort output, prioritize 1. in songs 2. alphabetic, prevent special songs being treated earlier than normal songs
        output.sort(key=lambda x: (x[0].split("/")[0] not in songs, x[0]))
        print(f"Info: {len(output)} assets found")

        root.after(0, lambda: progress_bar.config(maximum=len(output), value=0))
        root.after(0, lambda: set_info(f"{'正在检查并加载' if check_changes else '正在加载'}: 0/{len(output)}"))
        for count, (key, value) in enumerate(output, start=1):
            song_id, file_name = key.split("/")
            if check_changes and song_id not in song_ids:
                print(f"Info: New song ID found (asset file): {song_id}")
                song_ids.append(song_id)
            song = get_song(song_id)
            path = "assets/aa/Android/" + value
            suffix = Path(file_name).suffix.lower()
            assert suffix in [".wav",".json",".jpg"], f"Unknown suffix {suffix}"

            if check_changes:
                data = get_data(zf, path, key)
                old_hash = asset_hashes.get(key)
                new_hash = hashlib.sha256(get_content(data, suffix)).hexdigest()
                if old_hash == None:
                    print(f"Info: New asset found: {key}")
                elif old_hash != new_hash:
                    print(f"Info: Asset changed: {key}")
                asset_hashes[key] = new_hash
            if suffix == ".wav":
                if file_name == "music.wav":
                    song.default_music = path
                else:
                    assert file_name[:6] == "music_", f"Unknown music file {file_name}"
                    level = file_name[6:-4] # music_IN.wav -> IN (for Cristalisia)
                    add_level(song, level)
                    song.music[song.levels.index(level)] = path
            elif suffix == ".json":
                assert file_name[:6] == "Chart_", f"Unknown chart file {file_name}"
                level = file_name[6:-5] # Chart_IN.json -> IN
                add_level(song, level)
                song.charts[song.levels.index(level)] = path
            elif suffix == ".jpg":
                assert file_name in ["Illustration.jpg","IllustrationLowRes.jpg","IllustrationBlur.jpg"], f"Unknown illustration file {file_name}"
                if file_name == "Illustration.jpg": song.illustration = path
                elif file_name == "IllustrationLowRes.jpg": song.illustration_lowres = path
                elif file_name == "IllustrationBlur.jpg": song.illustration_blur = path
            root.after(0, lambda cnt=count: progress_bar.config(value=cnt))
            root.after(0, lambda cnt=count: set_info(f"{'正在检查并加载' if check_changes else '正在加载'}: {cnt}/{len(output)}"))
    if check_changes:
        with open("song_ids.json", "w", encoding="utf-8") as f:
            json.dump(song_ids, f, ensure_ascii=False, indent=2)
        with open("asset_hashes.json", "w", encoding="utf-8") as f:
            json.dump(asset_hashes, f, ensure_ascii=False, indent=2)

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
            if not (level_group(level) in output_levels or len(output_levels) == 0): continue
            if not (output_difficulty_min <= song.difficulty[index] <= output_difficulty_max): continue
            if song.charts[index] == "": continue # use "no chart" as filter condition instead of "difficulty = 0"
            output_indexes.append((song_id,index))
            candidates_listbox.insert(tk.END, f"[{song.levels[index]} {song.difficulty[index]:.1f}] {song.name} ({song_id})")
            trigger = 1
        song_count += trigger
    print(f"Info: {song_count} song{plural(song_count)} ({len(output_indexes)} chart{plural(len(output_indexes))}) found")
    set_info(f"找到 {song_count} 首曲目 ({len(output_indexes)} 张谱面)")

def clear_search():
    id_var.set("")
    for l in level_vars: level_vars[l].set(False)
    special_var.set(False)
    difficulty_min_entry.config(state="normal")
    difficulty_max_entry.config(state="normal")
    difficulty_min_var.set("")
    difficulty_max_var.set("")
    search()

def export():
    apk_path = path_var.get()
    if not apk_path:
        print(f"Error exporting: empty path")
        set_info("导出失败: 路径为空")
        return
    if not os.path.exists(apk_path):
        print(f"Error exporting: APK/XAPK file not found: {apk_path}")
        set_info("导出失败: APK/XAPK 文件不存在")
        return
    if not output_indexes:
        print(f"Error exporting: no candidates selected")
        set_info("导出失败: 无候选曲目")
        return
    output_indexes_ = list(output_indexes) # copy of output_indexes, will not be modified
    set_buttons_state("disabled")

    def worker():
        print("Info: Starting to export")
        root.after(0, lambda: set_info("正在导出"))
        try:
            os.makedirs("output", exist_ok=True)
            root.after(0, lambda: progress_bar.config(maximum=len(output_indexes_), value=0))
            root.after(0, lambda: set_info(f"正在导出: 0/{len(output_indexes_)}"))
            with GameZip(apk_path) as zf:
                for count, (song_id, index) in enumerate(output_indexes_, start=1):
                    song = songs[song_id]
                    data = get_data(zf, song.music[index] or song.default_music, f"music for song {song.name} {song.levels[index]}")
                    output_music = get_content(data, ".wav")
                    data = get_data(zf, song.charts[index], f"chart for song {song.name} {song.levels[index]}")
                    output_chart = get_content(data, ".json")
                    data = get_data(zf, song.illustration, f"illustration for song {song.name}")
                    output_illustration = get_content(data, ".jpg")
                    data = get_data(zf, song.illustration_lowres, f"illustrationLowRes for song {song.name}")
                    output_illustration_lowres = get_content(data, ".jpg")
                    data = get_data(zf, song.illustration_blur, f"illustrationBlur for song {song.name}")
                    output_illustration_blur = get_content(data, ".jpg")
                    with ZipFile(f"output/[{song.levels[index]} {song.difficulty[index]:.1f}] {sanitize_windows(song.name)} ({song_id}).zip", "w", compression=ZIP_DEFLATED) as output_zf:
                        output_zf.writestr("music.wav", output_music)
                        output_zf.writestr("chart.json", output_chart)
                        output_zf.writestr("illustration.jpg", output_illustration)
                        output_zf.writestr("illustrationLowRes.jpg", output_illustration_lowres)
                        output_zf.writestr("illustrationBlur.jpg", output_illustration_blur)
                        output_zf.writestr("info.yml", generate_yaml(song, index))
                    root.after(0, lambda cnt=count: progress_bar.config(value=cnt))
                    root.after(0, lambda cnt=count: set_info(f"正在导出: {cnt}/{len(output_indexes_)}"))
        except Exception as e:
            print(f"Error: Failed to export: {e}")
            root.after(0, lambda: set_info("导出失败"))
            root.after(0, lambda: set_buttons_state("normal"))
        else:
            print(f"Info: {len(output_indexes_)} zip file{plural(len(output_indexes_))} written to output/ directory")
            root.after(0, lambda: set_info(f"已导出 {len(output_indexes_)} 张谱面至 output/ 文件夹"))
            root.after(0, lambda: set_buttons_state("normal"))
    Thread(target=worker, daemon=True).start()

def select_path():
    apk_path = filedialog.askopenfilename(title="选择 APK/XAPK 文件", filetypes=[("APK/XAPK 文件", "*.apk *.xapk")])
    if not apk_path: return
    path_var.set(apk_path)
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump({"apk_path": apk_path}, f, ensure_ascii=False, indent=2)

def set_path():
    if not os.path.exists("config.json"): return
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    apk_path = config.get("apk_path", "")
    path_var.set(apk_path)

def load(check_changes=False):
    apk_path = path_var.get()
    if not apk_path:
        print(f"Error loading: empty path")
        set_info("加载失败: 路径为空")
        return
    if not os.path.exists(apk_path):
        print(f"Error loading: APK/XAPK file not found: {apk_path}")
        set_info("加载失败: APK/XAPK 文件不存在")
        return
    songs.clear()
    output_indexes.clear()
    candidates_listbox.delete(0, tk.END)
    set_buttons_state("disabled")

    def worker():
        print("Info: Starting to check and load" if check_changes else "Info: Starting to load")
        root.after(0, lambda: set_info(f"{'正在检查并加载' if check_changes else '正在加载'}"))
        try:
            load_assets(apk_path, check_changes)
        except Exception as e:
            print(f"Error: Failed to load assets: {e}")
            root.after(0, lambda: songs.clear())
            root.after(0, lambda: set_info(f"加载资源失败"))
            root.after(0, lambda: set_buttons_state("normal"))
        else:
            root.after(0, lambda: set_buttons_state("normal"))
            root.after(0, lambda: clear_search()) # to load level_frame
    Thread(target=worker, daemon=True).start()

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
    level = level_group(song.levels[index])
    for l in level_vars: level_vars[l].set(l == level)
    search()

def set_info(info):
    info_var.set(info)

def set_buttons_state(state):
    path_button.config(state=state)
    load_button.config(state=state)
    check_load_button.config(state=state)
    clear_button.config(state=state)
    search_button.config(state=state)
    candidates_listbox.config(state=state)
    export_button.config(state=state)
    id_entry.config(state=state)
    special_check.config(state=state)
    for child in level_frame.winfo_children():
        child.config(state=state)

def toggle_special():
    if special_var.get():
        difficulty_min_var.set("0")
        difficulty_max_var.set("0")
        difficulty_min_entry.config(state="readonly")
        difficulty_max_entry.config(state="readonly")
    else:
        difficulty_min_entry.config(state="normal")
        difficulty_max_entry.config(state="normal")
        difficulty_min_var.set("")
        difficulty_max_var.set("")
    search()

root = tk.Tk()
root.title("Phigros 谱面提取")
root.columnconfigure(0, weight=1)
root.rowconfigure(2, weight=1)

load_frame = ttk.LabelFrame(root, text="加载文件")
load_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
load_frame.columnconfigure(0, weight=1)
#
path_frame = ttk.Frame(load_frame)
path_frame.grid(row=0, column=0, sticky="ew")
path_frame.columnconfigure(0, weight=1)
#
path_var = tk.StringVar()
path_entry = ttk.Entry(path_frame, width=40, textvariable=path_var, state="readonly")
path_entry.grid(row=0, column=0, sticky="ew")
#
load_buttons_frame = ttk.Frame(load_frame)
load_buttons_frame.grid(row=1, column=0, sticky="ew")
load_buttons_frame.columnconfigure(1, weight=1)
#
path_button = ttk.Button(load_buttons_frame, text="选择文件", width=8, command=select_path)
path_button.grid(row=0, column=0, sticky="w")
load_button = ttk.Button(load_buttons_frame, text="加载", width=8, command=lambda: load(False))
load_button.grid(row=0, column=2, sticky="e")
ToolTip(load_button, "快速加载曲目列表")
check_load_button = ttk.Button(load_buttons_frame, text="检查并加载", width=10, command=lambda: load(True))
check_load_button.grid(row=0, column=3, sticky="e")
ToolTip(check_load_button, "检查资源变化并加载曲目列表")

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
for level in ["EZ", "HD", "IN", "AT", "Other"]:
    level_vars[level] = tk.BooleanVar(value=False)
    level_button = ttk.Checkbutton(level_frame, text=level, variable=level_vars[level], command=search)
    level_button.grid(row=0, column=len(level_vars)-1, sticky="w")
    if level == "Other":
        ToolTip(level_button, "Legacy等特殊难度")
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
special_var = tk.BooleanVar(value=False)
special_check = ttk.Checkbutton(difficulty_frame, text="SP", variable=special_var, command=toggle_special)
special_check.grid(row=0, column=3, sticky="w")
ToolTip(special_check, "定数为0的特殊谱面")
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

set_path()
root.mainloop()
