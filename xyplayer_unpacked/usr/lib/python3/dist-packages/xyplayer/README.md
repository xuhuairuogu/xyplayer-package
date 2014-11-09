xyplayer
========

This is a simple musicplayer that can search, play, download musics from the Internet.

xyplayer是由python3结合pyqt4库开发的一款简单的在线音乐播放器，项目主页：https://github.com/Zheng-Yejian/xyplayer

适用系统（ubuntu14.04或者linuxmint17，其他系统下还未测试过）

    xyplayer主要能进行本地歌曲管理、在线音乐搜索以及简单的歌曲下载管理，该播放只是个人根据自我需求和喜好而去学习开发的，功能方面虽然远逊于windows下的各类播放器，但对很多希望有一款兼具本地管理与网络功能播放器的linux用户来说应该基本够用。由于本人水平精力有限，目前暂时只能提供源代码（可以从我的github主页上下载），没有直接的安装包，但是我还是希望朋友们能尝试一下，我尽量帮你们解决运行上的问题，同时希望有人能帮我打包。


主要功能如下：
    1、实现基本播放功能，包括播放、暂停、停止、上一首、下一首、播放进度调节、音量调节；
    2、三种播放模式：列表循环、单曲循环、随机播放；
    3、列表操作：创建歌曲列表、删除列表、向列表添加删除歌曲；
    4、标记喜欢歌曲、批量标记；
    5、在线歌曲搜索、试听、下载（可按歌手、歌曲、专辑进行类型搜索）；
    6、歌曲下载管理，包括批量开始下载、暂停下载、取消下载、重新下载、网速显示；
    7、歌词处理功能，包括歌词同步下载、显示、简单的同步校准、桌面歌词显示；
    8、歌手信息显示；
    9、歌曲下载路径自定义设置；
    10、其他一些便捷操作设计。


播放器使用：（注意：以下步骤仅适用ubuntu14.04与linuxmint17）
    （1）从https://github.com/Zheng-Yejian/xyplayer上下载源代码并提取；
    （2）打开终端，执行“ sudo apt-get install python3-pyqt4 python3-pyqt4.qtsql python3-pyqt4.phonon python3-pyqt4.qsci phonon-backend-vlc ”
    （3）从http://pan.baidu.com/s/1lgTJo上下载mutagenx-1.23.tar.gz并提取，进入mutagenx-1.23,在终端下先后执行“  python3 setup.py build ”  “ sudo python3 setup.py install ”
    （4）在终端下进入xyplayer-master目录，执行“ python3 xyplayer.py”

目前安装使用上确实不方便，如果有时间，我会将软件打包。如果使用有问题，可以发邮件联系我，或者加群187870174交流，本人邮箱：1035766515@qq.com

