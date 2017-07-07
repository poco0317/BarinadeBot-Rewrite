import os
import discord
import asyncio
from discord.ext import commands
import random
import youtube_dl
import functools
import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from itertools import islice
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
        self.players = {} #format: self.players[serverID] = (channelplayer, playlist); playlist contains message/chan/vc/self
        
    @commands.command(aliases=["join", "come"])
    async def summon(self, ctx):
        '''Bring the bot into a voice channel'''
        if ctx.guild.id in self.players:
            if ctx.author.voice.channel.id != self.players[ctx.guild.id][0].channel.id:
                await self.players[ctx.guild.id][0].move_to(ctx.author.voice.channel)
                self.players[ctx.guild.id][1].voice_channel = ctx.author.voice.channel
            else:
                raise alreadyJoined
        player = await ctx.author.voice.channel.connect()
        self.players[ctx.guild.id] = (player, Playlist(self.BarryBot, ctx.channel, None, ctx.author.voice.channel, self))
        
    @commands.command(aliases=["kys", "leave"])
    async def disconnect(self, ctx):
        '''Make the bot leave the voice channel it is connected to on the server'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        player = self.players[ctx.guild.id][0]
        await player.disconnect()
        del self.players[ctx.guild.id]
        
    @commands.command()
    async def play(self, ctx, *, url : str):
        '''Queue an item on the music player'''
        #add extra checks here for if the player is in a channel
        
        try:
            info = await self.BarryBot.downloader.get_the_stuff(self.players[ctx.guild.id][1].loop, url, download=False, process=False)
        except:
            raise entryFailure
        if not info:
            raise entryFailure
        
        if info.get('url', '').startswith('ytsearch'):
            info = await self.BarryBot.downloader.get_the_stuff(
                self.players[ctx.guild.id][1].loop,
                url,
                download=False,
                process=True,
            )
            if not info:
                raise entryFailure
            url = info['entries'][0]['webpage_url']
            info = await self.BarryBot.downloader.get_the_stuff(self.players[ctx.guild.id][1].loop, url, download=False, process=False)
            
        if 'entries' in info:
            #basically this would start a loop to queue each song from the list or something
            raise unsupportedPlaylist
        else:
            #length check here but we skip this for now
            try:
                entry, position = await self.players[ctx.guild.id][1].add_entry(url, queuer=ctx.author.name)
            except:
                raise entryFailure
            sendMessage = "Found and queued **%s** at position %s in the queue."
            title = entry.name
        if position == 1 and not self.players[ctx.guild.id][0].is_playing():
            #make the player play the song and pretty much dont even need to queue it
            sendMessage = "Found and queued **%s** to play as soon as possible!"
            sendMessage %= (title)
            await ctx.send(sendMessage, delete_after=30)
            await self.players[ctx.guild.id][1].entries[0].download()
            self.players[ctx.guild.id][1].message = await self.players[ctx.guild.id][1].chan.send("Now playing in "+self.players[ctx.guild.id][1].voice_channel.name+": "+str(self.players[ctx.guild.id][1].entries[0]))
            self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
        else:
            #just add the queue and download it but dont do anything else
            try:
                time_to = await self.players[ctx.guild.id][1].time_to(position, self.players[ctx.guild.id][0])
                sendMessage += " - Max time until it plays: %s"
            except:
                time_to = "Error"
            try:
                sendMessage %= (title, position, time_to)
            except:
                sendMessage = "There was an error creating the final string, but "+title+" should have been queued anyways."
            await ctx.send(sendMessage, delete_after=30)
            if position == 2:
                await self.players[ctx.guild.id][1].entries[1].download()
        #await ctx.send(sendMessage, delete_after=30)
    
    @commands.command(aliases=["vol"])
    async def volume(self, ctx, *, vol : float = 0.050305):
        '''Change the music player volume'''
        # add extra checks for the player
        vol = vol*100
        if vol/100 == 0.050305:
            return ctx.send("The current volume is at "+str(self.players[ctx.guild.id][0].source.volume * 100)+"%.")
        self.players[ctx.guild.id][0].source.volume = vol/100
        self.players[ctx.guild.id][1].volume = vol/100
    
    @commands.command(aliases=["queue", "que", "list"])
    async def playlist(self, ctx):
        '''Show the playlist'''
        #add extra checks for the player
        
        finalStr = ""
        entries = self.players[ctx.guild.id][1].entries
        overLimit = 0
        for i in range(len(entries)):
            if len(finalStr) > 1900:
                overLimit += 1
            if i == 0 and not overLimit:
                finalStr = "Currently Playing: "+str(entries[i])
            elif i == 1 and not overLimit:
                finalStr = finalStr + "\n" + "Next Up: "+str(entries[i]) + "\n"
            elif i > 1 and not overLimit:
                finalStr = finalStr + "\n`" + str(i+1) + ".` "+str(entries[i])
        if overLimit:
            finalStr = finalStr + "\n\n" + "**...Plus "+str(overLimit)+" more...**"
        await ctx.send(finalStr)
        
    @commands.command(hidden=True)
    async def download(self, ctx):
        ''' download the first entry'''
        
        await self.players[ctx.guild.id][1].entries[0].download()
        
    @commands.command(hidden=True)
    async def forceplay(self, ctx):
        ''' force the first entry to play'''
        try:
            self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
        except:
            traceback.print_exc()
            
    @commands.command(hidden=True)
    async def dirplay(self, ctx, *, song:str):
        ''' force the bot to play a file'''
        self.players[ctx.guild.id][0].play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song), volume=0.5), after=lambda e: print("done", e))
            
    @commands.command(hidden=True)
    async def downplay(self, ctx):
        ''' download and play first entry'''
        await self.players[ctx.guild.id][1].entries[0].download()
        self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
    
    @commands.command(hidden=True)
    async def popleft(self, ctx):
        ''' g'''
        self.players[ctx.guild.id][1].entries.popleft()
        await self.players[ctx.guild.id][1].message.delete()
    
class Entry:
    def __init__(self, playlist, queuer, name, duration=0, filename=None, Filepath=None):
        self.downloading = False
        self.is_downloaded = False if not Filepath else True
        self.playlist = playlist
        self.author = queuer
        self.name = name
        self.filepath = Filepath #this is used if we are not going to download the file
        self.filename = filename #this is the direct filepath for a youtube download
        self.duration = duration
        
    def __str__(self):
        return "**"+self.name+"** queued by "+self.author+". **Duration**: "+str(datetime.timedelta(seconds=self.duration))
        
        
        
    async def download(self):
        if self.downloading or self.is_downloaded:
            return
        self.downloading = True
        if os.path.isfile(self.filename):
            self.downloading = False
            self.is_downloaded = True
            return
        try:
            if not os.path.exists(self.playlist.downloader.path+"/"+str(self.playlist.chan.guild.id)):
                os.makedirs(self.playlist.downloader.path+"/"+str(self.playlist.chan.guild.id))
            result = await self.playlist.downloader.get_the_stuff(self.playlist.loop, self.name)
        except:
            raise downloaderBroke
        if result is None:
            raise downloaderBroke
        self.downloading = False
        self.is_downloaded = True
    def play(self, player):
        ''' this plays the song '''
        #player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song), volume=0.5), after=lambda e: print("done", e))
        player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename), volume=self.playlist.volume), after=self._afterplay)
        
    def _afterplay(self, error):
        coro = self.playlist.afterplay(error)
        future = asyncio.run_coroutine_threadsafe(coro, self.playlist.loop)
        try:
            future.result()
        except:
            pass
        
        
    
            
        
class Playlist:
    def __init__(self, bot, chan, message, voice_channel, player):
        self.bot = bot
        self.downloader = bot.downloader
        self.entries = deque()
        self.loop = bot.loop
        self.chan = chan
        self.message = message
        self.voice_channel = voice_channel
        self.volume = 0.3
        self.player = player
    def __iter__(self):
        return iter(self.entries)
    def shuffle(self):
        random.shuffle(self.entries)
    def clear(self):
        self.entries.clear()
        
    async def add_entry(self, url=None, queuer="None", **meta):
        try:
            self.downloader.ytdl.params['outtmpl'] = os.path.join(self.downloader.path+"/"+str(self.chan.guild.id), self.downloader.tPN)
            info = await self.downloader.get_the_stuff(self.loop, url, download=False)
        except:
            raise entryFailure
        entry = Entry(
            self,
            queuer,
            info.get('title', 'Untitled'),
            info.get('duration', 0) or 0,
            self.downloader.ytdl.prepare_filename(info),
            **meta
        )
        
        self.entries.append(entry)
        if self.entries[0] is entry:
            pass
            #play the first song
            
        return entry, len(self.entries)
    async def time_to(self, position, player):
        estimated_time = sum([entry.duration for entry in islice(self.entries, position-1)])
        return datetime.timedelta(seconds=estimated_time)

    async def afterplay(self, error):
        if error:
            raise playerError
        if self.entries[0].filepath: #we are assuming we were triggering this function based off of playing the first entry and we are going to have serious issues if that isnt the case
            pass #this just skips deleting the file if it was triggered by something other than a link or search, something we dont want to deleted
        else:
            dontDelete = False
            if len(self.entries) > 1:
                for entry in self.entries[1:]:
                    if entry.filename == self.entries[0].filename:
                        dontDelete = True
                        break
            if not dontDelete:
                for x in range(10):
                    try:
                        os.unlink(self.entries[0].filename)
                        break
                    except:
                        await asyncio.sleep(0.25)
        self.entries.popleft()
        await self.message.delete()
        if len(self.entries) > 0:
            self.message = await self.chan.send("Now (downloading) in "+self.voice_channel.name+": "+str(self.entries[0]))
            await self.entries[0].download()
            await self.message.edit(content="Now playing in "+self.voice_channel.name+": "+str(self.entries[0]))
            self.entries[0].play(self.player.players[self.chan.guild.id][0])
            if len(self.entries) > 1:
                await self.entries[1].download()
                    
        
        
        
class Downloader:
    def __init__(self, download_path):
        self.threadpool = ThreadPoolExecutor(max_workers=2)
        self.ytdl = youtube_dl.YoutubeDL(ytdl_options)
        self.tPN = self.ytdl.params['outtmpl']
        self.ytdl.params['outtmpl'] = os.path.join(download_path, self.tPN)
        self.path = download_path
        
        
    async def get_the_stuff(self, loop, *args, **kwargs):
        return await loop.run_in_executor(self.threadpool, functools.partial(self.ytdl.extract_info, *args, **kwargs))