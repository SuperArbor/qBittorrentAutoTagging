# README

## 相关说明

* 脚本功能：(1)自动对qBittorrent中的torrent设置标签（按照内容、媒介、分辨率、压制组等）;(2)运行全局任务后，根据分类和标签对torrent进行统计（在statistics.yaml中查看结果）。
* 脚本中针对tagging的功能对qBittorrent版本有要求，估计至少在4.2以上。而“新增Torrent时运行”选项只在qBittorrent4.6以上版本中有，在较早版本中只有“Torrent完成时运行”选项。
* 仅测试过Windows10，其他操作系统请自行测试。
* 如果你原本就用到了qBittorrent的tagging系统，请谨慎使用该脚本，以免覆盖原有标签。作者不对任何后果负责。
* 依赖的库：qbittorrent-api, PyYAML，通过如下方法安装

```shell
pip install qbittorrent-api
pip install PyYAML
```

## 使用方法

### 设置

在根目录下创建config.yaml文件，格式参考config.yaml.temp。

```yaml
# qBittorrent所在主机的ip，以及qBittorrent WebUI的监听端口，在qBittorrent的设置 > WebUI中设置
host: localhost
port: 8080
# qBittorrent的webui的用户名、密码，在qBittorrent的设置 > WebUI > 验证中手动设置用户名和密码后，才能远程登陆，默认密码不一定能用
username: admin
password: admin
# 创建新的tag时是否清除已有标签
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
# 更新标签时保留的标签内容
tags_to_reserve:
  - ★Save
  - ★Post
# 定义各个trackers的特性
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

#### 一次性识别qBittorrent客户端中现有种子

在设置了config.yaml的基础上，直接运行qbittorrent_auto_tagging.py文件即可（实际调用脚本中的process_all()方法）。

在这个情况下，还可以通过设置update_statistics开启数据统计，结果记录在statistics.yaml中，包括分类统计(CATEGORIES)和全局统计(TOTAL)两部分，格式如下（不被识别的tag标记为"?"）

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

在设置了config.yaml的基础上，勾选qBittorrent设置 > 下载 > 运行外部程序 > 新增Torrent时运行，在添加新下载任务后，自动触发调用脚本中的process_new()方法。在该设置UI处，填写命令行指令

```shell
# 需要替换真实的python.exe和qBittorrent_auto_tagging.py路径
# 注意在系统中存在多个版本的python虚拟环境时，这里填写的python.exe必须是安装了依赖的虚拟环境对应的python路径
path\to\python.exe path\to\script\qbittorrent_auto_tagging.py "%I"
```

注意：在qBittorrent较早版本如4.3.9中，只能选“Torrent完成时运行”。 这种情况下，外部程序在正常下载完成时或Hash校验完成后触发，**如果采用跳过校验的方式添加种子，指令不触发**。

qBittorrent执行外部程序时，遇到问题不会报错。调试阶段可以在qBittorrent的视图 > 日志处开启“显示”功能，在新出现的“执行日志”页面可以看到调用外部程序时的完整指令，如

```shell
# 最右边的字符串是新添加种子的hash值
path\to\python.exe C:\xxx\qbittorrent_auto_tagging.py "a13685a7912e1cb0ed9ba7597abcb48eac9badd7"
```

复制该指令到PowerShell终端运行，有助于借助脚本输出内容排查问题。
