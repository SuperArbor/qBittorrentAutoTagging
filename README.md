# qtag

为 qBittorrent 自动设置分类与标签。

## 安装

```shell
uv tool install .
```

开发：`uv tool install -e .`

需要 Python 3.11+，以及已开启的 qBittorrent WebUI（tagging 约 4.2+；「新增 Torrent 时运行」需 4.6+）。若你已在用客户端自带标签，请先看配置里的 `overwrite` 和 `tags_to_reserve`。

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

字段含义和完整示例见 `config.yaml.temp`。`url_key` 是 tracker announce URL 里的关键词。

识别按 tracker 的 `content` 分流：空则按种子名识别 Movie/TV；`['Music']` 直接打 Music；含 `XXX` 再用编号规则；`['Ebook', 'Audiobook']` 看文件扩展名（同时出现时优先 Audiobook）。

## 使用

```shell
qtag              # 处理客户端里的全部种子
qtag HASH         # 只处理这一个种子
qtag --report     # 控制台输出统计（不写文件、不改客户端）
```

`HASH` 是种子的 Info hash v1：在 qBittorrent 中右键种子 → 复制 → 信息哈希值 v1。

新添加的种子可以让 qBittorrent 自动调用。设置 > 下载 > 运行外部程序 > **新增 Torrent 时运行**：

```shell
qtag "%I"
```

`%I` 就是上面的 `HASH`，添加种子时由 qBittorrent 自动填入。更多参数见 [qBittorrent 文档](https://github.com/qbittorrent/qBittorrent/wiki/External-programs-How-to)。

如果结果不对：qBittorrent 调用外部程序失败时通常不弹窗。打开 **视图 > 日志**，勾选「显示」，在「执行日志」里查看完整命令和报错；也可以把那里的命令复制到终端再跑一遍。

## 开发

```shell
uv sync --group dev
uv run pytest
uv run ruff check src tests
```
