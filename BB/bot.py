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
from BB.permissions import Perms




class Barry(discord.Client):

    def __init__(self, bot, conf=None, perms=None):
        self.config = Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+"\\config\\config.ini")
        self.THE_SECRET_TOKEN = self.config.THE_TOKEN
        self.loop = asyncio.get_event_loop()
        self.bot = bot
        self.bot.add_cog(BarryCommands(self.bot, self.config)) #add the main command class so the bot actually listens
        self.bot.add_cog(self) #also a cheaty way to just fit all the commands into this class
        self.bot.add_cog(Perms)
        super().__init__()

    
    @commands.command()
    @commands.check(Perms.force_error)
    async def test2(self, ctx):
        await ctx.send("yeh")

    @commands.command()
    @commands.check(Perms.is_owner)
    async def shutdown(self, ctx):
        await ctx.send("Shutting down. I will not restart until manually run again.")
        await self.logout()
        await self.bot.logout()

    async def delete_later(self, message, time): #self.loop.create_task(self.delete_later(message, time))
        await asyncio.sleep(time)
        try:
            await message.delete(reason="Automatic deletion by Bot.")
        except:
            pass



        
    
        
class BarryCommands: #command defs can go here as well

    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        

        
    @commands.command()
    @commands.check(Perms.is_owner)
    async def test(self, ctx):
        await ctx.send("test")
    
    