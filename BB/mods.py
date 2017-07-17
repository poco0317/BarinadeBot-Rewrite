import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter


class Moderation:
        #for things like linkblock or whatever
        #or maybe role specific muting

    def __init__(self, bot, config, loop, BarryBot):
        self.bot = bot
        self.loop = loop
        self.config = config
        self.BarryBot = BarryBot
        
    @commands.group()
    async def purge(self, ctx):
        ''' unimplemented'''
        raise unimplemented