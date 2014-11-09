# -*- coding : utf-8 -*-
import os, time, threading, random, json, re
from http.client import HTTPConnection
from socket import gaierror
from PyQt4.QtGui import (QWidget, QLineEdit, QToolButton, QIcon, QCursor, QMessageBox, QComboBox,
        QHBoxLayout, QSpacerItem, QLabel, QSizePolicy, QVBoxLayout, QDialog, QPalette, QColor, QFrame, 
        QPixmap, QKeySequence, QSlider, QSplitter, QTextEdit, QFont, QGridLayout, QStackedWidget, QLayout,
        QSystemTrayIcon, QApplication, QAction, QMenu, QTextCursor, QPushButton, QInputDialog, QFileDialog)
from PyQt4.QtCore import Qt, QEvent, QSize, QTime, QPoint, QUrl
from PyQt4.QtSql import QSqlTableModel, QSqlQuery

try:
    from PyQt4.phonon import Phonon
except ImportError:
    import sys
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Music Player",
            "Your Qt installation does not have Phonon support.",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton)
    sys.exit(1)
from xyplayer.mywidgets import DownloadPage, SearchFrame, SettingFrame, DesktopLyric
from xyplayer.mythreads import DownloadLrcThread
from xyplayer.mytables import TableModel, TableView, SqlOperate, ManageTableView
from xyplayer.urldispose import SearchOnline
from xyplayer.configure import Configures
from xyplayer.util import read_music_info, parse_lrc
import xyplayer.allIcons_rc

class Player(QDialog):
    def __init__(self, parent = None):
        super(Player, self).__init__(parent)
        self.initial_sql()
        Configures.check_dirs()
        self.initial_phonon()
        self.create_actions()
        self.setup_ui()
        self.create_connects()
        self.initial_parameters()
    
    def initial_parameters(self):
        self.lyricOffset = 0
        self.lyricOffsetIndex = 2
        self.playmodeIndex = 1
        self.volume = self.audioOutput.volume()
        self.currentSourceRow = 0
        self.totalTime = '00:00'
        self.cTime = '00:00'
        self.playTable =  "默认列表"
        self.currentTable = "默认列表"
        self.noError = 1
        self.dragPosition = QPoint(0, 0)
        self.allPlaySongs = []
        self.files = []
        self.toPlaySongs = []
        self.lyricDict = {}
        self.info = ''
        self.j = -5
        try:
            with open(Configures.settingFile, 'r') as f:
                self.downloadDir = f.read()
        except:
            self.downloadDir = Configures.musicsDir
        for i in range(0, self.model.rowCount()):
            self.allPlaySongs.append(self.model.record(i).value("paths"))  
        self.manageTable.selectRow(1)
        self.musicTableDisplay.addMusicAction.setVisible(True)
        self.musicTableDisplay.switchToSearchPageAction.setVisible(False)
        self.manageTable.addMusicHereAction.setVisible(True)
        self.manageTable.renameTableAction.setVisible(False)
        self.manageTable.deleteTableAction.setVisible(False)
        self.manageTable.switchToSearchPageAction.setVisible(False)
        self.musicTableDisplay.downloadAction.setVisible(False)
#        self.media_sources_seted(0)
#        self.mediaObject.stop()
        
    def initial_sql(self):
        self.sql = SqlOperate()
        self.sql.createConnection()
        
        self.sql.createTables()
        self.sql.createTable("在线试听")
        self.sql.createTable("默认列表")
        self.sql.createTable("喜欢歌曲")
    
    def initial_phonon(self):
        self.mediaObject = Phonon.MediaObject(self)
        self.audioOutput = Phonon.AudioOutput(Phonon.MusicCategory, self)
        Phonon.createPath(self.mediaObject, self.audioOutput)
        self.mediaObject.setTickInterval(550)        
        self.mediaObject.tick.connect(self.tick)        
        self.mediaObject.stateChanged.connect(self.state_changed)      
        self.mediaObject.currentSourceChanged.connect(self.source_changed)
        self.mediaObject.finished.connect(self.music_finished)
        self.audioOutput.mutedChanged.connect(self.muted_changed)
        self.audioOutput.volumeChanged.connect(self.volume_label_changed)

#创建主界面
    def setup_ui(self):        
        self.setWindowTitle(self.tr('xyPlayer'))
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowIcon(QIcon(":/iconSources/icons/musicface.png"))
#        self.setWindowFlags(Qt.FramelessWindowHint)
#        self.setWindowFlags(Qt.WindowMinMaxButtonsHint)
#        self.setWindowFlags(Qt.WindowStaysOnTopHint)
#        self.setAttribute(Qt.WA_TranslucentBackground)
#        self.resize(420, 670)
        self.setMinimumSize(QSize(400, 580))
        desktop = QApplication.desktop()
        screenRec = desktop.screenGeometry()
        desktopWidth = screenRec.width()
        self.setGeometry((desktopWidth - 400)//2, 40, 400, 620)
#        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Background, QColor(QColor(200, 200, 220)))
        self.setPalette(palette)
        
        self.controlFrame = QFrame(self)
        self.controlFrame.setMinimumSize(QSize(400, 0))
        self.controlFrame.setFrameShape(QFrame.WinPanel)
        self.controlFrame.setFrameShadow(QFrame.Raised)
        self.firstLineLayout = QHBoxLayout(self.controlFrame)
        self.firstLineLayout.setSpacing(0)
        self.firstLineLayout.setMargin(0)
        self.artistButton = QToolButton(clicked = self.show_artist_info)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.artistButton.sizePolicy().hasHeightForWidth())
        self.artistButton.setSizePolicy(sizePolicy)
        self.artistButton.setFixedSize(QSize(85, 85))
        self.artistButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.artistButton.setMouseTracking(False)
        self.artistButton.setContextMenuPolicy(Qt.NoContextMenu)
        icon = QIcon()
        icon.addPixmap(QPixmap(":/iconSources/icons/anonymous.png"), QIcon.Normal, QIcon.Off)
        self.artistButton.setIcon(icon)
        self.artistButton.setIconSize(QSize(82, 82))
        self.firstLineLayout.addWidget(self.artistButton)

        self.musicShowLayout = QHBoxLayout()
        self.musicShowLayout.setSpacing(0)
        self.musicTableButton = QPushButton(clicked = self.show_musictable)
        self.musicTableButton.setFocusPolicy(Qt.NoFocus)
        self.musicTableButton.setText("欢迎使用xyplayer！")
        self.musicTableButton.setFixedHeight(31)
        self.musicTableButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.musicShowLayout.addWidget(self.musicTableButton)
        self.favoriteButton = QToolButton(clicked = self.mark_as_favorite)
        self.favoriteButton.setFixedSize(QSize(22, 31))
        self.favoriteButton.setCursor(QCursor(Qt.PointingHandCursor))

        self.favoriteIcon = QIcon()
        self.favoriteIcon.addPixmap(QPixmap(":/iconSources/icons/favorite.png"), QIcon.Normal, QIcon.Off)
        self.favoriteIcon_no = QIcon()
        self.favoriteIcon_no.addPixmap(QPixmap(":/iconSources/icons/favorite_no.png"), QIcon.Normal, QIcon.Off)
        self.favoriteButton.setIcon(self.favoriteIcon)
        self.favoriteButton.setIconSize(QSize(16, 25))
        self.musicShowLayout.addWidget(self.favoriteButton)

        self.controlLayout = QHBoxLayout()
        self.controlLayout.setSpacing(2)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.controlLayout.addItem(spacerItem)
        
        self.playmodeButton = QToolButton(clicked = self.playmode_changed)
        self.playmodeButton.setFixedSize(QSize(36, 36))
        self.playmodeButton.setCursor(QCursor(Qt.PointingHandCursor))
        icon2 = QIcon()
        icon2.addPixmap(QPixmap(":/iconSources/icons/playmode1.png"), QIcon.Normal, QIcon.Off)
        self.playmodeButton.setIcon(icon2)
        self.playmodeButton.setIconSize(QSize(24, 24))
        self.playmodeButton.setShortcut(QKeySequence("Ctrl + M"))
        self.controlLayout.addWidget(self.playmodeButton)

        self.previousButton = QToolButton()
        self.previousButton.setDefaultAction(self.previousAction)
        self.previousButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.previousButton.setFixedSize(QSize(42, 42))
        self.previousButton.setIconSize(QSize(32, 32))
        self.previousButton.setShortcut(QKeySequence("Ctrl + Left"))
        self.controlLayout.addWidget(self.previousButton)

        self.playButton = QToolButton()
        self.playButton.setDefaultAction(self.playAction)
        self.playButton.setFixedSize(QSize(48, 48))
        self.playButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.playButton.setIconSize(QSize(40, 40))
        self.playButton.setShortcut(QKeySequence("Ctrl + Down"))
        self.controlLayout.addWidget(self.playButton)

        self.nextButton = QToolButton()
        self.nextButton.setDefaultAction(self.nextAction)
        self.nextButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.nextButton.setFixedSize(QSize(42, 42))
        self.nextButton.setIconSize(QSize(32, 32))
        self.nextButton.setShortcut(QKeySequence("Ctrl + Right"))
        self.controlLayout.addWidget(self.nextButton)
        
        self.stopButton = QToolButton()
        self.stopButton.setDefaultAction(self.stopAction)
        self.stopButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.stopButton.setFixedSize(QSize(36, 36))
        self.stopButton.setIconSize(QSize(25, 25))
        self.stopButton.setShortcut(QKeySequence("Ctrl + Up"))
        self.controlLayout.addWidget(self.stopButton)

        self.controlLayout.addItem(spacerItem)

        self.moreButton = QToolButton(self.controlFrame)
        self.moreButton.setFixedSize(30, 30)
        self.moreButton.setCursor(QCursor(Qt.PointingHandCursor))
        icon5 = QIcon()
        icon5.addPixmap(QPixmap(":/iconSources/icons/preference.png"), QIcon.Normal, QIcon.Off)
        self.moreButton.setIcon(icon5)
        self.moreButton.setIconSize(QSize(24, 24))
        self.controlLayout.addWidget(self.moreButton)
        
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setMargin(2)
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.addLayout(self.controlLayout)
        self.verticalLayout.addLayout(self.musicShowLayout)

        self.firstLineLayout.addLayout(self.verticalLayout)
 
        self.searchVolumeFrame = QFrame(self)
        self.searchVolumeFrame.setFrameShape(QFrame.NoFrame)
        self.searchVolumeFrame.setFrameShadow(QFrame.Raised)
        self.searchVolumeFrame.setObjectName("searchVolumeFrame")

        self.searchFrameButton = QToolButton(clicked = self.show_searchframe)
        self.searchFrameButton.setFixedSize(QSize(29, 29))
        self.searchFrameButton.setCursor(QCursor(Qt.PointingHandCursor))
        icon6 = QIcon()
        icon6.addPixmap(QPixmap(":/iconSources/icons/search.png"), QIcon.Normal, QIcon.Off)
        self.searchFrameButton.setIcon(icon6)
        self.searchFrameButton.setIconSize(QSize(20, 20))


        self.downloadButton  = QToolButton(clicked = self.show_downloadpage)
        self.downloadButton.setFixedSize(QSize(29, 29))
        self.downloadButton.setCursor(QCursor(Qt.PointingHandCursor))
        icon7 = QIcon()
        icon7.addPixmap(QPixmap(":/iconSources/icons/download.png"), QIcon.Normal, QIcon.Off)
        self.downloadButton.setIcon(icon7)
        self.downloadButton.setIconSize(QSize(20, 20))

        self.volumeButton = QToolButton(clicked = self.show_vlmslider)
        self.volumeButton.setFixedSize(QSize(26, 27))
        self.volumeButton.setCursor(QCursor(Qt.PointingHandCursor))
        icon7 = QIcon()
        icon7.addPixmap(QPixmap(":/iconSources/icons/volume.png"), QIcon.Normal, QIcon.Off)
        self.volumeButton.setIcon(icon7)
        self.volumeButton.setIconSize(QSize(20, 20))
        
        
        self.volumeSlider = Phonon.VolumeSlider(self)
        self.volumeSlider.setFixedHeight(29)
        self.volumeSlider.setIconSize(QSize(20, 20))
        self.volumeSlider.setAudioOutput(self.audioOutput)
        self.volumeSlider.hide()
        
        self.volumeLabel = QLabel()
        self.volumeLabel.setText("音量:" + self.volumeSlider.toolTip().split(':')[1])
        self.volumeLabel.hide()

        self.seekSlider = QSlider(Qt.Horizontal)
        self.seekSlider.setRange(0, 0)
#        self.seekSlider.setPageStep(2000)

        self.timeLabel = QLabel(self.searchVolumeFrame)
        self.timeLabel.setText(self.tr("00:00/00:00"))
        self.timeLabel.setAlignment(Qt.AlignRight and Qt.AlignVCenter)
        self.timeLabel.setFixedSize(QSize(63, 25))
        
        self.secondLineLayout = QHBoxLayout(self.searchVolumeFrame)
        self.secondLineLayout.setSpacing(1)
        self.secondLineLayout.setMargin(1)
        self.secondLineLayout.addWidget(self.searchFrameButton)
        self.secondLineLayout.addWidget(self.downloadButton)
        self.secondLineLayout.addWidget(self.volumeButton)
        self.secondLineLayout.addWidget(self.volumeSlider)
        self.secondLineLayout.addWidget(self.seekSlider)
        self.secondLineLayout.addWidget(self.timeLabel)
        self.secondLineLayout.addWidget(self.volumeLabel)

        self.manageModel = QSqlTableModel()
        self.manageModel.setTable("tablesManage")
        self.manageModel.setHeaderData(0, Qt.Horizontal, "*所有列表*")
        self.manageModel.select()
        self.manageTable = ManageTableView()
        self.manageTable.initial_view(self.manageModel)
        self.manageTable.setMaximumWidth(82)
        
        self.modelDisplay = TableModel()
        self.modelDisplay.initial_model("默认列表")
        self.musicTableDisplay = TableView()
        self.musicTableDisplay.setModel(self.modelDisplay)
        self.resize_music_table_display()
        
        self.model = TableModel()
        self.model.initial_model("喜欢歌曲")
        
        self.lovedSongs = []
        self.lovedSongs.clear()        
        for i in range(0, self.model.rowCount()):
            self.lovedSongs.append(self.model.record(i).value("title"))        
        self.model.initial_model("默认列表")
        
        self.musicTable = TableView()
        self.musicTable.initial_view(self.model)
       
#        self.textEdit = QTextEdit()
#        self.textEdit.hide()
        
        self.tablesSplitter = QSplitter(Qt.Horizontal, self)
        tablesLayout = QHBoxLayout()
        tablesLayout.addWidget(self.manageTable)
#####################################################################
#        tablesLayout.addWidget(self.musicTable)
#####################################################################
        tablesLayout.addWidget(self.musicTableDisplay)
#        tablesLayout.addWidget(self.textEdit)
        self.tablesSplitter.setLayout(tablesLayout)
        self.tablesSplitter.setOpaqueResize(False)

#搜索页面
        self.searchFrame =SearchFrame()

#下载页面
        self.downloadPage = DownloadPage()

#设置框
        self.settingFrame = SettingFrame()
        
#歌词页面
        self.lyricText = QTextEdit()
        self.document = self.lyricText.document()
        self.lyricText.setAlignment(Qt.AlignHCenter )
        self.lyricText.setReadOnly(True)
        font = QFont()
        font.setFamily("微软雅黑")
        font.setWeight(40)
        font.setPointSize(16)
        self.lyricText.setCurrentFont(font)
        self.lyricText.hide()

#歌手信息
        self.artistName = QLabel("姓名：")
        self.artistName.setFixedHeight(30)
        self.artistBirthday = QLabel("生日：")
        self.artistBirthday.setFixedHeight(30)
        self.artistBirthplace = QLabel("出生地：")
        self.artistBirthplace.setFixedHeight(30)
        self.artistCountry = QLabel("国籍：")
        self.artistCountry.setFixedHeight(30)
        self.artistLanguage = QLabel("语言：")
        self.artistLanguage.setFixedHeight(30)
        self.artistGender = QLabel("性别：")
        self.artistGender.setFixedHeight(30)
        self.artistConstellation = QLabel("星座：")
        self.artistConstellation.setFixedHeight(30)
        self.artistDetail = QTextEdit()
        self.artistDetail.setReadOnly(True)
        font.setFamily("微软雅黑")
        font.setWeight(25)
        font.setPointSize(13)
        self.artistDetail.setFont(font)
        
        artistInfoFrame = QFrame()
        artistInfoLayout = QGridLayout(artistInfoFrame)
        artistInfoLayout.setSpacing(2)
        artistInfoLayout.setMargin(0)
        artistInfoLayout.addWidget(self.artistName, 0, 0, 1, 2)
        artistInfoLayout.addWidget(self.artistBirthday, 1, 0)
        artistInfoLayout.addWidget(self.artistBirthplace, 1, 1)
        artistInfoLayout.addWidget(self.artistCountry, 2, 0)
        artistInfoLayout.addWidget(self.artistLanguage, 2, 1)
        artistInfoLayout.addWidget(self.artistGender, 3, 0)
        artistInfoLayout.addWidget(self.artistConstellation, 3, 1)
        artistInfoLayout.addWidget(self.artistDetail, 4, 0, 2, 2)
        

#堆栈窗口 
        self.stackedWidget = QStackedWidget(self)
        self.stackedWidget.setAutoFillBackground(True)
        palette.setColor(QPalette.Background, QColor(230, 230, 230))
        self.stackedWidget.setPalette(palette)
        self.stackedWidget.addWidget(self.tablesSplitter)
        self.stackedWidget.addWidget(self.searchFrame)
        self.stackedWidget.addWidget(self.downloadPage)
        self.stackedWidget.addWidget(artistInfoFrame)
        self.stackedWidget.addWidget(self.lyricText)

#电源那一行的代码
        self.playerControlWidget = QFrame(self)
        self.playerControlWidget.setAutoFillBackground(True)
        palette.setColor(QPalette.Background, QColor(150, 150, 150))
        self.playerControlWidget.setPalette(palette)
        self.playerControlWidget.setFixedHeight(29)
        self.playerInfoButton = QPushButton("关于", clicked = self.about)
        self.playerInfoButton.setFocusPolicy(Qt.NoFocus)
        self.playerInfoButton.setToolTip('关于播放器')
        self.playerInfoButton.setFixedSize(60, 28)
        self.playerInfoButton.setIcon(QIcon(":/iconSources/icons/info.png"))
        self.playerInfoButton.setIconSize(QSize(20, 20))
        
        self.currentStateLabel = QLabel('<- 播放列表 ->')
        font = QFont()
        font.setBold(True)
        font.setWeight(75)
        self.currentStateLabel.setFont(font)
        
        self.powerButton = QToolButton(clicked = self.close_all)
        self.powerButton.setToolTip('退出')
        self.powerButton.setIcon(QIcon(":/iconSources/icons/shutdown.png"))
        self.powerButton.setIconSize(QSize(25, 25))
        self.powerButton.setFixedSize(28, 28)
        
        self.hideButton = QToolButton(clicked = self.show_mainwindow)
        self.hideButton.setToolTip('最小化到托盘')
        self.hideButton.setIcon(QIcon(":/iconSources/icons/minimum.png"))
        self.hideButton.setIconSize(QSize(25, 25))
        self.hideButton.setFixedSize(28, 28)
        
#        self.simpleModeButton = QToolButton()
#        self.simpleModeButton.setToolTip('精简模式')
#        self.simpleModeButton.setIcon(QIcon(":/iconSources/icons/simpleMode.png"))
#        self.simpleModeButton.setIconSize(QSize(22, 22))
#        self.simpleModeButton.setFixedSize(28, 28)
        
        pcwLayout = QHBoxLayout(self.playerControlWidget)
        pcwLayout.setMargin(1)
        pcwLayout.setSpacing(2)
        pcwLayout.addWidget(self.powerButton)
#        pcwLayout.addWidget(self.simpleModeButton)
        pcwLayout.addWidget(self.hideButton)
        pcwLayout.addItem(spacerItem)
        pcwLayout.addWidget(self.currentStateLabel)
        pcwLayout.addItem(spacerItem)
        pcwLayout.addWidget(self.playerInfoButton)
 
 #歌词标签栏布局
        self.desktopLyricButton = QToolButton(clicked = self.show_desktop_lyric)
        self.desktopLyricButton.setFixedSize(34, 34)
        self.desktopLyricButton.setToolTip("开启桌面歌词")
        self.desktopLyricButton.setIcon(QIcon(":/iconSources/icons/desktopLyric.png"))
        self.desktopLyricButton.setIconSize(QSize(29, 29))
        
        self.lyricOffsetButton = QToolButton(clicked = self.show_lyric_text)
        self.lyricOffsetButton.setFixedSize(34, 34)
        self.lyricOffsetButton.setToolTip("校准歌词")
        self.lyricOffsetButton.setIcon(QIcon(":/iconSources/icons/lyric.png"))
        self.lyricOffsetButton.setIconSize(QSize(29, 29))
        

        self.lyricOffsetSButton = QToolButton(clicked = self.lyric_offset_save)
        self.lyricOffsetSButton.setText('保存数据')
        self.lyricOffsetSButton.setToolTip('保存调整数据')
        
        self.lyricOffsetCombo = QComboBox()
        self.lyricOffsetCombo.insertItem(0, '提前')
        self.lyricOffsetCombo.insertItem(1, '延迟')
        self.lyricOffsetCombo.insertItem(2, '正常')
        self.lyricOffsetCombo.setCurrentIndex(2)
        
        self.lyricOffsetSlider = QSlider(Qt.Horizontal)
        self.lyricOffsetSlider.setPageStep(1)
        self.lyricOffsetSlider.setRange(0, 0)
        
        self.lyricOffsetLabel = QLineEdit("0.0秒")
        self.lyricOffsetLabel.setMaximumWidth(43)
        self.lyricOffsetLabel.setReadOnly(True)
        
        self.lyricOffsetBack = QPushButton(clicked = self.show_lyric_text)
        self.lyricOffsetBack.setText('返回')
        self.lyricOffsetBack.setFixedWidth(45)
        
        self.ADOSWidget = QWidget()
        self.ADOSWidget.hide()
        lyricOffsetLayout = QHBoxLayout(self.ADOSWidget)
        lyricOffsetLayout.setSpacing(2)
        lyricOffsetLayout.setMargin(0)
#        lyricOffsetLayout.addItem(spacerItem)
        lyricOffsetLayout.addWidget(self.lyricOffsetCombo)
        lyricOffsetLayout.addWidget(self.lyricOffsetSlider)
        lyricOffsetLayout.addWidget(self.lyricOffsetLabel)
#        lyricOffsetLayout.addSpacing(5)
#        lyricOffsetLayout.addWidget(self.lyricOffsetAButton)
#        lyricOffsetLayout.addWidget(self.lyricOffsetOButton)
#        lyricOffsetLayout.addSpacing(15)
#        lyricOffsetLayout.addWidget(self.lyricOffsetDButton)
#        lyricOffsetLayout.addItem(spacerItem)
        lyricOffsetLayout.addWidget(self.lyricOffsetSButton)
        lyricOffsetLayout.addWidget(self.lyricOffsetBack)
        
        self.lyricLabel = QLabel("歌词同步显示于此！")
        self.lyricLabel.setFixedHeight(35)
        self.lyricLabel.setAlignment(Qt.AlignCenter)
        self.lyricLabel.setToolTip("歌词显示")
        font1 = QFont()
        font1.setFamily("微软雅黑")
#        font1.setWeight(60)
        font1.setPointSize(12)
        self.lyricLabel.setFont(font1)
        
        self.lyricWidget1 = QWidget()
        lyricLayout1 = QHBoxLayout(self.lyricWidget1)
        lyricLayout1.setSpacing(0)
        lyricLayout1.setMargin(0)
        lyricLayout1.addWidget(self.desktopLyricButton)
        lyricLayout1.addWidget(self.lyricLabel)
#        lyricLayout1.addWidget(self.ADOSWidget)
        lyricLayout1.addWidget(self.lyricOffsetButton)
        
        lyricLayout = QHBoxLayout()
        lyricLayout.addWidget(self.lyricWidget1)
        lyricLayout.addWidget(self.ADOSWidget)
        
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(1)
        self.mainLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.mainLayout.setMargin(2)
        self.mainLayout.addWidget(self.controlFrame)
        self.mainLayout.addWidget(self.searchVolumeFrame)
        self.mainLayout.addWidget(self.stackedWidget)
#        self.mainLayout.addWidget(self.lyricText)
        self.mainLayout.addLayout(lyricLayout)
        self.mainLayout.addWidget(self.playerControlWidget)
#桌面歌词标签
        self.desktopLyric = DesktopLyric()
        
#创建托盘图标
        icon = QIcon()
        icon.addPixmap(QPixmap(":/iconSources/icons/musicface.png"), QIcon.Normal, QIcon.Off)
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(icon)

        trayMenu = QMenu()
        trayMenu.addAction(self.showMainWindowAction)
        trayMenu.addAction(self.showDesktopLyricAction)
        trayMenu.addSeparator()
        trayMenu.addAction(self.previousAction)
        trayMenu.addAction(self.playAction)
        trayMenu.addAction(self.nextAction)
        trayMenu.addAction(self.stopAction)
        trayMenu.addSeparator()
#        trayMenu.addAction(self.aboutAction)
        trayMenu.addAction(self.exitAction)
        self.trayIcon.setContextMenu(trayMenu)
        self.trayIcon.show()
        
        self.artistButton.setToolTip("歌手信息")
        self.musicTableButton.setToolTip("打开播放列表")
        self.playmodeButton.setToolTip("顺序循环")
        self.searchFrameButton.setToolTip("在线搜索")
        self.timeLabel.setToolTip('当前播放时间/总时长')
        self.volumeButton.setToolTip("音量")
        self.downloadButton.setToolTip('下载管理')       
        self.favoriteButton.setToolTip('喜欢')
    
    def create_connects(self):      
        self.musicTableDisplay.installEventFilter(self)
        self.volumeSlider.installEventFilter(self)
        
        self.lyricOffsetCombo.currentIndexChanged.connect(self.lyric_offset_type)
        self.lyricOffsetSlider.valueChanged.connect(self.lyric_offset_changed)
        self.desktopLyric.hideDesktopLyricSignal.connect(self.show_desktop_lyric)
        
        self.seekSlider.valueChanged.connect(self.slider_value_changed)
        self.seekSlider.sliderPressed.connect(self.slider_pressed)
        self.seekSlider.sliderReleased.connect(self.seek)
#        self.seekSlider.valueChanged.connect(self.seek)

        self.musicTableDisplay.addMusicAction.triggered.connect(self.add_files)
        self.musicTableDisplay.markSelectedAsFavoriteAction.triggered.connect(self.mark_selected_as_favorite)
        self.musicTableDisplay.deleteSelectedsAction.triggered.connect(self.delete_selecteds)
        self.musicTableDisplay.clearTheListAction.triggered.connect(self.music_table_cleared)
        self.musicTableDisplay.downloadAction.triggered.connect(self.online_list_song_download)
        self.musicTableDisplay.switchToSearchPageAction.triggered.connect(self.show_searchframe)
        self.musicTableDisplay.doubleClicked.connect(self.music_table_clicked)

        self.manageTable.addTableAction.triggered.connect(self.add_tables)
        self.manageTable.addMusicHereAction.triggered.connect(self.add_files)
        self.manageTable.renameTableAction.triggered.connect(self.rename_tables)
        self.manageTable.deleteTableAction.triggered.connect(self.delete_tables)
        self.manageTable.switchToSearchPageAction.triggered.connect(self.show_searchframe)
        self.manageTable.pressed.connect(self.manage_table_clicked)
        
        self.downloadPage.listen_online_signal.connect(self.begin_to_listen)
        self.downloadPage.listen_local_signal.connect(self.listen_local)
        
        self.searchFrame.switch_to_online_list.connect(self.switch_to_online_list)
        self.searchFrame.listen_online_signal.connect(self.begin_to_listen)
        self.searchFrame.listen_local_signal.connect(self.listen_local)
        self.searchFrame.add_to_download_signal.connect(self.add_to_download)
        self.searchFrame.add_bunch_to_list_succeed.connect(self.fresh_online_list)
        
        self.moreButton.clicked.connect(self.show_setting_frame)
        self.settingFrame.downloadDirChanged.connect(self.set_new_downloaddir)
    
    def fresh_online_list(self):
        if self.playTable == '在线试听':
            self.model.initial_model('在线试听')
            self.musicTable.initial_view(self.model)
    
    def show_setting_frame(self):
        x = self.geometry().x() + self.geometry().width()
        y = self.geometry().y()
        self.settingFrame.set_place(x, y)
        self.settingFrame.show()
    
    def set_new_downloaddir(self, newDir):
        self.downloadDir = newDir
    
    def show_desktop_lyric(self):
        if self.desktopLyric.isHidden():
            self.desktopLyric.show()
#            self.desktopLyric.move(QPoint((self.desktopWidth - 800)//2, self.desktopHeight - 170))
            self.showDesktopLyricAction.setText('关闭桌面歌词')
            self.desktopLyricButton.setToolTip('关闭桌面歌词')
        else:
            self.desktopLyric.hide()
            self.showDesktopLyricAction.setText('开启桌面歌词')
            self.desktopLyricButton.setToolTip('开启桌面歌词')
    
    def lyric_offset_type(self, index):
        self.lyricOffsetIndex = index
        self.lyricOffset = 0
        self.lyricOffsetSlider.setValue(0)
        self.lyricOffsetLabel.setText('0.0秒')
        if index == 0 or index == 1:
            self.lyricOffsetSlider.setRange(0, 50)        
        else:
            self.lyricOffsetSlider.setRange(0, 0)
    
    def lyric_offset_changed(self, value):
        if self.lyricOffsetIndex == 0:
            self.lyricOffset = (0 - value*100)
        elif self.lyricOffsetIndex == 1:
            self.lyricOffset = value*100
        self.lyricOffsetLabel.setText('%s秒'%(value/10))
        self.check_lyric_offset()
    
    def lyric_offset_save(self):
        with open(self.lrcPath, 'r') as f:
           originalText = f.read() 
        m = re.search('offset\=',originalText,re.MULTILINE)
        if m:
            pos = m.end()
            lyricOffsetTemp = int(originalText[pos:])
            print('Player.py lyric_offset_save %s'%lyricOffsetTemp)
            if lyricOffsetTemp!= self.lyricOffset:
                newText = originalText[:pos] + '%s'%self.lyricOffset
                with open(self.lrcPath, 'w+') as f:
                    f.write(newText)
        else:
            with open(self.lrcPath, 'a+') as f:
                f.write('\noffset=%s'%self.lyricOffset)
        self.lyricOffsetSButton.setFocus()
            
    def check_lyric_offset(self):
        if len(self.lyricDict):
            if self.lyricOffset > 0:
                self.lyricLabel.setToolTip("已延迟%s秒"%(self.lyricOffset/1000))
            elif self.lyricOffset < 0:
                self.lyricLabel.setToolTip("已提前%s秒"%(abs(self.lyricOffset/1000)))
            else:
                self.lyricLabel.setToolTip("正常")
        else:
            self.lyricLabel.setToolTip("歌词显示")
    
    def muted_changed(self, isMuted):
        if isMuted:
            self.volumeLabel.setText("静音")
            self.volumeButton.setToolTip("静音")
            self.volumeButton.setIcon(QIcon(":/iconSources/icons/volumeMuted.png"))
        else:
            self.volumeLabel.setText("音量调节")
            self.volumeButton.setIcon(QIcon(":/iconSources/icons/volume.png"))

    def volume_label_changed(self):
        self.volumeLabel.setText("音量:" + self.volumeSlider.toolTip().split(':')[1])
        self.volumeButton.setToolTip("音量:" + self.volumeSlider.toolTip().split(':')[1])
    
    def slider_pressed(self):
        self.mediaObject.tick.disconnect(self.tick)
    
    def seek(self):
        if self.mediaObject.state() == Phonon.StoppedState:
            self.mediaObject.play()
            self.mediaObject.seek(self.seekSlider.value())
        else:
            self.mediaObject.seek(self.seekSlider.value())
            self.mediaObject.play()
        self.mediaObject.tick.connect(self.tick)

        
#删除选中项 
    def delete_selecteds(self):
        selections = self.musicTableDisplay.selectionModel()
        selecteds = selections.selectedIndexes()
        cnt = len(selecteds)//4        
        if not cnt:
            return
        selectedsSpan = selecteds[-1].row() - selecteds[0].row()  + 1
        cnt1 = 0
        cnt2 = 0
        for index in selecteds:
            if  index.row() < self.currentSourceRow and index.column() == 0:
                cnt1 += 1
            if index.row() == self.currentSourceRow and self.playTable == self.currentTable:
                cnt2 = 1
        ok = QMessageBox.warning(self, "删除选中项", "有%s首歌曲将被移出列表!"%cnt, QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
        if ok == QMessageBox.Yes:
            self.setCursor(QCursor(Qt.BusyCursor))
            if not cnt2:               
                self.modelDisplay.delete_selecteds(selecteds)
                if self.playTable == self.currentTable:
                    self.currentSourceRow  -=  cnt1
                    self.model.initial_model(self.playTable)
                    self.musicTable.selectRow(self.currentSourceRow)
                    self.musicTableDisplay.selectRow(self.currentSourceRow)
            else:
                currentMusic = self.modelDisplay.record(self.currentSourceRow).value("title")
                ok = QMessageBox.warning(self, "删除当前歌曲", "当前歌曲: %s 将会被删除!\n您是否要删除这首歌曲？"%currentMusic, QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
                if ok  == QMessageBox.Yes:
                    if cnt ==  self.modelDisplay.rowCount():
                        self.ui_initial()
                        self.modelDisplay.delete_selecteds(selecteds)
                        self.model.initial_model(self.playTable)
                    elif cnt == selectedsSpan and selecteds[-1].row() == self.modelDisplay.rowCount() - 1:
                        self.modelDisplay.delete_selecteds(selecteds)            
                        self.model.initial_model(self.playTable)     
                        self.media_sources_seted(0)
                        self.musicTableDisplay.selectRow(0)
                    else:     
                        firstDeletedRow = selecteds[0].row()
                        self.modelDisplay.delete_selecteds(selecteds)
                        self.model.initial_model(self.playTable)
                        self.media_sources_seted(firstDeletedRow)
                        self.musicTableDisplay.selectRow(firstDeletedRow)
                elif ok  == QMessageBox.No:
                    for index in selecteds:
                        row = index.row()
                        if index.column() == 0 and self.modelDisplay.record(row).value("paths")!=  self.modelDisplay.record(self.currentSourceRow).value("paths"):
                            self.modelDisplay.removeRow(row)
                    self.modelDisplay.submitAll()
                    self.model.initial_model(self.playTable)  
                    self.currentSourceRow  -=  cnt1
                    self.musicTableDisplay.selectRow(self.currentSourceRow)
                    self.musicTable.selectRow(self.currentSourceRow)
            self.setCursor(QCursor(Qt.ArrowCursor))
            if self.currentTable == "喜欢歌曲":
                self.lovedSongs.clear()
                for i in range(0, self.modelDisplay.rowCount()):
                    self.lovedSongs.append(self.modelDisplay.record(i).value("title"))
            if self.currentTable == self.playTable:
                self.allPlaySongs.clear()
                for i in range(0, self.modelDisplay.rowCount()):
                    self.allPlaySongs.append(self.modelDisplay.record(i).value("paths"))                
            self.check_favorite()

#标记选中项为喜欢
    def mark_selected_as_favorite(self):
        self.setCursor(QCursor(Qt.BusyCursor))
        selections = self.musicTableDisplay.selectionModel()
        selecteds = selections.selectedIndexes()
        marked = []
        marked.clear()
        for index in selecteds:
            row = index.row()
            record = self.modelDisplay.record(row)
            if index.column() == 0:
                if record.value("title") not in self.lovedSongs and os.path.exists(record.value("paths")):
                    marked.append(record.value("title"))
                    self.lovedSongs.append(record.value("title"))
                    self.model.initial_model("喜欢歌曲")
                    self.model.insertRecord(self.model.rowCount(), record)
                    self.model.submitAll()
        self.model.initial_model(self.playTable)
        self.musicTable.initial_view(self.model)
        self.check_favorite()
        
        if len(marked):
            markedStr = '\n'.join(marked)
            QMessageBox.information(self, "完成标记", "标记完成以下歌曲：\n%s，其他歌曲不存在无法标记喜欢！"%markedStr)
        self.setCursor(QCursor(Qt.ArrowCursor))
            
    def mark_as_favorite(self):   
        if self.playTable == "喜欢歌曲" or self.musicTableButton.text() == "欢迎使用xyPlayer！":
            return
        record = self.model.record(self.currentSourceRow)
        path = record.value("paths")
        title = record.value("title")
        if self.playTable == "在线试听":
            musicName = title + '.mp3'
            musicPath = os.path.join(self.downloadDir, musicName)
            musicPathO = os.path.join(Configures.musicsDir, musicName)
            if not os.path.exists(musicPath) and not os.path.exists(musicPathO):
                QMessageBox.information(self, '提示', '请先下载该歌曲再添加喜欢！')
                return
            if os.path.exists(musicPath):
                record.setValue("paths", musicPath)
            else:
                record.setValue("paths", musicPathO)
        elif not os.path.exists(path):
            QMessageBox.information(self, "提示", "路径'"+"%s"%path+"'无效，无法标记喜欢！")
            return
        if title in self.lovedSongs:
            self.model.setTable("喜欢歌曲")
            self.model.select()
            self.model.removeRow(self.lovedSongs.index(title))
            self.model.submitAll()
            self.lovedSongs.remove(title)
            self.model.initial_model(self.playTable)
            self.musicTable.initial_view(self.model)
            self.favoriteButton.setIcon(self.favoriteIcon_no)
            self.favoriteButton.setToolTip("标记为喜欢")
        else:
            self.model.initial_model("喜欢歌曲")
            self.model.insertRecord(self.model.rowCount(), record)
            self.model.submitAll()
            self.model.initial_model(self.playTable)
            self.musicTable.initial_view(self.model)
            self.lovedSongs.append(title)
            self.favoriteButton.setIcon(self.favoriteIcon)
            self.favoriteButton.setToolTip("取消喜欢标记")
        if self.currentTable == "喜欢歌曲":
            self.modelDisplay.initial_model(self.currentTable)
            self.musicTableDisplay.setModel(self.modelDisplay)
            self.resize_music_table_display()
    
    def check_favorite(self):
        if self.model.record(self.currentSourceRow).value("title") in self.lovedSongs:
            self.favoriteButton.setIcon(self.favoriteIcon)
            self.favoriteButton.setToolTip("取消喜欢标记")
        else:
            self.favoriteButton.setIcon(self.favoriteIcon_no)
            self.favoriteButton.setToolTip("标记为喜欢")
        if self.playTable == "喜欢歌曲":
            self.favoriteButton.setToolTip("喜欢")
 
    def show_musictable(self):
        self.switch_page(0, "<- 播放列表 ->")
        for i in range(0, self.manageModel.rowCount()):
            if self.manageModel.record(i).value("tableName") == self.playTable:
                k = i
                break
        self.manage_table_clicked(self.manageModel.index(k, 0))
        self.resize_music_table_display()

    def show_searchframe(self):
        self.switch_page(1, "<- 在线搜索 ->")
    
    def show_downloadpage(self):
        self.switch_page(2, "<- 下载管理 ->")
        if not self.downloadPage.downloadModel.rowCount():
            return
        tips = self.downloadPage.downloadModel.record(self.downloadPage.downloadTable.currentIndex().row()).value("title")
        self.downloadPage.downloadTable.setToolTip(tips)
    
    def switch_page(self, index, pageInfo):
        self.stackedWidget.setCurrentIndex(index)
        self.currentStateLabel.setText(pageInfo)    
        self.lyricWidget1.show()
        self.ADOSWidget.hide()
    
    def show_artist_info(self):
        if self.info:
            if self.stackedWidget.currentIndex() == 4:
                self.show_lyric_text()
            t = self.stackedWidget.currentIndex()
            if t!= 3:
                self.t = t
                self.stackedWidget.setCurrentIndex(3)
                self.currentStateLabel.setText("<- 歌手信息 ->")
            else:
                if self.t == 0:
                    self.show_musictable()
                elif self.t == 1:
                    self.show_searchframe()
                else:
                    self.show_downloadpage()
    
    def show_lyric_text(self):
        if len(self.lyricDict) and  self.lrcPath!= Configures.URLERROR and self.lrcPath!= None:
            if self.stackedWidget.currentIndex() == 3:
                self.show_artist_info()
            t = self.stackedWidget.currentIndex()
            if t!= 4:
                self.t = t
                self.stackedWidget.setCurrentIndex(4)
                self.currentStateLabel.setText("<- 全部歌词 ->")
                self.lyricWidget1.hide()
                self.ADOSWidget.show()
            else:
                if self.t == 0:
                    self.show_musictable()
                elif self.t == 1:
                    self.show_searchframe()
                else:
                    self.show_downloadpage()
                self.lyricWidget1.show()
                self.ADOSWidget.hide()
#            
    def listen_local(self, file):
        self.manage_table_clicked(self.manageModel.index(1, 0))
        self.playTable = "默认列表"
        musics = file.split('->')
        self.add_and_choose_play(musics)
        self.mediaObject.play()
    
    def begin_to_listen(self, title, album, songLink):
        if not songLink:
            QMessageBox.critical(self, '错误', '链接为空，无法播放！')
            return
        self.modelDisplay.initial_model("在线试听")
        self.musicTableDisplay.setModel(self.modelDisplay)
        self.resize_music_table_display()
        k = -1
        for i in range(0, self.modelDisplay.rowCount()):
            if self.modelDisplay.record(i).value("paths") == songLink:
                k = i
                break
        if k == -1:
            musicId = songLink.split('~')[1]
            lrcName = title + '.lrc'
            lrcPath = os.path.join(Configures.lrcsDir, lrcName)
            if os.path.exists(lrcPath):
                os.remove(lrcPath)
            SearchOnline.get_lrc_path(title, musicId)
            self.modelDisplay.add_record(title, '未知', album, songLink)
            self.model.initial_model("在线试听")
            self.musicTable.initial_view(self.model)
            self.music_table_clicked(self.modelDisplay.index(self.modelDisplay.rowCount()-1, 0))
        else:
            self.model.initial_model("在线试听")
            self.musicTable.initial_view(self.model)
            if self.playTable == "在线试听" and self.currentSourceRow == k:
                return
            self.music_table_clicked(self.modelDisplay.index(k, 0))
    
    def add_to_download(self):
#        songInfos = json.loads(songInfos)
        for songInfoList in self.searchFrame.toBeEmited:
#            songInfoList = songInfo.split('->')
            songLink = songInfoList[0]
            musicPath = songInfoList[1]
            title = songInfoList[2]
            album = songInfoList[3]
            musicId = songInfoList[4]
            self.downloadPage.add_to_downloadtable(songLink, musicPath, title, album, musicId)
    
    def online_list_song_download(self):
        selections = self.musicTableDisplay.selectionModel()
        selecteds = selections.selectedIndexes()
        isExistsSongs = []
        isErrorSongs = []
        for index in selecteds:
            if index.column() == 0:
                row = index.row()
                songLinkwrap = self.modelDisplay.record(row).value("paths").split('~')
                title = self.modelDisplay.record(row).value("title")
                try:
                    songLink = songLinkwrap[0]
                    musicId = songLinkwrap[1]
                except:
                    isErrorSongs.append(title)
                    continue
                album = self.modelDisplay.record(row).value("album")
                musicName = title + '.mp3'
                musicPath = os.path.join(self.downloadDir, musicName)
                musicPathO = os.path.join(Configures.musicsDir, musicName)
                if  os.path.exists(musicPath) or os.path.exists(musicPathO):
                    isExistsSongs.append(title)
                    continue
                self.downloadPage.add_to_downloadtable(songLink, musicPath, title, album, musicId)
        if len(isErrorSongs):
            errorSongs = '\n'.join(isErrorSongs)
            QMessageBox.information(self, "提示", "以下歌曲链接出错，无法下载！\n%s"%errorSongs)
        if len(isExistsSongs):
            existsSongs = '\n'.join(isExistsSongs)
            QMessageBox.information(self, "提示", "以下歌曲已在下载目录中不再进行下载，您可以在不联网的情况下点击在线列表播放！\n%s"%existsSongs)
    
    def show_vlmslider(self):
        if self.volumeSlider.isHidden():
            self.volumeSlider.show()
            self.seekSlider.hide()
            self.volumeButton.hide()
            self.timeLabel.hide()
            self.volumeLabel.show()

    def playmode_changed(self):
        self.playmodeIndex += 1
        if self.playmodeIndex > 3:
            self.playmodeIndex = 1
        icon = QIcon()
        if self.playmodeIndex == 1:
            self.playmodeButton.setToolTip("顺序循环")
            icon.addPixmap(QPixmap(":/iconSources/icons/playmode1.png"), QIcon.Normal, QIcon.Off)
        elif self.playmodeIndex == 2:
            self.playmodeButton.setToolTip("随机播放")
            icon.addPixmap(QPixmap(":/iconSources/icons/playmode2.png"), QIcon.Normal, QIcon.Off)
        elif self.playmodeIndex == 3:
            self.playmodeButton.setToolTip("单曲循环")
            icon.addPixmap(QPixmap(":/iconSources/icons/playmode3.png"), QIcon.Normal, QIcon.Off)
        
        self.playmodeButton.setIcon(icon)
        self.playmodeButton.setIconSize(QSize(24, 24))

    def create_actions(self):
        self.showMainWindowAction = QAction(
             QIcon(":/iconSources/icons/showMainWindow.png"), "隐藏主界面", 
                self,  triggered = self.show_mainwindow )
        
        self.showDesktopLyricAction = QAction(
             QIcon(":/iconSources/icons/desktopLyric.png"), "开启桌面歌词", 
                self,  triggered = self.show_desktop_lyric )
                
        self.stopAction = QAction(
                QIcon(":/iconSources/icons/stop.png"), "停止",
                self, enabled = True,
                triggered = self.stop_music)
        
        self.nextAction = QAction(
        QIcon(":/iconSources/icons/next.png"), "下一首", 
                self, enabled = True,
                triggered = self.next_song)
        
        self.playAction = QAction(
        QIcon(":/iconSources/icons/musiclogo.png"), "播放/暂停",
                self, enabled = True,
                triggered = self.play_music)
        
        self.previousAction = QAction(
        QIcon(":/iconSources/icons/previous.png"), "上一首", 
                self, enabled = True,
                triggered = self.previous_song)
        
        self.exitAction = QAction(
                QIcon(":/iconSources/icons/shutdown.png"), "退出", 
                self,  triggered = self.close_all)

        self.aboutAction = QAction(
                QIcon(":/iconSources/icons/info.png"), "关于", 
                self,triggered = self.about)

    def show_mainwindow(self):
        if self.isHidden():
#            self.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.show()
            self.showMainWindowAction.setText('隐藏主界面')
        else:
            self.hide()
            self.showMainWindowAction.setText('显示主界面')
    
    def add_files(self):
        self.files = QFileDialog.getOpenFileNames(self, "选择音乐文件",
                self.downloadDir, self.tr("*.mp3"))
        self.adding()

    def add_only(self, files):
        if not len(files):
            return
        addCount = len(files)
        pathsInTable = []
        newAddedTitles = []
        pathsInTable.clear()
        for i in range(0, self.modelDisplay.rowCount()):
            pathsInTable.append(self.modelDisplay.record(i).value("paths"))
        newAddedCount = 0
        t1 = time.time()
        for item in files:
            if item not in pathsInTable:
                self.setCursor(QCursor(Qt.BusyCursor))
                title, album, totalTime =  read_music_info(item)
                if self.currentTable == "喜欢歌曲":
                    self.lovedSongs.append(title)
                if self.currentTable == self.playTable:
                    self.allPlaySongs.append(item)
                t3 = time.time()
                self.modelDisplay.add_record(title, totalTime, album, item)      
                t4 = time.time()
                print('Player.py Player.add_only t4-t3 = %s'%(t4-t3))
                newAddedTitles.append((title, item))
        t2 = time.time()
        print('Player.py Player.add_only t2-t1 = %s'%(t2-t1))
        newAddedCount = len(newAddedTitles)
        repeatCount = addCount-newAddedCount     
        try:
            index = pathsInTable.index(files[0])
        except:
            index = len(pathsInTable)
        self.musicTableDisplay.selectRow(index)
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.check_favorite()
        if len(newAddedTitles):
            thread = DownloadLrcThread(newAddedTitles)
            thread.setDaemon(True)
            thread.setName("downloadLrc")
            thread.start()
        return addCount, newAddedCount, repeatCount, index
        
    def add_and_choose_play(self, files):
        addCount, newAddedCount, repeatCount, k = self.add_only(files)
        if self.playTable == self.currentTable:
            self.model.initial_model(self.currentTable)    
            self.musicTable.selectRow(k)
            self.media_sources_seted(k)
        return addCount, newAddedCount, repeatCount

    def adding(self):  
        if not self.files:
            return
        addCount, newAddedCount, repeatCount = self.add_and_choose_play(self.files)
        QMessageBox.information(self, "添加完成", "您选择了%s首歌曲！\n新添加了%s首歌曲，有%s首歌曲已在列表中不被添加！"%(addCount, newAddedCount, repeatCount))
        
    def tick(self):
        if not self.musicTable.currentIndex():
            self.musicTable.selectRow(self.currentSourceRow)
        self.seekSlider.setRange(0, self.mediaObject.totalTime())
#        self.musicTableButton.setText('%s'%self.mediaObject.totalTime())
        currentTime = self.mediaObject.currentTime()
        self.syc_lyric(currentTime)
        self.seekSlider.setValue(currentTime)
        minutes = (currentTime / 60000) % 60
        seconds = (currentTime / 1000) % 60
        self.cTime = QTime(0, minutes, seconds ).toString('mm:ss')
        if self.totalTime == '未知':
            totalTimeValue = self.mediaObject.totalTime()/1000
            hours = totalTimeValue/3600
            minutes = (totalTimeValue%3600)/60
            seconds = (totalTimeValue)%3600%60
            if totalTimeValue < 3600:
                self.totalTime = QTime(0, minutes, seconds).toString('mm:ss')
            else:
                self.totalTime = QTime(hours, minutes, seconds).toString('hh:mm:ss')
            self.model.setData(self.model.index(self.currentSourceRow, 1), self.totalTime)
            self.model.submitAll()
            self.musicTable.selectRow(self.currentSourceRow)
            if self.currentTable == self.playTable:
                self.modelDisplay.initial_model(self.playTable)
                self.musicTableDisplay.setModel(self.modelDisplay)
                self.resize_music_table_display()
                self.musicTableDisplay.selectRow(self.currentSourceRow)
        self.timeLabel.setText(self.cTime + '/' + self.totalTime)
    
    def syc_lyric(self, currentTime):
        if len(self.lyricDict) and self.document.blockCount():
            t = sorted(self.lyricDict.keys())
            if currentTime-self.lyricOffset <= t[1]:
                self.lyricLabel.setText('歌词同步显示于此！')
                return
            for i in range(1, len(t)-1):
                if t[i] < currentTime-self.lyricOffset and t[i + 1] > currentTime-self.lyricOffset and i!= self.j:
                    if self.lyricDict[t[i]]:
                        self.lyricLabel.setText(self.lyricDict[t[i]])
                        self.jump_to_line(i-2)
                    else:
                        self.lyricLabel.setText("音乐伴奏... ...")
                    self.j = i
                    break
            if currentTime > t[-1] and self.j != len(t) - 1:
                if self.lyricDict[t[-1]]:
                    self.lyricLabel.setText(self.lyricDict[t[-1]])
                    self.jump_to_line(self.document.blockCount() - 1)
                else:
                    self.lyricLabel.setText("音乐伴奏... ...")
                self.j = len(t) - 1
            if not self.desktopLyric.isHidden():
                self.desktopLyric.setText(self.lyricLabel.text())
                
    def jump_to_line(self, line):
        block = self.document.findBlockByNumber(line)
        pos = block.position()
        print("jumpToLine_%s"%pos)
        cur = self.lyricText.textCursor()
        cur.setPosition(pos, QTextCursor.MoveAnchor)
        cur.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        self.lyricText.setTextCursor(cur)
#        if self.j > 4:
#            self.lyricText.scrollContentsBy(0, -1)
    
    
    def state_changed(self, newState, oldState):
        self.manageTable.setToolTip('当前播放列表：\n    %s'%self.playTable)
        self.musicTableDisplay.setToolTip('当前播放列表：\n    %s\n'%self.playTable + '当前曲目：\n  %s'%self.model.record(self.currentSourceRow).value("title"))        
        if not self.model.rowCount():
            return        
        if not self.musicTable.currentIndex:
            self.musicTable.selectRow(self.currentSourceRow)
        if newState == Phonon.ErrorState:
            self.noError = 0
            sourceDispose =  Phonon.MediaSource("file://" + Configures.INSTALLPATH + "/" + "error.ogg")
            self.mediaObject.setCurrentSource(sourceDispose)
            self.mediaObject.play()
            self.show()
            if self.mediaObject.errorType() == Phonon.FatalError:
                QMessageBox.warning(self, "致命错误", self.mediaObject.errorString())
            else:
                QMessageBox.warning(self, "错误", self.mediaObject.errorString())
        elif newState == Phonon.PlayingState:
            self.playAction.setIcon(QIcon(":/iconSources/icons/pause.png"))
            self.playAction.setToolTip("暂停")
            self.setWindowTitle("xyPlayer        当前状态： 正在播放...")
        elif newState == Phonon.StoppedState:
            self.playAction.setIcon(QIcon(":/iconSources/icons/play.png"))
            self.playAction.setToolTip("播放")
            self.setWindowTitle("xyPlayer        当前状态： 已停止!")
        elif newState == Phonon.PausedState:
            self.playAction.setIcon(QIcon(":/iconSources/icons/play.png"))
#            self.playAction.setIconSize(QSize(40, 40))
            self.playAction.setToolTip("播放")
            self.setWindowTitle("xyPlayer        当前状态： 已暂停!")

    def source_changed(self):  
        if not self.model.rowCount():
            return
        self.update_parameters()
        if self.playTable == "在线试听" or os.path.exists(self.model.record(self.currentSourceRow).value("paths")) :
            self.update_artist_info()
            self.update_lyric()
        else:
            self.lyricLabel.setText('歌词同步显示于此！')
            self.lyricDict.clear()
            icon = QIcon()
            icon.addPixmap(QPixmap(":/iconSources/icons/anonymous.png"), QIcon.Normal, QIcon.Off)
            self.artistButton.setIcon(icon)
            self.info=''
        self.update_vlmtags()
        self.update_near_played_queue()
        self.check_favorite()
    
    def update_parameters(self):
        self.playTable = self.model.tableName()
        self.currentSourceRow = self.musicTable.currentIndex().row()
        self.totalTime = self.model.record(self.currentSourceRow).value("length")
        title = self.model.record(self.currentSourceRow).value("title")
        self.musicTableButton.setText(title.replace('&', '/'))
    
    def update_near_played_queue(self):
        currentSourcePath = self.model.record(self.currentSourceRow).value("paths")
        if currentSourcePath not in self.toPlaySongs:
            self.toPlaySongs.append(currentSourcePath)
        while len(self.toPlaySongs) > self.model.rowCount()*3//5:
            del self.toPlaySongs[0]
            
    def update_vlmtags(self):
        try:
            volumeToolTip = self.volumeSlider.toolTip().split(':')[1]
            self.volumeLabel.setText("音量:" + volumeToolTip)
            self.volumeButton.setToolTip("音量:" + volumeToolTip)
        except:
            self.volumeLabel.setText("静音")
            self.volumeButton.setToolTip("静音")
            
    def update_artist_info(self):
        title = self.model.record(self.currentSourceRow).value("title")
        icon = QIcon()
        try:
            artist = title.split('._.')[0].strip()
            infoPath = SearchOnline.get_artist_info_path(artist)
            if infoPath:
                with open(infoPath, 'r+') as f:
                    self.info = f.read()
                infoList = json.loads(self.info)
                name = infoList['name']
                birthday = infoList['birthday']
                if not birthday:
                    birthday = '保密'
                birthplace = infoList['birthplace']
                if not birthplace:
                    birthplace = '保密'
                country = infoList['country']
                if not country:
                    country = '全球'
                language = infoList['language']
                gender = infoList['gender']
                if not gender:
                    gender = '男/女'
                constellation = infoList['constellation']
                if not constellation:
                    constellation = '神马座'
                info = infoList['info']
                infos = info.split('<br>')
                self.artistName.setText('姓名：' + name)
                self.artistBirthday.setText('生日：' + birthday)
                self.artistBirthplace.setText('出生地：' + birthplace)
                self.artistCountry.setText('国籍：' + country)
                self.artistLanguage.setText('语言：' + language)
                self.artistGender.setText('性别：' + gender)
                self.artistConstellation.setText('星座：' + constellation)
                self.artistDetail.clear()
                for line in infos:
                    self.artistDetail.append(line)
                cur = self.artistDetail.textCursor()
                cur.setPosition(0, QTextCursor.MoveAnchor)
                self.artistDetail.setTextCursor(cur)
            else:
                self.info = ''
            imagePath = SearchOnline.get_artist_image_path(artist)
            if imagePath:
                icon.addPixmap(QPixmap(imagePath), QIcon.Normal, QIcon.Off)
            else:
                icon.addPixmap(QPixmap(":/iconSources/icons/anonymous.png"), QIcon.Normal, QIcon.Off)
        except:
            self.info = ''
            icon.addPixmap(QPixmap(":/iconSources/icons/anonymous.png"), QIcon.Normal, QIcon.Off)
        self.artistButton.setIcon(icon)
        self.artistButton.setIconSize(QSize(82, 82))
    
    def update_lyric(self):
        self.lyricLabel.setToolTip("正常")
        self.lyricOffset = 0     
        musicPath = self.model.record(self.currentSourceRow).value("paths")
        title = self.model.record(self.currentSourceRow).value("title")
        if musicPath[0:4] == 'http':
            musicId = musicPath.split('~')[1]
        else:
            musicId = 0
        self.lrcPath = SearchOnline.is_lrc_path_exists(title)
        if not self.lrcPath:
            self.lrcPath = SearchOnline.get_lrc_path(title, musicId)
        with open(self.lrcPath, 'r+') as f:
            lyric = f.read()
        if lyric == 'Configures.URLERROR':
            self.lrcPath = SearchOnline.get_lrc_path(title, musicId)
            with open(self.lrcPath, 'r+') as f:
                lyric = f.read()
            if lyric == 'Configures.URLERROR':
                self.lyricLabel.setText("网络出错，无法搜索歌词！")
                self.desktopLyric.setText("网络出错，无法搜索歌词！")
                self.lyricDict.clear()
        elif lyric == 'None':
            self.lyricLabel.setText("搜索不到匹配歌词！")
            self.desktopLyric.setText("搜索不到匹配歌词！")
            self.lyricDict.clear()
        else:
            self.lyricLabel.setText("歌词同步显示于此！")
            self.lyricOffset, self.lyricDict = parse_lrc(lyric)
            self.check_lyric_offset()
            if self.lyricOffset < 0:
                k = 0
                self.lyricOffsetSlider.setRange(0, 50)
            elif self.lyricOffset > 0:
                k = 1
                self.lyricOffsetSlider.setRange(0, 50)
            else:
                k = 2
                self.lyricOffsetSlider.setRange(0, 0)
            lyricOffsetTemp = self.lyricOffset
            self.lyricOffsetIndex = k
            self.lyricOffsetCombo.setCurrentIndex(k)
            self.lyricOffset = lyricOffsetTemp
            self.lyricOffsetSlider.setValue(abs(self.lyricOffset)//100)
            self.lyricOffsetLabel.setText('%s秒'%round(abs(self.lyricOffset)/1000, 1))
            self.lyricText.clear()
            self.lyricText.setAlignment(Qt.AlignHCenter)
            for k in sorted(self.lyricDict.keys()):
                self.lyricText.append(self.lyricDict[k])  
            self.lyricDict[-1] = '歌词同步显示于此！'
            cur = self.lyricText.textCursor()
            cur.setPosition(0, QTextCursor.MoveAnchor)
            self.lyricText.setTextCursor(cur)
        if not self.lyricDict:
            self.show_musictable()
        
    def music_finished(self):
        if self.noError:
            self.next_song()
        else:
            self.noError = 1

    def manage_table_clicked(self, index):
        tableName = self.manageModel.data(index)
        self.manageTable.selectRow(index.row())
        if index.row() == 0:
            self.musicTableDisplay.addMusicAction.setVisible(False)
            self.musicTableDisplay.switchToSearchPageAction.setVisible(True)
            self.musicTableDisplay.downloadAction.setVisible(True)
            self.manageTable.addMusicHereAction.setVisible(False)
            self.manageTable.renameTableAction.setVisible(False)
            self.manageTable.deleteTableAction.setVisible(False)
            self.manageTable.switchToSearchPageAction.setVisible(True)
        elif index.row() == 1 or index.row() == 2:
            self.musicTableDisplay.downloadAction.setVisible(False)
            self.musicTableDisplay.addMusicAction.setVisible(True)
            self.musicTableDisplay.switchToSearchPageAction.setVisible(False)
            self.manageTable.addMusicHereAction.setVisible(True)
            self.manageTable.renameTableAction.setVisible(False)
            self.manageTable.deleteTableAction.setVisible(False)
            self.manageTable.switchToSearchPageAction.setVisible(False)
        else:
            self.musicTableDisplay.downloadAction.setVisible(False)
            self.musicTableDisplay.addMusicAction.setVisible(True)
            self.musicTableDisplay.switchToSearchPageAction.setVisible(False)
            self.manageTable.addMusicHereAction.setVisible(True)
            self.manageTable.renameTableAction.setVisible(True)
            self.manageTable.deleteTableAction.setVisible(True)
            self.manageTable.switchToSearchPageAction.setVisible(False)
        if index.row() == 0 or index.row() == 2:
            self.musicTableDisplay.markSelectedAsFavoriteAction.setVisible(False)
        else:
            self.musicTableDisplay.markSelectedAsFavoriteAction.setVisible(True)
        self.currentTable = tableName
        self.modelDisplay.initial_model(tableName)
        self.musicTableDisplay.setModel(self.modelDisplay)
        self.resize_music_table_display()
        if tableName == self.playTable:
            self.musicTableDisplay.selectRow(self.currentSourceRow)

    def add_tables(self):
        existTables = []
        for i in range(0, self.manageModel.rowCount()):
            existTables.append(self.manageModel.record(i).value("tableName"))
        j = 1
        while True:            
            textOld = "新建列表%s"%j
            if textOld not in existTables:
                break
            j += 1            
        text, ok = QInputDialog.getText(self, "添加列表", "请输入列表名：", QLineEdit.Normal, textOld)
        if ok:
            if text:
                if text in existTables:
                    QMessageBox.critical(self, "注意！", "列表'%s'已存在！\n请重新添加！"%text)
                    return
                if text in ['tablesManage', 'downloadTable']:
                    QMessageBox.critical(self, "注意！", "列表名'tablesManage'与'downloadTable'为系统所用，请选择其他名称!")
                    return
                self.manageTable.add_tables(self.manageModel, "%s"%text)
            else:
                self.manageTable.add_tables(self.manageModel, "%s"%textOld)
                text = textOld
            self.sql.createTable(text)
            self.manageModel.setTable("tablesManage")
            self.manageModel.setHeaderData(0, Qt.Horizontal, "所有列表")
            self.manageModel.select()
            self.manage_table_clicked(self.manageModel.index(self.manageModel.rowCount() - 1, 0))
            self.manageTable.selectRow(self.manageModel.rowCount() - 1)

    def rename_tables(self):
        selections = self.manageTable.selectionModel()
        selecteds = selections.selectedIndexes()
        selectedsRow = selecteds[0].row()
        oldName = self.manageModel.data(self.manageModel.index(selectedsRow, 0))
        newName, ok = QInputDialog.getText(self, "修改列表名", "请输入新列表名：", QLineEdit.Normal, oldName)
        if ok:
            if newName:
                for i in range(0, self.manageModel.rowCount()):
                    if newName == self.manageModel.record(i).value("tableName"):
                        QMessageBox.critical(self, "注意！", "列表'%s'已存在！\n请重新修改！"%newName)
                        return
                if newName in ['tablesManage', 'downloadTable']:
                    QMessageBox.critical(self, "注意！", "列表名'tablesManage'与'downloadTable'为系统所用，请选择其他名称!")
                    return
                q = QSqlQuery()
                q.exec_("alter table %s rename to %s"%(oldName, newName))
                q.exec_("commit")
                self.manageModel.setData(self.manageModel.index(selectedsRow, 0), newName)
                self.manageModel.submitAll()
                self.manageModel.setTable("tablesmanage")
                self.manageModel.setHeaderData(0, Qt.Horizontal, "所有列表")
                self.manageModel.select()
                if oldName == self.playTable:
                    self.playTable = newName
                self.manage_table_clicked(selecteds[0])
                self.manageTable.selectRow(selectedsRow)


    def delete_tables(self):    
        selections = self.manageTable.selectionModel()
        selecteds = selections.selectedIndexes()
        tableDeleted = self.manageModel.data(self.manageModel.index(selecteds[0].row(), 0))
        ok = QMessageBox.warning(self, "删除列表", "列表'%s'将被删除，表中记录将被全部移除！\n您是否继续？"%tableDeleted, QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
        if ok == QMessageBox.Yes:
            q = QSqlQuery()
            q.exec_("drop table %s"%tableDeleted)
            q.exec_("commit")
            self.manageModel.removeRow(selecteds[0].row())
            self.manageModel.submitAll()
            if self.playTable!= tableDeleted:
                for i in range(0, self.manageModel.rowCount()):
                    if self.manageModel.record(i).value("tableName") == self.playTable:
                        k = i
                        break
                self.manage_table_clicked(self.manageModel.index(k, 0))
            else:
                self.ui_initial()
                self.modelDisplay.initial_model("默认列表")
                self.musicTableDisplay.setModel(self.modelDisplay)
                self.resize_music_table_display()
                self.manage_table_clicked(self.manageModel.index(0, 0))

    def music_table_clicked(self, index):
        self.musicTableDisplay.selectRow(index.row())
#        with open(Configures.settingFile, 'r') as f:
#            self.downloadDir = f.read()
        if self.modelDisplay.tableName() == self.playTable:
            if  index.row()!= self.currentSourceRow or self.mediaObject.state() == Phonon.StoppedState:
                self.media_sources_seted(index.row())
            elif self.mediaObject.state()  == Phonon.PausedState:
                self.mediaObject.play()
            elif self.mediaObject.state() == Phonon.PlayingState:
                self.mediaObject.pause()
        else:
            self.playTable = self.modelDisplay.tableName()
            self.model.initial_model(self.modelDisplay.tableName())
            self.musicTable.initial_view(self.model)
            self.media_sources_seted(index.row())
            self.allPlaySongs = []
            for i in range(0, self.model.rowCount()):
                self.allPlaySongs.append(self.model.record(i).value("paths"))  

    def music_table_cleared(self):
        if not self.modelDisplay.rowCount():
            return
        ok = QMessageBox.warning(self, "清空列表", "当前列表的所有歌曲(包括当前播放歌曲)都将被移除，请确认!", QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
        if ok  == QMessageBox.Yes:
            currentIndex = self.manageTable.currentIndex()
            q = QSqlQuery()
            q.exec_("drop table %s"%self.currentTable)
            q.exec_("commit")
            q.exec_("create table %s (title varchar(50), length varchar(10), album varchar(40), paths varchar(65))"%self.currentTable)
            q.exec_("commit")
            self.manage_table_clicked(currentIndex)
            if self.playTable == self.currentTable:
                self.model.initial_model(self.playTable)
                self.ui_initial()
            if self.currentTable == "喜欢歌曲":
                self.lovedSongs.clear()
            if self.currentTable == self.playTable:
                self.allPlaySongs.clear()
            self.favoriteButton.setIcon(self.favoriteIcon)
            self.favoriteButton.setToolTip("喜欢")

    def switch_to_online_list(self):
        self.stackedWidget.setCurrentIndex(0)
        self.manage_table_clicked(self.manageModel.index(0, 0))
        self.resize_music_table_display()

    def ui_initial(self):
        self.mediaObject.stop()
        self.mediaObject.clear()
        print('Player.py ui_initial success here')
        self.seekSlider.setRange(0, 0)
        self.musicTableButton.setText("欢迎使用xyPlayer!")
        self.totalTime = '00:00'
        self.setWindowTitle("xyPlayer")
        self.lyricLabel.setText('歌词同步显示于此！')
        self.playButton.setIcon(QIcon(":/iconSources/icons/musiclogo.png"))
        icon = QIcon()
        icon.addPixmap(QPixmap(":/iconSources/icons/anonymous.png"), QIcon.Normal, QIcon.Off)
        self.artistButton.setIcon(icon)
        self.artistButton.setIconSize(QSize(82, 82))
        
    def slider_value_changed(self, value):
        minutes = (value / 60000) % 60
        seconds = (value / 1000) % 60
        cTime = QTime(0, minutes, seconds ).toString('mm:ss')
        self.timeLabel.setText(cTime + '/' + self.totalTime)
        self.syc_lyric(value)
        
    def media_sources_seted(self, row):    
        if not self.model.rowCount():
            return 
        self.stop_music()
#        self.mediaObject.clearQueue()
        self.musicTable.selectRow(row)
        if self.playTable == self.modelDisplay.tableName():
            self.musicTableDisplay.selectRow(row)
        
        sourcePath = self.model.record(row).value("paths")
        title = self.model.record(row).value("title")
#        if sourcePath[0:4] == 'http':
        
        musicName = title + '.mp3'
        musicPathO = os.path.join(Configures.musicsDir, musicName)
        musicPath = os.path.join(self.downloadDir, musicName)
        if  os.path.exists(musicPath):
            sourcePath = musicPath
        elif os.path.exists(musicPathO):
            sourcePath = musicPathO
        elif self.playTable == "在线试听":
            isErrorHappen = self.is_url_error()
            if isErrorHappen:
                self.noError = 0
                sourceDispose =  Phonon.MediaSource("file://" + Configures.INSTALLPATH + "/" + "error.ogg")
                self.mediaObject.setCurrentSource(sourceDispose)
                self.mediaObject.play()
                if self.isHidden():
                    self.show()
#                    if errorType == Configures.URLERROR:
                QMessageBox.critical(self, "错误", "联网出错！\n"+"无法联网播放歌曲'"+"%s"%self.model.record(row).value("title")+"'！\n您最好在网络畅通时下载该曲目！")
            else:
                sourcePath = sourcePath.split('~')[0].strip()
                sourceDispose =  Phonon.MediaSource(QUrl(sourcePath))
                self.mediaObject.setCurrentSource(sourceDispose)
                self.mediaObject.play()
            return
        else:
            if os.path.exists(self.model.record(row).value('paths')):
                sourcePath=self.model.record(row).value('paths')
            else:
                self.noError = 0
                sourceDispose =  Phonon.MediaSource('file://' + Configures.INSTALLPATH + "/"+"error.ogg")
                self.mediaObject.setCurrentSource(sourceDispose)
                self.mediaObject.play()
                self.show()
                QMessageBox.information(self, "提示", "路径'"+"%s"%self.model.record(row).value("paths")+"'无效，请尝试重新下载并添加对应歌曲！")
                return
        sourcePath = 'file://' + sourcePath
        sourceDispose =  Phonon.MediaSource(QUrl(sourcePath))
        self.mediaObject.setCurrentSource(sourceDispose)
        self.mediaObject.play()

    def is_url_error(self):
        t1 = time.time()
        try:
            conn = HTTPConnection('www.baidu.com')
            conn.request('GET', '/')
            res = conn.getresponse()
            print('Player.py Player.is_url_error %s'%(time.time() - t1))
            if res.status == 200 and res.reason == 'OK':
                return False
            return True
        except gaierror:
            return True

    def play_music(self):
        if self.mediaObject.state() == Phonon.PlayingState :
            self.mediaObject.pause()
        else:
            self.mediaObject.play()
    
    def stop_music(self):
        self.mediaObject.stop()
        self.seekSlider.setValue(0)
        self.syc_lyric(-0.5)

    def previous_song(self):
        if not self.model.rowCount():
            return
        self.stop_music()
        self.mediaObject.clearQueue()
        if self.playmodeIndex == 1:
            if self.currentSourceRow - 1 >= 0:
                self.media_sources_seted(self.currentSourceRow - 1)
            else:
                self.media_sources_seted(self.model.rowCount() - 1)
        if self.playmodeIndex == 2:
            listTemp = []
            for item in self.allPlaySongs:
                if item not in self.toPlaySongs:
                    listTemp.append(item)
            nextSongPath = random.sample(listTemp, 1)[0]
            nextRow = self.allPlaySongs.index(nextSongPath)
            self.media_sources_seted(nextRow)
        if self.playmodeIndex == 3:
            self.media_sources_seted(self.currentSourceRow)
        if self.playTable == self.modelDisplay.tableName():
            self.musicTableDisplay.selectRow(self.musicTable.currentIndex().row())

    def next_song(self):
        if not self.model.rowCount():
            return
        self.stop_music()
        self.mediaObject.clearQueue()
        if self.playmodeIndex == 1:
            if  self.currentSourceRow + 1 < self.model.rowCount():
                self.media_sources_seted(self.currentSourceRow + 1)
            else:
                self.media_sources_seted(0)
        if self.playmodeIndex == 2:
            listTemp = []
            for item in self.allPlaySongs:
                if item not in self.toPlaySongs:
                    listTemp.append(item)
            nextSongPath = random.sample(listTemp, 1)[0]
            nextRow = self.allPlaySongs.index(nextSongPath)
            self.media_sources_seted(nextRow)
        if self.playmodeIndex == 3:
            self.media_sources_seted(self.currentSourceRow)
        if self.playTable == self.modelDisplay.tableName():
            self.musicTableDisplay.selectRow(self.musicTable.currentIndex().row())

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()
    
    def closeEvent(self, event):
        self.show()
        self.settingFrame.close()
        if threading.active_count() == 1:
            ok = QMessageBox.question(self, '退出', '您确定退出？',QMessageBox.Cancel|QMessageBox.Ok, QMessageBox.Cancel )
            if ok == QMessageBox.Ok:
                self.trayIcon.hide()
                self.downloadPage.downloadModel.submitAll()
                event.accept()
            else:
                event.ignore()
        else:
            ok = QMessageBox.question(self, '退出', '当前有下载任务正在进行，您是否要挂起全部下载任务并退出？',QMessageBox.Cancel|QMessageBox.Ok, QMessageBox.Cancel )
            if ok == QMessageBox.Ok:
                self.hide()
                self.trayIcon.hide()
                for t in threading.enumerate():
                    if t.name == 'downloadLrc':
                        t.stop()
                    if t!= threading.main_thread():
                        t.pause()
                        t.join()
                self.downloadPage.downloadModel.submitAll()
                event.accept()
            else:
                event.ignore()
            
    def eventFilter(self, target, event):
        if target == self.volumeSlider:
            if event.type() == QEvent.Leave:
                self.volumeSlider.hide()
                self.volumeLabel.hide()
                self.seekSlider.show()
                self.volumeButton.show()
                self.timeLabel.show()
        elif target == self.musicTableDisplay:
            if event.type() == QEvent.Resize:
                self.resize_music_table_display()
        return False
    
    def resize_music_table_display(self):
        width = self.musicTableDisplay.width()
        if width > 800:
            widthTemp = (width - 70)/3
            self.musicTableDisplay.showColumn(3)
            self.musicTableDisplay.showColumn(2)
            self.musicTableDisplay.setColumnWidth(0, widthTemp)
            self.musicTableDisplay.setColumnWidth(1, 70)
            self.musicTableDisplay.setColumnWidth(2, widthTemp)
            self.musicTableDisplay.setColumnWidth(3, widthTemp)
            self.musicTableDisplay.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter)
        elif  400 < width < 800:
            widthTemp = (width - 70)/2
            self.musicTableDisplay.hideColumn(3)
            self.musicTableDisplay.showColumn(2)
            self.musicTableDisplay.setColumnWidth(0, widthTemp)
            self.musicTableDisplay.setColumnWidth(1, 70)
            self.musicTableDisplay.setColumnWidth(2, widthTemp)
            self.musicTableDisplay.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter)
        else:
            self.musicTableDisplay.setColumnWidth(0, width - 80)
            self.musicTableDisplay.setColumnWidth(1, 70)
            self.musicTableDisplay.hideColumn(2)
            self.musicTableDisplay.hideColumn(3)
            self.musicTableDisplay.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        
    def about(self):
        author = '作  者：Zheng-Yejian'
        email = '邮  箱：1035766515@qq.com'
        address = '项目网址：https://github.com/Zheng-Yejian/xyplayer'
        specification = "说  明：本播放器是我的毕业设计成果，旨在设计一个能实现基本播放以及在线搜索播放媒体资源功能的音乐播放器。由于本人为初学者，程序中大部分代码是边学边用的，因此可能还存在许多实现方法和编程规范方面的问题及一些bug，希望大家通过邮箱与我交流。另外，如果有人愿意协助将程序打包，请与我联系，不胜感谢。"   
        thanks = '鸣谢：这里要感谢github上项目kwplayer的作者LiuLang，我正是从他的项目中获取的开发灵感和动力，而且也从中学到了许多东西。该项目的网址为https://github.com/LiuLang/kwplayer。'
        QMessageBox.information(self, "关于xyPlayer","%s\n\n%s\n\n%s\n\n%s\n\n%s"%(author, email, address, specification, thanks))

    def close_all(self):
        self.close()
    










