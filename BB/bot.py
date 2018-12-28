import os
import re
import asyncio
import unicodedata
import aiohttp
import random
import discord
import traceback

from discord.ext import commands
from decimal import Decimal


#from BB.file import class
from BB.conf import Conf
from BB.permissions import *
from BB.unogame import The_Game, Uno
from BB.player import Player, Downloader
from BB.settings import Settings, ServerSettings
from BB.mods import Moderation
from BB.misc import GenericPaginator
from BB.idlerpg import *
from BB.bar import *
from BB.reminder import Reminders


class Barry(discord.Client):

    def __init__(self, bot, loop):
        self.config = Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+"/config/config.ini")
        self.THE_SECRET_TOKEN = self.config.THE_TOKEN
        self.loop = loop
        self.bot = bot

        self.BarTalk_sessions = {}
        self.downloader = Downloader(self.config.download_path)
        self.bot.add_cog(MainCommands(self.bot, self.config)) #add the main command class for laziness sake
        self.bot.add_cog(self) #also a cheaty way to just fit all the commands into this class
        self.bot.add_cog(Uno(self.bot, self.config, self.loop, self))        
        self.bot.add_cog(Player(self.bot, self.config, self.loop, self))
        self.bot.add_cog(Settings(self.bot, self.config, self.loop, self))
        self.bot.add_cog(Moderation(self.bot, self.config, self.loop, self))
        #self.bot.add_cog(RPG(self.bot, self.config, self.loop, self))
        self.bot.add_cog(BarTalk(self.bot, self.config, self))
        self.bot.add_cog(Reminders(self.bot, self.config, self.loop, self))

        self.UnoGames = {}
        self.RPGSessions = {}
        self.settings = {}
        self.paginators = set()
        self.streamMessages = {}
        
        self.logchan = None


        self.blacklist = set()

        decimal.getcontext().prec = 800

        
        
        super().__init__()
    def guild_settings(self, ctx): #this is for general use to retrieve the context's server specific settings quickly
        ''' this just returns a settings object quickly for the context
        if it returns none then there was something wrong
        WARNING: this should not be used if modifications to server settings need to be done.
        '''
        try:
            if ctx.guild.id in self.settings:
                return self.settings[ctx.guild.id]
        except: # something is terribly wrong with the context
            print("something broke")
            return None


    def initializeRPGSessions(self):
        '''Just set the dict up'''
        print(self.bot.guilds)
        #print(self.guilds)
        for g in self.bot.guilds:
            print(g)
            try:
                if self.settings[g.id].features["rpg_Enabled"] == "1":
                    chanID = self.settings[g.id].features["rpg_channel_ID"]
                    chan = discord.utils.get(g.text_channels, id=int(chanID))
                    if chan is None:
                        print("RPG channel for guild "+g.name+" ID "+str(g.id)+" not found.")
                    else:
                        self.RPGSessions[g.id] = RPGSession(self.bot, g, chan, self)
            except:
                traceback.print_exc()

    async def createBarTalkSessions(self):
        '''Fired at on_ready to create the bar sessions, resetting the brain and everything on login'''
        self.BarTalk_sessions = {}
        for guild in self.bot.guilds:
            self.BarTalk_sessions[guild.id] = Brain(guild.id, self.config)
        print("Brain fully reinitialized...")

    def createSingleBarTalkSession(self, guildID):
        '''Fires on server join. Only for this purpose'''
        self.BarTalk_sessions[guildID] = Brain(guild.id, self.config)
        print("I joined a new server. I have created a default BarTalk memory for it.")


    @commands.command(hidden=True)
    async def blacklistme(self, ctx):
        self.blacklist.add(ctx.message.author.id)

    @commands.command(hidden=True)
    #@commands.check(Perms.is_owner)
    async def respond(self, ctx, *, words):
        '''Literally replies with exactly what you said'''
        await ctx.send(words)
        #await self.logchan.send(words)

    @commands.command()
    async def report(self, ctx, *, words):
        ''' Report an issue to the developers '''
        await self.logchan.send("REPORT - "+ctx.author.name+" in "+ctx.guild.name+": "+words)

    @commands.group(hidden=True)
    async def cgt(self, ctx):
        '''g'''
        print(ctx.command.name)
        await ctx.send(str(discord.utils.get(ctx.guild.text_channels, id=0)))

    @cgt.command(hidden=True)
    async def rer(self, ctx):
        '''g'''
        print(ctx.command.name)
        print(ctx.command.parent.name)
        print(ctx.command.qualified_name)

    @commands.command(hidden=True)
    async def roletest(self, ctx, *, role : discord.Role):
        print(role)

    @commands.command(hidden=True)
    async def mathmult(self, ctx, *, words):
        '''Multiply all arguments repeatedly.'''
        result = Decimal("1.0")
        args = words.split()
        for g in args:
            try:
                result = Decimal(g) * result
            except:
                pass
        await ctx.send("Heres the answer lmao: "+str(result))


    @commands.command(hidden=True)
    async def atvatar(self, ctx, *, id : str):
        ''' input id i give avatar ok'''
        try:
            await ctx.send((await commands.UserConverter().convert(ctx, id)).avatar_url, delete_after=15)
        except:
            traceback.print_exc()

    @commands.command(aliases=["colors"], usage="[color]")
    async def color(self, ctx, *, colorStr : str = "give me the list"):
        ''' Change your color to a predefined one
        This will only work if the feature is enabled on your server and roles have been added to the list of colors
        To add them to the list, create a role and place it at the top of the hierarchy. Leave the permissions default.
        Set the color of the role to what you want and use !feat colors to add it to the list of colors.
        !color              - Show the list of colors available
        !color [color name] - Set your color to that one
            Note: If you say the name of your current color, it is removed.
        !color remove       - Remove your color
            Note: Naming a color "remove" will make it unusable.
        '''
        try:
            setting = self.settings[ctx.guild.id]
            if setting.features["colors_Enabled"] == "0":
                return await ctx.send("Color Roles are not enabled on your server. Ask an Admin about it.", delete_after=15)
            if len(setting.features["colors_IDs"].split()) == 0:
                return await ctx.send("Color Roles are enabled but there are no roles set. Ask an Admin about it.", delete_after=15)
            setting.sanity_check_individual("Features", "sublists_IDs", ctx.guild)
            if colorStr == "give me the list":
                p = GenericPaginator(self, ctx, markdown="css")
                for x in setting.features["colors_IDs"].split():
                    p.add_line(line=str(discord.utils.get(ctx.guild.roles, id=int(x))))
                msg = await ctx.send("Here is a list of all colors on the server. Pick one using !color [colorname].\n"+str(p))
                p.msg = msg
                p.original_msg = "Here is a list of all colors on the server. Pick one using !color [colorname].\n"
                await p.add_reactions()
                await p.start_waiting()
                return

            list_of_colors = {discord.utils.get(ctx.guild.roles, id=int(x)).name:discord.utils.get(ctx.guild.roles, id=int(x)) for x in setting.features["colors_IDs"].split()}
            if colorStr in list_of_colors:
                user_roles = {x.name:x for x in ctx.author.roles}
                if colorStr in user_roles:
                    try:
                        await ctx.author.remove_roles(user_roles[colorStr])
                    except:
                        raise specific_error("Something went wrong with removing your current color. Permission issue? Other error?")
                    return await ctx.send("I have removed your color.", delete_after=15)
                to_remove = set()
                for x in user_roles:
                    if x in list_of_colors:
                        to_remove.add(list_of_colors[x])
                if len(to_remove) != 0:
                    await ctx.author.remove_roles(*[x for x in to_remove])
                try:
                    await ctx.author.add_roles(list_of_colors[colorStr])
                except:
                    raise specific_error("Something went wrong with adding your color. Permission issue? Other error?")
                return await ctx.send("I have changed your color to "+colorStr, delete_after=15)
            else:
                return await ctx.send("That is not a color in the given list. Use proper capitalization. Copy-paste if you have to.", delete_after=15)
        except:
            traceback.print_exc()

    @commands.command(aliases=["sub", "unsubscribe", "unsub"], usage="[sublist]")
    async def subscribe(self, ctx, *, subStr : str = "give me the list"):
        ''' Subscribe to or unsubscribe from a sublist
        This will only work if the feature is enabled on your server and roles have been added to the list.
        To add them to the list, create a role and place it at the bottom of the hierarchy. Leave the permissions default.
        Set the name to what you want and use !feat sublists to add it to the list.
        !sub            - Show the list of usable options
        !sub [name]     - Sub or unsub from a specific option
        '''
        setting = self.settings[ctx.guild.id]
        if setting.features["sublists_Enabled"] == "0":
            return await ctx.send("Subscribing is not enabled on your server. Ask an Admin about it.", delete_after=15)
        if len(setting.features["sublists_IDs"].split()) == 0:
            return await ctx.send("Subscribing is enabled but there are no roles set. Ask an Admin about it.", delete_after=15)
        setting.sanity_check_individual("Features", "sublists_IDs", ctx.guild)
        if subStr == "give me the list":
            p = GenericPaginator(self, ctx, page_header='List Name  |  Subscribed (Yes/No)', markdown="css")
            user_roles = {str(x.id):x for x in ctx.author.roles}
            for x in setting.features["sublists_IDs"].split():
                p.add_line(line=str(discord.utils.get(ctx.guild.roles, id=int(x)))+"  -  "+("Yes" if x in user_roles else "No"))
            msg = await ctx.send("Here is a list of all sublists on the server. Pick any by using !sub [rolename].\n"+str(p))
            p.msg = msg
            p.original_msg = "Here is a list of all sublists on the server. Pick any by using !sub [rolename].\n"
            await p.add_reactions()
            await p.start_waiting()
            return

        list_of_subs = {discord.utils.get(ctx.guild.roles, id=int(x)).name:discord.utils.get(ctx.guild.roles, id=int(x)) for x in setting.features["sublists_IDs"].split()}
        try:
            if subStr in list_of_subs:
                user_roles = {x.name:x for x in ctx.author.roles}
                if subStr in user_roles:
                    try:
                        await ctx.author.remove_roles(user_roles[subStr])
                    except:
                        raise specific_error("Something went wrong with removing the subscription. Permission issue??")
                    return await ctx.send("I have unsubbed you from "+subStr, delete_after=15)
                try:
                    await ctx.author.add_roles(list_of_subs[subStr])
                except:
                    traceback.print_exc()
                    raise specific_error("Something went wrong with adding your role. Permission issue??")
                return await ctx.send("I have subscribed you to "+subStr, delete_after=15)
            else:
                return await ctx.send("That is not an option in the list. Use proper capitalization. Copy-paste if you have to.", delete_after=15)
        except:
            traceback.print_exc()







    @commands.command(hidden=True, aliases=["shtudown", "sd", "shtdon", "shutdwon"])
    @commands.check(Perms.is_owner)
    async def shutdown(self, ctx):
        await ctx.send("Shutting down. I will not restart until manually run again.")
        await self.logout()
        await self.bot.logout()

    @commands.command()
    async def emoji(self, ctx):
        ''' Send back the code for the emote found'''
        try:
            output = ""
            for char in " ".join(ctx.message.content.split()[1:]):
                num = f'{ord(char):x}'
                output += "\n"+unicodedata.name(char, "oof")+" "+f'\\U{num:>08}'
            await ctx.send(output)
        except:
            traceback.print_exc()


    
    async def delete_later(self, message, time=15): #self.loop.create_task(self._actually_delete_later(message, time))
        self.loop.create_task(self._actually_delete_later(message, time))
    async def _actually_delete_later(self, message, time=15):
        await asyncio.sleep(time)
        try:
            await message.delete()
        except:
            pass

    async def check_looper_slow(self):
        ''' This is the function which holds a loop that begins in on_ready and runs every 5 minutes'''
        to_remove_Paginators = set()
        for paginator in self.paginators:
            if paginator.ended:
                to_remove_Paginators.add(paginator)
        for nator in to_remove_Paginators:
            self.paginators.remove(nator)



        await asyncio.sleep(300)
        self.loop.create_task(self.check_looper_slow())

    async def check_looper_fast(self):
        ''' This is the function which holds a loop that begins in on_ready and runs every 30 seconds'''



        await asyncio.sleep(30)
        self.loop.create_task(self.check_looper_fast())






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

    @commands.command(hidden=True)
    async def embedtest(self, ctx):
        try:
            e = discord.Embed(title="Title", description="Description\nDescription line 2", url="https://google.com", timestamp=ctx.message.created_at, color=discord.Color.dark_red())
            e.set_author(name="author name", url="https://google.com", icon_url=ctx.author.avatar_url)
            e.set_footer(text="footer text", icon_url="https://b.thumbs.redditmedia.com/lFyUdvrOpXS9hrZQDKK-iH3QEq7JyhH909SZZfSsszA.jpg")
            e.set_image(url="https://b.thumbs.redditmedia.com/BW9495LYTE5NugV2--7Vi7BhzyJtnTAILhoj9RcqVYI.jpg")
            e.set_thumbnail(url="https://b.thumbs.redditmedia.com/-TND4M2kMG9KaEzhgwpUmgvIqJEYm6fUC_IMljjS_DA.jpg")
            e.add_field(name="field name 1", value="field value 1")
            e.add_field(name="field name 2", value="field value 2")
            e.add_field(name="field name 3", value="field value 2")
            e.add_field(name="field name 4", value="field value 2")
            e.add_field(name="field name 5", value="field value 2")
            e.add_field(name="field name 6", value="field value 2")
            e.add_field(name="field name 7", value="field value 2")
            e.add_field(name="field name 8", value="field value 2")
            e.add_field(name="field name 9", value="field value 2")
            e.add_field(name="field name 10", value="field value 2")
            e.add_field(name="field name 11", value="field value 2")
            e.add_field(name="field name 12", value="field value 2")
            e.add_field(name="field name 13", value="field value 2")
            e.add_field(name="field name 14", value="field value 2")
            e.add_field(name="field name 15", value="field value 2")
            e.add_field(name="field name 16", value="field value 2")
            e.add_field(name="field name 17", value="field value 2")


            await ctx.send(embed=e)
        except:
            traceback.print_exc()



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
    
    
    
    

        