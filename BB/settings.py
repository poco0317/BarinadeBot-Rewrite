import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter
import configparser
import shutil

class Settings:
    # these are per-server settings 
    # things like whether or not they want per channel command monitoring or whatever
    # this is the class which controls the commands

    def __init__(self, bot, config, loop, BarryBot):
        self.bot = bot
        self.config = config
        self.loop = loop
        self.BarryBot = BarryBot
        
    @commands.command()
    async def settings(self, ctx):
        ''' unimplemented '''
        raise unimplemented
        
class ServerSettings:
    # this is the object which describes each servers settings
    # it parses a .ini file given by the server id and so forth
    
    def __init__(self, serverID, config):
        self.serverID = str(serverID)
        self.config_filepath = os.path.dirname(config.options)+"/settings/"+str(serverID)+".ini"
        self.config = configparser.ConfigParser(interpolation=None)
        if not self.config.read(self.config_filepath, encoding='utf-8'):
            try:
                shutil.copy(os.path.dirname(config.options)+"/example_server.ini", self.config_filepath)
            except:
                self.fallback_vars()
                print("failure")
    
        self.config.read(self.config_filepath, encoding='utf-8')
        
        self.clearChannel_list = self.config.get("Features", "clr_channel_ids", fallback=SettingDefaults.clearChannel_list).split()  #a list of ids (updated when the channels are cleared
        self.clearChannel_frequency = self.config.get("Features", "clr_channel_freq", fallback=SettingDefaults.clearChannel_frequency)#an int of seconds at least 12 hours long
        #... more to come
    
    def verify(self):
        pass
        
        
    def fallback_vars(self):
        pass
        
class SettingDefaults:
    clearChannel_list = 0
    clearChannel_frequency = 43200