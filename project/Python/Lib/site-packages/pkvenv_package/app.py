import datetime
import json
import re
import os
import zipfile
from mmgui import BrowserWindow, App

win = App(headless=False)
app = None


def open_file():
    path = win.show_file_dialog_for_file("打开文件", "*")
    return path


def open_dir():
    path = win.show_file_dialog_for_dir("打开文件")
    return path

def find_all_file(file_path):
    if os.path.isdir(file_path):
        file_list = []
        for root, dirs, files in os.walk(file_path):
            for file in files:
                file_list.append(os.path.join(root, file))
        return file_list
    elif os.path.isfile(file_path):
        return [file_path]
    else:
        return []
def process_path(file_path, choice, string_list=None, output_folder=None):
    result = []
    path = find_all_file(file_path)
    if choice == "1" or choice == "2":
        for p in path:
            file_result = file_type(p, choice)
            if file_result is not None:
                result.append(file_result)
    elif choice == "3":
        string = string_list.split(",")
        for paths in path:
            file_extension = os.path.splitext(paths)[1]
            if file_extension in ['.log', '.txt']:
                results = search_sensitive_words(paths, string, output_folder)
                if results:
                    result.append(results)
    elif choice == "4":
        ue4_pak_result = search_files(file_path, b'\xE1\x12\x6F\x5A')
        ue4_pak_count = ue4_pak_result[0]
        if os.path.isfile(file_path):
            result = ue4_pak_result
            return result
        else:
            result = f"该目录共有 {ue4_pak_count} 个pak文件"
            return result
    elif choice == "5":
        unity_ab_result = search_files(file_path, b'Unity')
        unity_ab_count = unity_ab_result[1]
        if os.path.isfile(file_path):
            result = unity_ab_result
            return result
        else:
            result = f"该目录共有 {unity_ab_count} 个AB资源文件"
            return result
    elif choice == "6":
        result = json.dumps(unpack_apk(file_path, output_folder), ensure_ascii=False, indent=4)  # 将字典转换为JSON格式的字符串
        print(result)
    return result


def file_type(file, choice):
    with open(file, 'rb') as f:
        if choice == "1":
            hex_data = ' '.join(format(byte, '02X') for byte in f.read(16))
            if hex_data[:5] == '4D 5A':
                return file
            return None
        elif choice == "2":
            hex_data = ' '.join(format(byte, '02X') for byte in f.read(48))
            if hex_data[:5] == '4D 5A' and hex_data[120:-12] == '53 45 4E 53':
                return file
            return None

def search_sensitive_words(file_path, string_list, output_folder):
    last_lines = -10
    result = []
    with open(file_path, 'rb') as f:
        lines = [line.decode('utf-8', 'ignore').strip() for line in f.readlines()]
        catch_lines = []
        sensitive_names = []
        for index, line in enumerate(lines):
            into = False
            for word in string_list:
                if re.search(word, line, flags=re.IGNORECASE):
                    sensitive_names.append(word)
                    if index - last_lines > 10:
                        if index - last_lines < 20:
                            start = max(0, last_lines + 11)
                            end = min(index + 11, len(lines))
                            last_lines = index
                            into = True
                        else:
                            start = max(0, index - 10)
                            end = min(index + 11, len(lines))
                            last_lines = index
                            into = True
            if into:
                for i in lines[start:end]:
                    catch_lines.append(i)
        if len(catch_lines) > 0:
            time = datetime.datetime.now().strftime("%Y%m%d%H%M")
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_file = f"{'+'.join(set(sensitive_names))}+{base_name}+{time}.txt"
            with open(os.path.join(output_folder, output_file), 'w', encoding='utf-8') as w:
                for i in catch_lines:
                    w.write(str(i) + '\n')

            result.append(f"找到敏感词{','.join(set(sensitive_names))}在{file_path}")
    return result

def search_files(path, keyword):
    ue4_pak_count = 0
    unity_ab_count = 0
    print(path)
    if os.path.isfile(path):
        if path.endswith(".pak"):
            found, index = search_file(path, keyword)
            if found:
                # print(f"关键词 {keyword.hex()} 在文件 {path} 中的位置: 0x{index:02X}")
                file_result = f"在文件 {path} 中的位置: 0x{index:02X}找到关键词 {keyword.hex()} "
                return file_result
            else:
                print("该文件不是UE4的资源pak文件")
        elif path.endswith(".bytes"):
            if is_ab_file(path):
                print(f"文件 {path} 是AB资源文件")
                file_result = f"文件 {path} 是AB资源文件"
                return file_result
        else:
            print("该文件不符合情况")
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith(".pak"):
                    found, index = search_file(file_path, keyword)
                    if found:
                        ue4_pak_count += 1
                else:
                    if is_ab_file(file_path):
                        unity_ab_count += 1
    return ue4_pak_count, unity_ab_count


def search_file(file_path, keyword):
    with open(file_path, 'rb') as f:
        content = f.read()
        index = content.find(keyword)
        if index != -1:
            return True, index
    return False, -1


def is_ab_file(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(8)
        return b'Unity' in header


def unpack_apk(apk_path, output_dir):
    result = {
        "游戏引擎": "",
        "VirBox": False,
        "MTP加固": False,
        "MTP反调试": False
    }

    try:
        with zipfile.ZipFile(apk_path, 'r') as apk_file:
            apk_file.extractall(output_dir)
        print('解包成功！解包路径:', output_dir)
        lib_path = os.path.join(output_dir, 'lib', 'arm64-v8a')
        files = os.listdir(lib_path)

        if 'libtprt.so' in files:
            result["MTP加固"] = True
        if 'libtersafe2.so' in files:
            result["MTP反调试"] = True

        if 'libunity.so' in files:
            result["游戏引擎"] = "Unity"
            libil2cpp_path = os.path.join(lib_path, 'libil2cpp.so')
            libunity_path = os.path.join(lib_path, 'libunity.so')
            if check_string(libil2cpp_path) and check_string(libunity_path):
                result["VirBox"] = True
        elif 'libUE4.so' in files:
            result["游戏引擎"] = "UE4"
            libUE4_path = os.path.join(lib_path, 'libUE4.so')
            if check_string(libUE4_path):
                result["VirBox"] = True
        print(result)
        return result
    except Exception as e:
        print('解包失败:', str(e))


def check_string(file_path):
    with open(file_path, 'r', errors='ignore') as file:
        f = file.read()
        if 'Virbox Protecto' in f:
            return True
        return False


def on_create(ctx):
    global win
    win = BrowserWindow({
        "title": "文件处理功能",
        "width": 1300,
        "height": 920,
        "dev_mode": False,
    })

    win.webview.bind_function("process_path", process_path)
    win.webview.bind_function("open_file", open_file)
    win.webview.bind_function("open_dir", open_dir)
    win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.html"))
    win.show()


def main():
    global app
    app = App(headless=False)
    app.on("create", on_create)
    app.run()


main()
