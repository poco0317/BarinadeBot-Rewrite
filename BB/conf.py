import configparser
import os

class Conf:
    def __init__(self, conf):
        self.options = conf
        config = configparser.ConfigParser(interpolation=None)
        
        if not config.read(conf, encoding='utf-8'):
            print("I'm missing important stuff. (it's config related)")
            print("Check to see that the config exists here:" +self.options)
            os._exit(1)
            
        config.read(conf, encoding='utf-8')
        
        self.THE_TOKEN = config.get("Login", "Token", fallback=Fallbacks.token)
        self.owner_id = int(config.get("Permissions", "OwnerID", fallback=Fallbacks.ownerID))
        self.download_path = config.get("Music", "Path", fallback=Fallbacks.download_path)

        
        
class Fallbacks:
    token = "0"
    ownerID = 0
    download_path = ""
