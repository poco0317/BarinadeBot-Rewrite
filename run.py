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
            role = discord.utils.get(member.guild.roles, id=int(settings.features["defaultrole_ID"]))
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
        pass
    except:
        pass

@bot.event
async def on_message_delete(message):
    ''' pertains to log_deletes'''
    try:
        pass
    except:
        pass

    

print("That's done; let's try to connect.")


bot.run(BarryBot.THE_SECRET_TOKEN)
