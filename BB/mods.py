import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter, GenericPaginator


class Moderation(commands.Cog):
        #for things like linkblock or whatever
        #or maybe role specific muting

    def __init__(self, bot, config, loop, BarryBot):
        self.bot = bot
        self.loop = loop
        self.config = config
        self.BarryBot = BarryBot
        
    @commands.command(aliases=["unmute", "silence"])
    async def mute(self, ctx):
        ''' Make a user unable to send text messages'''
        # if not Perms.has_specific_set_perms(ctx, self.BarryBot.settings[ctx.guild.id]):
        #     Perms.is_guild_mod(ctx)
        raise unimplemented


    @commands.command(usage="@user 'reason'")
    async def ban(self, ctx, person : discord.Member, rezon : str = None):
        ''' Ban a user from the server
        This simply removes a user from the server permanently.
        Messages from them are NOT cleaned up.
        If you wish to supply a ban reason, surround it with quotes after the member name.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        dead_guy_lvl = Perms.get_custom_perms_by_member(person, setting)
        if executor_lvl <= dead_guy_lvl:
            raise specific_error("You can't ban someone of equal or higher power than yourself.")
        try:
            if str(person.id) in setting.Features["bar_ignoreuser_IDs"].split():
                setting.modify("Features", "bar_ignoreuser_IDs", " ".join([pid for pid in setting.Features["bar_ignoreuser_IDs"].split() if id != str(person.id)]))
            await person.ban(reason=rezon, delete_message_days=0)
        except:
            raise specific_error("Something went wrong when trying to ban this person. Maybe I don't have permission?")
        await ctx.send("I have banned "+person.name+" permanently for '"+str(rezon)+"'")

    @commands.command(usage="@user 'reason'")
    async def cleanban(self, ctx, person : discord.Member, rezon : str = None):
        ''' Ban a user from the server and delete their messages
        This removes a user from the server permanently in addition to deleting all of their messages.
        If you wish to supply a ban reason, surround it with quotes after the member name.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        dead_guy_lvl = Perms.get_custom_perms_by_member(person, setting)
        if executor_lvl <= dead_guy_lvl:
            raise specific_error("You can't ban someone of equal or higher power than yourself.")
        try:
            if str(person.id) in setting.Features["bar_ignoreuser_IDs"].split():
                setting.modify("Features", "bar_ignoreuser_IDs", " ".join([pid for pid in setting.Features["bar_ignoreuser_IDs"].split() if id != str(person.id)]))
            await person.ban(reason=rezon, delete_message_days=0)
        except:
            raise specific_error("Something went wrong when trying to ban this person. Maybe I don't have permission?")
        try:
            def check_msg(message):
                if message.author.id == person.id:
                    return True
                else:
                    return False
            for chan in ctx.guild.text_channels:
                await chan.purge(limit=None, check=check_msg, bulk=False)
        except:
            raise specific_error("Something went wrong when deleting his messages. Maybe I don't have permission?")
        await ctx.send("I have banned and erased the history of "+person.name+" for '"+str(rezon)+"'")

    @commands.command(aliases=["pardon", "allow"])
    async def unban(self, ctx, person : discord.User):
        ''' Unban a user from the server'''
        try:
            await ctx.guild.unban(person)
        except:
            raise specific_error("Something went wrong when unbanning this person. Maybe I don't have permission or they are not banned?")
        await ctx.send("I have unbanned "+person.name+"")

    @commands.command()
    async def kick(self, ctx, person : discord.Member, rezon : str = None):
        ''' Kick a user from the server
        This removes a user from the server.
        Messages from them are NOT cleaned up.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        dead_guy_lvl = Perms.get_custom_perms_by_member(person, setting)
        if executor_lvl <= dead_guy_lvl:
            raise specific_error("You can't kick someone of equal or higher power than yourself.")
        try:
            if str(person.id) in setting.Features["bar_ignoreuser_IDs"].split():
                setting.modify("Features", "bar_ignoreuser_IDs", " ".join([pid for pid in setting.Features["bar_ignoreuser_IDs"].split() if id != str(person.id)]))
            await person.kick(reason=rezon)
        except:
            raise specific_error("Something went wrong when kicking this person. Maybe I don't have permission?")
        await ctx.send("I have kicked "+person.name+" from the server.")

    @commands.group(aliases=["del"], invoke_without_command=True)
    async def delete(self, ctx, *args):
        ''' Delete a number of messages or only certain ones
        NOTE: The number given is the number of messages searched, NOT the number deleted.
        !del [specify a number]     - Delete this many messages in the channel
        !del [specify a user]       - Delete everything from this user in the channel
        !del [user] [number]        - Delete this many messages from this user in the channel
        !del bots                   - Delete everything from any bot in the channel
        !del bots [specify a number]- Delete this many messages from bots in the channel
        !del phrase "phrase"        - Delete anything with the phrase from the channel
        !del all                    - Delete the whole history of the current channel
        !del all [specify a number] - Delete this many messages from every channel
        !del all [specify a user]   - Delete everything from this user in the server
        !del all bots               - Delete everything from any bot in the server
        !del all phrase "phrase"    - Delete anything with the phrase from the server
        Include the quotes in the phrase commands.
        Each command requires confirmation to execute.'''
        try:
            amount_to_delete = 0
            member_to_delete = None
            def check_if_bot(message):
                return message.author.bot
            def check_if_author(reaction, user):
                return reaction.emoji == "👌" and user.id == ctx.author.id
            if len(args) == 0:
                raise specific_error('!del [specify a number]     - Delete this many messages in the channel\n!del [specify a user]       - Delete everything from this user in the channel\n!del [user] [number]        - Delete this many messages from this user in the channel\n!del bots                   - Delete everything from any bot in the channel\n!del bots [specify a number]- Delete this many messages from bots in the channel\n!del phrase "phrase"        - Delete anything with the phrase from the channel\n!del all                    - Delete the whole history of the current channel\n!del all [specify a number] - Delete this many messages from every channel\n!del all [specify a user]   - Delete everything from this user in the server\n!del all bots               - Delete everything from any bot in the server\n!del all phrase "phrase"    - Delete anything with the phrase from the server\nInclude the quotes in the phrase commands.\nEach command requires confirmation to execute.')
            if args[0] == "bots":
                try:
                    amount_to_delete = int(args[1])
                    delete_later = await ctx.send("I will be searching {} messages and deleting messages found by bots from this channel only.\nHit me with a 👌 to confirm this (you have 15 seconds)".format(amount_to_delete))
                except:
                    amount_to_delete = None
                    delete_later = await ctx.send("I will be deleting every message made by bots from this channel only.\nHit me with a 👌 to confirm this (you have 15 seconds)")
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                await delete_later.edit(content="Working....")
                try:
                    ripped = await ctx.channel.purge(limit=amount_to_delete, check=check_if_bot, before=delete_later, bulk=True)
                except:
                    await delete_later.delete()
                    raise specific_error("I attempted to delete only messages written by bots in this channel but failed. Maybe I don't have permission?")
                await delete_later.delete()
                return await ctx.send("I have deleted {} message(s)...".format(len(ripped)), delete_after=5)
            elif args[0] == "phrase":
                try:
                    the_phrase = args[1]
                except:
                    raise specific_error("You did not specify a phrase to delete.")
                def check_if_phrase(message):
                    return the_phrase in message.content
                delete_later = await ctx.send("I will be deleting messages from anyone containing the phrase '{}' from this channel only. This is a liberal deletion, meaning that if it is just 1 letter, it may delete hundreds of messages.\nHit me with a 👌 to confirm this (you have 15 seconds)".format(the_phrase))
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                await delete_later.edit(content="Working....")
                try:
                    ripped = await ctx.channel.purge(limit=None, check=check_if_phrase, before=delete_later, bulk=True)
                except:
                    await delete_later.delete()
                    raise specific_error("I attempted to delete messages containing a phrase from this channel but failed. Maybe I don't have permission?")
                await delete_later.delete()
                return await ctx.send("I have deleted {} message(s) including your own...".format(len(ripped)), delete_after=5)
            else:
                try:
                    amount_to_delete = int(args[0]) + 1
                except:
                    try:
                        amount_to_delete = int(args[1]) + 1
                    except:
                        pass
                try:
                    member_to_delete = await commands.MemberConverter().convert(ctx, args[0])
                except:
                    pass
            if amount_to_delete == 0 and member_to_delete is not None:
                def check_if_member(message):
                    return message.author.id == member_to_delete.id
                delete_later = await ctx.send("I will be deleting ALL messages by {} in this channel only.\nHit me with a 👌 to confirm this (you have 15 seconds)".format(member_to_delete.name))
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                await delete_later.edit(content="Working....")
                try:
                    ripped = await ctx.channel.purge(limit=None, check=check_if_member, before=delete_later, bulk=True)
                except:
                    await delete_later.delete()
                    raise specific_error("I attempted to delete all messages from a member in this channel but failed. Maybe I don't have permission?")
                await delete_later.delete()
                return await ctx.send("I have deleted {} message(s)...".format(len(ripped)), delete_after=5)
            elif amount_to_delete > 0 and member_to_delete is None:
                delete_later = await ctx.send("I will be searching for and deleting {} messages from this channel from anyone.\nHit me with a 👌 to confirm this (you have 15 seconds)".format(amount_to_delete))
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                await delete_later.edit(content="Working....")
                try:
                    ripped = await ctx.channel.purge(limit=amount_to_delete, check=None, before=delete_later, bulk=True)
                except:
                    await delete_later.delete()
                    raise specific_error("I attempted to delete a number of messages from anyone in this channel but failed. Maybe I don't have permission?")
                await delete_later.delete()
                return await ctx.send("I have deleted {} message(s)...".format(len(ripped)), delete_after=5)
            elif amount_to_delete > 0 and member_to_delete is not None:
                def check_if_member(message):
                    return message.author.id == member_to_delete.id
                delete_later = await ctx.send("I will be searching {} messages from this channel and deleting any from {} if found.\nHit me with a 👌 to confirm this (you have 15 seconds)".format(amount_to_delete, member_to_delete.name))
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                await delete_later.edit(content="Working....")
                try:
                    ripped = await ctx.channel.purge(limit=amount_to_delete, check=check_if_member, before=delete_later, bulk=True)
                except:
                    await delete_later.delete()
                    raise specific_error("I attempted to delete a number of messages from a member in this channel but failed. Maybe I don't have permission?")
                await delete_later.delete()
                return await ctx.send("I have deleted {} message(s) from {}...".format(len(ripped), member_to_delete.name), delete_after=5)
            else:
                raise specific_error("You likely entered something that didn't make sense. Check !help delete for more info.")
        except:
            traceback.print_exc()

    @delete.command(name="all")
    async def _all(self, ctx, *args):
        ''' Delete a very large amount of messages
        !del all                    - Delete the whole history of the current channel
        !del all [specify a number] - Delete this many messages ALL channels
        !del all [user]             - Delete ALL messages from this user in ALL channels
        !del all bots               - Delete ALL messages from bots in ALL channels
        !del all phrase "phrase"    - Delete everything containing this phrase from ALL channels
        Include the quotes in the phrase commands.
        Each command requires confirmation to execute.'''
        def check_if_author(reaction, user):
            return reaction.emoji == "👌" and user.id == ctx.author.id

        try:
            if len(args) == 0:
                delete_later = await ctx.send("I will be attempting to clear the entire history of this channel ("+ctx.channel.name+").\nHit me with a 👌 to confirm this (you have 15 seconds)")
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                await delete_later.edit(content="Working....")
                try:
                    ripped = await ctx.channel.purge(limit=9999999, check=None, before=delete_later, bulk=True)
                except:
                    await delete_later.delete()
                    raise specific_error("I attempted to delete every message from this channel but encountered an error while trying. Maybe I don't have permission?")
                await delete_later.delete()
                return await ctx.send("I have deleted {} message(s)...".format(len(ripped)), delete_after=5)
            if len(args) >= 1:
                if args[0].lower() == "bots":
                    delete_later = await ctx.send("I will be attempting to clear every bot message from the server.\nHit me with a 👌 to confirm this (you have 15 seconds)")
                    await delete_later.add_reaction("👌")
                    try:
                        await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                    except:
                        return await delete_later.delete()
                    await delete_later.edit(content="Working....")
                    try:
                        def check_if_bot(message):
                            return message.author.bot
                        for chan in ctx.guild.text_channels:
                            await chan.purge(limit=999999, check=check_if_bot, before=delete_later, bulk=True)
                    except:
                        await delete_later.delete()
                        raise specific_error("I attempted to delete every bot message from this server but encountered an error while trying. Maybe I don't have permission?")
                    await delete_later.delete()
                    return await ctx.send("I have deleted the messages...", delete_after=5)
                if args[0].lower() == "phrase" and len(args) > 1:
                    delete_later = await ctx.send("I will be attempting to clear every message on the server containing the phrase '"+" ".join(args[1:])+"'.\nHit me with a 👌 to confirm this (you have 15 seconds)")
                    await delete_later.add_reaction("👌")
                    try:
                        await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                    except:
                        return await delete_later.delete()
                    await delete_later.edit(content="Working....")
                    try:
                        def check_if_phrase(message):
                            return " ".join(args[1:]) in message.content
                        for chan in ctx.guild.text_channels:
                            await chan.purge(limit=999999, check=check_if_phrase, before=delete_later, bulk=True)
                    except:
                        await delete_later.delete()
                        raise specific_error("I attempted to delete every message on the server containing a phrase and encountered an error while trying. Maybe I don't have permission?")
                    await delete_later.delete()
                    return await ctx.send("I have deleted the messages...", delete_after=5)
                if len(args) > 1:
                    raise specific_error("Invalid parameters have been given. Check the !help section on this command.")


                member_to_delete = None
                amount_to_delete = 0
                try:
                    member_to_delete = await commands.MemberConverter().convert(ctx, args[0])
                except:
                    pass
                try:
                    amount_to_delete = int(args[0])
                except:
                    pass
                if member_to_delete is not None:
                    def check_if_member(message):
                        return message.author.id == member_to_delete.id
                    delete_later = await ctx.send("I will be deleting all messages by this user on the server.\nHit me with a 👌 to confirm this (you have 15 seconds)")
                    await delete_later.add_reaction("👌")
                    try:
                        await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                    except:
                        return await delete_later.delete()
                    await delete_later.edit(content="Working....")
                    try:
                        for chan in ctx.guild.text_channels:
                            await chan.purge(limit=0, check=check_if_member, before=delete_later, bulk=True)
                    except:
                        await delete_later.delete()
                        raise specific_error("I attempted to delete every message by a member from this server but encountered an error while trying. Maybe I don't have permission?")
                    await delete_later.delete()
                    return await ctx.send("I have deleted the messages...", delete_after=5)
                elif amount_to_delete > 0:
                    delete_later = await ctx.send("I will be deleting {} messages from this server from anyone.\nHit me with a 👌 to confirm this (you have 15 seconds)".format(amount_to_delete))
                    await delete_later.add_reactions("👌")
                    try:
                        await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                    except:
                        return await delete_later.delete()
                    await delete_later.edit(content="Working....")
                    try:
                        for chan in ctx.guild.text_channels:
                            await chan.purge(limit=amount_to_delete, check=None, before=delete_later, bulk=True)
                    except:
                        await delete_later.delete()
                        raise specific_error("I attempted to delete a number of messages but encountered an error while trying. Maybe I don't have permission?")
                    await delete_later.delete()
                    return await ctx.send("I have deleted the messages...", delete_after=5)
                elif amount_to_delete < 1 and member_to_delete is None:
                    raise specific_error("The input was invalid. Check the !help command.")

        except:
            traceback.print_exc()

    @commands.command(aliases=["vban", "vunban", "voiceunban"])
    async def voiceban(self, ctx):
        ''' Toggle a ban on someone from only the voice channels'''
        raise unimplemented

    @commands.command()
    async def ignore(self, ctx):
        ''' Toggle ignore on a user
        When a user is ignored, the bot will never respond to them.'''
        raise unimplemented

    @commands.command()
    async def offliners(self, ctx):
        ''' Show a list of offline members'''
        try:
            the_offliners = [mmbr for mmbr in ctx.guild.members if mmbr.status != discord.Status.online and mmbr.status != discord.Status.idle and mmbr.status != discord.Status.dnd]
            if len(the_offliners) == 0:
                return await ctx.send("Nobody is offline! wow")
            p = GenericPaginator(self.BarryBot, ctx, markdown="", timeout=60)
            for memer in the_offliners:
                p.add_line(line=str(memer))
            msg = await ctx.send("Here are the offline members. ("+str(len(the_offliners))+" of them out of "+str(len(ctx.guild.members))+")\n"+str(p))
            p.msg = msg
            p.original_msg = "Here are the offline members. ("+str(len(the_offliners))+" of them out of "+str(len(ctx.guild.members))+")\n"
            await p.add_reactions()
            await p.start_waiting()
        except:
            traceback.print_exc()