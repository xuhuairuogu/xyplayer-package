# -*- coding = utf-8 -*-
import os, re, time
from urllib import parse, request
from mutagenx.mp3 import MP3
from mutagenx.easyid3 import EasyID3
from PyQt4.QtCore import QTime

def read_music_info(path):
    audio = MP3(path)
    basepath = os.path.splitext(path)[0]
    basename = os.path.split(basepath)[-1]
    musicname = '%s'%audio.get("TIT2", basename)          
    artist = '%s'%audio.get("TPE1", "") 
    album = '%s'%audio.get("TALB", "未知专辑")        
    totalTimeValue = int(audio.info.length)
    if not artist:
        title = musicname
    else:
        title = artist + '._.' + musicname

    hours = totalTimeValue/3600
    minutes = (totalTimeValue%3600)/60
    seconds = (totalTimeValue)%3600%60
    if totalTimeValue < 3600:
        totalTime = QTime(0, minutes, seconds).toString('mm:ss')
    else:
        totalTime = QTime(hours, minutes, seconds).toString('hh:mm:ss')
    return title,album, totalTime

def list_to_seconds(list):
    min, sec, ms = list
    if not ms:
        currentTime = int(min)*60 + int(sec)
    else:
        currentTime = int(min)*60 + int(sec) + float(ms)
    return currentTime*1000

def parse_lrc(text):
    lines = text.split('\n')
    lrcDisposed = {-2:''}
    screen = re.compile('\[([0-9]{2}):([0-9]{2})(\.[0-9]{1,3})?\]')
    for line in lines:
        offset = 0
        match = screen.match(line)
        timeTags = []
        while match:
            currentTime = list_to_seconds(match.groups())
            timeTags.append(currentTime)
            offset = match.end()
            match = screen.match(line, offset)
        content = line[offset:]
        for tag in timeTags:
            lrcDisposed[tag] = content
    try:
        c = re.match('offset\=(\-?\d+)',lines[-1])
        offset = int(c.group(1))
        print('parse_lrc: %s'%offset)
    except:
        offset = 0
    return offset, lrcDisposed
    
def write_tags(musicPath, title, album):
    audio = MP3(musicPath, ID3 = EasyID3)
    audio.clear()
    songName = title.split('._.')[1]
    artist = title.split('._.')[0]
    audio['title'] = songName.strip()
    audio['artist'] = artist.strip()
    audio['album'] = album.strip()
    audio.save()

def parse_songs_wrap(str):
    t1 = time.time()
    hit = int(re.search('Hit\=(\d+)', str).group(1))
    songs_wrap = []
    str_list = str.split('\r\n\r\n')
    for i in range(1, 16):
        if str_list[i]:
            song_list = str_list[i].split('\r\n')
            songname = song_list[0][9:]
            artist = song_list[1][7:]
            album = song_list[2][6:]
            music_id = song_list[6][15:]
            score = song_list[18][9:]
            songs_wrap.append([songname, artist, album, music_id, score])
            continue
        break
    t2 = time.time()
    print('urlsDispose.py parse_songs_wrap t2-t1 = %s'%(t2 - t1))
    return songs_wrap, hit

def parse_quote(str):
    return parse.quote(str, safe = '~@#$&()*!+=:;,.?/\'')

def url_open(url, retries = 3):
    try:
        req = request.urlopen(url, timeout = 3)
        req = req.read()
        reqContent = req.decode()
        reqContent = reqContent.lstrip()
        return reqContent
    except:
        return -2
