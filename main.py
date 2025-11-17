import os, json, base64, struct, UnityPy, io, yaml, re
from math import floor, ceil
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from tqdm import tqdm

def i32(b,p): return struct.unpack_from("<i",b,p)[0], p+4 # int32
def u32(b,p): return struct.unpack_from("<I",b,p)[0], p+4 # unsigned int32
def f32(b,p): return struct.unpack_from("<f",b,p)[0], p+4 # float32
def utf8(b,p): length, p = u32(b,p); return b[p:p+length].decode("utf-8"), p+length
def utf16(b,p): length, p = u32(b,p); return b[p:p+length].decode("utf-16"), p+length

songs = {}
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

os.makedirs("input", exist_ok=True)
input_dir = Path("./input")
apk_paths = [p for p in input_dir.iterdir() if p.is_file() and p.suffix == ".apk"]
if len(apk_paths) == 0: raise Exception("Need apk file in input/ directory")
apk_path = apk_paths[0]
print(f"Info: Using {apk_path} as input")

with ZipFile(apk_path) as zf:
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
with open("assembly-csharp.json") as f: # extracted using Il2CppDumper and TypeTreeGenerator
    typetree = json.load(f)
print("Info: Input files loaded")

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
print("Info: Total number of songs:", len(songs))

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

output_id = None
while output_id == None:
    query_id = input("搜索曲目名称/ID (可留空): ")
    if query_id == "":
        output_id = ""
    elif query_id in songs:
        output_id = query_id
        print(f"已选择 {songs[query_id].name} ({query_id})")
    else:
        candidates = [(song_id,song) for song_id,song in songs.items() if query_id.lower() in song.name.lower()]
        if len(candidates) == 0: 
            print("无匹配项")
            print("再次", end="")
        elif len(candidates) == 1:
            song_id,song = candidates[0]
            output_id = song_id
            print(f"已选择 {song.name} ({song_id})")
        else:
            print(f"多个匹配项 (共{len(candidates)}个):")
            for song_id,song in candidates[:5]:
                print(f"{song.name} ({song_id})")
            print("再次", end="")
output_levels = [i for i in input("筛选难度 (空格分隔, 如'IN AT Legacy', 大小写敏感, 可留空): ").split(" ") if i != ""]
if len(output_levels) != 0:
    print(f"已设为 {output_levels}")
output_difficulty_min = None
output_difficulty_max = None
if output_id != "":
    output_difficulty_min = 0
    output_difficulty_max = float("inf")
while output_difficulty_min == None:
    query_difficulty_min = input("筛选定数最小值 (可留空): ")
    if query_difficulty_min == "":
        output_difficulty_min = 0
    else:
        try:
            output_difficulty_min = ceil(float(query_difficulty_min)*10)/10
            print(f"已设为 {output_difficulty_min}")
        except:
            print(f"{query_difficulty_min} 非数值")
            print("再次", end="")
while output_difficulty_max == None:
    query_difficulty_max = input("筛选定数最大值 (可留空): ")
    if query_difficulty_max == "":
        output_difficulty_max = float("inf")
    else:
        try:
            output_difficulty_max = floor(float(query_difficulty_max)*10)/10
            print(f"已设为 {output_difficulty_max}")
        except:
            print(f"{query_difficulty_max} 非数值")
            print("再次", end="")

output_indexes = []
output_count = 0
for song_id,song in songs.items():
    if not (song_id == output_id or output_id == ""): continue
    indexes = []
    for index in range(len(song.levels)):
        if not (song.levels[index] in output_levels or len(output_levels) == 0): continue
        if not (output_difficulty_min <= song.difficulty[index] <= output_difficulty_max and song.difficulty[index] != 0): continue
        indexes.append(index)
        output_count += 1
    if indexes != []: output_indexes.append((song_id,song,indexes))
print(f"Info: {len(output_indexes)} song(s) ({output_count} chart(s)) found")

print("Info: Starting to output")
os.makedirs("output", exist_ok=True)
for song_id,song,indexes in tqdm(output_indexes):
    for index in indexes:
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
print(f"Info: {output_count} zip file(s) written to output/ directory")
