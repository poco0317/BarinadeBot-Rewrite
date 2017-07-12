import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter



class Settings:
    # these are per-server settings 
    # things like whether or not they want per channel command monitoring or whatever

    def __init__(self, bot, config, loop, BarryBot):
        self.bot = bot
        self.config = config
        self.loop = loop
        self.BarryBot = BarryBot
        
    @commands.command()
    async def settings(self, ctx):
        ''' unimplemented '''
        raise unimplemented