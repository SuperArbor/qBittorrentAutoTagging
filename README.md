# README

## 相关说明

* 脚本功能：

  * 自动对 qBittorrent 中的 torrent 设置标签（按照内容、媒介、分辨率、压制组等）;  
  * 运行全局任务后，根据分类和标签对 torrent 进行统计（在 *statistics.yaml* 中查看结果）。

* 基于命名规范程度，主要识别的内容为电影（*Movie*）和电视剧（*TV*），对于在 *config.yaml* 中设定为仅包含 *Music* 内容的 tracker，也会对相应种子赋予 *Music* 标签。

* 脚本中针对 tagging 的功能对 qBittorrent 版本有要求，估计至少在 4.2 以上。而 “新增 Torrent 时运行” 选项只在 qBittorrent 4.6 以上版本中有，在较早版本中只有 “Torrent 完成时运行” 选项。

* 仅测试过 Windows10，其他操作系统请自行测试。

* 如果你原本就用到了 qBittorrent 的 tagging 系统，请谨慎使用该脚本，以免覆盖原有标签（充分利用 *config.yaml* 中的 *overwrite* 和 *tags_to_reserve* 选项）。作者不对任何后果负责。

* 依赖的库：*qbittorrent-api*, *PyYAML*，推荐使用 UV 安装

```shell
cd qbit-tag
uv sync
uv tool install -e .
```

## 使用方法

### 设置

在根目录下创建 *config.yaml* 文件，格式参考 *config.yaml.temp*。

```yaml
# qBittorrent 所在主机的 ip，以及 qBittorrent WebUI 的监听端口，在 qBittorrent 的设置 > WebUI中设置
host: localhost
port: 8080
# qBittorrent 的 webui 的用户名、密码，在 qBittorrent 的设置 > WebUI > 验证中手动设置用户名和密码后，才能远程登陆，默认密码不一定能用
username: admin
password: admin
# 创建新的 tag 时是否清除已有标签
overwrite: true
# 定义标签类型，可选的标签类型范围 TAGS_ALL = ['content', 'media', 'year', 'resolution', 'process_method', 'process_type', 'team']
tag_types:
  content:              # Movie, TV, Music
    prefix: '#'         # the prefix to decorate before the tag
    max_number: -1      # max number of instances to keep under this tag type
    ignore: false       # whether to ignore the tag type or not when tagging
  media:                # BluRay, DVD, HDTV, WEB
    prefix: '$'
    max_number: -1
    ignore: false
  resolution:           # 720p/i, 1080p/i, 2160p/i 
    prefix: ''
    max_number: -1
    ignore: false
  team:                 # Author of the Encode
    prefix: '-'
    max_number: 2
    ignore: false
  process_type:         # Encode, Raw
    prefix: '~'
    max_number: -1
    ignore: true
  process_method:       # H264/H265, x264/x265
    prefix: ''
    max_number: -1
    ignore: true
  year:                 # year when the workpiece was produced
    prefix: ''
    max_number: 3
    ignore: true
  producer:
    prefix: '*'
    max_number: -1
    ignore: false
# 更新标签时保留的标签内容
tags_to_reserve:
  - ★Save
  - ★Post
# 定义各个 trackers 的特性
trackers:
  NHD: 
    url_key: nexushd    # key word in tracker url
    ignore: false       # whether to ignore the tracker or not when tagging
    content:            # specify content types in the tracker
  PuTao: 
    url_key: sjtu
    ignore: false
    content:
```

### 使用

使用分为两种场景：

#### 一次性识别 qBittorrent 客户端中现有种子

在设置了 *config.yaml* 的基础上，直接运行 *qbit-tag* 即可（实际调用脚本中的 *process_all* 方法）。

在这个情况下，还可以通过设置 *update_statistics* 开启数据统计，结果记录在 *statistics.yaml* 中，包括分类统计 (*CATEGORIES*) 和全局统计 (*TOTAL*) 两部分，格式如下（不被识别的 tag 标记为 "*?*"）

```yaml
CATEGORIES:
  NHD:
    content:
      '?': 12
      Movie: 1075
      TV: 100
    media:
      '?': 5
      BluRay: 1030
      DVD: 3
      HDTV: 0
      WEB: 137
    resolution:
      1080p: 1056
      2160p: 9
      720p: 103
      '?': 7
    team:
      0LED: 1
      '147': 2
      7SinS: 1
      '?': 11
      A: 1
      ADE: 2
      ADWeb: 3
      AREY: 4
      ARiN: 3
      ...
  PuTao:
    content:
      '?': 3
      Movie: 330
      TV: 17
    media:
      '?': 2
      BluRay: 313
      DVD: 0
      HDTV: 0
      WEB: 32
    resolution:
      1080p: 329
      2160p: 0
      720p: 18
    team:
      '?': 3
      A: 1
      ADE: 1
      AREY: 1
      BMF: 8
      CALiGARi: 1
      ...
TOTAL:
  content:
    '?': 375
    Movie: 4736
    TV: 228
  media:
    '?': 21
    BluRay: 4638
    DVD: 9
    HDTV: 1
    WEB: 295
  resolution:
    1080p: 4601
    2160p: 24
    720p: 326
    '?': 13
  team:
    0LED: 5
    '147': 5
    7SinS: 1
    '?': 34
    A: 6
    ADE: 6
    ...
```

#### 识别新添加的种子

在设置了 *config.yaml* 的基础上，勾选 qBittorrent 设置 > 下载 > 运行外部程序 > 新增 Torrent 时运行，在添加新下载任务后，自动触发调用脚本中的 *process_new* 方法。在该设置 UI 处，填写命令行指令

```shell
qbit-tag "%I"
```

注意，qBittorrent 中，触发 “添加新下载任务” 有三种方式：

* 开始下载
* 已在列表中的种子手动完成 Hash 校验
* 下载时跳过校验

较早版本如 4.3.9 中，只有 “Torrent 完成时运行”。 这种情况下，外部程序在正常下载完成时或 Hash 校验完成后触发，如果采用跳过校验的方式添加种子，指令不触发。

qBittorrent 执行外部程序时，遇到问题不会报错。调试阶段可以在 qBittorrent 的视图 > 日志处开启 “显示” 功能，在新出现的 “执行日志” 页面可以看到调用外部程序时的完整指令，如

```shell
# 最右边的字符串是新添加种子的hash值
qbit-tag "a13685a7912e1cb0ed9ba7597abcb48eac9badd7"
```

复制该指令到 PowerShell 或 CMD 终端运行，有助于借助脚本输出内容排查问题。
