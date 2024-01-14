# README

## 相关说明

* 脚本功能：自动对qBittorrent中的torrent设置标签（按照内容、媒介、分辨率、压制组等）。
* 脚本中针对tagging的功能对qbittorrent版本有要求，估计至少在4.2以上，个人只在4.3.9版本测试过。
* 内容方面只识别Movie和TV。各压制组的命名方式不尽相同，该脚本仅识别符合大部分压制组明明规范的文件名。个人测试了5000多个种子，除少数命名不规范的情况以外，基本都能准确识别。
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

值得注意的是，必须在qBittorrent的设置 > WebUI > 验证中手动设置用户名和密码后，才能远程登陆，默认密码不一定能用。

### 使用

使用分为两种场景：

* 一次性识别qBittorrent客户端中现有种子

在设置了config.yaml的基础上，直接运行qbittorrent_auto_tagging.py文件即可（实际调用脚本中的process_all()方法）。

* 识别新添加的种子

利用qBittorrent设置 > 下载 > Torrent完成时运行外部程序功能，在完成新下载任务后，自动触发调用脚本中的process_new()方法。方法为在该设置UI处，填写命令行指令

```shell
# 需要替换真实的python.exe和qbittorrent_auto_tagging.py路径
# 注意在系统中存在多个版本的python虚拟环境时，这里填写的python.exe必须是安装了依赖的虚拟环境
path\to\python.exe path\to\script\qbittorrent_auto_tagging.py "%I"
```

经测试， 该指令在正常下载完成时触发。如果种子文件在本地已经存在，经qBittorrent客户端校验完成后也会触发。如果采用跳过检测的方式，指令不触发。
