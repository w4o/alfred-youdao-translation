#!/usr/bin/env python3
"""Alfred Script Filter: translate text with the Youdao Open API."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API_URL = "https://openapi.youdao.com/api"
VOICE_URL = "https://dict.youdao.com/dictvoice"
HISTORY_LIMIT = 10
HISTORY_KEEP = 200

ERROR_MESSAGES = {
    "101": "缺少必填参数",
    "102": "不支持的语言类型",
    "103": "翻译文本过长",
    "108": "应用 ID 无效，请检查 App Key",
    "111": "开发者账号无效",
    "202": "签名校验失败，请检查 App Secret",
    "203": "当前 IP 不在有道白名单里",
    "301": "辞典查询失败",
    "302": "翻译查询失败",
    "303": "有道服务暂时异常",
    "401": "有道账户已欠费",
    "411": "访问过于频繁，请稍后再试",
    "412": "长文本请求过于频繁，请稍后再试",
}


def truncate(text):
    size = len(text)
    if size <= 20:
        return text
    return text[:10] + str(size) + text[-10:]


def sign(app_key, app_secret, text, salt, curtime):
    raw = app_key + truncate(text) + salt + curtime + app_secret
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def has_cjk(text):
    for char in text:
        code = ord(char)
        if (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0x3040 <= code <= 0x30FF
            or 0xAC00 <= code <= 0xD7AF
        ):
            return True
    return False


def emit(items):
    json.dump(
        {"skipknowledge": True, "items": items},
        sys.stdout,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")


def make_item(title, subtitle, arg, icon="translate.png", valid=True, copy_text=None):
    text = title if copy_text is None else copy_text
    item = {
        "title": title,
        "subtitle": subtitle,
        "arg": arg,
        "valid": valid,
        "icon": {"path": icon},
        "text": {"copy": text, "largetype": text},
    }
    if valid and arg and not str(arg).startswith("~"):
        item["mods"] = {
            "cmd": {
                "valid": True,
                "arg": arg,
                "subtitle": "用系统语音朗读",
            }
        }
    elif valid and str(arg).startswith("~"):
        spoken = str(arg)[1:]
        item["mods"] = {
            "cmd": {
                "valid": True,
                "arg": spoken,
                "subtitle": "用系统语音朗读",
            }
        }
    return item


def history_path():
    folder = os.environ.get("alfred_workflow_data")
    if not folder:
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".data")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "history.jsonl")


def load_history():
    path = history_path()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows[-HISTORY_LIMIT:][::-1]


def save_history(entry):
    path = history_path()
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    if len(lines) > HISTORY_KEEP:
        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines(lines[-HISTORY_KEEP:])


def show_history():
    rows = load_history()
    if not rows:
        emit([make_item("没有历史记录", "先用 yd 翻译一点内容", "", valid=False)])
        return
    items = []
    for row in rows:
        title = row.get("title") or ""
        subtitle = row.get("subtitle") or ""
        if not title:
            continue
        items.append(make_item(title, subtitle, title))
    emit(items or [make_item("没有历史记录", "先用 yd 翻译一点内容", "", valid=False)])


def credentials():
    app_key = os.environ.get("youdao_app_key", "").strip()
    app_secret = os.environ.get("youdao_app_secret", "").strip()
    return app_key, app_secret


def request_translation(text, app_key, app_secret):
    salt = uuid.uuid4().hex
    curtime = str(int(time.time()))
    payload = {
        "q": text,
        "from": "auto",
        "to": "zh-CHS",
        "appKey": app_key,
        "salt": salt,
        "sign": sign(app_key, app_secret, text, salt, curtime),
        "signType": "v3",
        "curtime": curtime,
        "strict": "false",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(API_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("有道接口返回 HTTP {0}".format(exc.code))
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError("网络请求失败：{0}".format(reason))


def phonetic_line(basic, query):
    parts = []
    phonetic = basic.get("phonetic")
    if phonetic and has_cjk(query):
        parts.append("[{0}]".format(phonetic))
    us_phonetic = basic.get("us-phonetic")
    uk_phonetic = basic.get("uk-phonetic")
    if us_phonetic:
        parts.append("[美: {0}]".format(us_phonetic))
    if uk_phonetic:
        parts.append("[英: {0}]".format(uk_phonetic))
    if not parts and phonetic:
        parts.append("[{0}]".format(phonetic))
    return " ".join(parts)


def build_items(query, result):
    items = []
    seen = set()
    translations = result.get("translation") or []
    pronounce = translations[0] if has_cjk(query) and translations else query

    def add(title, subtitle, arg, icon="translate.png"):
        title = (title or "").strip()
        if not title or title in seen:
            return
        seen.add(title)
        items.append(make_item(title, subtitle, arg, icon=icon))

    if translations:
        direction = result.get("l") or ""
        subtitle = query if not direction else "{0}  ·  {1}".format(query, direction)
        add(translations[0], subtitle, translations[0])
        for extra in translations[1:]:
            add(extra, query, extra)

    basic = result.get("basic") or {}
    if isinstance(basic, dict):
        for explain in basic.get("explains") or []:
            add(explain, "词典释义 · {0}".format(query), explain)
        phonetic = phonetic_line(basic, query)
        if phonetic:
            add(phonetic, "回车播放发音", "~" + pronounce, icon="translate-say.png")

    for entry in result.get("web") or []:
        if not isinstance(entry, dict):
            continue
        values = entry.get("value") or []
        if isinstance(values, str):
            values = [values]
        title = ", ".join(str(value) for value in values if value)
        key = entry.get("key") or "网络释义"
        add(title, "网络释义 · {0}".format(key), title)

    if translations:
        save_history({"title": translations[0], "subtitle": query})
    return items


def translate(query):
    query = (query or "").strip()
    if not query:
        emit(
            [
                make_item(
                    "yd 要翻译的内容",
                    "中英自动互译。yd * 查看最近记录",
                    "",
                    valid=False,
                )
            ]
        )
        return
    if query == "*":
        show_history()
        return
    if len(query) > 5000:
        emit([make_item("文本超过 5000 字", "请缩短后再翻译", "", valid=False)])
        return

    app_key, app_secret = credentials()
    if not app_key or not app_secret:
        emit(
            [
                make_item(
                    "还没有配置有道密钥",
                    "Workflow 右上角配置里填写 App Key 和 App Secret",
                    "",
                    valid=False,
                )
            ]
        )
        return

    result = request_translation(query, app_key, app_secret)
    error_code = str(result.get("errorCode", ""))
    if error_code != "0":
        message = ERROR_MESSAGES.get(error_code, "翻译失败")
        emit(
            [
                make_item(
                    message,
                    "有道错误码 {0}".format(error_code),
                    "",
                    valid=False,
                )
            ]
        )
        return

    items = build_items(query, result)
    if not items:
        emit([make_item("没有翻译结果", query, "", valid=False)])
        return
    emit(items)


def strip_marker(text):
    text = (text or "").strip()
    if text.startswith("~"):
        return text[1:]
    return text


def say(text):
    text = strip_marker(text)
    if not text:
        return
    voice = "Tingting" if has_cjk(text) else "Samantha"
    completed = subprocess.run(["say", "-v", voice, text])
    if completed.returncode != 0:
        subprocess.run(["say", text])


def speak(text):
    text = strip_marker(text)
    if not text:
        return
    query = urllib.parse.urlencode({"audio": text, "type": "1"})
    url = VOICE_URL + "?" + query
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        urllib.request.urlretrieve(url, path)
        completed = subprocess.run(["afplay", path])
        if completed.returncode != 0:
            say(text)
    except (urllib.error.URLError, OSError):
        say(text)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main(argv):
    mode = os.environ.get("YOUDAO_MODE", "translate")
    text = argv[1] if len(argv) > 1 else ""
    if mode == "speak":
        speak(text)
        return 0
    if mode == "say":
        say(text)
        return 0
    try:
        translate(text)
    except Exception as exc:
        emit([make_item("翻译出错", str(exc), "", valid=False)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
