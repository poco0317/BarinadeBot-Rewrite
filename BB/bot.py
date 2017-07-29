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
from BB.unogame import The_Game, Uno
from BB.player import Player, Downloader
from BB.settings import Settings, ServerSettings
from BB.mods import Moderation


class Barry(discord.Client):

    def __init__(self, bot, loop):
        self.config = Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+"\\config\\config.ini")
        self.THE_SECRET_TOKEN = self.config.THE_TOKEN
        self.loop = loop
        self.bot = bot
        self.downloader = Downloader(self.config.download_path)
        self.bot.add_cog(MainCommands(self.bot, self.config)) #add the main command class for laziness sake
        self.bot.add_cog(self) #also a cheaty way to just fit all the commands into this class
        self.bot.add_cog(Uno(self.bot, self.config, self.loop, self))        
        self.bot.add_cog(Player(self.bot, self.config, self.loop, self))
        self.bot.add_cog(Settings(self.bot, self.config, self.loop, self))
        self.bot.add_cog(Moderation(self.bot, self.config, self.loop, self))
        self.UnoGames = {}
        self.settings = {}
        
        
        self.logchan = None
        
        
        self.blacklist = set()
        
        
        super().__init__()
    def guild_settings(ctx): #this is for general use to retrieve the context's server specific settings quickly
        ''' this just returns a settings object quickly for the context
        if it returns none then there was something wrong'''
        try:
            if ctx.guild.id in self.settings:
                return self.settings[ctx.guild.id]
        except: # something is terribly wrong with the context
            return None
        finally: # guild is isnt even in the settings file
            return None
        
    @commands.command(hidden=True)
    async def blacklistme(self, ctx):
        self.blacklist.add(ctx.message.author.id)

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def respond(self, ctx, *, words):
        '''Literally replies with exactly what you said'''
        await ctx.send(words)
        #await self.logchan.send(words)

    @commands.group(hidden=True)
    async def cgt(self, ctx):
        '''g'''
        print(ctx.command.name)

    @cgt.command(hidden=True)
    async def rer(self, ctx):
        '''g'''
        print(ctx.command.name)
        print(ctx.command.parent.name)
        print(ctx.command.qualified_name)

    @commands.command(hidden=True)
    async def roletest(self, ctx, *, role : discord.Role):
        print(role)

    @commands.command(hidden=True, aliases=["shtudown", "sd", "shtdon", "shutdwon"])
    @commands.check(Perms.is_owner)
    async def shutdown(self, ctx):
        await ctx.send("Shutting down. I will not restart until manually run again.")
        await self.logout()
        await self.bot.logout()
    
    async def delete_later(self, message, time=15): #self.loop.create_task(self._actually_delete_later(message, time))
        self.loop.create_task(self._actually_delete_later(message, time))
    async def _actually_delete_later(self, message, time=15):
        await asyncio.sleep(time)
        try:
            await message.delete(reason="Automatic deletion by Bot.")
        except:
            pass


    @commands.command(hidden=True)
    async def pagtest(self, ctx):
        p = commands.Paginator()
        for i in range(100):
            try:
                p.add_line(line=str(i*i)+"ggggggggggggggggggggggggggggggggggggggggggggg")
            except:
                p.close_page()
                p.add_line(line=str(i*i)+"gdsfdsfdasfdsfdsffdsfsdsdfdfdsfsdfsdsdfsfsfdfs")
        print(p.pages)
        await ctx.send(p.pages[0])



class MainCommands: #command defs can go here as well

    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.players = set()
        

        
    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def test(self, ctx, *, song : str):
        player = await ctx.author.voice.channel.connect()

        player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song), volume=0.1), after=lambda e: print("done", e))
        player.is_playing()
        self.players.add(player)
        
    
    @commands.group(hidden=True)
    async def g(self, ctx):
        pass
    @g.command(hidden=True)
    async def p(self, ctx):
        pass
    
    
    
    

        