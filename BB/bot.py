import os
import re
import asyncio
import aiohttp
import random
import discord
import traceback

from discord.ext import commands

#from BB.file import class
from BB.conf import Conf



class Barry(discord.Client):

    def __init__(self, bot, conf=None, perms=None):
        self.config = Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+"\\config\\config.ini")
        self.THE_SECRET_TOKEN = self.config.THE_TOKEN
        self.loop = asyncio.get_event_loop()
        self.bot = bot
        self.bot.add_cog(BarryCommands(self.bot)) #add the main command class so the bot actually listens
        self.bot.add_cog(self) #also a cheaty way to just fit all the commands into this class
        super().__init__()

    
    @commands.command()
    async def test2(self, ctx):
        await ctx.send("yeh")






        
    
        
class BarryCommands: #command defs can go here as well

    def __init__(self, bot):
        self.bot = bot

        
    @commands.command()
    async def test(self, ctx):
        await ctx.send("test")
    
    