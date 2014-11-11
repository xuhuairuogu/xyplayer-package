import time, os, threading
from PyQt4.QtGui import (QApplication, QWidget, QIcon, QCursor, QMessageBox,QHBoxLayout, 
        QPushButton, QSpacerItem, QSizePolicy, QVBoxLayout, QDesktopServices, QPalette, QLineEdit,
        QToolButton, QComboBox, QLabel, QDialog, QFileDialog, QFont, QMenu, QAction)
from PyQt4.QtCore import Qt, pyqtSignal, QEvent, QTimer, QPoint, QUrl, QSize
from PyQt4 import QtSql
from xyplayer.mytables import DownloadTable, DownloadModel, MyDelegate, SearchTable, TableModel
from xyplayer.mythreads import DownloadThread, DownloadLrcThread
from xyplayer.urldispose import SearchOnline
from xyplayer.configure import Configures

class DownloadPage(QWidget):
    listen_online_signal = pyqtSignal(str, str, str)
    listen_local_signal = pyqtSignal(str)
    def __init__(self, parent = None):
        super(DownloadPage, self).__init__(parent)
        self.setup_ui()
        self.create_connects()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_datas)
        
    def setup_ui(self):
        self.openDir = QPushButton("下载目录")
        self.openDir.setFocusPolicy(Qt.NoFocus)
        self.openDir.setIcon(QIcon(":/iconSources/icons/openDir.png"))
        self.netSpeedInfo = QLabel("当前网速：0.0 kB/s")
        self.netSpeedInfo.setAlignment(Qt.AlignRight and Qt.AlignVCenter)
        self.downloadModel = DownloadModel()
        self.downloadModel.initial_model()
        self.downloadTable = DownloadTable()
        self.downloadTable.initial_view(self.downloadModel)
        self.downloadTable.selectRow(0)
        self.myDelegate = MyDelegate()
        self.downloadTable.setItemDelegate(self.myDelegate)
        
        spacerItem  =  QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        firstLayout = QHBoxLayout()
        firstLayout.addWidget(self.openDir)
        firstLayout.addItem(spacerItem)
        firstLayout.addWidget(self.netSpeedInfo)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setMargin(2)
        mainLayout.setSpacing(1)
        mainLayout.addWidget(self.downloadTable)
        mainLayout.addLayout(firstLayout)
        
    def create_connects(self):
        self.downloadTable.installEventFilter(self)

        self.openDir.clicked.connect(self.open_downloaddir)
        self.downloadTable.playAction.triggered.connect(self.play_music)
        self.downloadTable.startDownloadAction.triggered.connect(self.start_download)
        self.downloadTable.startAllAction.triggered.connect(self.start_all)
        self.downloadTable.pauseDownloadAction.triggered.connect(self.pause_download)
        self.downloadTable.stopDownloadAction.triggered.connect(self.stop_download)
        self.downloadTable.pauseAllAction.triggered.connect(self.pause_all)
        self.downloadTable.removeRowsAction.triggered.connect(self.remove_these_rows)
        self.downloadTable.clearTableAction.triggered.connect(self.clear_table)
        
        self.downloadTable.clicked.connect(self.show_title)
        self.downloadTable.doubleClicked.connect(self.begin_to_listen)
        self.downloadTable.customContextMenuRequested.connect(self.music_table_menu)
    
    def show_title(self, index):
        tips = self.downloadModel.record(index.row()).value("title")
        self.downloadTable.setToolTip(tips)
    
    def music_table_menu(self, pos):
        pos  += QPoint(20, 33)
        self.downloadTable.listMenu.exec_(self.mapToGlobal(pos))
    
    def play_music(self):
        if not self.downloadModel.rowCount():
            return
        selections = self.downloadTable.selectionModel()
        selecteds = selections.selectedIndexes()
        valid = []
        for index in selecteds:
            if index.column() == 0:
                state = self.downloadModel.record(index.row()).value("remain")
                musicPath = self.downloadModel.record(index.row()).value("musicPath")
                if state == "已完成" and os.path.exists(musicPath):
                    valid.append(musicPath)
        cnt = len(valid)
        if cnt:
            musics = '->'.join(valid)
            self.listen_local_signal.emit(musics)
            QMessageBox.information(self, "提示", "已添加%s首歌曲到默认列表，其他歌曲未完成下载，建议您在线播放（双击即可）！"%cnt)
        else:
            QMessageBox.information(self, "提示", "选中歌曲均未完成下载，建议您在线播放（双击即可）！")
            
    def begin_to_listen(self, index):
        musicPath = self.downloadModel.record(index.row()).value("musicPath")
        if self.downloadModel.record(index.row()).value("remain") != "已完成":
            ok = QMessageBox.question(self, '注意', '下载未完成，您是否要在线试听？', QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
            if ok == QMessageBox.Yes:
                title = self.downloadModel.record(index.row()).value("title")
                album = self.downloadModel.record(index.row()).value("album")
                musicId = self.downloadModel.record(index.row()).value("musicId")
                songLink = self.downloadModel.record(index.row()).value("songLink")
                songLinkwrap = songLink + '~' + '~' + musicId
                self.listen_online_signal.emit(title, album, songLinkwrap)
        elif not os.path.exists(musicPath):
            ok = QMessageBox.warning(self, '注意', '歌曲不存在，您是否要重新下载？', QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
            if ok == QMessageBox.Yes:
                self.start_one(index.row())
        else:
            self.listen_local_signal.emit(musicPath)
    
    def add_to_downloadtable(self, songLink, musicPath, title, album, musicId):
        for t in threading.enumerate():
            if t.name == musicPath:
                return
        k = -1
        for i in range(self.downloadModel.rowCount()):
            if musicPath == self.downloadModel.record(i).value("musicPath"):
                k = i
                break
        if k != -1:
            self.downloadTable.selectRow(k)
            self.start_download()
        else:
            self.downloadModel.add_record(title, 0, '未知', '等待', album, songLink, musicPath, musicId)
            row = self.downloadModel.rowCount()-1
            self.downloadTable.selectRow(row)
            downloadThread1 = DownloadThread(self.downloadModel, row)
            downloadThread1.setDaemon(True)
            downloadThread1.setName(musicPath)
            downloadThread1.start()
            
            lrcName = title + '.lrc'
            lrcPath = os.path.join(Configures.lrcsDir, lrcName)
            if os.path.exists(lrcPath):
                os.remove(lrcPath)
            path_item_temp = songLink + '~' + musicId
            list_temp = [(title, path_item_temp)]
            thread = DownloadLrcThread(list_temp)
            thread.setDaemon(True)
            thread.setName(musicPath)
            thread.start()
            
            if not self.timer.isActive():
                self.timer.start(700)
    
    def update_datas(self):
        totalSpeed = 0
        for i in range(self.downloadModel.rowCount()):
            temp = float(self.downloadModel.record(i).value("netSpeed"))
            totalSpeed  += temp
        totalSpeed = round(totalSpeed, 2)
        self.netSpeedInfo.setText('当前网速：%s kB/s'%totalSpeed)
        i = 0
        for t in threading.enumerate():
            if t.name == "downloadLrc" or t.name == "volumeThread" or t == threading.main_thread():
                continue
            i  += 1
        if i == 0:
            self.netSpeedInfo.setText('当前网速：0.0 kB/s')
            row = self.downloadTable.currentIndex().row()
            self.downloadModel.submitAll()
            self.downloadTable.selectRow(row)
            self.timer.stop()
    
    def open_downloaddir(self):
        with open(Configures.settingFile, 'r') as f:
            downloadDir = f.read()
        QDesktopServices.openUrl(QUrl('file://'+downloadDir))
    
    def start_download(self):
        selections = self.downloadTable.selectionModel()
        selecteds = selections.selectedIndexes()
        for index in selecteds:
            if index.column() == 0:
                row = index.row()
                self.start_one(row)
    
    def start_all(self):
        for i in range(self.downloadModel.rowCount()):
#            if self.downloadModel.data(self.downloadModel.index(i, 3)) in ["已取消", "已暂停"]:
            self.start_one(i)
    
    def start_one(self, row):
        if not self.downloadModel.rowCount():
            return
        state = self.downloadModel.data(self.downloadModel.index(row, 3))
        musicPath = self.downloadModel.data(self.downloadModel.index(row, 6))
#        tempfile = musicPath + '.temp'
        if state in ["已取消", "已暂停", '等待'] or not os.path.exists(self.downloadModel.data(self.downloadModel.index(row, 6))):
            for t in threading.enumerate():
                if t.name == musicPath:
                    return
            downloadThread1 = DownloadThread(self.downloadModel, row)
            downloadThread1.setDaemon(True)
            downloadThread1.setName(self.downloadModel.data(self.downloadModel.index(row, 6)))
            downloadThread1.start()
            if not self.timer.isActive():
                self.timer.start(700)
            
    def pause_download(self):
        selections = self.downloadTable.selectionModel()
        selecteds = selections.selectedIndexes()
        if not len(selecteds):
            return
        for index in selecteds:
            if index.column() == 0:
                row = index.row()
                downloadState = self.downloadModel.record(row).value("remain")
                if downloadState not in ["已完成", "已取消", "已暂停"]:
                    musicPath = self.downloadModel.record(row).value("musicPath")
                    for t in threading.enumerate():
                        if t.name == musicPath:
                            t.pause()
                            break
    
    def stop_download(self):
        selections = self.downloadTable.selectionModel()
        selecteds = selections.selectedIndexes()
        if not len(selecteds):
            return
        for index in selecteds:
            if index.column() == 0:
                row = index.row()
                downloadState = self.downloadModel.record(row).value("remain")
                if downloadState not in ["已完成", "已取消"]:
                    musicPath = self.downloadModel.record(row).value("musicPath")
                    tempfileName = musicPath + '.temp'
                    if os.path.exists(tempfileName):
                        os.remove(tempfileName)
                    self.downloadModel.setData(self.downloadModel.index(row, 3), "已取消")
                    self.downloadModel.setData(self.downloadModel.index(row, 1), 0)
                    for t in threading.enumerate():
                        if t.name == musicPath:
                            t.stop()
                            break
        self.downloadModel.submitAll()
        self.downloadTable.selectRow(selecteds[0].row())

    def pause_all(self):
        if threading.active_count() == 1:
            return
#        ok = QMessageBox.question(self, '注意', '所有正在下载任务将被暂停，您是否继续？', QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
#        if ok == QMessageBox.Yes:
        for t in threading.enumerate():
            if t.name == "downloadLrc" or t.name == "volumeThread" or t == threading.main_thread():
                continue
            t.pause()
    
#    def stopAll(self):
#        if threading.active_count() == 1:
#            return
#        ok = QMessageBox.question(self, '注意', '所有正在下载任务将被取消，您是否继续？', QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
#        if ok == QMessageBox.Yes:
#            for t in threading.enumerate():
#                if t != threading.main_thread():
#                    t.stop()
    
    def remove_these_rows(self):
        if not self.downloadModel.rowCount():
            return
        selections = self.downloadTable.selectionModel()
        selecteds = selections.selectedIndexes()
        if not len(selecteds):
            return
        ok = QMessageBox.warning(self, '注意', '您确定要移除选中项？', QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
        if ok == QMessageBox.Yes:
            self.setCursor(QCursor(Qt.BusyCursor))
            self.downloadModel.delete_selecteds(selecteds)
            self.setCursor(QCursor(Qt.ArrowCursor))
            
    def clear_table(self):
        if not self.downloadModel.rowCount():
            return
        ok = QMessageBox.warning(self, '注意', '当前列表将被清空，当前下载也将被取消！\n您是否继续？', QMessageBox.No|QMessageBox.Yes, QMessageBox.No)
        if ok == QMessageBox.Yes:
            self.setCursor(QCursor(Qt.BusyCursor))
            self.netSpeedInfo.setText('当前网速：0.0 kB/s')
            for t in threading.enumerate():
                if t != threading.main_thread():
                    t.stop()
#            os.system("rm -f *.temp")
            self.timer.stop()
            q = QtSql.QSqlQuery()
            q.exec_("drop table downloadTable")
            q.exec_("commit")
            q.exec_("create table downloadTable (title varchar(50), progress varchar(20), size varchar(20), remain varchar(20), album varchar(20), songLink varchar(30), musicPath varchar(30),netSpeed varchar(30),musicId varchar(10))")
            q.exec_("commit")
            self.downloadModel.initial_model()
            self.downloadTable.initial_view(self.downloadModel)
            self.setCursor(QCursor(Qt.ArrowCursor))
        
    def eventFilter(self, target, event):
        if target == self.downloadTable:
            if event.type() == QEvent.Resize:
                self.resize_downloadtable()
            if threading.active_count() == 1:
#                self.downloadTable.setSelectionMode(QAbstractItemView.ExtendedSelection)     
                self.downloadTable.removeRowsAction.setVisible(True)
            else:
                self.downloadTable.removeRowsAction.setVisible(False)
#                self.downloadTable.setSelectionMode(QAbstractItemView.SingleSelection)
        return False
        
    def resize_downloadtable(self):
        width = self.downloadTable.width()
        self.downloadTable.setColumnWidth(0, width/3)
        self.downloadTable.setColumnWidth(1, width/3)
        self.downloadTable.setColumnWidth(2, width/6)
        self.downloadTable.setColumnWidth(3, width/6)


        
class SearchBox(QWidget):
    def __init__(self, parent = None):
        super(SearchBox, self).__init__(parent) 
        self.setFixedHeight(30)
        
        self.lineEdit = QLineEdit()                
        self.lineEdit.setFixedHeight(29)
        self.lineEdit.setToolTip("输入搜索关键词")
        self.lineEdit.setFocusPolicy(Qt.ClickFocus)
        
        self.searchButton = QToolButton()
        self.searchButton.setText("搜索")
        self.searchButton.setFixedHeight(30)
        self.searchButton.setToolTip("点击搜索")
        self.searchButton.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.resetButton = QToolButton()
        self.resetButton.setIcon(QIcon(":/iconSources/icons/reset.png"))
        self.resetButton.setIconSize(QSize(24, 24))
        self.resetButton.setFixedSize(27, 27)
        self.resetButton.setToolTip("重置搜索")
        self.resetButton.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.clearButton = QToolButton()
        self.searchComboBox = QComboBox()
        self.searchComboBox.setToolTip("选择搜索类型")
        musicIcon = QIcon(":/iconSources/icons/music.png")
        artistIcon = QIcon(":/iconSources/icons/artist.png")
        albumIcon = QIcon(":/iconSources/icons/album.png")       
        self.searchComboBox.setIconSize(QSize(20,20))
        self.searchComboBox.insertItem(0, musicIcon, "歌曲")
        self.searchComboBox.insertItem(1, artistIcon, "歌手")
        self.searchComboBox.insertItem(2, albumIcon, "专辑")
        self.searchComboBox.setFixedSize(78, 27)
        self.searchComboBox.setCursor(Qt.PointingHandCursor)
        
        searchIcon = QIcon(":/iconSources/icons/delete.png")
        self.clearButton.setFixedSize(27, 27)
        self.clearButton.setIcon(searchIcon)
        self.clearButton.setIconSize(QSize(18, 18))
        self.clearButton.setAutoRaise(True)
        self.clearButton.setToolTip("清空搜索栏")
        self.clearButton.setCursor(Qt.PointingHandCursor)
        self.clearButton.hide()
        
        searchLayout = QHBoxLayout()
        searchLayout.addWidget(self.searchComboBox)
        searchLayout.addStretch()
        searchLayout.addWidget(self.clearButton)
        searchLayout.setMargin(1)
        searchLayout.setSpacing(0)
        searchLayout.setContentsMargins(0, 0, 0, 0)
        self.lineEdit.setLayout(searchLayout)
        self.lineEdit.setTextMargins(self.searchComboBox.width(), 0, self.clearButton.width(), 0)
        
        mainLayout = QHBoxLayout(self)
        mainLayout.setMargin(0)
        mainLayout.setSpacing(1)
        mainLayout.addWidget(self.resetButton)
        mainLayout.addWidget(self.lineEdit)
        mainLayout.addWidget(self.searchButton)

        #self.connect(self.clearButton, SIGNAL("clicked()"), self.lineEdit.clear)
        self.clearButton.clicked.connect(self.lineEdit.clear)
        self.lineEdit.textChanged.connect(self.clrbutton_show)
        
    def clrbutton_show(self):
        if self.lineEdit.text():
            self.clearButton.show()
        else:
            self.clearButton.hide()

class SearchFrame(QWidget):
    switch_to_online_list = pyqtSignal()
    add_bunch_to_list_succeed = pyqtSignal()
    listen_online_signal = pyqtSignal(str, str, str)
    listen_local_signal = pyqtSignal(str)
    add_to_download_signal = pyqtSignal()
    def  __init__(self, parent = None):
        super(SearchFrame, self).__init__(parent)
        self.setup_ui()
        self.reset_search()
        self.create_connects()
    
    def setup_ui(self):
        self.searchTable = SearchTable()
        self.searchBox = SearchBox()      
        
        self.previousPageButton = QToolButton()
        self.previousPageButton.setFixedSize(40, 31)
        icon0  =  QIcon(":/iconSources/icons/previousPage.png")
        self.previousPageButton.setIcon(icon0)
        self.previousPageButton.setIconSize(QSize(25, 25))
        self.previousPageButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.previousPageButton.setToolTip('上一页')
        
        self.nextPageButton = QToolButton()
        self.nextPageButton.setFixedSize(40, 31)
        icon1  =  QIcon(":/iconSources/icons/nextPage.png")
        self.nextPageButton.setIcon(icon1)
        self.nextPageButton.setIconSize(QSize(25, 25))
        self.nextPageButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.nextPageButton.setToolTip('下一页')
        
        self.jumpNum = QLineEdit('0')
        self.jumpNum.setFixedWidth(39)
        self.jumpNum.setAlignment(Qt.AlignRight)
        
        self.pageNum = QLabel("/ 0")
        self.pageNum.setFixedHeight(35)
        self.pageNum.setFixedWidth(35)
        self.pageNum.setAlignment(Qt.AlignCenter )
        self.pageNum.setToolTip('当前页码/总页数')
        
        self.controlWidget = QWidget()
        controlLayout = QHBoxLayout(self.controlWidget)
        controlLayout.setMargin(0)
        controlLayout.setSpacing(4)
        spacerItem  =  QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        controlLayout.addItem(spacerItem)
        controlLayout.addWidget(self.previousPageButton)
        controlLayout.addWidget(self.jumpNum)
        controlLayout.addWidget(self.pageNum)
        controlLayout.addWidget(self.nextPageButton)
        controlLayout.addItem(spacerItem)
        
        self.controlSearch = QWidget()       
        controlSearchLayout = QVBoxLayout(self.controlSearch)
        controlSearchLayout.setMargin(0)
        controlSearchLayout.setSpacing(2)
        controlSearchLayout.addWidget(self.searchTable)
        controlSearchLayout.addWidget(self.controlWidget)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setMargin(2)
        mainLayout.setSpacing(2)
        mainLayout.addWidget(self.searchBox)
        mainLayout.addWidget(self.controlSearch)
                
        self.searchByType = 'all'
        self.searchBox.searchComboBox.setCurrentIndex(0)
    
    def create_connects(self):
        self.searchTable.installEventFilter(self)
        
        self.previousPageButton.clicked.connect(self.previous_page)
        self.nextPageButton.clicked.connect(self.next_page)
        self.jumpNum.returnPressed.connect(self.go_to_page)
        self.searchBox.searchButton.clicked.connect(self.search_musics)
        self.searchBox.lineEdit.returnPressed.connect(self.search_musics)
        self.searchBox.searchComboBox.currentIndexChanged.connect(self.searchtype_changed)
        self.searchBox.resetButton.clicked.connect(self.reset_search)
        self.searchTable.switchToOnlineListAction.triggered.connect(self.switch_to_online_list)
        self.searchTable.cellDoubleClicked.connect(self.searchtable_clicked)
        self.searchTable.cellClicked.connect(self.show_tooltip)
        self.searchTable.listenOnlineAction.triggered.connect(self.listen_online)
        self.searchTable.downloadAction.triggered.connect(self.download)
        self.searchTable.addBunchToListAction.triggered.connect(self.add_bunch_to_list)
    
    def eventFilter(self, target, event):
        if target == self.searchTable:
            if event.type() == QEvent.Resize:
                width = self.searchTable.width()
                widthTemp = (width-35)/3
                self.searchTable.setColumnWidth(0, 35)
                self.searchTable.setColumnWidth(1, widthTemp)
                self.searchTable.setColumnWidth(2, widthTemp)
                self.searchTable.setColumnWidth(3, widthTemp)
        return False
    
    def show_tooltip(self, row):
        mark = self.searchTable.item(row, 0).text()
        songName = self.searchTable.item(row, 1).text()
        artist = self.searchTable.item(row, 2).text()
        album = self.searchTable.item(row, 3).text()
        self.searchTable.setToolTip("评分：%s\n 歌曲：%s\n歌手：%s\n专辑：%s"%(mark, songName, artist, album))
    
    def switch_to_list(self):
        self.switchToOnlineList.emit()    
    
    def listen_online(self):
        if not self.searchTable.rowCount():
            return
        self.searchtable_clicked(self.searchTable.currentRow())
            
    def searchtable_clicked(self, row):
        musicName = self.searchTable.item(row, 1).text()
        artist = self.searchTable.item(row, 2).text()
        title = artist + '._.' + musicName
        album = self.searchTable.item(row, 3).text()
        musicId = self.searchTable.item(row, 4).text()
        songLink = SearchOnline.get_song_link(musicId)
        if not songLink:
            return
        songLinkWrap = songLink + '~' + musicId
        self.listen_online_signal.emit(title, album, songLinkWrap)
    
    def add_bunch_to_list(self):
        selections = self.searchTable.selectionModel()
        selecteds = selections.selectedIndexes()
        if not len(selecteds):
            return
        model = TableModel()
        model.initial_model("在线试听")
        songsInOnlineList = []
        added_items = []
        t1 = time.time()
        for i in range(model.rowCount()):
            songsInOnlineList.append(model.record(i).value("paths"))
        t2 = time.time()
        print(t2-t1)
        self.setCursor(QCursor(Qt.BusyCursor))
        for index in selecteds:
            if index.column() == 0:
                row = index.row()
                musicId = self.searchTable.item(row, 4).text()
                songLink = SearchOnline.get_song_link(musicId)
                if not songLink:
                    continue
                songLinkWrap = songLink + '~' + musicId
                if songLinkWrap  not in songsInOnlineList:
                    musicName = self.searchTable.item(row, 1).text()
                    artist = self.searchTable.item(row, 2).text()
                    title = artist + '._.' + musicName
                    album = self.searchTable.item(row, 3).text()
                    lrcName = title + '.lrc'
                    lrcPath = os.path.join(Configures.lrcsDir, lrcName)
                    if os.path.exists(lrcPath):
                        os.remove(lrcPath)
                    added_items.append([title, songLinkWrap])
#                    SearchOnline.get_lrc_path(title, musicId)
                    model.add_record(title, '未知', album, songLinkWrap)
        if len(added_items):
            thread = DownloadLrcThread(added_items)
            thread.setDaemon(True)
            thread.setName("downloadLrc")
            thread.start()
            self.add_bunch_to_list_succeed.emit()
        self.setCursor(QCursor(Qt.ArrowCursor))
        print(time.time()-t2)
        print("Success")
            
    def download(self):
        if not self.searchTable.rowCount():
            return
#        t1 = time.time()
        hasExisted = []
        linkError = []
        self.toBeEmited = []
        selections = self.searchTable.selectionModel()
        selecteds = selections.selectedIndexes()
        if  not len(selecteds):
            return
        with open(Configures.settingFile,  'r') as f:
            downloadDir = f.read()
        self.setCursor(QCursor(Qt.BusyCursor))
        for index in selecteds:
            if index.column() == 0:
                row = index.row()
                songName = self.searchTable.item(row, 1).text()
                artist = self.searchTable.item(row, 2).text()
                title = artist + '._.' + songName
                musicName = title + '.mp3'
                musicPath = os.path.join(downloadDir, musicName)
                if os.path.exists(musicPath):
                    hasExisted.append(title)
                    continue
                for t in threading.enumerate():
                    if t.name == musicPath:
                        continue
                album = self.searchTable.item(row, 3).text()
                musicId = self.searchTable.item(row, 4).text()
                songLink = SearchOnline.get_song_link(musicId)
                if not songLink:
                    linkError.append(title)
                    continue
        #            QMessageBox.critical(self, '错误','链接错误，无法下载该歌曲！')
        #            return
#                songInfo = '->'.join([songLink, musicPath, title , album, musicId])
                self.toBeEmited.append([songLink, musicPath, title , album, musicId])
#        songInfos = json.dumps(toBeEmited)
        self.add_to_download_signal.emit()
        self.setCursor(QCursor(Qt.ArrowCursor))
#        print('searchPageWidget.py searchFrame.download timecost = %s'%(time.time()-t1))
        if len(hasExisted):
            hasExistFiles = '\n'.join(hasExisted)
            self.show()
            QMessageBox.information(self, '提示','以下歌曲已在下载目录中，将不再进行下载！\n%s'%hasExistFiles)
        if len(linkError):
            linkErrorFiles = '\n'.join(linkError)
            self.show()
            QMessageBox.critical(self, '错误','以下歌曲链接出错，无法下载！\n%s'%linkErrorFiles)
    
    def reset_search(self):
        self.searchBox.lineEdit.clear()
        self.searchTable.clear_search_table()
        self.currentKeyword  =  None
        self.currentPage  =  0
        self.hit = 0
        self.pages = 0
        self.searchBox.searchButton.setText('搜索')
        self.pageNum.setText('/ 0')
        self.jumpNum.setText('0')
    
    def searchtype_changed(self, index):
        if index == 0:
            self.searchByType = 'all'
        elif index == 1:
            self.searchByType = 'artist'
        else:
            self.searchByType = 'album'
        self.search_musics()
        
    
    def go_to_page(self):
        if not self.currentKeyword:
            self.jumpNum.setText('%s'%self.currentPage)
            self.pageNum.setFocus()
            return
        page = self.jumpNum.text()
        try:
            page = int(page)
        except ValueError :
            self.jumpNum.setText('%s'%(self.currentPage + 1))
            QMessageBox.information(None, "提示", "请输入1~%s内的整数！"%self.pages)
            return
        if page == (self.currentPage + 1):
            self.pageNum.setFocus()
            return
        if page > self.pages or page < 1:
            self.jumpNum.setText('%s'%(self.currentPage + 1))
            QMessageBox.information(None, "提示", "页码范围1~%s"%self.pages)
            return
        self.show_musics(self.searchByType, self.currentKeyword, page - 1)    
        self.currentPage = page - 1
        self.searchBox.searchButton.setFocus()
    
    def search_musics(self):
        self.searchBox.searchButton.setFocus()
        keyword = self.searchBox.lineEdit.text()
        if not keyword:
            QMessageBox.information(self, '提示', '请输入搜索关键词！')
            return
#        if keyword == self.currentKeyword:
#            return
        self.currentKeyword = keyword
        self.hit  =  self.show_musics(self.searchByType, self.currentKeyword, 0)
        if self.hit == Configures.URLERROR:
            return
        self.currentPage = 0
        if self.hit:
            self.pages = self.hit//15 + 1
            self.jumpNum.setText('1')
            self.pageNum.setText('/ %s'%self.pages)
        else:
            self.jumpNum.setText('0')
            self.pageNum.setText('/ 0')
        self.searchBox.searchButton.setText('搜索(%s)'%self.hit)
        
    def previous_page(self):
        if not self.currentPage:
            return
        self.currentPage -= 1
        self.show_musics(self.searchByType, self.currentKeyword, self.currentPage)
        self.jumpNum.setText('%s'%(self.currentPage + 1))
        
    def next_page(self):
        if self.currentPage  +  1 >= self.pages:
            return
        self.currentPage  += 1
        self.show_musics(self.searchByType, self.currentKeyword, self.currentPage)
        self.jumpNum.setText('%s'%(self.currentPage + 1))
            
    def show_musics(self, searchByType, keyword, page):    
        self.searchTable.clear_search_table()
        t1 = time.time()
        songs, hit = SearchOnline.search_songs(searchByType, keyword, page)
        if hit == Configures.URLERROR:
            QMessageBox.critical(None, "错误", "联网出错！\n请检查网络连接是否正常！")     
            return Configures.URLERROR
        if not songs or hit == 0:
            return hit
        for song in songs:
            music = song[0]
            artist = song[1]
            album = song[2] 
            if not album:
                album = '未知专辑'
            music_id = song[3]
#            artistId = song['ARTISTID']
            score = song[4]
            self.searchTable.add_record(score, music, artist, album, music_id)
            self.searchTable.sortItems(0, Qt.DescendingOrder)
        t2 = time.time()
        print('searchPageWidget.py searchFrame.show_musics %s'%(t2 - t1))
        return hit

class SettingFrame(QDialog):
    downloadDirChanged = pyqtSignal(str)
    def __init__(self, parent = None):
        super(SettingFrame, self).__init__(parent)
        self.setMinimumSize(370, 110)
        label = QLabel("歌曲下载到：")
        with open(Configures.settingFile,  'r') as f:
            self.oldDir = f.read()
        self.lineEdit = QLineEdit("%s"%self.oldDir)
        self.setWindowTitle("当前设置："+self.oldDir)
        self.openDir = QToolButton(clicked = self.select_dir)
        self.openDir.setText('...')
        self.defaultButton = QPushButton("默认值", clicked = self.default)
        self.okButton = QPushButton("确定", clicked = self.confirm)
        self.cancelButton = QPushButton("取消", clicked = self.cancel)
        
        inputLayout = QHBoxLayout()
        inputLayout.addWidget(self.lineEdit)
        inputLayout.addWidget(self.openDir)
        
        buttonsLayout = QHBoxLayout()
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        buttonsLayout.addItem(spacerItem)
        buttonsLayout.addWidget(self.defaultButton)
        buttonsLayout.addWidget(self.cancelButton)
        buttonsLayout.addWidget(self.okButton)
        buttonsLayout.addItem(spacerItem)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(label)
        mainLayout.addLayout(inputLayout)
        mainLayout.addLayout(buttonsLayout)
    
    def set_place(self, x, y):
        self.setGeometry(x, y, 370, 110)
    
    def select_dir(self):
        f = QFileDialog()
        newDir = f.getExistingDirectory(self, "选择下载文件夹", Configures.homeDir, QFileDialog.ShowDirsOnly)
        if newDir:
            self.lineEdit.setText(newDir)
    
    def confirm(self):
        print('setting.py  here1')
        newDir = self.lineEdit.text()
        if not os.path.isdir(newDir):
            QMessageBox.critical(self, '错误', '您输入的不是一个文件夹！')
            self.lineEdit.setText(self.oldDir)
            return
        if newDir != self.oldDir:
            if not os.path.exists(newDir):
                os.mkdir(newDir)
            with open(Configures.settingFile, 'w') as f:
                f.write(newDir)
            self.oldDir = newDir
            self.setWindowTitle("当前设置："+newDir)
            self.downloadDirChanged.emit(newDir)
        self.close()
    
    def cancel(self):
        self.lineEdit.setText(self.oldDir)
        self.close()
    
    def default(self):
        self.lineEdit.setText(Configures.musicsDir)
    
class DesktopLyric(QLabel):
    hideDesktopLyricSignal = pyqtSignal()
    
    def __init__(self):
        super(DesktopLyric, self).__init__()
#        self.setFixedSize(700, 60)
        desktop = QApplication.desktop()
        screenRec = desktop.screenGeometry()
        self.desktopWidth = screenRec.width()
        self.desktopHeight = screenRec.height()
        self.setGeometry((self.desktopWidth - 800)//2, self.desktopHeight - 100, 800, 100)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWordWrap(True)
        self.setText('桌面歌词显示于此！')
        self.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setFamily("楷体")
        font.setWeight(60)
        font.setPointSize(28)
        self.setFont(font)
        pe = QPalette()
        pe.setColor(QPalette.WindowText, Qt.blue)
        self.setPalette(pe)
        self.create_contextmenu()
    
    def create_contextmenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listMenu = QMenu()
        self.originalPlaceAction = QAction("放回原位置", self)
        self.hideLyricAction = QAction("关闭桌面歌词", self)
        self.listMenu.addAction(self.originalPlaceAction)
        self.listMenu.addAction(self.hideLyricAction)
        self.originalPlaceAction.triggered.connect(self.original_place)
        self.hideLyricAction.triggered.connect(self.hide_desktop_lyric)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def original_place(self):
        self.move(QPoint((self.desktopWidth - 800)//2, self.desktopHeight - 100))
    
    def hide_desktop_lyric(self):
        self.hideDesktopLyricSignal.emit()
    
    def show_context_menu(self, pos):
        self.listMenu.exec_(self.mapToGlobal(pos))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()
    
    def closeEvent(self, event):
        self.hideDesktopLyricSignal.emit()
        event.ignore()



        
        
        
        
        
        
        
        
        
        
