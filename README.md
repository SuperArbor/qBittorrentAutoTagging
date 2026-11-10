# qtag

为 qBittorrent 自动设置分类与标签。

## 安装

```shell
uv tool install .
```

开发：`uv tool install -e .`

需要 Python 3.11–3.14，以及已开启的 qBittorrent WebUI（tagging 约 4.2+；「新增 Torrent 时运行」需 4.6+）。若你已在用客户端自带标签，把它们写进 `manual_tags`，运行 qtag 时不会被清掉。自动标签规则在 `auto_tags`。

## 配置

配置在系统用户目录，不在项目里：

| 系统 | 路径 |
| --- | --- |
| Windows | `%APPDATA%\qtag\config.yaml` |
| Linux | `~/.config/qtag/config.yaml` |
| macOS | `~/Library/Application Support/qtag/config.yaml` |

第一次使用先生成默认配置，再用编辑器填入 WebUI 的地址、用户名和密码：

```shell
qtag --init
```

完整示例见 `config.yaml.temp`。字段含义见下方「自动标签」。`url_key` 是 tracker announce URL 里的关键词。

## 使用

```shell
qtag --help                 # 查看全部参数
qtag                        # 处理客户端里的全部种子
qtag HASH                   # 只处理这一个种子
qtag --report               # 控制台输出统计（不写文件、不改客户端）
qtag --config PATH          # 指定配置文件，或 config.yaml 所在目录
```

`HASH` 是种子的 Info hash v1：在 qBittorrent 中右键种子 → 复制 → 信息哈希值 v1。

新添加的种子可以让 qBittorrent 自动调用。设置 > 下载 > 运行外部程序 > **新增 Torrent 时运行**：

```shell
qtag "%I"
```

`%I` 就是上面的 `HASH`，添加种子时由 qBittorrent 自动填入。更多参数见 [qBittorrent 文档](https://github.com/qbittorrent/qBittorrent/wiki/External-programs-How-to)。

如果结果不对：qBittorrent 调用外部程序失败时通常不弹窗。打开 **视图 > 日志**，勾选「显示」，在「执行日志」里查看完整命令和报错；也可以把那里的命令复制到终端再跑一遍。

## 自动标签

`media` 是基础项：先判定这个种子是 Movie / TV / Music / XXX / Ebook / Audiobook / Manga，其余自动标签都按它来推导（主要是 `when`）。

Tracker 的 `media` 列表决定怎么认：空则按种子名走 Movie/TV（以及启用 `producer` 时的 XXX）；`['Music']` 固定为 Music；`['Ebook', 'Audiobook', 'Manga']` 看内容文件后缀（同时出现时优先 Audiobook，其次 Manga）。

### 通用字段

写在任意 `auto_tags.*` 下：

| 字段 | 作用 |
| --- | --- |
| `prefix` | 写到客户端时加在取值前面的符号。省略则为空。 |
| `max_number` | 全库这一类最多保留几种取值（按出现次数取前 N）。省略或 `-1` = 不限制。只在 `qtag` 处理全部种子时生效。 |
| `ignore` | `true` 则不生成这一类。省略或 `false` = 生成。 |
| `when` | 仅当该种 `media` 为所列值时才打。省略则不限制。 |

### 限定字段

只对特定一类有效：

| 字段 | 属于 | 作用 |
| --- | --- | --- |
| `special` | `team` | 含 `-` 或 `[]`、不能按最后一个 `-` 切开的组名，优先整段匹配。 |
| `multi_tag` | `format` | `true` 时对每个够格的内容文件后缀各打一个 format（去重）。省略或 `false` = 只保留出现最多的一种。 |
| `patterns` | `producer` | 从上到下第一条正则命中则 `media=XXX` 且打该 producer。`producer` 被 `ignore` 时连 XXX 识别一起关掉。 |

### 各项从哪来

| 项 | 来源 |
| --- | --- |
| `media` | tracker 分流 + 种子名或内容文件。 |
| `source` / `resolution` / `process` / `year` / `team` / `codec` | 种子名。`codec` 是视频编码（x264、H.265），`when` 一般为 `[Movie, TV]`。 |
| `format` | 内容文件后缀（EPUB、FLAC、CBZ、MKV…），不是种子名里的 codec。默认 `when` 为非视频。`multi_tag: true` 时，`Title.epub` + `Title.mobi` 会打两个 format；tracker 未允许的类型（例如 MAM 里的 mkv）不参与。 |
| `producer` | 种子名匹配 `patterns`。 |

`manual_tags` 里的标签运行时不会被自动摘掉。

## 开发

```shell
uv sync --group dev
uv run pytest
uv run ruff check src tests
```
