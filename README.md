# qtag

为 qBittorrent 中的种子自动设置分类与标签，并可按分类/标签做统计。

## 功能

- 按 tracker 设置 qBittorrent **分类**
- 按内容、媒介、分辨率、压制组等设置 **标签**
- 一次性处理客户端中的全部种子，或在添加新种子时处理单个 hash
- 全局任务可将统计写入 `statistics.yaml`

识别策略按 tracker 的 `content` 分流：

| tracker `content` | 识别方式 |
| --- | --- |
| 空（默认） | 按种子名识别 Movie / TV |
| `['Music']` | 不解析文件名，直接打 `Music` |
| 含 `XXX` | 片名规则之外，再用 FC2 / JAV 等编号匹配 |
| `['Ebook', 'Audiobook']` | 看种子**文件扩展名**（MAM） |

Ebook / Audiobook 会忽略封面、cue、nfo 等附属文件。同一本书的 epub + mobi/azw 仍算 Ebook；分轨 mp3 / 单个 m4b 都算 Audiobook。两种内容文件同时出现时，**优先 Audiobook**。Comic Book、Manga、Radio、Musicology 暂不单独识别。

## 要求

- Python 3.11–3.14（3.15 上 PyYAML 还没有预编译包，安装时会被 Windows 智能应用控制拦截）
- qBittorrent WebUI 已开启（tagging 大约需要 4.2+；「新增 Torrent 时运行」需要 4.6+）
- 如果你本来就在用 qBittorrent 的标签系统，请先看配置里的 `overwrite` 和 `tags_to_reserve`，避免覆盖已有标签

## 安装

推荐用 [uv](https://docs.astral.sh/uv/)：

```shell
cd qBittorrentAutoTagging
uv tool install --python 3.14 .
```

开发时用可编辑安装：

```shell
uv tool install --python 3.14 -e .
```

Windows 若开着 **智能应用控制（Smart App Control）**，`qtag.exe` 会被拦截。不要走被拦截的 exe，改用工具环境里的 Python：

```bat
%APPDATA%\uv\tools\qtag\Scripts\python.exe -m qtag --version
```

仓库里的 `qtag.cmd` 就是这一层包装，qBittorrent 外挂也可以直接填它的完整路径。

智能应用控制的开关不在微软那篇说明网页上，而在系统里：

1. 开始菜单搜索并打开 **Windows 安全中心**
2. **应用和浏览器控制**
3. **智能应用控制**（英文界面是 Smart App Control）

也可以在开始菜单直接搜「智能应用控制」。不必为了安装去关它；用上面的 `python.exe -m qtag` 即可。

## 配置

配置文件不在项目目录，而在系统用户配置目录：

| 系统 | 路径 |
| --- | --- |
| Windows | `%APPDATA%\qtag\`（Roaming） |
| Linux | `$XDG_CONFIG_HOME/qtag/` 或 `~/.config/qtag/` |
| macOS | `~/Library/Application Support/qtag/` |

其中：

- `config.yaml`：连接信息、标签规则、tracker 列表
- `statistics.yaml`：全局统计（首次运行时自动创建）

没有配置时，直接运行 `qtag` 会写出模板并退出。也可以显式生成：

```shell
qtag --init
qtag --init --config-dir D:\path\to\qtag
```

完整示例见仓库里的 `config.yaml.temp`。常用字段：

```yaml
host: localhost
port: 8080
username: admin
password: admin
overwrite: true
update_statistics: true
update_tags: true
tag_types:
  content:              # Movie, TV, Music, XXX, Ebook, Audiobook
    prefix: '#'
    max_number: -1
    ignore: false
  media:
    prefix: '$'
    max_number: -1
    ignore: false
trackers:
  NHD:
    url_key: nexushd
    ignore: false
    content:
  OpenCD:
    url_key: open.cd
    ignore: false
    content:
      - Music
  MAM:
    url_key: myanonamouse
    ignore: false
    content:
      - Ebook
      - Audiobook
```

`url_key` 是 announce URL 里的关键词。MAM 一般是 `t.myanonamouse.net`，所以用 `myanonamouse`。

## 使用

### 处理客户端中现有种子

```shell
qtag
```

会调用 `process_all`。若 `update_statistics` 为 true，结果写入配置目录下的 `statistics.yaml`，包括分类统计 (`CATEGORIES`) 和全局统计 (`TOTAL`)。无法识别的 content 记为 `?`。

```yaml
CATEGORIES:
  NHD:
    content:
      Movie: 1075
      TV: 100
  MAM:
    content:
      Ebook: 80
      Audiobook: 40
TOTAL:
  content:
    Movie: 4736
    Ebook: 80
    Audiobook: 40
```

### 新添加的种子

在 qBittorrent 设置 > 下载 > 运行外部程序 > **新增 Torrent 时运行**，填写：

```shell
qtag "%I"
```

若 `qtag.exe` 被智能应用控制拦截，改填（把路径换成你的仓库位置）：

```bat
C:\Users\arbor\repos\qBittorrentAutoTagging\qtag.cmd "%I"
```

或：

```bat
%APPDATA%\uv\tools\qtag\Scripts\python.exe -m qtag "%I"
```

`%I` 是种子 hash。触发「添加新下载任务」通常包括：开始下载、手动完成 Hash 校验、下载时跳过校验。较早版本（如 4.3.9）只有「Torrent 完成时运行」；跳过校验添加的种子不会触发。

磁链刚加入、元数据尚未下载时，MAM 可能还看不到文件列表，这时 content 会暂时无法识别。元数据齐了之后再跑一次 `qtag` 即可。

qBittorrent 调用外部程序失败时不一定弹窗。调试可在 视图 > 日志 打开「显示」，在「执行日志」里看完整命令，复制到终端运行：

```shell
qtag "a13685a7912e1cb0ed9ba7597abcb48eac9badd7"
```

### 其它命令

```shell
qtag --help
qtag --version
qtag -v                  # 调试日志
qtag --config-dir PATH   # 使用指定配置目录
```

## 开发

```shell
uv sync --group dev
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```
