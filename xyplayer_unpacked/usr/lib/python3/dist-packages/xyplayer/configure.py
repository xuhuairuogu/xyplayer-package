import os

class Configures():
    INSTALLPATH = '/usr/lib/python3/dist-packages/xyplayer'
    NOERROR = -1
    URLERROR = -2
    TYPEERROR = -3
    homeDir = os.path.expanduser('~')
    cacheDir = os.path.join(homeDir, '.xyplayer')
    musicsDir = os.path.join(cacheDir, 'downloads')
    imagesDir = os.path.join(cacheDir, 'images')
    artistInfosDir = os.path.join(cacheDir, 'infos')
    lrcsDir = os.path.join(cacheDir, 'lrcs')
    settingFile = os.path.join(cacheDir, 'settings')
    db = os.path.join(cacheDir, 'xyplayer.db')
    
    def check_dirs():
        if not os.path.exists(Configures.cacheDir):
            os.makedirs(Configures.cacheDir)
            os.mkdir(Configures.musicsDir)
            os.mkdir(Configures.imagesDir)
            os.mkdir(Configures.lrcsDir)
            os.mkdir(Configures.artistInfosDir)
        if not os.path.exists(Configures.settingFile):
            with open(Configures.settingFile, 'w') as f:
                f.write(Configures.musicsDir)
            
