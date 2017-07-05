import os
import discord
import asyncio
from discord.ext import commands
import random
import youtube_dl
import functools
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from BB.conf import Conf
from BB.permissions import *

#i am not original so a lot of this is at least remotely based from the example playlist.py and possibly MusicBot, but what are you gonna do
#everything cant be original
# im sorry so much of this is a copy paste or close rip of MusicBot's downloader.py
# with the changes to discord.py rewrite, i couldnt think of a better way to get remote audio

ytdl_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
youtube_dl.utils.bug_reports_message = lambda: ''

if not discord.opus.is_loaded():
    discord.opus.load_opus()
    
class Player: #this represents commands and not an actual player/voicechan object
    def __init__(self, bot, config, loop, mainbot):
        self.bot = bot #commands related for making this all disorganized
        self.config = config
        self.loop = loop 
        self.BarryBot = mainbot #contains the Downloader and mainly everything
        self.players = {} #format: self.players[serverID] = (channelplayer, playlist)
        
    @commands.command(aliases=["join", "come"])
    async def summon(self, ctx):
        '''Bring the bot into a voice channel'''
        if ctx.guild.id in self.players:
            if ctx.author.voice.channel.id != self.players[ctx.guild.id][0].channel.id:
                await self.players[ctx.guild.id][0].move_to(ctx.author.voice.channel)
            else:
                raise alreadyJoined
        player = await ctx.author.voice.channel.connect()
        self.players[ctx.guild.id] = (player, Playlist(self.BarryBot))
        
    @commands.command(aliases=["kys", "leave"])
    async def disconnect(self, ctx):
        '''Make the bot leave the voice channel it is connected to on the server'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        player = self.players[ctx.guild.id][0]
        await player.disconnect()
        del self.players[ctx.guild.id]
        
    @commands.command()
    async def play(self, ctx):
        '''Queue an item on the music player'''
        #player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song), volume=0.5), after=lambda e: print("done", e))
        return
    
    
    
class Entry:
    def __init__(self, playlist, queuer, name, Filepath=None):
        self.downloading = False
        self.is_downloaded = False if not Filepath else True
        self.playlist = playlist
        self.author = queuer
        self.name = name
        self.filepath = Filepath
        
    def __str__(self):
        return "entry string"
        
        
        
    async def download(self):
        if self.downloading:
            return
        self.downloading = True
        try:
            result = await self.playlist.downloader.get_the_stuff(self.playlist.loop, self.name)
        except:
            raise downloaderBroke
        if result is None:
            raise downloaderBroke
    async def play(self):
        pass
        
class Playlist:
    def __init__(self, bot):
        self.bot = bot
        self.downloader = bot.downloader
        self.entries = deque()
    def __iter__(self):
        return iter(self.entries)
    def shuffle(self):
        random.shuffle(self.entries)
    def clear(self):
        self.entries.clear()
        
        
        
class Downloader:
    def __init(self, download_path=Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+"\\config\\config.ini")):
        self.threadpool = ThreadPoolExecutor(max_workers=2)
        self.ytdl = youtube_dl.YoutubeDL(ytdl_options)
        tPN = self.ytdl.params['outtmpl']
        self.ytdl.params['outtmpl'] = os.path.join(download_path, tPN)
        
    async def get_the_stuff(self, loop, *args, **kwargs):
        return await loop.run_in_executor(self.threadpool, functools.partial(self.get_the_stuff, *args, **kwargs))