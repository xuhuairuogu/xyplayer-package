import os, time, threading
from urllib import request
from xyplayer.util import write_tags
from xyplayer.urldispose import SearchOnline

class DownloadThread(threading.Thread):     
    def __init__(self, model, row):
        super(DownloadThread, self).__init__()
        self.title = model.data(model.index(row, 0))
        self.currentLength = int(model.data(model.index(row, 1)))
        self.length = model.data(model.index(row, 2))
        self.album = model.data(model.index(row, 4))
        self.songLink = model.data(model.index(row, 5))
        self.musicPath = model.data(model.index(row, 6))
        self.musicId = model.data(model.index(row, 8))
        self.model = model
        self.row = row
        self.runPermit = True
        self.noPause = True
        
    def run(self):
        if self.length == '未知':
            res = request.urlopen(self.songLink)
            if res.status == 200 and  res.reason == 'OK' and res.getheader('Content-Type') == 'audio/mpeg':
                self.length = res.getheader('Content-Length')
            else:
                self.model.setData(self.model.index(self.row, 3), '资源出错')
                return
        self.length = int(self.length)
        tempfileName = self.musicPath + '.temp'
        if not os.path.exists(tempfileName):
            self.currentLength = 0
        elif self.currentLength == 0:
            os.remove(tempfileName)
        print("开始下载")
        print(threading.active_count())
        req = request.Request(self.songLink)
        req.headers['Range'] = 'bytes= %s-%s'%(self.currentLength, self.length)
        res = request.urlopen(req)
        if res.getheader('Content-Type') != 'audio/mpeg':
            self.model.setData(self.model.index(self.row, 3), '资源出错')
            return
        while self.currentLength<self.length and self.runPermit and self.noPause:
            time1 = time.time()
            contentCache = res.read(51200)
            with open(tempfileName, 'ab+') as f:
                f.write(contentCache)
            time2 = time.time()
            span = time2-time1
            if len(contentCache) == 51200:
                netSpeed = 50/span
                remainTime = (self.length-self.currentLength)/(netSpeed*512)
            else:
                netSpeed = 0
                remainTime = 0
            self.currentLength  += 51200
            if self.currentLength>self.length:
                self.currentLength = self.length
            self.model.setData(self.model.index(self.row, 1), self.currentLength)
            self.model.setData(self.model.index(self.row, 3), remainTime)
            self.model.setData(self.model.index(self.row, 7), netSpeed)
            if self.model.record(self.row).value('size') == '未知':
                self.model.setData(self.model.index(self.row, 2), self.length)
        res.close()
        if self.currentLength == self.length:
            os.rename(tempfileName, self.musicPath)
            write_tags(self.musicPath, self.title, self.album)
            self.model.setData(self.model.index(self.row, 1), self.length)
            self.model.setData(self.model.index(self.row, 3), "已完成")
        else:
            if not self.runPermit:
                if os.path.exists(tempfileName):
                    os.remove(tempfileName)
                self.model.setData(self.model.index(self.row, 3), "已取消")
                self.model.setData(self.model.index(self.row, 1), 0)
                print("已取消")
            if not self.noPause:
                self.model.setData(self.model.index(self.row, 3), "已暂停")
                print("已暂停")
        self.model.setData(self.model.index(self.row, 7), 0)
        print("下载完成")
        
    def stop(self):
        self.runPermit = False
    
    def pause(self):
        self.noPause = False
        

class DownloadLrcThread(threading.Thread):
    def __init__(self, list):
        super(DownloadLrcThread, self).__init__()
        self.list = list
        self.runPermit = True
    
    def run(self):
        i = 0
        cnt = len(self.list)
        while i < cnt and self.runPermit:
            title = self.list[i][0]
            try:
                artist = title.split('._.')[0].strip()
                SearchOnline.get_artist_image_path(artist)
            except:
                pass
            path = self.list[i][1]
            if path[0:4] == 'http':
                musicId = path.split('~')[1]
            else:
                musicId = 0
            if not SearchOnline.is_lrc_path_exists(title):
                SearchOnline.get_lrc_path(title, musicId)
            i  += 1
    
    def stop(self):
        self.runPermit = False
