import discord
from BB.permissions import *
from BB.bot import Barry
from BB.settings import ServerSettings
from discord.ext import commands
import asyncio
import traceback
import datetime
import sys
import re
import os

if os.name == "nt":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)

print("Barinade Bot Beginning...")
bot = commands.Bot(command_prefix="~", description="I am a sunglasses-wearing shiba running out, eager to steal your money and provide you services in return.\nAlso please use the help command on a command you don't get 100%. I promise you will understand.")
#all the bot events must go in this file



print("I'm constructing the largest class...")
gotloop = asyncio.get_event_loop()
BarryBot = Barry(bot, gotloop)


@bot.event
async def on_ready():
    print("\nI'm in.")
    print("Here is a list of servers I'm in:\n- ", end="")
    print("\n- ".join([guild.name for guild in bot.guilds]))
    print("\nI have access to "+str(sum([len(guild.text_channels) for guild in bot.guilds]))+" text channels.")
    print("I have access to "+str(sum([len(guild.voice_channels) for guild in bot.guilds]))+" voice channels.")
    print("I can see "+str(len(set(bot.get_all_members())))+" distinct members.")
    print("\n\nHere we gooooo! I'm ready to take commands.")
    for guild in bot.guilds:
        if guild.id == 328088072568700929:
            for channel in guild.channels:
                if channel.id == 328089520258023424:
                    BarryBot.logchan = channel
                    break
            break
    
    for guild in bot.guilds:
        BarryBot.settings[guild.id] = ServerSettings(guild.id, BarryBot.config)
        BarryBot.settings[guild.id].verify()
    try:
        BarryBot.loop.create_task(BarryBot.check_looper_fast())
        BarryBot.loop.create_task(BarryBot.check_looper_slow())
        BarryBot.loop.create_task(BarryBot.createBarTalkSessions())
    except:
        traceback.print_exc()



@bot.event
async def on_message(message):
    #to reply: message.channel.send("g")
    #throw extra on_message stuff here if needed
    if message.author.bot:
        return
    if message.author.id in BarryBot.blacklist:
        return
    if message.guild is None:
        ctx = await bot.get_context(message)
        if ctx.valid:
            args = message.content.split()
            try:
                if args[0][1:].lower() in ["uno", "u", "uon", "nuo"]:
                    if args[1].lower() in ["play", "p", "plcard", "playcard", "card", "pc", "pass", "passturn", "draw", "pa", "pas", "d", "getcard", "get", "darw", "ward", "endturn"]:
                        await bot.process_commands(message)
                        return
            except:
                traceback.print_exc()

        return

    if message.tts:
        if BarryBot.settings[message.guild.id].features["logging_Enabled"] == "1" and BarryBot.settings[message.guild.id].features["log_tts_Enabled"] == "1":
            try:
                foundchan = discord.utils.get(message.guild.text_channels, id=int(BarryBot.settings[message.guild.id].features["logchan_ID"]))
                e = discord.Embed(description="By "+message.author.mention+" in "+message.channel.name+"\n\nContent:\n\n"+message.content, color=discord.Color.dark_red(), timestamp=message.created_at)
                e.set_author(name="Text To Speech Message Sent")
                e.set_footer(text="TTS Message Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                await foundchan.send(embed=e)
            except:
                pass

    if message.content.startswith(bot.command_prefix):
        ctx = await bot.get_context(message)
        setting = BarryBot.settings[message.guild.id]
        foundCommand = None
        for c,a in setting.aliases.items():
            if message.content[1:].split()[0] in a.split():
                foundCommand = c
                break
        if foundCommand:
            finalCommand = re.sub("_", " ", foundCommand)
            invoker = bot.get_command(finalCommand)
            try:
                await invoker.invoke(ctx)
            except Exception as e:
                await on_command_error(ctx, e)
            return
    await bot.process_commands(message)

    try:
        mentionlist = set()
        if message.mentions:
            for member in message.mentions:
                mentionlist.add(member.id)
        if str(message.channel.id) in BarryBot.BarTalk_sessions[message.guild.id].listened_channels and str(message.author.id) not in BarryBot.BarTalk_sessions[message.guild.id].ignored_users and (message.content.lower().startswith(("bar ", "barry", "bar.", "bar, ", "bar?", "bar!", "bartholomew ", "bartholomew, ")) or bot.user.id in mentionlist or message.content.lower() in ["bar", "barry", "bartholomew"] or message.content.lower().endswith(("bar.", "bar", "bar!", "bar?", "bartholomew.", "bartholomew?", "bartholomew!"))):
            ctx = await bot.get_context(message)
            try:
                await ctx.send(BarryBot.BarTalk_sessions[message.guild.id].response(message.content, message.guild))
            except:
                traceback.print_exc()
    except:
        traceback.print_exc()

    try:
        if message.content.isprintable() and not message.author.bot:
            if re.sub("[\s.!,&?'-]", "", message.content).isalnum() and message.content[0].isalnum() and str(message.channel.id) in BarryBot.BarTalk_sessions[message.guild.id].listened_channels and str(message.author.id) not in BarryBot.BarTalk_sessions[message.guild.id].ignored_users:
                theFinalMsg = message.content
                theFinalMsgList = theFinalMsg.split()
                if len(theFinalMsg) > 5 and len(theFinalMsg.split()) > 1:
                    if not theFinalMsg[1:4].isalnum(): # this is an obscure check to see whether or not a message found is a weird bot command prefix
                        theFinalMsgList = theFinalMsg.split()[1:]
                        theFinalMsg = " ".join(theFinalMsgList)
                if len(theFinalMsgList) <= 2:
                    return
                for word in theFinalMsgList:    # check for words which are all the same letter (repeat of 3 letters)
                    repeats = 0
                    for i in range(len(word)-1):
                        if word[i] == word[i+1]:
                            repeats += 1
                        if repeats >= 3:
                            return
                tmpDct = {}
                tmp2Dct = {}
                for word in theFinalMsgList:    # check for the same word too many times (5 is good i guess)
                    if word in tmpDct:
                        tmpDct[word] += 1
                    else:
                        tmpDct[word] = 1
                    if tmpDct[word] >= 5:
                        return
                for i in range(len(theFinalMsgList)-1):   # check for repeated duet of words (5 is good)
                    if theFinalMsgList[i] == theFinalMsgList[i+1]:
                        couplet = theFinalMsgList[i].lower() + " " + theFinalMsgList[i+1].lower()
                        if couplet in tmp2Dct:
                            tmp2Dct[couplet] += 1
                        else:
                            tmp2Dct[couplet] = 1
                        if tmp2Dct[couplet] >= 5:
                            return


                pindex = 0
                tindex = 2
                while tindex < len(theFinalMsgList):
                    key = " ".join(theFinalMsgList[pindex:pindex+2])
                    val = theFinalMsgList[tindex]
                    BarryBot.BarTalk_sessions[message.guild.id].collect(key, val)
                    pindex += 1
                    tindex += 1
    except:
        traceback.print_exc()

# @bot.event
# async def on_error(event, *args, **kwargs):
#     print("There was an error related directly to a built in event that was uncaught by on_command_error. Here is the event: "+event)

@bot.check
async def check_serverside_permissions(ctx):
    '''This is a global command check which checks to see if the command given needs to use specific permissions.
    tbh this just replaces all forms of command checking unless otherwise noted'''
    try:
        if not Perms.has_specific_set_perms(ctx, BarryBot.settings[ctx.guild.id]):
            return True
        else:
            return Perms.has_specific_set_perms(ctx, BarryBot.settings[ctx.guild.id])
    except KeyError:        # There was an error because something relating to settings broke: fall to defaults
        return True
    except AttributeError:  # There was an error because this is a private message: fall to defaults
        return True


@bot.event
async def on_command_error(ctx, error):
    #print(error.__class__.__name__)
    if isinstance(error, uno_error):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, player_error):
        try:
            await BarryBot.delete_later(ctx.message, 15)
            return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
        except:
            return await error.passed_ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, not_owner):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly the host of the bot may use this command.```", delete_after=15)
    if isinstance(error, not_server_owner):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly the server owner may use this command.```", delete_after=15)
    if isinstance(error, not_a_mod):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly a server mod may use this command. Mods have the tag 'Manage Messages' in one of their roles.```", delete_after=15)
    if isinstance(error, not_an_admin):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly a server admin may use this command. Admins have the tag 'Manage Server' in one of their roles.```", delete_after=15)
    if isinstance(error, not_a_superadmin):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly a superadmin may use this command. Superadmins have the tag 'Administrator' in one of their roles.```", delete_after=15)
    if isinstance(error, commands.MissingRequiredArgument):
        await BarryBot.delete_later(ctx.message, 15)
        try:
            return await ctx.send("```Error\nSome argument is missing:\n"+ctx.command.usage+"```", delete_after=15)
        except:
            return await ctx.send("```Error\nSome argument is missing, but for some reason wasn't defined explicitly. Good luck. (report to dev)```", delete_after=15)
    if isinstance(error, unimplemented):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, disabled_command):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, commands.BadArgument):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+str(error)+"```", delete_after=15)
    if isinstance(error, cant_do_that):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, specific_error): #i am ashamed of how long it took to figure this out
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    try:
        if isinstance(error.original, discord.Forbidden):
            if error.original.status == 403 and error.original.text == "Missing Permissions":
                await BarryBot.delete_later(ctx.message, 15)
                return await ctx.send("```Error\nI am missing some type of permission involved in executing this command.```", delete_after=15)
            else:
                await BarryBot.delete_later(ctx.message, 15)
                return await ctx.send("```Error\nThere was a Forbidden error while executing the command. Status: "+str(error.original.status)+" Text:"+error.original.text+"```", delete_after=15)
    except:
        pass
    # print(error.with_traceback(error))
    # print(error.original)
    # print(dir(error.original))
    # print(type(error))
    # print(dir(error))
    try:
        traceback.print_tb(error.__traceback__)
    except:
        pass
    try:
        traceback.print_exc()
    except:
        print("no traceback")
    
@bot.event
async def on_command(ctx):
    # todo make this a feature which can be toggled per server
    try:
        await BarryBot.delete_later(ctx.message, 20)
    except:
        pass
@bot.event
async def on_guild_join(guild):
    # todo this is broken because guild.create_invite is dead
    BarryBot.createSingleBarTalkSession(guild.id)
    try:
        newInvite = await guild.create_invite()
        finalStr = "Invite: "+str(newInvite)
    except:
        try:
            newInvite = await guild.create_invite(unique=False)
            finalStr = "Invite: "+str(newInvite)
        except:
            finalStr = "I failed to find an invite."
    if guild.id not in BarryBot.settings:
        BarryBot.settings[guild.id] = ServerSettings(guild.id, BarryBot.config)
    await BarryBot.logchan.send("I have joined a new server called "+guild.name+". ID: "+str(guild.id)+" "+finalStr)

@bot.event
async def on_guild_remove(guild):
    await BarryBot.logchan.send("A server I was in called '"+guild.name+"' disappeared. Maybe I got kicked? ID: "+str(guild.id))

@bot.event
async def on_guild_channel_update(before, after):
    ''' pertains to log_chanSettingChange'''
    try:

        if BarryBot.settings[before.guild.id].features["log_chanSettingChange_Enabled"] == "1" and BarryBot.settings[before.guild.id].features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_red())
            e.set_author(name="Channel Setting Change for "+before.name)
            e.set_footer(text="Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            changes = 0
            if before.name != after.name:
                e.add_field(name="Name Change", value="From: '"+before.name+"' to '"+after.name+"'")
                changes += 1
            if len(before.changed_roles) != len(after.changed_roles) or len(before.overwrites) != len(after.overwrites):
                e.add_field(name="Roles Overwrites Changed", value=".")
                changes += 1
            if isinstance(before, discord.TextChannel):
                if before.topic != after.topic:
                    if before.topic is None:
                        e.add_field(name="Topic Set", value="To '"+after.topic+"'")
                    elif after.topic is None:
                        e.add_field(name="Topic Removed", value="From '"+before.topic+"'")
                    else:
                        e.add_field(name="Topic Changed", value="From: '"+before.topic+"' to '"+after.topic+"'")
                    changes += 1
            if isinstance(before, discord.VoiceChannel):
                if before.bitrate != after.bitrate:
                    e.add_field(name="Bitrate Changed", value="From: '"+str(before.bitrate)+"' to '"+str(after.bitrate)+"'")
                    changes += 1
                if before.user_limit != after.user_limit:
                    e.add_field(name="User Limit Changed", value="From: '"+str(before.user_limit)+"' to '"+str(after.user_limit)+"'")
                    changes += 1
            else:
                if before.is_nsfw() != after.is_nsfw():
                    e.add_field(name="NSFW Toggled", value="NSFW: "+str(after.is_nsfw()))
                    changes += 1
            if changes > 0:
                foundchan = discord.utils.get(before.guild.text_channels, id=int(BarryBot.settings[before.guild.id].features["logchan_ID"]))
                await foundchan.send(embed=e)


    except:
        print("Error in guild channel update for guild "+str(before.guild.id))
        traceback.print_exc()

@bot.event
async def on_guild_channel_delete(channel):
    ''' pertains to log_chanSettingChange'''
    try:
        if BarryBot.settings[channel.guild.id].features["log_chanSettingChange_Enabled"] == "1" and BarryBot.settings[channel.guild.id].features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_red())
            e.set_author(name="Channel Deleted: "+channel.name)
            e.set_footer(text="Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            if isinstance(channel, discord.TextChannel):
                e.add_field(name="Channel Type", value="Text Channel")
            elif isinstance(channel, discord.VoiceChannel):
                e.add_field(name="Channel Type", value="Voice Channel")
            else:
                e.add_field(name="Channel Type", value="Category")
            foundchan = discord.utils.get(channel.guild.text_channels,
                                              id=int(BarryBot.settings[channel.guild.id].features["logchan_ID"]))
            await foundchan.send(embed=e)
    except:
        print("Error in guild channel delete for guild "+str(channel.guild.id))
        traceback.print_exc()

@bot.event
async def on_guild_channel_create(channel):
    ''' pertains to log_chanSettingChange'''
    try:
        if BarryBot.settings[channel.guild.id].features["log_chanSettingChange_Enabled"] == "1" and BarryBot.settings[channel.guild.id].features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_red())
            e.set_author(name="Channel Created: "+channel.name)
            e.set_footer(text="Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            if isinstance(channel, discord.TextChannel):
                e.add_field(name="Channel Type", value="Text Channel")
            elif isinstance(channel, discord.VoiceChannel):
                e.add_field(name="Channel Type", value="Voice Channel")
            else:
                e.add_field(name="Channel Type", value="Category")
            foundchan = discord.utils.get(channel.guild.text_channels,
                                              id=int(BarryBot.settings[channel.guild.id].features["logchan_ID"]))
            await foundchan.send(embed=e)
    except:
        print("Error in guild channel create for guild "+str(channel.guild.id))
        traceback.print_exc()

@bot.event
async def on_member_join(member):
    ''' pertains to log_joins'''
    try:
        if BarryBot.settings[member.guild.id].features["log_joins_Enabled"] == "1" and BarryBot.settings[member.guild.id].features["logging_Enabled"] == "1":
            e = discord.Embed(description=member.mention+"\n", color=discord.Color.dark_green())
            e.set_author(name="Member Joined")
            e.add_field(name="Member ID", value=str(member.id))
            e.add_field(name="Bot Member?", value=str(member.bot))
            e.add_field(name="Member Account Creation", value=str(member.created_at))
            e.set_footer(text="Member Join Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            e.set_thumbnail(url=member.avatar_url)
            foundchan = discord.utils.get(member.guild.text_channels,
                                          id=int(BarryBot.settings[member.guild.id].features["logchan_ID"]))
            await foundchan.send(embed=e)
        if BarryBot.settings[member.guild.id].features["defaultchannel_Enabled"] == "1" and BarryBot.settings[member.guild.id].features["welcome_Enabled"] == "1":
            foundchan = discord.utils.get(member.guild.text_channels, id=int(BarryBot.settings[member.guild.id].features["defaultchannel_ID"]))
            await foundchan.send(content=member.mention+"\n"+BarryBot.settings[member.guild.id].features["welcome_Message"])
        if BarryBot.settings[member.guild.id].features["defaultrole_Enabled"] == "1":
            role = discord.utils.get(member.guild.roles, id=int(BarryBot.settings[member.guild.id].features["defaultrole_ID"]))
            await member.add_roles(role)
    except:
        print("Error in member join event for guild "+str(member.guild.id))
        traceback.print_exc()

@bot.event
async def on_member_remove(member):
    ''' pertains to log_kicks
        pertains to log_leaves'''
    try:
        settings = BarryBot.settings[member.guild.id]
        if (settings.features["log_kicks_Enabled"] == "1" or settings.features["log_leaves_Enabled"] == "1") and settings.features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_purple())
            e.set_author(name="Member Leave/Kick: "+str(member))
            e.set_footer(text="Member Leave/Kick Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            e.set_thumbnail(url=member.avatar_url)
            e.add_field(name="Member ID", value=str(member.id))
            e.add_field(name="Bot Member?", value=str(member.bot))
            e.add_field(name="Member Account Creation", value=str(member.created_at))
            e.add_field(name="Roles", value=", ".join([role.name for role in member.roles]))
            foundchan = discord.utils.get(member.guild.text_channels,
                                          id=int(settings.features["logchan_ID"]))
            await foundchan.send(embed=e)
    except:
        print("Error in member leave/kick event for guild "+str(member.guild.id))
        traceback.print_exc()

@bot.event
async def on_member_ban(guild, user):
    ''' pertains to log_bans'''
    try:
        settings = BarryBot.settings[guild.id]
        if settings.features["log_bans_Enabled"] == "1" and settings.features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_orange())
            e.set_author(name="Member BANNED: "+str(user))
            e.set_footer(text="Member Ban Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            e.set_thumbnail(url=user.avatar_url)
            e.add_field(name="User ID", value=str(user.id))
            e.add_field(name="Bot User?", value=str(user.bot))
            e.add_field(name="User Account Creation", value=str(user.created_at))
            e.add_field(name="Roles", value=", ".join([role.name for role in member.roles]))
            foundchan = discord.utils.get(guild.text_channels,
                                          id=int(settings.features["logchan_ID"]))
            await foundchan.send(embed=e)
    except:
        print("Error in member ban event for guild "+str(guild.id))
        traceback.print_exc()

@bot.event
async def on_member_unban(guild, user):
    ''' pertains to log_bans'''
    try:
        settings = BarryBot.settings[guild.id]
        if settings.features["log_bans_Enabled"] == "1" and settings.features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_orange())
            e.set_author(name="Member Unbanned: " + str(user))
            e.set_footer(text="Member Unban Spotted! Disable this with the 'feature' command.",
                         icon_url=BarryBot.bot.user.avatar_url)
            e.set_thumbnail(url=user.avatar_url)
            e.add_field(name="User ID", value=str(user.id))
            e.add_field(name="Bot User?", value=str(user.bot))
            e.add_field(name="User Account Creation", value=str(user.created_at))
            foundchan = discord.utils.get(guild.text_channels,
                                          id=int(settings.features["logchan_ID"]))
            await foundchan.send(embed=e)
    except:
        print("Error in member unban event for guild " + str(guild.id))
        traceback.print_exc()

@bot.event
async def on_member_update(before, after):
    ''' pertains to log_userRoleChange
        pertains to log_userNickChange'''
    try:
        settings = BarryBot.settings[before.guild.id]
        if len(before.roles) != len(after.roles):
            if settings.features["log_userRoleChange_Enabled"] == "1" and settings.features["logging_Enabled"] == "1":
                e = discord.Embed(description=after.mention+"\n", color=discord.Color.dark_blue())
                e.set_author(name="Member Role Change")
                e.set_footer(text="Member Role Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                e.set_thumbnail(url=before.avatar_url)

                e.add_field(name="Roles After Change", value=", ".join([role.name for role in after.roles]))
                if len(before.roles) > len(after.roles):
                    removedRoles = []
                    for role in before.roles:
                        if role not in after.roles:
                            removedRoles.append(role.name)
                    e.add_field(name="Roles Removed", value=", ".join(removedRoles))
                else:
                    addedRoles = []
                    for role in after.roles:
                        if role not in before.roles:
                            addedRoles.append(role.name)
                    e.add_field(name="Roles Added", value=", ".join(addedRoles))
                foundchan = discord.utils.get(after.guild.text_channels,
                                              id=int(settings.features["logchan_ID"]))
                await foundchan.send(embed=e)
        if before.nick != after.nick:
            if settings.features["log_userNickChange_Enabled"] == "1" and settings.features["logging_Enabled"] == "1":
                if before.nick is None:
                    e = discord.Embed(description=after.mention+"\n", color=discord.Color.dark_blue())
                    e.set_author(name="Member Nickname Set")
                    e.set_footer(text="Member Nickname Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                    e.set_thumbnail(url=before.avatar_url)

                    e.add_field(name='Nickname Before', value="No nickname")
                    e.add_field(name="Nickname After", value=after.nick)
                elif after.nick is None:
                    e = discord.Embed(description=after.mention+"\n", color=discord.Color.dark_blue())
                    e.set_author(name="Member Nickname Removed")
                    e.set_footer(text="Member Nickname Change Spotted! Disable this with the 'feature' command.",
                                 icon_url=BarryBot.bot.user.avatar_url)
                    e.set_thumbnail(url=before.avatar_url)

                    e.add_field(name='Nickname Before', value=before.nick)
                    e.add_field(name="Nickname After", value="Nickname Removed")
                else:
                    e = discord.Embed(description=after.mention+"\n", color=discord.Color.dark_blue())
                    e.set_author(name="Member Nickname Changed")
                    e.set_footer(text="Member Nickname Change Spotted! Disable this with the 'feature' command.",
                                 icon_url=BarryBot.bot.user.avatar_url)
                    e.set_thumbnail(url=before.avatar_url)

                    e.add_field(name='Nickname Before', value=before.nick)
                    e.add_field(name="Nickname After", value=after.nick)
                foundchan = discord.utils.get(after.guild.text_channels,
                                              id=int(settings.features["logchan_ID"]))
                await foundchan.send(embed=e)
        try:
            if before.activity != after.activity:
                if settings.features["stream_Enabled"] == "1" and settings.validateIDType(settings.features["stream_channel_ID"], before.guild, 'text'):
                    if before.activity is None or before.activity.type != discord.ActivityType.streaming:
                        if after.activity is not None and after.activity.type == discord.ActivityType.streaming:
                            foundchan = discord.utils.get(after.guild.text_channels, id=int(settings.features["stream_channel_ID"]))
                            # todo add sub mention here
                            e = discord.Embed(description=after.mention, color=discord.Color.dark_purple())
                            e.set_author(name="Stream Active:")
                            e.set_footer(text="Stream Activity Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                            e.set_thumbnail(url=after.avatar_url)
                            e.add_field(name="Stream Name", value=after.activity.name)
                            if after.activity.url:
                                e.add_field(name="Stream URL", value=after.activity.url)
                            if after.activity.details:
                                e.add_field(name="Stream Game", value=after.activity.details)
                            if after.activity.twitch_name:
                                e.add_field(name="Twitch Name", value=after.activity.twitch_name)
                            BarryBot.streamMessages[after.id] = await foundchan.send(embed=e)
                    if before.activity is not None and before.activity.type == discord.ActivityType.streaming:
                        if after.activity is None or after.activity.type != discord.ActivityType.streaming:
                            await BarryBot.streamMessages[after.id].delete()
                            del BarryBot.streamMessages[after.id]
        except:
            traceback.print_exc()

    except:
        print("Error in member nick/role change event for guild "+str(before.guild.id))
        traceback.print_exc()

@bot.event
async def on_guild_update(before, after):
    ''' pertains to log_inviteCreate ??? -- do later in repeat thing
        pertains to log_inviteDelete ??? -- do later in repeat thing
        pertains to log_srvrSettingChange'''
    try:
        settings = BarryBot.settings[before.id]
        if settings.features["log_srvrSettingChange_Enabled"] == "1" and settings.features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_red())
            e.set_author(name="Server Setting Change")
            e.set_footer(text="Server Setting Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            changes = 0
            if before.name != after.name:
                e.add_field(name="Name Change", value="From: '"+before.name+"' to '"+after.name+"'")
                changes += 1
            if before.region != after.region:
                e.add_field(name="Voice Region Change", value="From: '"+str(before.region)+"' to '"+str(after.region)+"'")
                changes += 1
            if before.afk_timeout != after.afk_timeout:
                e.add_field(name="AFK Timeout Change", value="From: '"+str(before.afk_timeout)+"' to '"+str(after.afk_timeout)+"'")
                changes += 1
            if before.afk_channel != after.afk_channel:
                if before.afk_channel is None:
                    e.add_field(name="AFK Channel Changed", value="Set to "+after.afk_channel.name)
                elif after.afk_channel is None:
                    e.add_field(name="AFK Channel Changed", value="Unassigned")
                else:
                    e.add_field(name="AFK Channel Changed", value="From '"+before.afk_channel.name+"' to '"+after.afk_channel.name+"'")
                changes += 1
            if before.system_channel != after.system_channel:
                if before.system_channel is None:
                    e.add_field(name="System Channel Changed", value="Set to "+after.system_channel.name)
                elif after.system_channel is None:
                    e.add_field(name="System Channel Changed", value="Unassigned")
                else:
                    e.add_field(name="System Channel Changed", value="From '"+before.system_channel.name+"' to '"+after.system_channel.name+"'")
                changes += 1
            if before.icon_url != after.icon_url:
                e.add_field(name="Icon Changed", value=".")
                changes += 1
            if changes > 0:
                foundchan = discord.utils.get(before.text_channels, id=int(settings.features["logchan_ID"]))
                await foundchan.send(embed=e)
    except:
        print("Error in guild setting update for guild "+str(after.id))
        traceback.print_exc()

@bot.event
async def on_guild_role_update(before, after):
    ''' pertains to log_roleChange'''
    try:
        settings = BarryBot.settings[before.guild.id]
        if settings.features["log_roleChange_Enabled"] == "1" and settings.features["logging_Enabled"] == "1":
            e = discord.Embed(color=discord.Color.dark_red())
            e.set_author(name="Role Changed: "+after.name)
            e.set_footer(text="Role Change Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
            changes = 0
            if before.name != after.name:
                e.add_field(name="Name Change", value="From: '"+before.name+"' to '"+after.name+"'")
                changes += 1
            if before.permissions.value != after.permissions.value:
                listofchanges = []
                g = before.permissions
                h = after.permissions
                if g.create_instant_invite != h.create_instant_invite:
                    listofchanges.append("invite creation")
                if g.kick_members != h.kick_members:
                    listofchanges.append("kick members")
                if g.ban_members != h.ban_members:
                    listofchanges.append("ban members")
                if g.administrator != h.administrator:
                    listofchanges.append("administrator")
                if g.manage_channels != h.manage_channels:
                    listofchanges.append("manage channels")
                if g.manage_guild != h.manage_guild:
                    listofchanges.append("manage server")
                if g.add_reactions != h.add_reactions:
                    listofchanges.append("add reactions")
                if g.view_audit_log != h.view_audit_log:
                    listofchanges.append("view audit logs")
                if g.read_messages != h.read_messages:
                    listofchanges.append("reading messages")
                if g.send_messages != h.send_messages:
                    listofchanges.append("sending messages")
                if g.send_tts_messages != h.send_tts_messages:
                    listofchanges.append("sending TTS messages")
                if g.manage_messages != h.manage_messages:
                    listofchanges.append("managing messages")
                if g.embed_links != h.embed_links:
                    listofchanges.append("link embedding")
                if g.attach_files != h.attach_files:
                    listofchanges.append("attach files")
                if g.read_message_history != h.read_message_history:
                    listofchanges.append("reading message history")
                if g.mention_everyone != h.mention_everyone:
                    listofchanges.append("mentioning everyone")
                if g.external_emojis != h.external_emojis:
                    listofchanges.append("use external emojis")
                if g.connect != h.connect:
                    listofchanges.append("connect to VC")
                if g.speak != h.speak:
                    listofchanges.append("speak in VC")
                if g.mute_members != h.mute_members:
                    listofchanges.append("mute members in VC")
                if g.deafen_members != h.deafen_members:
                    listofchanges.append("deafen members in VC")
                if g.move_members != h.move_members:
                    listofchanges.append("move members in VC")
                if g.use_voice_activation != h.use_voice_activation:
                    listofchanges.append("VA force")
                if g.change_nickname != h.change_nickname:
                    listofchanges.append("change self nick")
                if g.manage_nicknames != h.manage_nicknames:
                    listofchanges.append("edit other nicks")
                if g.manage_roles != h.manage_roles:
                    listofchanges.append("edit roles")
                if g.manage_webhooks != h.manage_webhooks:
                    listofchanges.append("manage webhooks")
                if g.manage_emojis != h.manage_emojis:
                    listofchanges.append("manage emojis")
                e.add_field(name="Permissions Toggled", value=", ".join(listofchanges))
                changes += 1
            if before.color != after.color:
                e.add_field(name="Color Change", value="From '"+str(before.color)+"' to '"+str(after.color)+"'")
                changes += 1
            if before.hoist != after.hoist:
                e.add_field(name="Hoist Toggled", value=".")
                changes += 1
            if before.mentionable != after.mentionable:
                e.add_field(name="Mentionable Toggled", value=".")
                changes += 1
            if changes > 0:
                foundchan = discord.utils.get(after.guild.text_channels, id=int(settings.features["logchan_ID"]))
                await foundchan.send(embed=e)
    except:
        print("Error in role update for guild "+str(before.guild.id))
        traceback.print_exc()

@bot.event
async def on_message_edit(before, after):
    ''' pertains to log_edits'''
    try:
        if before.content != after.content and not before.author.bot:
            if BarryBot.settings[before.guild.id].features["log_edits_Enabled"] == "1" and BarryBot.settings[before.guild.id].features["logging_Enabled"] == "1":
                firstStr = before.content
                secondStr = after.content
                if len(firstStr) + len(secondStr) > 1900:
                    e = discord.Embed(description="By "+before.author.mention+" in "+before.channel.mention+"\n**Before Edit**:\n"+firstStr, color=discord.Color.magenta(), timestamp=before.created_at)
                    e2 = discord.Embed(description="By "+before.author.mention+" in "+before.channel.mention+"\n**After Edit**:\n"+secondStr, color=discord.Color.magenta(), timestamp=after.edited_at)
                    e.set_author(name="Message Edited (Split into 2 Alerts - Message ID "+str(before.id)+")", url=after.jump_url)
                    e2.set_author(name="Message Edited (Split into 2 Alerts - Message ID "+str(after.id)+")", url=after.jump_url)
                    if len(before.attachments) > 0:
                        e.add_field(name="Attachments", value=str(len(before.attachments)) + " attachments")
                        e2.add_field(name="Attachments", value=str(len(after.attachments)) + " attachments")
                    e.set_footer(text="Message Edit Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                    e2.set_footer(text="Message Edit Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                    foundchan = discord.utils.get(before.guild.text_channels, id=int(BarryBot.settings[before.guild.id].features["logchan_ID"]))
                    await foundchan.send(embed=e)
                    await foundchan.send(embed=e2)
                    return
                e = discord.Embed(description="By "+before.author.mention+" in "+before.channel.mention+"\n**Before Edit**:\n\n"+firstStr+"\n\n**After Edit**:\n\n"+secondStr, color=discord.Color.dark_magenta(), timestamp=after.edited_at)
                e.set_author(name="Message Edited (Single Alert - Message ID "+str(after.id)+")", url=after.jump_url)
                if len(before.attachments) > 0:
                    e.add_field(name="Attachments", value="\n".join([x.url for x in after.attachments]))
                    try:
                        e.set_thumbnail(url=after.attachments[0].url)
                    except:
                        traceback.print_exc()
                e.set_footer(text="Message Edit Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                foundchan = discord.utils.get(before.guild.text_channels, id=int(BarryBot.settings[before.guild.id].features["logchan_ID"]))
                await foundchan.send(embed=e)



        # section reserved for pin catching



    except:
        print("Error in message edit event for guild "+str(before.guild.id))
        traceback.print_exc()

@bot.event
async def on_message_delete(message):
    ''' pertains to log_deletes'''
    if message.type == discord.MessageType.pins_add:
        pass
    else:
        try:
            if not message.author.bot:
                if BarryBot.settings[message.guild.id].features["log_deletes_Enabled"] == "1" and BarryBot.settings[message.guild.id].features["logging_Enabled"] == "1":
                    for prefix in BarryBot.settings[message.guild.id].features["log_deletes_Ignores"].split():
                        if message.content.lower().startswith(prefix.lower()):
                            return
                    e = discord.Embed(description="By "+message.author.mention+" in "+message.channel.mention+"\n**Contents**:\n\n"+message.content, color=discord.Color.dark_magenta(), timestamp=message.created_at)
                    e.set_author(name="Message Deleted (Message ID "+str(message.id)+")", url=message.jump_url)
                    e.set_footer(text="Message Delete Spotted! Disable this with the 'feature' command.", icon_url=BarryBot.bot.user.avatar_url)
                    if len(message.attachments) > 0:
                        e.add_field(name="Attachments", value="\n".join([x.url for x in message.attachments]))
                        try:
                            e.set_thumbnail(url=message.attachments[0].url)
                        except:
                            traceback.print_exc()
                    if len(message.embeds) > 0:
                        e.add_field(name="Fields", value=str(len(message.embeds))+" embed(s) present")
                    foundchan = discord.utils.get(message.guild.text_channels, id=int(BarryBot.settings[message.guild.id].features["logchan_ID"]))
                    await foundchan.send(embed=e)
        except:
            print("Error in message delete event for guild "+str(message.guild.id))
            traceback.print_exc()

    

print("That's done; let's try to connect.")


bot.run(BarryBot.THE_SECRET_TOKEN)
