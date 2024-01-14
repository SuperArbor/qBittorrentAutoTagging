# README

* 脚本功能：自动对qBittorrent中的torrent设置标签（按照内容、媒介、分辨率、压制组等）。
* 相关设置：在根目录下创建config.yaml文件，格式参考config.yaml.temp。
* 使用方法：在设置了config.yaml的基础上，直接运行qbittorrent_auto_tagging.py文件即可。
* 脚本中针对tagging的功能对qbittorrent版本有要求，估计至少在4.2以上，个人只在4.3.9版本测试过。
* 内容方面只识别Movie和TV。各压制组的命名方式不尽相同，该脚本仅识别符合大部分压制组明明规范的文件名。个人测试了5000多个种子，除少数命名不规范的情况以外，基本都能准确识别。
* 仅测试过Windows10，其他操作系统请自行测试。
* 如果你原本就用到了qBittorrent的tagging系统，请谨慎使用该脚本，以免覆盖原有标签。作者不对任何后果负责。
* 依赖的库：qbittorrent-api, PyYAML，通过如下方法安装

```shell
pip install qbittorrent-api
pip install PyYAML
```
  