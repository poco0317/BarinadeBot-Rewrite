import configparser
import os
import shutil

class Conf:
    def __init__(self, conf):
        self.options = conf
        config = configparser.ConfigParser(interpolation=None)
        
        if not config.read(conf, encoding='utf-8'):
            print("I had to remake the config file from default. Please check the config and restart once the proper settings have been changed.")
            print("The config should exist here: " +self.options)
            try:
                shutil.copy(os.path.dirname(self.options)+"/example_config.ini", self.options)
            except:
                print("Well... Somehow the example I was copying from is also gone. You're in a bad spot.")
            os._exit(1)
            
        config.read(conf, encoding='utf-8')
        
        self.THE_TOKEN = config.get("Login", "Token", fallback=Fallbacks.token)
        self.owner_id = int(config.get("Permissions", "OwnerID", fallback=Fallbacks.ownerID))
        self.download_path = config.get("Music", "Path", fallback=Fallbacks.download_path)

        
        
class Fallbacks: #these will only get used if the user leaves the config.ini existant but really messes something up... everything breaks if they get used.
    token = "0"
    ownerID = 0
    download_path = ""
