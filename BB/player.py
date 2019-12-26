import os, errno, glob
import discord
import asyncio
from discord.ext import commands
import random
import youtube_dl
import functools
import datetime
import traceback
import subprocess
from concurrent.futures import ThreadPoolExecutor
from shutil import rmtree
from collections import deque
from itertools import islice
from BB.conf import Conf
from BB.permissions import *

#i am not original so a lot of this is at least remotely based from the example playlist.py and possibly MusicBot, but what are you gonna do
#everything cant be original
# im sorry so much of this is a copy paste or close rip of MusicBot's downloader.py
# with the changes to discord.py rewrite, i couldnt think of a better way to get remote audio

# but anyways heres a way to bass boost something because why not
# ffmpeg -i "filename..." -af bass=g=999 "outputname"

ytdl_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    #'outtmpl': '%(id)s-%(title)s.%(ext)s',
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
        self.players = {} #format: self.players[serverID] = (channelplayer, playlist); playlist contains message/chan/vc/self etc
        try:
            rmtree(config.download_path)
        except:
            pass

    @commands.command(aliases=["join", "come"])
    async def summon(self, ctx):
        '''Bring the bot into a voice channel
        Server mods are allowed to use this command during music play.'''
        if not ctx.author.voice:
            raise impossible_noChannel
        if ctx.guild.id in self.players:
            try:
                is_mod = Perms.is_guild_mod(ctx)
            except:
                is_mod = False
            if self.players[ctx.guild.id][0].is_playing() and not is_mod:
                raise currentlyPlaying
            if ctx.author.voice.channel.id != self.players[ctx.guild.id][0].channel.id:
                await self.players[ctx.guild.id][0].move_to(ctx.author.voice.channel)
                self.players[ctx.guild.id][1].voice_channel = ctx.author.voice.channel
                return
            else:
                raise alreadyJoined
        try:
            player = await ctx.author.voice.channel.connect()
        except ClientException:
            await ctx.send("It seems I'm in the channel but I can't see for sure. Let me refresh...", delete_after=15)
            try:
                del self.players[ctx.guild.id]
            except:
                pass
            player = await ctx.author.voice.channel.connect()
            self.players[ctx.guild.id] = (player, Playlist(self.BarryBot, ctx.channel, None, ctx.author.voice.channel, self, ctx))
            return
        self.players[ctx.guild.id] = (player, Playlist(self.BarryBot, ctx.channel, None, ctx.author.voice.channel, self, ctx))

    @commands.command(aliases=["kys", "leave"])
    @commands.check(Perms.is_guild_mod)
    async def disconnect(self, ctx):
        '''Make the bot leave the voice channel, killing the player
        Only server mods can use this.'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        player = self.players[ctx.guild.id][0]
        await player.disconnect()
        del self.players[ctx.guild.id]

    @commands.command()
    async def play(self, ctx, *, url : str):
        '''Queue an item on the music player
        If I am not in a channel, I will join yours.
        If I am not in your voice channel, I will move if I'm not playing music.

        Bonus: Adding the -b flag just after the command and before the search terms or link will give an obnoxious bass boost to the song.
        Example: !play -b poop'''
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if not ctx.author.voice:
            if not is_mod:
                raise noChannel
            else:
                pass

        if ctx.guild.id not in self.players and ctx.author.voice:
            await self.summon.invoke(ctx)
        elif ctx.guild.id not in self.players and not ctx.author.voice:
            raise modBypassAttempt
        else:
            if ctx.author.voice:
                if ctx.author.voice.channel.id != self.players[ctx.guild.id][1].voice_channel.id and ctx.author.voice.channel.id != self.players[ctx.guild.id][0].channel.id:
                    if not is_mod:
                        if self.players[ctx.guild.id][0].is_playing():
                            raise outsideChannel
                        else:
                            await self.summon.invoke(ctx)
                    else:
                        if self.players[ctx.guild.id][0].is_playing():
                            pass
                        else:
                            await self.summon.invoke(ctx)
                    #basically this is a bunch of bypasses and permission checking    

        change_later = await ctx.send("Looking...")
        try:
            info = await self.BarryBot.downloader.get_the_stuff(self.players[ctx.guild.id][1].loop, url, download=False, process=False)
        except:
            await change_later.delete()
            raise entryFailure
        if not info:
            await change_later.delete()
            raise entryFailure
        bassboost = False
        if url.split()[0].lower() == "-b":
            if len(url.split()) == 1:
                raise specific_error("You did not specify a search term or link to use after the Bass Boost flag.")
            bassboost = True
            url = " ".join(url.split()[1:])
        if info.get('url', '').startswith('ytsearch'):
            info = await self.BarryBot.downloader.get_the_stuff(
                self.players[ctx.guild.id][1].loop,
                url,
                download=False,
                process=True,
            )
            if not info:
                await change_later.delete()
                raise entryFailure
            url = info['entries'][0]['webpage_url']
            info = await self.BarryBot.downloader.get_the_stuff(self.players[ctx.guild.id][1].loop, url, download=False, process=False)
        try:
            self.players[ctx.guild.id][1].waitingTask.cancel()
        except:
            pass
        if 'entries' in info:
            #basically this would start a loop to queue each song from the list or something
            await change_later.delete()
            raise unsupportedPlaylist
        else:
            #check length of song and error if too long
            if info.get('duration',0) > 10800:
                await change_later.delete()
                raise songTooLong

            try:
                entry, position = await self.players[ctx.guild.id][1].add_entry(url, queuer=ctx.author, bass=bassboost)
            except:
                await change_later.delete()
                raise entryFailure
            sendMessage = "Found and queued **%s** at position %s in the queue"
            title = entry.name
        self.players[ctx.guild.id][1].chan = ctx.channel
        try:
            self.players[ctx.guild.id][1].waitingTask.cancel()
        except:
            pass
        if position == 1 and not self.players[ctx.guild.id][0].is_playing():
            #make the player play the song and pretty much dont even need to queue it
            sendMessage = "Found and queued **%s** to play as soon as possible!"
            sendMessage %= title
            await change_later.edit(content=sendMessage)
            await self.BarryBot.delete_later(change_later, 30)
            self.players[ctx.guild.id][1].temp_message = change_later
            cur_entr = self.players[ctx.guild.id][1].current_entry()
            await self.players[ctx.guild.id][1].entries[0].download()
            if cur_entr.skipped:
                return
            self.players[ctx.guild.id][1].message = await self.players[ctx.guild.id][1].chan.send("Now playing in "+self.players[ctx.guild.id][0].channel.name+": "+str(self.players[ctx.guild.id][1].entries[0]))
            await self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
        else:
            #just add the queue and download it but dont do anything else
            try:
                time_to = await self.players[ctx.guild.id][1].time_to(position)
                sendMessage += " - Rough estimation for when it will play: %s"
            except:
                time_to = "Error"
            try:
                sendMessage %= (title, position, time_to)
            except:
                sendMessage = "There was an error creating the final string, but "+title+" should have been queued anyways."
            await change_later.edit(content=sendMessage)
            await self.BarryBot.delete_later(change_later, 30)
            if position == 2:
                await self.players[ctx.guild.id][1].entries[1].download()
        #await ctx.send(sendMessage, delete_after=30)

    @commands.command(aliases=["vol"])
    async def volume(self, ctx, *, vol : float = 0.050305):
        '''Change the music player volume
        The player default is 30%.
        You can only change the volume by 30% at a time.
        Server mods can bypass the change restriction.
        The max volume is 200.'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        vol = vol/100
        if vol*100 == 0.050305:
            return await ctx.send("The current volume is at "+str(self.players[ctx.guild.id][1].volume * 100)+"%.", delete_after=15)
        if abs(self.players[ctx.guild.id][1].volume - vol) > 0.3 and not is_mod:
            raise drasticChange
        if vol*100 > 200 or vol*100 < 1:
            raise volOutOfBounds
        if self.players[ctx.guild.id][0].is_playing():
            self.players[ctx.guild.id][0].source.volume = vol
        self.players[ctx.guild.id][1].volume = vol
        await ctx.send("The volume has been changed to "+str(vol*100)+"%.", delete_after=15)

    @commands.command(aliases=["queue", "que", "list"])
    async def playlist(self, ctx):
        '''Show the playlist'''
        #add extra checks for the player
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        if len(self.players[ctx.guild.id][1].entries) == 0:
            return await ctx.send("There are no entries in the playlist!", delete_after=15)
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
        await ctx.send(finalStr, delete_after=60)

    @commands.command(aliases=["np", "playing"])
    async def nowplaying(self, ctx):
        '''Show the current playing song'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        if len(self.players[ctx.guild.id][1].entries) == 0:
            return await ctx.send("There is nothing playing because there are no entries in the playlist!", delete_after=15)
        if not self.players[ctx.guild.id][0].is_playing():
            return await ctx.send("The music is paused on: "+str(self.players[ctx.guild.id][1].entries[0]))
        await ctx.send("Currently Playing: "+str(self.players[ctx.guild.id][1].entries[0]))


    @commands.command(aliases=["reorder", "randomize"])
    async def shuffle(self, ctx):
        '''Randomize the order of the playlist'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        if not ctx.author.voice:
            try:
                is_mod = Perms.is_guild_mod(ctx)
            except:
                is_mod = False
            if is_mod:
                pass
            else:
                raise noChannel

        if len(self.players[ctx.guild.id][1].entries) == 0:
            return await ctx.send("There are no entries in the playlist!", delete_after=15)

        self.players[ctx.guild.id][1].shuffle()
        await ctx.send("The playlist has been shuffled.", delete_after=15)

    @commands.command(aliases=["listpurge"])
    @commands.check(Perms.is_guild_mod)
    async def clear(self, ctx):
        '''Empties the playlist completely. The current song keeps playing
        If you wish to just kill the entire player and remove it from the server, try !kys instead.'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        if len(self.players[ctx.guild.id][1].entries) == 0:
            return await ctx.send("There are no entries in the playlist.", delete_after=15)
        songs = len(self.players[ctx.guild.id][1].entries)
        self.players[ctx.guild.id][1].clear()
        return await ctx.send("I have removed "+str(songs)+" songs from the queue.", delete_after=20)


    @commands.command()
    async def skip(self, ctx, *, pos : int = 1):
        '''Skip the current entry or the entry at the given position
        If the person who added the song or a server mod uses this, it instantly works.
        Otherwise, if 5 skip votes in general are given, the skip passes.'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        pos -= 1
        try:
            self.players[ctx.guild.id][1].entries[pos]
        except:
            raise entryDoesntExist
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id in self.players[ctx.guild.id][1].entries[pos].skipvotes:
            raise alreadySkipped
        playlist = self.players[ctx.guild.id][1]
        if playlist.entries[pos].author_obj.id == ctx.author.id or is_mod:
            if pos == 0:
                if self.players[ctx.guild.id][0].is_playing():
                    await ctx.send("The current song (**"+playlist.entries[pos].name+"**) has been skipped.", delete_after=15)
                    try:
                        self.players[ctx.guild.id][0].stop()
                    except:
                        raise skipFailure
                else:
                    #await playlist.afterplay(None)
                    await ctx.send("The current song (**"+playlist.entries[pos].name+"**) has been skipped. The player wasn't playing (or was downloading), but the entry was removed.", delete_after=15)
                    playlist.entries[pos].skipped = True
                    if playlist.entries[pos].downloading:
                        return await playlist.afterplay(None)
                    playlist.entries.remove(playlist.entries[pos])
            else:
                playlist.entries[pos].skipped = True
                playlist.entries.remove(playlist.entries[pos])
                await ctx.send("The song (**"+playlist.entries[pos].name+"**) at position "+str(pos+1)+" has been removed.", delete_after=15)
        else:
            playlist.entries[pos].skipvotes.add(ctx.author.id)
            if len(playlist.entries[pos].skipvotes) >= 5:
                if pos == 0:
                    if self.players[ctx.guild.id][0].is_playing():
                        await ctx.send("Vote passed; current song (**"+playlist.entries[pos].name+"**) skipped.", delete_after=15)
                        try:
                            self.players[ctx.guild.id][0].stop()
                        except:
                            raise skipFailure
                    else:
                        await ctx.send("The current song (**"+playlist.entries[pos].name+"**) has been skipped. The player wasn't playing (or was downloading), but the entry was removed.", delete_after=15)
                        playlist.entries[pos].skipped = True
                        if playlist.entries[pos].downloading:
                            return await playlist.afterplay(None)
                        playlist.entries.remove(playlist.entries[pos])
                else:
                    playlist.entries[pos].skipped = True
                    playlist.entries.remove(playlist.entries[pos])
                    await ctx.send("The song (**"+playlist.entries[pos].name+"**) at position "+str(pos+1)+" has been removed by vote.", delete_after=15)
            else:
                # notify how many skips there are out of 5
                await ctx.send("Vote confirmed. The song (**"+playlist.entries[pos].name+"**) in position "+str(pos+1)+" needs "+str(5-len(playlist.entries[pos].skipvotes))+" more skip votes to be skipped.", delete_after=15)

    @commands.command(aliases=["unpause", "resume"])
    async def pause(self, ctx):
        '''Pause or unpause the music'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        playa = self.players[ctx.guild.id][0]
        playalist = self.players[ctx.guild.id][1]
        if playa.is_playing():
            playa.pause()
            return await ctx.send(ctx.author.name +" paused the music.")
        if len(playalist.entries) > 0 and playa.is_paused():
            playa.resume()
            return await ctx.send(ctx.author.name +" resumed the music.")
        if len(playalist.entries) == 0:
            await ctx.send("I cannot unpause because the playlist is empty.")
            try:
                playa.resume()
            except:
                pass




    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def download(self, ctx):
        ''' download the first entry
        Testing only'''

        await self.players[ctx.guild.id][1].entries[0].download()

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def forceplay(self, ctx):
        ''' force the first entry to play
        Testing only'''
        try:
            await self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
        except:
            traceback.print_exc()

    def recursivelyGetAudioFiles(self, dir):
        ''' get the files in a directory
        at this point, dir should be something like:
        C:/audiodirectory/
        '''
        output = []
        folders = []
        try:
            folders = [x for x in os.scandir(dir) if not x.is_file()]
        except:
            folders = []
        types = ("*.wav", "*.mp3", "*.flac", "*.ogg", "*.mp4", "*.mov", "*.m4v")
        for type in types:
            try:
                output.extend(glob.glob(os.path.join(dir, type)))
            except:
                pass
        for folder in folders:
            path = os.path.splitext(folder)[0]
            output.extend(self.recursivelyGetAudioFiles(path + "/"))
        return output

    @commands.command(hidden=True, aliases=["dir2play"])
    @commands.check(Perms.is_owner)
    async def recursiveplay(self, ctx, *, directory:str):
        ''' queue an entire directory of songs recursively.
        also works with -b'''

        try:
            # dont need to check for vc unless the command is open to all
            if ctx.guild.id not in self.players and ctx.author.voice:
                await self.summon.invoke(ctx)
            else:
                if ctx.author.voice:
                    if ctx.author.voice.channel.id != self.players[ctx.guild.id][
                        1].voice_channel.id and ctx.author.voice.channel.id != players[ctx.guild.id][0].channel.id:
                        if not (self.players[ctx.guild.id][0].is_playing()):
                            await self.summon.invoke(ctx)
            change_later = await ctx.send("Getting recursive listing...")
            try:
                self.players[ctx.guild.id][1].waitingTask.cancel()
            except:
                pass
            bassboost = False
            if directory.split()[0].lower() == "-b":
                if len(directory.split()) == 1:
                    await change_later.delete()
                    raise specific_error("You can't bass boost nothing.")
                bassboost = True
                directory = " ".join(directory.split()[1:])
            if directory[-1] != "/":
                directory += "/"
            entries = self.recursivelyGetAudioFiles(directory)


            position = 1
            count = 0
            entry = None
            title = ""
            try:
                for song in entries:
                    title = re.search(r"([^\\/]*$)", song).group(0)
                    entry, position = await self.players[ctx.guild.id][1].add_entry(queuer=ctx.author, bass=bassboost,
                                                                                    forced_info={"title": title, "filepath": song})
                    count += 1
            except:
                traceback.print_exc()
                await change_later.delete()
                raise entryFailure

            position -= len(entries) - 1

            sendMessage = "Found and queued **%s** songs starting at position %s in the queue"

            self.players[ctx.guild.id][1].chan = ctx.channel
            if position == 1 and not self.players[ctx.guild.id][0].is_playing():
                sendMessage = "Found and queued **%s** songs to play as soon as possible!"
                sendMessage %= count
                await change_later.edit(content=sendMessage)
                await self.BarryBot.delete_later(change_later, 30)
                self.players[ctx.guild.id][1].temp_message = change_later
                cur_entr = self.players[ctx.guild.id][1].current_entry()
                await self.players[ctx.guild.id][1].entries[0].download()
                if cur_entr.skipped:
                    return
                self.players[ctx.guild.id][1].message = await self.players[ctx.guild.id][1].chan.send(
                    "Now playing in " + self.players[ctx.guild.id][0].channel.name + ": " + str(
                        self.players[ctx.guild.id][1].entries[0]))
                await self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
            else:
                try:
                    time_to = await self.players[ctx.guild.id][1].time_to(position)
                    sendMessage += " - Rough estimation for when it will play: %s"
                except:
                    time_to = "Error"
                try:
                    sendMessage %= (count, position, time_to)
                except:
                    sendMessage = "There was an error creating the final string, but " + count + " songs should have been queued anyways."
                await change_later.edit(content=sendMessage)
                await self.BarryBot.delete_later(change_later, 30)
        except:
            traceback.print_exc()


    @commands.command(hidden=True, aliases=["dirplay"])
    @commands.check(Perms.is_owner)
    async def directoryplay(self, ctx, *, song:str):
        ''' play something straight from a filepath
        also allows the use of -b
        if you use -b you probably have to use quotes i dunno
        Testing only (functional)'''

        # dont need to check for vc unless the command is open to all
        if ctx.guild.id not in self.players and ctx.author.voice:
            await self.summon.invoke(ctx)
        else:
            if ctx.author.voice:
                if ctx.author.voice.channel.id != self.players[ctx.guild.id][1].voice_channel.id and ctx.author.voice.channel.id != players[ctx.guild.id][0].channel.id:
                    if not(self.players[ctx.guild.id][0].is_playing()):
                        await self.summon.invoke(ctx)
        change_later = await ctx.send("Adding manual link...")
        try:
            self.players[ctx.guild.id][1].waitingTask.cancel()
        except:
            pass
        bassboost = False
        if song.split()[0].lower() == "-b":
            if len(song.split()) == 1:
                await change_later.delete()
                raise specific_error("You can't bass boost nothing.")
            bassboost = True
            song = " ".join(song.split()[1:])
        if not os.path.isfile(song):
            await change_later.delete()
            raise specific_error("That file does not exist.")
        try:
            title = re.search(r"([^\\/]*$)", song).group(0)
            entry, position = await self.players[ctx.guild.id][1].add_entry(queuer=ctx.author, bass=bassboost, forced_info={"title":title, "filepath":song})
        except:
            traceback.print_exc()
            await change_later.delete()
            raise entryFailure
        sendMessage = "Found and queued **%s** at position %s in the queue"

        self.players[ctx.guild.id][1].chan = ctx.channel
        if position == 1 and not self.players[ctx.guild.id][0].is_playing():
            sendMessage = "Found and queued **%s** to play as soon as possible!"
            sendMessage %= title
            await change_later.edit(content=sendMessage)
            await self.BarryBot.delete_later(change_later, 30)
            self.players[ctx.guild.id][1].temp_message = change_later
            cur_entr = self.players[ctx.guild.id][1].current_entry()
            await self.players[ctx.guild.id][1].entries[0].download()
            if cur_entr.skipped:
                return
            self.players[ctx.guild.id][1].message = await self.players[ctx.guild.id][1].chan.send("Now playing in "+self.players[ctx.guild.id][0].channel.name+": "+str(self.players[ctx.guild.id][1].entries[0]))
            await self.players[ctx.guild.id][1].entries[0].play(self.players[ctx.guild.id][0])
        else:
            try:
                time_to = await self.players[ctx.guild.id][1].time_to(position)
                sendMessage += " - Rough estimation for when it will play: %s"
            except:
                time_to = "Error"
            try:
                sendMessage %= (title, position, time_to)
            except:
                sendMessage = "There was an error creating the final string, but "+title+" should have been queued anyways."
            await change_later.edit(content=sendMessage)
            await self.BarryBot.delete_later(change_later, 30)

    @commands.command()
    async def seek(self, ctx, position:str):
        ''' Seek in the current audio to a position
        The given position should be in an easy to interpret format.
        The most complicated format is: HH:MM:SS.msms
        If simply an integer or decimal is given, it uses that many seconds to seek to.
        All seek times are from the beginning of the file.
        If the seek time is not within the bounds of the file, the audio ends and the playlist continues.
        If there is an error in your formatting, the audio ends and the playlist continues.'''
        if ctx.guild.id not in self.players:
            raise alreadyLeft
        real_playa = self.players[ctx.guild.id][0]
        if not real_playa.is_playing():
            raise specific_error("The music is paused or nothing is queued.")

        entry = self.players[ctx.guild.id][1].entries[0]
        playa = self.players[ctx.guild.id][1]
        try:
            self.players[ctx.guild.id][0].source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(entry.filename, before_options="-ss "+position), volume=playa.volume)
            try:
                pos = int(position)
            except:
                return await ctx.send("I moved the current position to "+position, delete_after=15)
            hours = (int(pos/60/60))
            pos = pos - 60*60*hours
            mins = (int(pos/60))
            pos = pos - 60*mins
            return await ctx.send(f"I moved the current position to {hours:02}:{mins:02}:{pos:02}", delete_after=15)
        except:
            traceback.print_exc()



class Entry:
    def __init__(self, playlist, queuer, name, duration=0, filename=None, url=None, bass=False, Filepath=None):
        self.downloading = False
        self.is_downloaded = False if not Filepath else True
        self.playlist = playlist
        self.author = queuer.name
        self.author_obj = queuer
        self.name = name
        self.filepath = Filepath #this is used if we are not going to download the file
        self.filename = filename #this is the direct filepath for a youtube download
        self.duration = duration
        self.skipvotes = set()
        self.skipped = False
        self.url = url
        self.bassy = bass
        self.boosted = False
        
    def __str__(self):
        if self.bassy:
            return "**"+self.name+"** queued by "+self.author+". **Duration**: "+str(datetime.timedelta(seconds=self.duration))+" **Bass Boosted**"
        else:
            return "**"+self.name+"** queued by "+self.author+". **Duration**: "+str(datetime.timedelta(seconds=self.duration))

        
        
    async def download(self):
        if self.filepath:
            self.downloading = False
            self.is_downloaded = True
            return
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
            result = await self.playlist.downloader.get_the_stuff(self.playlist.loop, self.url, download=True)
        except:
            raise downloaderBroke(self.playlist.stored_ctx)
        if result is None:
            raise downloaderBroke(self.playlist.stored_ctx)
        self.downloading = False
        self.is_downloaded = True
        if self.skipped:
            return await self.playlist.prune_song(self)
        if self.bassy:
            pass
            # if not self.boosted:
            #     try:
            #         proc = await asyncio.create_subprocess_exec("ffmpeg", "-loglevel", "quiet", "-y", "-i", self.filename, "-af",
            #                                                     "bass=g=15", self.filename+"_bass_"+self.filename[-5:])
            #         await proc.wait()
            #         await self.playlist.prune_song(self)
            #         self.filename = self.filename+"_bass_"+self.filename[-5:]
            #     except:
            #         traceback.print_exc()
            #     self.boosted = True

    async def download_play(self, player):
        ''' this downloads and plays a song. this is a fallback for if somehow, a song gets deleted or is never downloaded'''
        if self.playlist.voice_channel.id != player.channel.id:
            self.playlist.voice_channel = player.channel
        try:
            await self.playlist.message.edit(content="Now (redownloading) in "+self.playlist.voice_channel.name+": "+str(self))
        except:
            pass
        if self.skipped: #the song was skipped before done downloading
            return await self.playlist.prune_song(self)
        await self.download()
        await self.play(player)
        
    async def play(self, player):
        ''' this plays the song '''
        #player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song), volume=0.5), after=lambda e: print("done", e))
        if self.downloading:
            await self.playlist.message.edit(content="Now (finishing download) in "+self.playlist.voice_channel.name+": "+str(self))
            while self.downloading:
                await asyncio.sleep(0.25)
        if not self.is_downloaded:
            self.playlist.loop.create_task(self.download_play(player))
            return
        if self.skipped:
            return await self.playlist.prune_song(self)
        self._play_sync(player)
            
    def _play_sync(self, player):
        ''' i lied, this plays the song'''
        if self.bassy:
            player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename, options="-af bass=g=15"), volume=self.playlist.volume), after=self._afterplay)
        else:
            player.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename), volume=self.playlist.volume), after=self._afterplay)
        
    def _afterplay(self, error):
        coro = self.playlist.afterplay(error)
        future = asyncio.run_coroutine_threadsafe(coro, self.playlist.loop)
        future.result()
        
        
    
            
        
class Playlist:
    def __init__(self, bot, chan, message, voice_channel, player, ctx):
        self.bot = bot #BarryBot
        self.downloader = bot.downloader
        self.entries = deque()
        self.loop = bot.loop
        self.chan = chan
        self.message = message
        self.temp_message = None
        self.voice_channel = voice_channel
        self.volume = float(bot.settings[chan.guild.id].features["playervol"])/100
        self.player = player
        self.stored_ctx = ctx
        self.waitingTask = None
        
    def __iter__(self):
        return iter(self.entries)
    def shuffle(self):
        random.shuffle(self.entries)
    def clear(self):
        if self.player.players[self.chan.guild.id][0].is_playing():
            playing = self.entries[0]
            self.entries.clear()
            self.entries.append(playing)
        else:
            self.entries.clear()
        
    async def add_entry(self, url=None, queuer=None, bass=False, forced_info=None, **meta):
        if forced_info:
            entry = Entry(
                self,
                queuer,
                forced_info.get('title', "Untitled"),
                0,
                forced_info.get("filepath", "Error"),
                url,
                bass,
                forced_info.get("filepath", "Error"),
            )
            self.entries.append(entry)
            return entry, len(self.entries)
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
            url,
            bass,
            **meta
        )
        
        self.entries.append(entry)
        if self.entries[0] is entry:
            pass
            #play the first song
            
        return entry, len(self.entries)
    async def time_to(self, position):
        estimated_time = sum([entry.duration for entry in islice(self.entries, position-1)])
        return datetime.timedelta(seconds=estimated_time)
    
    def current_entry(self):
        return self.entries[0]
        
    async def afterplay(self, error, playNext=True):
        if error:
            print(error)
            raise playerError(self.stored_ctx)
        try:
            if self.entries[0].filepath: #we are assuming we were triggering this function based off of playing the first entry and we are going to have serious issues if that isnt the case
                pass #this just skips deleting the file if it was triggered by something other than a link or search, something we dont want to deleted
            else:
                dontDelete = False
                if len(self.entries) > 1:
                    otherentries = [entry for entry in self.entries] #this is unfortunate because you arent allowed to copy.deepcopy() a deque in another thread... something about pickling, im no genius
                    otherentries.pop(0)
                    for entry in otherentries:
                        if entry.filename == self.entries[0].filename:
                            dontDelete = True
                            break
                if not dontDelete:
                    done = False
                    for x in range(10): #trying 10 good times
                        try:
                            os.unlink(self.entries[0].filename)
                            done = True
                            break
                        except:
                            await asyncio.sleep(0.25)
                    if not done:
                        self.loop.create_task(self.prune_song(self.entries[0]))
            self.entries.popleft()
            try:
                await self.message.delete()
            except:
                pass
            try:
                await self.temp_message.delete()
            except:
                pass
            if self.voice_channel.id != self.player.players[self.chan.guild.id][0].channel.id:
                self.voice_channel = self.player.players[self.chan.guild.id][0].channel
            if len(self.entries) > 0 and playNext:
                editLater = False
                if not self.current_entry().is_downloaded:
                    self.message = await self.chan.send("Now (downloading) in "+self.voice_channel.name+": "+str(self.entries[0]))
                    editLater = True
                try:
                    await self.entries[0].download()
                except:
                    traceback.print_exc()
                try:
                    await self.entries[0].play(self.player.players[self.chan.guild.id][0])
                except:
                    traceback.print_exc()
                if editLater:
                    await self.message.edit(content="Now playing in "+self.voice_channel.name+": "+str(self.entries[0]))
                else:
                    self.message = await self.chan.send("Now playing in "+self.voice_channel.name+": "+str(self.entries[0]))
                if len(self.entries) > 1:
                    await self.entries[1].download()
            else:
                lengthoftime = int(self.bot.settings[self.chan.guild.id].features["playerleave"])
                await self.chan.send("The playlist is empty. The music has ended.", delete_after=lengthoftime)
                self.waitingTask = asyncio.ensure_future(self._eventually_leave(lengthoftime))
        except:
            traceback.print_exc()

    async def _eventually_leave(self, time):
        ''' leave the channel eventually, but this is cancellable'''
        try:
            await asyncio.sleep(time)
            await self.player.players[self.chan.guild.id][0].disconnect()
            del self.player.players[self.chan.guild.id]
        except:
            pass


    async def prune_song(self, given): #given is an Entry object
        ''' given an entry it tries to run an afterplay but doesnt play anything after (basically it just deletes the file)'''
        #removes the song from the directory but still leaves it if it exists later in the playlist for some reason
        #this is meant to just clean up the directory, not remove stuff from the playlist
        try:
            if given.filepath:
                return
            else:
                dontDelete = False
                if len(self.entries) > 1:
                    otherentries = [entry for entry in self.entries]
                    otherentries.pop(0)
                    for entry in otherentries:
                        if entry.filename == given.filename:
                            dontDelete = True
                            break
                if not dontDelete:
                    done = False
                    for x in range(30): #give it a good 30 tries instead because some songs could download for a long time
                        try:
                            os.unlink(given.filename)
                            done = True
                            break
                        except OSError as e:
                            if e.errno == errno.ENOENT:
                                done = True
                                print("tried to delete a file that doesn't exist. exiting early.")
                                break
                            else:
                                print("failed to delete currently downloading song")
                            await asyncio.sleep(0.5)
                    if not done:
                        self.loop.call_later(60, self.prune_song_retry, given)
        except:
            traceback.print_exc()
    def prune_song_retry(self, given): #its prune_song but a retry because sometimes the download takes way too long and we dont want to waste time in a loop
        ''' to keep trying 30 times every 15 seconds every minute because we dont want to stick to this loop forever
        also this is a failsafe to hopefully delete stuff if it ends up skipped or loose and should be deleted'''
        self.loop.create_task(self.prune_song(given)) #but now that i think back, this might be unnecessary... still, its a fallback if somehow the song starts downloading after being queued to prune or ends up being pulled by another program and cant be deleted
        
        
        
        
class Downloader:
    def __init__(self, download_path):
        self.threadpool = ThreadPoolExecutor(max_workers=2)
        self.ytdl = youtube_dl.YoutubeDL(ytdl_options)
        self.tPN = self.ytdl.params['outtmpl']
        self.ytdl.params['outtmpl'] = os.path.join(download_path, self.tPN)
        self.path = download_path
        
        
    async def get_the_stuff(self, loop, *args, **kwargs):
        return await loop.run_in_executor(self.threadpool, functools.partial(self.ytdl.extract_info, *args, **kwargs))
        