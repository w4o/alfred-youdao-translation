# Youdao Translate

Alfred Workflow。呼出 Alfred，用关键字 `yd` 调用 [有道智云文本翻译](https://ai.youdao.com/DOCSIRMA/html/trans/api/wbfy/index.html)，做中英互译。

回车复制译文，音标行回车播放有道发音，`⌘↩` 用 macOS 语音朗读。密钥只保存在本机 Alfred 配置里，不会写进仓库。

## 功能

- 关键字 `yd`，中文译成英文，英文译成中文
- 展示译文、词典释义、英美音标和网络释义
- 回车把当前行复制到剪贴板
- 音标那一行回车，播放有道词典发音；下载失败时改用系统语音
- `⌘↩` 用系统语音朗读（中文 `Tingting`，英文 `Samantha`）
- `⌘C` 复制当前行，`⌘L` 大字显示
- `yd *` 查看最近 10 条翻译

## 环境

- macOS
- [Alfred 5](https://www.alfredapp.com/) 或更新版本，并已购买 Powerpack（Workflow 是 Powerpack 功能）
- `/usr/bin/python3` 可用。本机用 Xcode 命令行工具自带的 Python 即可，脚本只用标准库，不需要 `pip install`
- 有道智云账号，应用已开通「文本翻译」

检查 Python：

```bash
/usr/bin/python3 --version
```

如果提示安装开发者工具，执行 `xcode-select --install`。Homebrew 的 Python 一般在 `/opt/homebrew/bin/python3`，Workflow 调用的是 `/usr/bin/python3`，两者不是同一个解释器。

## 安装

双击仓库里的 [`Youdao Translate.alfredworkflow`](Youdao%20Translate.alfredworkflow)，Alfred 会提示导入。

也可以从源码自己打包：

```bash
zip -r "Youdao Translate.alfredworkflow" \
  info.plist \
  youdao.py \
  icon.png \
  translate.png \
  translate-say.png

open "Youdao Translate.alfredworkflow"
```

压缩包根目录必须直接是这些文件，不要多套一层文件夹。不要把 `.git`、`.data`、`prefs.plist` 打进去。

## 申请密钥

1. 打开 [有道智云](https://ai.youdao.com/) 并登录。
2. 进入控制台，创建应用。
3. 在应用里开通「自然语言翻译」下的「文本翻译」。
4. 复制应用 ID 和应用密钥。

新应用通常有免费额度。额度用完、账户欠费，或请求过于频繁时，Alfred 会显示对应的有道错误码。如果控制台设置了 IP 白名单，而当前网络不在名单里，会返回错误码 `203`。个人使用可以不填白名单。

## 配置

1. 打开 Alfred 设置 → Workflows → **Youdao Translate**。
2. 点工作流右上角的配置按钮（显示为 `[x]`）。
3. 填入：

| 配置项 | 对应环境变量 | 填什么 |
| --- | --- | --- |
| App Key | `youdao_app_key` | 应用 ID |
| App Secret | `youdao_app_secret` | 应用密钥 |

两项都会去掉首尾空格。导出或分享 Workflow 时，Alfred 不会带上这两个变量（`variablesdontexport`）。请不要把密钥写进 `info.plist`、`youdao.py` 或提交说明。

改过的配置保存在本机的 `prefs.plist`，这个文件已在 `.gitignore` 里。

## 使用

呼出 Alfred，输入 `yd`，空格，再输入要翻译的内容。输入会稍作等待再请求，避免每个按键都打一次接口。

| 输入 | 结果 |
| --- | --- |
| `yd hello` | 译文「你好」，以及词典释义、音标、网络释义 |
| `yd 你好世界` | 英文译文 |
| `yd *` | 最近 10 条记录，回车复制那条译文 |
| 选中译文后回车 | 复制到剪贴板 |
| 选中音标行后回车 | 播放有道发音 |
| `⌘↩` | 系统语音朗读 |
| `⌘C` | 复制当前行标题 |
| `⌘L` | 大字显示当前行 |

关键字写死在 Script Filter 里，默认是 `yd`。要改的话，在 Alfred 里打开这个 Script Filter，修改 Keyword。

## 结果每一行是什么

有道返回成功（`errorCode` 为 `0`）后，按这个顺序显示，重复的标题会去掉：

1. **译文**。副标题是原文和有道返回的语言方向（例如 `en2zh-CHS`）。
2. **词典释义**，来自 `basic.explains`。
3. **音标**。英文查询显示美式、英式音标；中文查询还会显示拼音。这一行的参数以 `~` 开头，回车走发音，不走复制。
4. **网络释义**，来自 `web`。

只有第一条译文会写入历史。历史存在 Alfred 为这个 Workflow 分配的数据目录：

```text
~/Library/Application Support/Alfred/Workflow Data/com.w4o.youdao-translate/history.jsonl
```

界面只显示最近 10 条，文件里最多保留 200 条。在终端里直接跑脚本、而 Alfred 没有设置数据目录时，历史写到仓库下的 `.data/history.jsonl`（已忽略，不会提交）。

## 发音

音标行回车后，请求：

```text
https://dict.youdao.com/dictvoice?audio=<文本>&type=1
```

`type=1` 是英式发音。音频下到临时文件后用 `afplay` 播放，播完即删。下载或播放失败时，改用 `say`。

朗读哪一段文本：

- 查询本身含中日韩文字时，朗读译文
- 否则朗读你输入的原文

`⌘↩` 不走有道音频，直接调用 `say`。文本含中日韩文字时用 `Tingting`，否则用 `Samantha`。对应语音没装好时，再退回系统默认语音。

## 数据会发到哪里

| 数据 | 去向 | 是否随仓库分发 |
| --- | --- | --- |
| 待翻译文本 | `https://openapi.youdao.com/api` | 否 |
| 发音文本 | `https://dict.youdao.com/dictvoice` | 否 |
| App Key / App Secret | 只留在本机 Alfred 配置 | 否 |
| 最近译文 | 本机 `history.jsonl` | 否 |

翻译内容会发送到有道。不要用它翻译密码、密钥或其他不能离开本机的文本。

## 工作原理

Script Filter 用 `/bin/bash` 调用：

```bash
/usr/bin/python3 ./youdao.py "$1"
```

查询通过 argv 传入，避免空格和引号被 shell 吃掉。脚本向 stdout 打印 [Alfred Script Filter JSON](https://www.alfredapp.com/help/workflows/inputs/script-filter/json/)。`skipknowledge` 为 `true`，结果顺序保持脚本返回的顺序。

接口是有道智云文本翻译 v3：

- 地址：`POST https://openapi.youdao.com/api`
- `from=auto`，`to=zh-CHS`，`strict=false`
- `strict=false` 时，有道按中英方向自动对调：英文译成中文，中文译成英文
- 签名：`SHA256(应用ID + input + salt + curtime + 应用密钥)`
- `input`：文本不超过 20 个字符时用原文；更长时用「前 10 个字符 + 字符数 + 后 10 个字符」

这是中英互译，不是通用多语种翻译。单次查询在客户端限制为 5000 字。

选中结果后，Workflow 用两条过滤分流：

- 不以 `~` 开头：复制到剪贴板
- 以 `~` 开头：去掉 `~`，再以 `YOUDAO_MODE=speak` 调用同一个脚本播放发音
- 按住 `⌘` 回车：以 `YOUDAO_MODE=say` 调用系统语音

## 项目结构

```text
.
├── Youdao Translate.alfredworkflow   # 可双击安装的包
├── info.plist                        # Workflow 定义、关键字、配置项
├── youdao.py                         # 翻译、历史、发音
├── icon.png                          # Workflow 图标
├── translate.png                     # 普通结果图标
├── translate-say.png                 # 音标 / 发音行图标
├── LICENSE
└── README.md
```

`youdao.py` 选择 Python 3，是因为签名、HTTP 和 JSON 都在标准库里（`hashlib`、`urllib`、`json`），Workflow 不必再带一套依赖。macOS 已不再自带 PHP。

## 本地调试

在仓库目录执行。把密钥只放在当前终端会话里：

```bash
export youdao_app_key="应用 ID"
export youdao_app_secret="应用密钥"

python3 youdao.py "hello"
python3 youdao.py "你好"
python3 youdao.py "*"
```

发音和朗读：

```bash
YOUDAO_MODE=speak python3 youdao.py "~hello"
YOUDAO_MODE=say python3 youdao.py "hello"
```

没配密钥、查询为空、或有道返回错误时，脚本仍输出合法的 Script Filter JSON，Alfred 里会看到一条不可回车的说明。

改完脚本后，重新执行上面的 `zip` 命令再双击安装，Alfred 才会用到新文件。已经导入的那份在 Alfred 的 Workflow 目录里，改仓库不会自动生效。

## 常见问题

| 现象 | 含义 | 处理 |
| --- | --- | --- |
| 还没有配置有道密钥 | App Key 或 App Secret 为空 | 在 Workflow 配置里填写 |
| 错误码 `108` | 应用 ID 无效 | 核对 App Key，确认没有多余空格 |
| 错误码 `202` | 签名失败 | 核对 App Secret；确认用的是应用密钥，不是别的 token |
| 错误码 `203` | 当前 IP 不在白名单 | 在有道控制台放行当前 IP，或清空白名单 |
| 错误码 `401` | 账户欠费或额度用完 | 到有道控制台查看余额和免费额度 |
| 错误码 `411` / `412` | 请求过于频繁 | 等一会儿再查 |
| 错误码 `103` 或提示超过 5000 字 | 文本过长 | 缩短后再翻译 |
| `python3: command not found` 或一闪而过没有结果 | `/usr/bin/python3` 不可用 | 安装 Xcode 命令行工具后再试 |
| 有译文但没有发音 | 有道词典音频下载失败 | 脚本会改用 `say`；检查网络，或改用 `⌘↩` |
| 改了代码，Alfred 里仍是旧行为 | 运行的是已导入的副本 | 重新打包并双击安装 |

Alfred 里打开这个 Workflow 的调试器（右上角虫子图标），可以看到脚本输出的 JSON 和报错。

## 许可证

[MIT License](LICENSE)。
