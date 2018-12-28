import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter, GenericPaginator
import configparser
import shutil

class Settings:
    # these are per-server settings 
    # things like whether or not they want per channel command monitoring or whatever
    # this is the class which controls the commands

    # per server settings can be found via: self.BarryBot.settings[ctx.guild.id].<the setting name>
    # per server, per command settings are checked via: Perms.has_specific_set_perms(ctx, self.BarryBot.settings[ctx.guild.id], <string of the command setting>)
    #   during these checks, False or True are returned if there is not a permission error.
    #   if True: success            if False: fall back to default perms for the command (Perms.is_guild_...(ctx))
    # a quicker way to get the settings for the ctx is BarryBot.guild_settings(ctx), it returns ServerSettings or None

    def __init__(self, bot, config, loop, BarryBot):
        self.bot = bot
        self.config = config
        self.loop = loop
        self.BarryBot = BarryBot
        # ####
        # This is a list of commands you are not allowed to modify with !set command
        self.forbidden = {"commands", "respond", "commands permissions", "features", "settings"}
        # ####


    @commands.group(name="commands", aliases=["command", "cmd"], invoke_without_command=True)
    @commands.check(Perms.is_guild_superadmin)
    async def commandz(self, ctx):
        '''The main command for managing the server commands
        If no extra argument is given, this returns a list of all the commands on the server and their assigned permission levels.
        It is extremely recommended to read each !help menu for the commands before using them.'''
        p = GenericPaginator(self.BarryBot, ctx, markdown="css")
        setting = self.BarryBot.settings[ctx.guild.id]
        personalPerms = Perms.get_custom_perms(ctx, setting)
        for x in setting.commands:
            if int(setting.commands[x]) <= personalPerms:
                p.add_line(line=setting.commands[x] + "  -  " + x)
        msg = await ctx.send("Here is a list of all commands you are allowed to modify with your permissions. Modify them using !cmd perm.\n"+str(p))
        p.msg = msg
        p.original_msg = "Here is a list of all commands you are allowed to modify with your permissions. Modify them using !cmd perm.\n"
        await p.add_reactions()
        await p.start_waiting()

    @commandz.command(usage="[command name]", aliases=["perms", "perm", "p"])
    async def permissions(self, ctx, *, commandStr : str):
        '''- Allows changing the permissions required to use a command
        An alias of a command will work.

        You must reply with an integer in the following list when prompted after using the command:
        -2: Reset the permission for that command
        -1: DISABLE THE COMMAND
        0: Anyone can use the command
        1: Mod - Manage Messages permissions
        2: Admin - Manage Server permissions
        3: Superadmin - Administrator permissions
        4: Server Owner Only

        You cannot set a level of permission higher than your own. (You must be able to execute the command)
        Some commands are barred from modification for your safety. Usually these commands require being level 3, a superadmin (The Administrator Tag).
        Note: If you set a group command (such as !uno) to a harsher setting than its children, you require permission to use the parent command before any of the children.
            Setting permissions to child commands gets a little complicated behind the scenes, but in a nutshell it still works exactly the same as outlined above.
        Another Note: Use the !role perm command to give a specific role these permissions without giving them things like Manage Server.
        '''
        setting = self.BarryBot.settings[ctx.guild.id]
        if self.bot.get_command(commandStr):
            commandName = self.bot.get_command(commandStr).qualified_name
            checkName = re.sub("\s", "_", commandName)
        else:
            commandName = setting.get_command_from_alias(commandStr)
            if commandName is None:
                raise invalid_command(commandStr)
            checkName = re.sub("\s", "_", commandName)
        if commandName in self.forbidden:
            raise specific_error("This command cannot be modified under any circumstances.")

        # vvv this thing is meant to just error if it doesnt work out.
        roleCheck = Perms.has_specific_set_perms_no_cmd(ctx, setting, checkName)

        mainmsg = await ctx.send("Command '"+commandName+"' found. Currently at level "+setting.commands[checkName]+"\nInput an integer from -2 to 4 to change.\nSay anything else to cancel.\nThis will timeout in 15 seconds.")

        def checker(m):
            try:
                return m.channel == ctx.channel and m.author == ctx.author
            except:
                return False
        try:
            msg = await self.bot.wait_for("message", check=checker, timeout=30)
        except asyncio.TimeoutError:
            await mainmsg.edit(content="Automatic timeout reached.")
            await self.BarryBot.delete_later(mainmsg)
            return
        try:
            int(msg.content)
        except:
            await mainmsg.delete()
            await msg.delete()
            return

        changeTo = str(int(msg.content))
        if changeTo == "-2":
            changeTo = setting.get_default("Commands", checkName)

        if roleCheck < int(msg.content) or int(changeTo) > roleCheck:
            raise specific_error("You can't set a level of permission outside of your own permission level.")


        if setting.modify("Commands", checkName, changeTo):
            await mainmsg.delete()
            await msg.delete()
            theChange = setting.commands[checkName]
            if theChange == "5":
                changeStr = "5 (Bot Host Only)"
            elif theChange == "4":
                changeStr = "4 (Server Owner Only)"
            elif theChange == "3":
                changeStr = "3 (Superadmins and Up)"
            elif theChange == "2":
                changeStr = "2 (Admins and Up)"
            elif theChange == "1":
                changeStr = "1 (Server Mods and Up)"
            elif theChange == "0":
                changeStr = "0 (Anyone)"
            elif theChange == "-1":
                changeStr = "-1 (DISABLED COMMAND)"
            else:
                changeStr = "invalid (SOMETHING IS BROKEN)"
            await ctx.send("I have changed command '"+commandName+"' to level "+changeStr, delete_after=15)
        else:
            await mainmsg.delete()
            await msg.delete()
            raise specific_error("I couldn't modify the server settings for some reason...")

    @commandz.command(usage="[command name]", aliases=["a"])
    async def alias(self, ctx, *, commandStr : str = "give me the list"):
        '''- Allows creating or deleting an alias for a command
        Using this command with no argument will provide a list of aliases.
        If the alias already exists and is NOT hardcoded, then the alias is removed.
        The alias must contain no spaces and must be less than 25 characters.
        Note: These aliases work 'globally' in a way, meaning that an alias set for a subcommand, such as 'poop' for !uno play, would work as !poop
        Any capitalization in the alias will be removed.
        Quirk Note: It is possible to have an alias match a hardcoded alias for a subcommand (like !play doing something different than !uno play)

        You must reply with the alias after using this command to finish.'''
        if commandStr == "give me the list":
            p = GenericPaginator(self.BarryBot, ctx, page_header = "Command || Alias", markdown="css")
            setting = self.BarryBot.settings[ctx.guild.id]
            for x in setting.aliases:
                p.add_line(line=x + " - " + ", ".join(setting.aliases[x].split()))
            if p.lines_on_a_page == 0 and p.pagenum == 0:
                p.add_line(line="There are no aliases!")
            msg = await ctx.send("Here is a list of all the custom aliases on the server. Modify them using !cmd alias [commandname].\n"+str(p))
            p.msg = msg
            p.original_msg = "Here is a list of all the custom aliases on the server. Modify them using !cmd alias [commandname].\n"
            await p.add_reactions()
            await p.start_waiting()
            return

        setting = self.BarryBot.guild_settings(ctx)
        if self.bot.get_command(commandStr):
            commandName = self.bot.get_command(commandStr).qualified_name
            checkName = re.sub("\s", "_", commandName)
        else:
            checkName = None
            for c,a in setting.aliases.items():
                if commandStr in a.split():
                    checkName = c
                    break
            if checkName is None:
                raise invalid_command(commandStr)
            commandName = re.sub("_", " ", checkName)

        def check(message):
            return message.author.id == ctx.author.id and len(message.content.split()) == 1 and len(message.content.split()[0]) <= 25 and not re.search("[^a-zA-Z0-9]", message.content)

        extraStr = ""
        if checkName in setting.aliases:
            extraStr = "\nHere is the current list of aliases for this command:```css\n"
            for a in setting.aliases[checkName].split():
                extraStr = extraStr + "\n" + a
            extraStr = extraStr + "```"


        delete_later = await ctx.send("Command found: "+commandName+". Reply with what you want your alias to be.\nDo not use any spaces or special characters.\nI will ignore you until you use the correct syntax.\nOtherwise, say `cancel` or wait 15 seconds to do nothing."+extraStr)

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=15)
        except:
            return await delete_later.delete()

        msgW = msg.content.lower().split()[0]

        await delete_later.delete()
        if self.bot.get_command(msgW):
            await msg.delete()
            return await ctx.send("That is already a hardcoded name or alias for another command ("+self.bot.get_command(msgW).name+").", delete_after=15)
        if msgW == "cancel":
            await msg.delete()
            return await ctx.send("Exited the alias editor.", delete_after=5)

        theBigList = set()
        for _, v in setting.aliases.items():
            theBigList.update(v.split())
        if checkName in setting.aliases:
            theList = set(setting.aliases[checkName].split())
            if msgW in theList:
                setting.remove("Aliases", checkName, value=msgW)
                await ctx.send("I have removed "+msgW+" from the aliases of "+checkName, delete_after=15)
            else:
                if msgW in theBigList:
                    for cmd in setting.aliases:
                        if msgW in setting.aliases[cmd].split():
                            foundCmd = cmd
                            break
                    await msg.delete()
                    return await ctx.send("That is already an alias for another command ("+foundCmd+").", delete_after=15)
                theList.add(msgW)
                await ctx.send("I have added "+msgW+" as an alias to "+checkName, delete_after=15)
                setting.aliases[checkName] = " ".join(theList)
        else:
            setting.add("Aliases", checkName, msgW)
            await ctx.send("I have added "+msgW+" as an alias to "+checkName, delete_after=15)
        with open(setting.config_filepath, "w") as file:
            setting.config.write(file)
        self.BarryBot.settings[ctx.guild.id] = setting
        await msg.delete()





    @commands.command(aliases=["feature", "feat"], usage="[feature name]")
    async def features(self, ctx, *, featureStr : str = "Show Features"):
        '''The main command for managing the server features (or list them)
        To show a list of features and their values, use this command with no parameters.
        To access settings for a specific feature, use this command again, also supplying the feature name.

        If there are no extra settings for a feature, it will be toggled on or off instead of displaying options.
        If there are extra settings for a feature, I will indicate that you need to reply with certain information.

        For example: >!feature playerleave
                     >30
        What that does: Sets the amount of time in seconds the bot will wait in the voice channel after the playlist is empty, in case someone tries to queue something else.'''
        # this will get quite complicated.
        # many wait_fors and many checks
        # ifs to check what the reply was, what to do... etc
        setting = self.BarryBot.settings[ctx.guild.id]
        list_of_feature_names = {"playerleave", "playervol", "defaultchannel", "defaultrole", "welcome", "wotd", "quotesfrompins", "ignoredchans", "nocommandchans", "nologchans", "logging", "modchan", "logchan", "filteredwords", "capsspam", "bar", "filterlinks", "sublists", "colors", "rpg", "stream"}

        # unfortunately we are also about to do something you never want to see ever
        # there isn't much of a better way to do it that i can tell without making every single feature an object
        # if i were to do that i would be wasting so much time
        # ... now that i think about it making features objects would be neat but then again somewhere along the line i feel like im going to have to do something super explicit anyways so why not do it here instead
        try:
            #p = GenericPaginator(self.BarryBot, ctx, page_header = "Feature     | Details", markdown="css")
            p = GenericPaginator(self.BarryBot, ctx, markdown="css")
            if featureStr == "Show Features":
                #p.add_line(line="autoclear   - Set a list of channels to be emptied every certain number of minutes (")
                #p.add_line(line=" IDs: "+", ".join(setting.features["clr_channel_ids"].split()))
                #p.add_line(line=" Time: "+", ".join([setting.features["clr_channel_freq"].split()[i*2] + ": " + setting.features["clr_channel_freq"].split()[i*2+1] for i in range(len(setting.features["clr_channel_freq"].split()))]))
                p.add_line(line="playerleave - How many seconds the player waits after the playlist is empty before leaving the channel")
                p.add_line(line=" Time: "+setting.features["playerleave"])
                p.add_line(line="playervol - The default player volume set upon playlist creation")
                p.add_line(line=" Volume: "+setting.features["playervol"])
                p.add_line(line="defaultchannel - The default channel for the server. This is usually the general chat")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["defaultchannel_Enabled"]))))
                p.add_line(line=" Channel: "+str(discord.utils.get(ctx.guild.text_channels, id=int(setting.features["defaultchannel_ID"]))))
                p.add_line(line="defaultrole - The default role to be assigned to all users upon joining the server")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["defaultrole_Enabled"]))))
                p.add_line(line=" Role: "+str(discord.utils.get(ctx.guild.roles, id=int(setting.features["defaultrole_ID"]))))
                p.add_line(line="welcome - The welcome message displayed in the default channel when new users join")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["welcome_Enabled"]))))
                p.add_line(line=" Message: "+setting.features["welcome_Message"])
                p.add_line(line="wotd - The Word of The Day, displayed in the default channel at 6pm CST")
                p.add_line(line=" Dictionary Enabled: "+str(bool(int(setting.features["wotd_D"]))))
                p.add_line(line=" Urban Dictionary Enabled: "+str(bool(int(setting.features["wotd_UD"]))))
                p.add_line(line=" Quote Enabled: "+str(bool(int(setting.features["wotd_Quotes"]))))
                p.add_line(line="quotesfrompins - Messages which are pinned get pulled and put in a quote list")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["quotesfrompins_Enabled"]))))
                p.add_line(line=" Ignored Channels: "+", ".join([str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["quotesfrompins_Ignored_IDs"].split()]))
                p.add_line(line="ignoredchans - Channels the bot entirely ignores for all purposes")
                p.add_line(line=" Channels: "+", ".join([str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["ignoredchans_IDs"].split()]))
                p.add_line(line="nocommandchans - Channels the bot does not answer to command invokes")
                p.add_line(line=" Channels: "+", ".join([str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["nocommandchans_IDs"].split()]))
                p.add_line(line="nologchans - Channels the bot will not read or listen to for logging (the feature) purposes")
                p.add_line(line=" Channels: "+", ".join([str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["nologgingchans_IDs"].split()]))
                p.add_line(line="logging - Watch everywhere for things that happen, report them in a log channel (These are not saved locally!)")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["logging_Enabled"]))))
                p.add_line(line=" Log TTS: "+str(bool(int(setting.features["log_tts_Enabled"]))))
                p.add_line(line=" Log Deletes: "+str(bool(int(setting.features["log_deletes_Enabled"]))))
                p.add_line(line=" Ignore Message Prefixes: "+str(", ".join(setting.features["log_deletes_Ignores"].split())))
                p.add_line(line=" Log Edits: "+str(bool(int(setting.features['log_edits_Enabled']))))
                p.add_line(line=" Log Leaves: "+str(bool(int(setting.features["log_leaves_Enabled"]))))
                p.add_line(line=" Log Kicks: "+str(bool(int(setting.features["log_kicks_Enabled"]))))
                p.add_line(line=" Log Bans: "+str(bool(int(setting.features["log_bans_Enabled"]))))
                p.add_line(line=" Log Joins: "+str(bool(int(setting.features["log_joins_Enabled"]))))
                p.add_line(line=" Log Channel Changes: "+str(bool(int(setting.features['log_chanSettingChange_Enabled']))))
                p.add_line(line=" Log Server Changes: "+str(bool(int(setting.features["log_srvrSettingChange_Enabled"]))))
                p.add_line(line=" Log User Role Changes: "+str(bool(int(setting.features['log_userRoleChange_Enabled']))))
                p.add_line(line=" Log User Nickname Changes: "+str(bool(int(setting.features["log_userNickChange_Enabled"]))))
                p.add_line(line=" Log Role Changes: "+str(bool(int(setting.features["log_roleChange_Enabled"]))))
                p.add_line(line=" Log Caps Spam: "+str(bool(int(setting.features['log_capsSpam_Enabled']))))
                p.add_line(line=" Log Use of Filtered Words: "+str(bool(int(setting.features["log_filteredWords_Enabled"]))))
                p.add_line(line=" Log Invite Creation: "+str(bool(int(setting.features["log_inviteCreate_Enabled"]))))
                p.add_line(line=" Log Invite Deletion: "+str(bool(int(setting.features["log_inviteDelete_Enabled"]))))
                p.add_line(line="modchan - The channel designated for mods and above only")
                p.add_line(line=" Channel: "+str(discord.utils.get(ctx.guild.text_channels, id=int(setting.features["modchan_ID"]))))
                p.add_line(line="logchan - The channel designated for logging")
                p.add_line(line=" Channel: "+str(discord.utils.get(ctx.guild.text_channels, id=int(setting.features["logchan_ID"]))))
                p.add_line(line="filteredwords - Delete new messages containing words or mute the users who say them")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["filterwords_Enabled"]))))
                p.add_line(line=" Words: "+", ".join(setting.features["filterwords_Words"].split()))
                p.add_line(line=" Mute: "+str(bool(int(setting.features["filterwords_Harsh"]))))
                p.add_line(line="capsspam - Alert or take action when a user spams caps")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["capsSpam_Enabled"]))))
                p.add_line(line=" Threshold: "+setting.features["capsSpam_Limit"])
                p.add_line(line=" Mute: "+str(bool(int(setting.features["capsSpam_Harsh"]))))
                p.add_line(line="bar - A Markov Chain bot which keeps track of things everyone says in specific channels and spits them out when you say his name.")
                p.add_line(line=" Cooldown Time: "+setting.features["bar_cooldown"])
                p.add_line(line=" Listened Channels: "+", ".join([str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["bar_listenchan_IDs"].split()]))
                p.add_line(line=" Ignored Users: "+", ".join([str(discord.utils.get(ctx.guild.members, id=int(x))) for x in setting.features["bar_ignoreuser_IDs"].split()]))
                p.add_line(line="filterlinks - Delete new messages including a link to a site or mute the users instead")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["filterlinks_Enabled"]))))
                p.add_line(line=" Links: "+", ".join(setting.features["filterlinks_Links"].split()))
                p.add_line(line=" Mute: "+str(bool(int(setting.features["filterlinks_Harsh"]))))
                p.add_line(line="sublists - Roles which can be joined by anyone used to mention a lot of users at once")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["sublists_Enabled"]))))
                p.add_line(line=" Roles: "+", ".join([str(discord.utils.get(ctx.guild.roles, id=int(x))) for x in setting.features["sublists_IDs"].split()]))
                p.add_line(line="colors - Roles which can be joined by anyone for the purpose of colors")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["colors_Enabled"]))))
                p.add_line(line=" Roles: "+", ".join([str(discord.utils.get(ctx.guild.roles, id=int(x))) for x in setting.features["colors_IDs"].split()]))
                p.add_line(line="rpg - An Idle RPG where you gain XP and stats by doing nothing")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["rpg_Enabled"]))))
                p.add_line(line=" Channel: "+str(discord.utils.get(ctx.guild.text_channels, id=int(setting.features["rpg_channel_ID"]))))
                p.add_line(line="stream - Stream Alerts for any member in the server")
                p.add_line(line=" Enabled: "+str(bool(int(setting.features["stream_Enabled"]))))
                p.add_line(line=" Channel: "+str(discord.utils.get(ctx.guild.text_channels, id=int(setting.features["stream_channel_ID"]))))
                #if p.lines_on_a_page == 0 and p.pagenum == 0:
                #    p.add_line(line="Something is terribly wrong here...........")
                msg = await ctx.send("Here is a list of all the features available to your server. Modify them using !feat [featurename]. Do not specify things like 'IDs' or 'Time.'\n"+str(p))
                p.original_msg = "Here is a list of all the features available to your server. Modify them using !feat [featurename]. Do not specify things like 'IDs' or 'Time.'\n"
                p.msg = msg
                await p.add_reactions()
                await p.start_waiting()
                return
        except:
            traceback.print_exc()
        if featureStr.split()[0].lower() in list_of_feature_names:
            the_feature = featureStr.split()[0].lower()
        else:
            raise specific_error("That feature does not exist. Specify an exact name from the given list seen in !features")

        ###
        #
        #feature trigger block
        #
        ###
        if the_feature == "playerleave":
            delete_later = await ctx.send("Feature found: Player Leave Time. Reply with a number of seconds you would like the bot to wait in the voice channel before leaving, after the playlist is empty.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nDefault: 10\nCurrent: "+setting.features["playerleave"])
            def check(message):
                if message.author.id == ctx.author.id and message.content.lower() == "cancel":
                    return True
                try:
                    int(message.content)
                except:
                    return False
                return message.author.id == ctx.author.id and int(message.content) <= 60
            success_str = "I have set the Player Leave Time to %s"
        if the_feature == "playervol":
            delete_later = await ctx.send("Feature Found: Player Default Volume. Reply with a number 0-100 you would like the player volume to be automatically set to every time the bot joins a voice channel.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nDefault: 30\nCurrent: "+setting.features["playervol"])
            def check(message):
                if message.author.id == ctx.author.id and message.content.lower() == "cancel":
                    return True
                try:
                    float(message.content)
                except:
                    return False
                return message.author.id == ctx.author.id and 0.0 <= float(message.content) <= 100.0
            success_str = "I have set the Player Default Volume to %s"
        if the_feature == "defaultchannel":
            if setting.features["defaultchannel_Enabled"] == "1":
                channame = str(discord.utils.get(ctx.guild.text_channels, id=int(setting.features["defaultchannel_ID"])))
            else:
                channame = "Off"
            delete_later = await ctx.send("Feature Found: Server Default Channel. Reply with a text channel you would like to designate as the default channel. Certain announcements from the bot will appear here. This is typically the General Chat.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nSay `off` to turn this feature off.\nDefault: Off\nCurrent: "+channame)
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            def check(message):
                if message.author.id == ctx.author.id and message.content.lower() == "cancel" or message.content.lower() == "off":
                    return True
                try:
                    if message.author.id == ctx.author.id and message.content in guild_channels_names or message.content in guild_channels_mentions or message.content in guild_channels_ids:
                        return True
                except:
                    return False
            success_str = "I have set the Server Default Channel to %s"
        if the_feature == "defaultrole":
            if setting.features["defaultrole_Enabled"] == "1":
                rolename = str(discord.utils.get(ctx.guild.roles, id=int(setting.features["defaultrole_ID"])))
            else:
                rolename = "Off"
            delete_later = await ctx.send("Feature Found: Server Default Role. Reply with a role you would like to designate as the default role. Members who join the server will get this role immediately upon joining.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nSay `off` to turn this feature off.\nDefault: Off\nCurrent: "+rolename)
            guild_roles_names = [role.name for role in ctx.guild.roles]
            guild_roles_mentions = [role.mention for role in ctx.guild.roles]
            guild_roles_ids = [role.id for role in ctx.guild.roles]
            def check(message):
                if message.author.id == ctx.author.id and message.content.lower() == "cancel" or message.content.lower() == "off":
                    return True
                try:
                    if message.author.id == ctx.author.id and message.content in guild_roles_names or message.content in guild_roles_mentions or message.content in guild_roles_ids:
                        return True
                except:
                    return False
        if the_feature == "welcome":
            if setting.features["welcome_Enabled"] == "1":
                welcomeStr = setting.features["welcome_Message"]
            else:
                welcomeStr = "Off"
            delete_later = await ctx.send("Feature Found: New Join Welcome Message. Reply with a message you would like to send in the default channel when a new member joins. The message always begins with '@user' so your message will be added after the mention.\nIf no default channel is set, this will not work.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nSay `t` to toggle this feature on/off.\nDefault: Off\nCurrent: "+welcomeStr)
            def check(message):
                if message.author.id == ctx.author.id:
                    return True
                return False
        if the_feature == "wotd":
            if setting.features["wotd_Enabled"] == "1":
                wotdEnabled = "On"
            else:
                wotdEnabled = "Off"
            if setting.features["wotd_D"] == "1":
                wotdD = "On"
            else:
                wotdD = "Off"
            if setting.features["wotd_UD"] == "1":
                wotdUD = "On"
            else:
                wotdUD = "Off"
            if setting.features["wotd_Quotes"] == "1":
                wotdQ = "On"
            else:
                wotdQ = "Off"
            delete_later = await ctx.send("Feature Found: Word of The Day. This is a message which occurs at 18:00 bot-host time daily.\nReply with which option you would like to toggle.\nIf no default channel is set, this will not work.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nSay `t` to toggle this feature on/off.\nDefault: Off\nCurrent: "+wotdEnabled+"\nwotd_d - Dictionary.com: "+wotdD+"\nwotd_ud - UrbanDictionary: "+wotdUD+"\nwotd_q - Quotes: "+wotdQ)
            def check(message):
                accepted = ["t", "cancel", "wotd_d", "wotd_ud", "wotd_q"]
                if message.author.id == ctx.author.id and message.content.lower() in accepted:
                    return True
                return False
        if the_feature == "quotesfrompins":
            if setting.features["quotesfrompins_Enabled"] == "1":
                quotes = "On"
            else:
                quotes = "Off"
            ignored_chans = [str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["quotesfrompins_Ignored_IDs"].split()]
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            delete_later = await ctx.send("Feature Found: Quotes From Pins. This, along with the quote command, automatically redirects pinned messages in all channels to the quote list. Ignored channels do not have any pins pulled.\nReply with `t` to toggle on or off.\nReply with a channel mention, name, or ID to add or remove a channel from the ignore list.\nI will ignore you until you use the correct syntax.\nSay `cancel` or wait 30 seconds to do nothing.\nSay `t` to toggle this feature on/off.\nDefault: Off\nCurrent: "+quotes+"\nIgnored Channels: "+", ".join(ignored_chans))
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() == "cancel" or message.content.lower() == "t":
                        return True
                    try:
                        if message.content in guild_channels_names or message.content.lower() in guild_channels_mentions or message.content.lower() in guild_channels_ids:
                            return True
                    except:
                        return False
        if the_feature == "ignoredchans":
            ignored_chans = [str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["ignoredchans_IDs"].split()]
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            delete_later = await ctx.send("Feature Found: Globally Ignored Channels. Enabling this for a channel will cause the bot to ignore the channel for all purposes, including using commands.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a channel mention, name, or ID to add or remove a channel from the ignore list.\nI will ignore you until you use the correct syntax.\nIgnored Channels: "+", ".join(ignored_chans))
            def check(message):
                if message.author.id == ctx.author.id:
                    try:
                        if message.content.lower() == "cancel" or message.content in guild_channels_names or message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions:
                            return True
                    except:
                        return False
        if the_feature == "nocommandchans":
            ignored_chans = [str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["nocommandchans_IDs"].split()]
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            delete_later = await ctx.send("Feature Found: Command-Invoke Ignored Channels. Enabling this for a channel will cause the bot to ignore any commands that are executed in the channel.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a channel mention, name, or ID to add or remove a channel from the ignore list.\nI will ignore you until you use the correct syntax.\nIgnored Channels: " + ", ".join(ignored_chans))
            def check(message):
                if message.author.id == ctx.author.id:
                    try:
                        if message.content.lower() == "cancel" or message.content in guild_channels_names or message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions:
                            return True
                    except:
                        return False
        if the_feature == "nologgingchans":
            ignored_chans = [str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["nologgingchans_IDs"].split()]
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            delete_later = await ctx.send("Feature Found: Logging Ignored Channels. Enabling this for a channel will cause the bot to ignore it regarding any logging. This means that any message deletes, edits, etc. will not be noted.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a channel mention, name, or ID to add or remove a channel from the ignore list.\nI will ignore you until you use the correct syntax.\nIgnored Channels: " + ", ".join(ignored_chans))
            def check(message):
                if message.author.id == ctx.author.id:
                    try:
                        if message.content.lower() == "cancel" or message.content in guild_channels_names or message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions:
                            return True
                    except:
                        return False
        if the_feature == "logging":
            logging = setting.num_to_bool("Features", "logging_Enabled")
            tts = setting.num_to_bool("Features", "log_tts_Enabled")
            dels = setting.num_to_bool("Features", "log_deletes_Enabled")
            ignored_dels = ", ".join(setting.features["log_deletes_Ignores"].split())
            edits = setting.num_to_bool("Features", "log_edits_Enabled")
            leaves = setting.num_to_bool("Features", "log_leaves_Enabled")
            kicks = setting.num_to_bool("Features", "log_kicks_Enabled")
            bans = setting.num_to_bool("Features", "log_bans_Enabled")
            joins = setting.num_to_bool("Features", "log_joins_Enabled")
            chansetting = setting.num_to_bool("Features", "log_chanSettingChange_Enabled")
            serversetting = setting.num_to_bool("Features", "log_srvrSettingChange_Enabled")
            userrole = setting.num_to_bool("Features", "log_userRoleChange_Enabled")
            usernick = setting.num_to_bool("Features", "log_userNickChange_Enabled")
            rolechange = setting.num_to_bool("Features", "log_roleChange_Enabled")
            capsspam = setting.num_to_bool("Features", "log_capsSpam_Enabled")
            filtered = setting.num_to_bool("Features", "log_filteredWords_Enabled")
            invitecreate = setting.num_to_bool("Features", "log_inviteCreate_Enabled")
            invitedelete = setting.num_to_bool("Features", "log_inviteDelete_Enabled")
            choices = {"logging", "tts", "deletes", "prefixes", "edits", "leaves", "kicks", "bans", "joins", "chansetting", "serversetting", "userroles", "usernick", "rolechange", "capsspam", "filtered", "invcreate", "invdelete"}
            delete_later = await ctx.send("Feature Found: Logging. Enabling this will allow the bot to begin relaying certain server-wide events that may or may not concern administrators to a channel for moderators or administrators. None of the content is actually saved by the bot locally.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle this feature on or off.\nReply with the name of any sub-feature to toggle it.\nI will ignore you until you use the correct syntax.\nLogging Enabled: {}\ntts: {} - Send an alert when a /TTS message is sent\ndeletes: {} - Deleted messages will be reposted upon deletion\nprefixes: {} - Deleted messages starting with these prefixes are ignored\nedits: {} - Edited messages will be reposted, showing the changes\nleaves: {} - Triggered when anyone leaves the server\nkicks: {} - Triggered when anyone is kicked from the server\nbans: {} - Triggered when anyone is banned from the server\njoins: {} - Triggered when anyone joins the server\nchansetting: {} - Shows when settings are changed for any channel\nserversetting: {} - Shows when the server settings are changed\nuserroles: {} - Shows when a user gains or loses a role\nusernick: {} - Shows nickname changes\nrolechange: {} - Shows when a role has been changed\ncapsspam: {} - Triggered when all caps are spammed somewhere. See the capsSpam feature for more\nfiltered: {} - Triggered when filtered words are used. See the filterWords feature for more\ninvcreate: {} - Triggered on invite creation\ninvdelete: {} - Triggered on invite deletion".format(logging, tts, dels, ignored_dels, edits, leaves, kicks, bans, joins, chansetting, serversetting, userrole, usernick, rolechange, capsspam, filtered, invitecreate, invitedelete))
            def check(message):
                if message.author.id == ctx.author.id:
                    try:
                        if message.content.lower() == "cancel" or message.content.lower() == "t" or message.content.lower() in choices:
                            return True
                    except:
                        return False
        if the_feature == "modchan":
            try:
                foundchan = discord.utils.get(ctx.guild.text_channels, id=int(setting.features["modchan_ID"])).name
            except:
                foundchan = "NO CHANNEL"
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            delete_later = await ctx.send("Feature Found: Moderation Channel. Setting this will determine where certain notifications meant for mods or admins will go.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a channel mention, name, or ID to set the channel.\nReply with `0` to set this to nothing.\nCurrent Mod Channel: "+foundchan)
            def check(message):
                if message.author.id == ctx.author.id:
                    try:
                        if message.content.lower() == "cancel" or message.content.lower() == "0" or message.content in guild_channels_names or message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions:
                            return True
                    except:
                        return False
        if the_feature == "logchan":
            try:
                foundchan = discord.utils.get(ctx.guild.text_channels, id=int(setting.features["logchan_ID"])).name
            except:
                foundchan = "NO CHANNEL"
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            delete_later = await ctx.send("Feature Found: Logging Channel. Setting this will determine where the logging feature will send messages.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a channel mention, name, or ID to set the channel.\nReply with `0` to set this to nothing.\nCurrent Logging Channel: "+foundchan)
            def check(message):
                if message.author.id == ctx.author.id:
                    try:
                        if message.content.lower() == "cancel" or message.content.lower() == "0" or message.content in guild_channels_names or message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions:
                            return True
                    except:
                        return False
        if the_feature == "filterwords":
            listofwords = setting.features["filterwords_Words"].split()
            filter_enable = setting.num_to_bool("Features", "filterwords_Enabled")
            filter_harsh = setting.num_to_bool("Features", "filter_Harsh")
            delete_later = await ctx.send("Feature Found: Word Filtering. Enabling this will either enforce deleting messages with filtered words in them or muting the users, depending on if harsh mode is on or not.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a word to add or remove it from the list of filtered words.\nReply with `t` to toggle this on or off.\nReply with `harsh` to toggle harsh on or off.\nFiltered Words Are: {}\nHarsh Filter Is: {}\n".format(filter_enable, filter_harsh)+"List of filtered words: "+", ".join(listofwords))
            def check(message):
                if message.author.id == ctx.author.id:
                    if re.search("^[a-zA-Z0-9]+$", message.content.lower()) or message.content.lower() == "cancel":
                        return True
                return False
        if the_feature == "capsspam":
            caps_enable = setting.num_to_bool("Features", "capsSpam_Enabled")
            caps_harsh = setting.num_to_bool("Features", "capsSpam_Harsh")
            lim = setting.features["capsSpam_Limit"]
            delete_later = await ctx.send("Feature Found: All Caps Spam Triggering. Enabling this will either alert Mods/Admins via the Mod channel to someone spamming caps in any channel, or mute them if harsh mode is on.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with a number to change the threshold for how many lines of all-caps are required to trigger an alert or action.\nReply with `t` to toggle this on or off.\nReply with `harsh` to toggle harsh on or off.\nCaps Spam Triggering Is: {}\nHarsh Mode Is: {}\nThe Threshold Is: {}".format(caps_enable, caps_harsh, lim))
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() == "t" or message.content.lower() == "harsh" or message.content.lower() == "cancel":
                        return True
                    try:
                        int(message.content)
                        return True
                    except:
                        return False
        if the_feature == "bar":
            time = setting.features["bar_cooldown"]
            bar_enable = setting.num_to_bool("Features", "bar_Enabled")
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            guild_users_names = [usr.name for usr in ctx.guild.members]
            guild_users_mentions = [usr.mention for usr in ctx.guild.members]
            guild_users_ids = [usr.id for usr in ctx.guild.members]


            listened_chans = [str(discord.utils.get(ctx.guild.text_channels, id=int(x))) for x in setting.features["bar_listenchan_IDs"].split()]
            ignored_users = [str(ctx.guild.get_member(x)) for x in setting.features["bar_ignoreuser_IDs"].split()]
            delete_later = await ctx.send("Feature Found: Bar, the Markov Chain Bot. Having this enabled will allow the bot to watch what all users say in the specified channels. Setting a cooldown timer will restrict users to invoking it after a certain number of seconds. It will only watch channels which are on the listen-list. It will ignore users in the ignore list\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle this on or off.\nReply with a channel mention, name, or ID to add or remove it from the listen list.\nReply with a user mention, name, or ID to add or remove them to the ignore list.\nBar is: {}\nThe cooldown is: {} seconds\nBar will listen to these channels: {}\nBar is ignoring these users: {}".format(bar_enable, time, " ".join(listened_chans), " ".join(ignored_users)))
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() == 't' or message.content.lower() == "cancel":
                        return True
                    if message.content in guild_channels_names or message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions or message.content.lower() in guild_users_ids or message.content in guild_users_names or message.content.lower() in guild_users_mentions:
                        return True
                    try:
                        int(message.content)
                        return True
                    except:
                        return False
                return False
        if the_feature == "filterlinks":
            filter_enable = setting.num_to_bool("Features", 'filterlinks_Enabled')
            filter_links = setting.features["filterlinks_Links"].split()
            filter_harsh = setting.num_to_bool("Features", 'filterlinks_Harsh')
            delete_later = await ctx.send("Feature Found: Link Filtering. Having this enable will delete any message containing specified links in chat. If harsh mode is on, users are muted instead.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle link filtering on or off.\nReply with `harsh` to toggle harsh filtering on or off.\nReply with a domain to add or remove it from the filtered link list.\nFiltered Links Is: {}\nHarsh Filtering Is: {}\nList of Filtered Links: {}".format(filter_enable, filter_harsh, " ".join(filter_links)))
            def check(message):
                if message.author.id == ctx.author.id:
                    return True
        if the_feature == "sublists":
            sub_enabled = setting.num_to_bool("Features", "sublists_Enabled")
            sub_roles = ", ".join([str(discord.utils.get(ctx.guild.roles, id=int(x))) for x in setting.features["sublists_IDs"].split()])
            delete_later = await ctx.send("Feature Found: Sublists. Having this enabled and having roles assigned to this feature allows users to 'subscribe' to the roles in order to allow for mass notification without the use of `@everyone`.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle sublists on or off.\nReply with a role mention, ID, or name to add or remove it from the list of subbable roles.\nSublists Are: {}\nList of Sub-roles: {}".format(sub_enabled, sub_roles))
            guild_roles_names = [role.name for role in ctx.guild.roles]
            guild_roles_mentions = [role.mention for role in ctx.guild.roles]
            guild_roles_ids = [role.id for role in ctx.guild.roles]
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() in guild_roles_ids or message.content.lower() in guild_roles_mentions or message.content in guild_roles_names or message.content.lower() == "t" or message.content.lower() == "cancel":
                        return True
        if the_feature == 'colors':
            colors_enabled = setting.num_to_bool("Features", "colors_Enabled")
            color_roles = ", ".join([str(discord.utils.get(ctx.guild.roles, id=int(x))) for x in setting.features["colors_IDs"].split()])
            delete_later = await ctx.send("Feature Found: Color Roles. Having this enabled and having roles assigned to this feature allows users to 'self assign' a color.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle color roles on or off.\nReply with a role mention, ID, or name to add or remove it from the list of color roles.\nSublists Are: {}\nList of Sub-roles: {}".format(colors_enabled, color_roles))
            guild_roles_names = [role.name for role in ctx.guild.roles]
            guild_roles_mentions = [role.mention for role in ctx.guild.roles]
            guild_roles_ids = [role.id for role in ctx.guild.roles]
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() in guild_roles_ids or message.content.lower() in guild_roles_mentions or message.content in guild_roles_names or message.content.lower() == "t" or message.content.lower() == "cancel":
                        return True
        if the_feature == 'rpg':
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            rpg_enable = setting.num_to_bool("Features", "rpg_Enabled")
            try:
                foundchan = discord.utils.get(ctx.guild.text_channels, id=int(setting.features["rpg_channel_ID"])).name
            except:
                foundchan = "NO CHANNEL"

            delete_later = await ctx.send("Feature Found: Idle RPG. Enabling this and specifying a channel will allow any user to join and participate in an Idle RPG. You earn XP and other things by doing nothing.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle Idle RPG on or off.\nReply with a channel mention, ID, or name to set one.\nIdle RPG is: {}\nChannel: {}".format(rpg_enable, foundchan))
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions or message.content in guild_channels_names or message.content.lower() == "t" or message.content.lower() == "cancel":
                        return True
        if the_feature == 'stream':
            guild_channels_names = [chan.name for chan in ctx.guild.text_channels]
            guild_channels_mentions = [chan.mention for chan in ctx.guild.text_channels]
            guild_channels_ids = [chan.id for chan in ctx.guild.text_channels]
            stream_enable = setting.num_to_bool("Features", "stream_Enabled")
            try:
                foundchan = discord.utils.get(ctx.guild.text_channels, id=int(setting.features["stream_channel_ID"])).name
            except:
                foundchan = "NO CHANNEL"

            delete_later = await ctx.send("Feature Found: Stream Notifications. Enabling this and specifying a channel will make it so that when any member of the server sets their status to Streaming, I update the channel with that information.\nReply with `cancel` or wait 30 seconds to do nothing.\nReply with `t` to toggle Stream Alerts on or off.\nReply with a channel mention, ID, or name to set one.\nStream Alerts are: {}\nChannel: {}".format(stream_enable, foundchan))
            def check(message):
                if message.author.id == ctx.author.id:
                    if message.content.lower() in guild_channels_ids or message.content.lower() in guild_channels_mentions or message.content in guild_channels_names or message.content.lower() == "t" or message.content.lower() == "cancel":
                        return True


        if the_feature == "other stuff":
            pass

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except:
            return await delete_later.delete()

        await delete_later.delete()
        if msg.content.lower() == "cancel":
            await msg.delete()
            return await ctx.send("Exited the feature editor without changing anything.", delete_after=5)
        ###
        #
        #the feature change block (only ever reached upon successful entry)
        #
        ###
        try:
            if the_feature == "playerleave":
                setting.modify("Features", "playerleave", msg.content)
                return await ctx.send("I have changed the music player leave time to "+msg.content+" seconds.", delete_after=15)
            if the_feature == "playervol":
                setting.modify("Features", "playervol", msg.content)
                return await ctx.send("I have changed the music player default volume to "+msg.content+"%.", delete_after=15)
            if the_feature == "defaultchannel":
                if msg.content.lower() == "off":
                    setting.modify("Features", "defaultchannel_Enabled", "0")
                    return await ctx.send("I have disabled the default channel setting.", delete_after=15)
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (defaultchannel)")
                setting.modify("Features", "defaultchannel_Enabled", "1")
                setting.modify("Features", "defaultchannel_ID", str(foundchan.id))
                return await ctx.send("I have enabled the default channel and set the default channel to "+foundchan.name)
            if the_feature == "defaultrole":
                if msg.content.lower() == "off":
                    setting.modify("Features", "defaultrole_Enabled", "0")
                    return await ctx.send("I have disabled the default role setting.", delete_after=15)
                try:
                    foundrole = await commands.RoleConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (defaultrole)")
                setting.modify("Features", "defaultrole_Enabled", "1")
                setting.modify("Features", "defaultrole_ID", str(foundrole.id))
                return await ctx.send("I have enabled default roles and set the default role to "+foundrole.name)
            if the_feature == "welcome":
                if msg.content.lower() == "t":
                    if setting.features["welcome_Enabled"] == "1":
                        setting.modify("Features", "welcome_Enabled", "0")
                        return await ctx.send("I have disabled the new member welcome message.", delete_after=15)
                    else:
                        setting.modify("Features", "welcome_Enabled", "1")
                        return await ctx.send("I have enabled the new member welcome message.", delete_after=15)
                setting.modify("Features", "welcome_Enabled", "1")
                setting.modify("Features", "welcome_Message", msg.content)
                return await ctx.send("I have enabled and set the new member welcome message to: "+msg.content)
            if the_feature == "wotd":
                if msg.content.lower() == "t":
                    if setting.features["wotd_Enabled"] == "1":
                        setting.modify("Features", "wotd_Enabled", "0")
                        return await ctx.send("I have disabled the word of the day message.", delete_after=15)
                    else:
                        setting.modify("Features", "wotd_Enabled", "1")
                        return await ctx.send("I have enabled the word of the day message.", delete_after=15)
                if msg.content.lower() == "wotd_d":
                    if setting.features["wotd_D"] == "0":
                        setting.modify("Features", "wotd_D", "1")
                        return await ctx.send("I have enabled the Dictionary.com section of the word of the day message.", delete_after=15)
                    else:
                        setting.modify("Features", "wotd_D", "0")
                        return await ctx.send("I have disabled the Dictionary.com section of the word of the day message.", delete_after=15)
                elif msg.content.lower() == "wotd_ud":
                    if setting.features["wotd_UD"] == "0":
                        setting.modify("Features", "wotd_UD", "1")
                        return await ctx.send("I have enabled the UrbanDictionary section of the word of the day message.", delete_after=15)
                    else:
                        setting.modify("Features", "wotd_UD", "0")
                        return await ctx.send("I have disabled the UrbanDictionary section of the word of the day message.", delete_after=15)
                elif msg.content.lower() == "wotd_q":
                    if setting.features["wotd_Quotes"] == "0":
                        setting.modify("Features", "wotd_Quotes", "1")
                        return await ctx.send("I have enabled the Quotes section of the word of the day message.", delete_after=15)
                    else:
                        setting.modify("Features", "wotd_Quotes", "0")
                        return await ctx.send("I have disabled the Quotes section of the word of the day message.", delete_after=15)
            if the_feature == "quotesfrompins":
                if msg.content.lower() == "t":
                    if setting.features["quotesfrompins_Enabled"] == "1":
                        setting.modify("Features", "quotesfrompins_Enabled", "0")
                        return await ctx.send("I have disabled redirecting quotes from pins in all channels.", delete_after=15)
                    else:
                        setting.modify("Features", "quotesfrompins_Enabled", "1")
                        return await ctx.send("I have enabled redirecting quotes from pins.", delete_after=15)
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (quotesfrompins)")
                ignored_ids = setting.features["quotesfrompins_Ignored_IDs"].split()
                if str(foundchan.id) in ignored_ids:
                    ignored_ids.remove(str(foundchan.id))
                    setting.modify("Features", "quotesfrompins_Ignored_IDs", " ".join(ignored_ids))
                    return await ctx.send("I have removed "+str(foundchan)+" from the ignored channels. Future pins will be redirected to the quotes in that channel.", delete_after=15)
                ignored_ids.append(str(foundchan.id))
                setting.modify("Features", "quotesfrompins_Ignored_IDs", " ".join(ignored_ids))
                return await ctx.send("I have added "+str(foundchan)+" to the list of ignored channels. Pins will not longer be redirected to the quotes in that channel.", delete_after=15)
            if the_feature == "ignoredchans":
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (ignoredchans)")
                ignored_ids = setting.features["ignoredchans_IDs"].split()
                if str(foundchan.id) in ignored_ids:
                    ignored_ids.remove(str(foundchan.id))
                    setting.modify("Features", "ignoredchans_IDs", " ".join(ignored_ids))
                    return await ctx.send("I have removed "+str(foundchan)+" from the list of globally ignored channels. I am now listening to it.", delete_after=15)
                ignored_ids.append(str(foundchan.id))
                setting.modify("Features", "ignoredchans_IDs", " ".join(ignored_ids))
                return await ctx.send("I have added "+str(foundchan)+" to the list of globally ignored channels. I will no longer listen to it.", delete_after=15)
            if the_feature == "nocommandchans":
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (nocommandchans)")
                ignored_ids = setting.features["nocommandchans_IDs"].split()
                if str(foundchan.id) in ignored_ids:
                    ignored_ids.remove(str(foundchan.id))
                    setting.modify("Features", "nocommandchans_IDs", " ".join(ignored_ids))
                    return await ctx.send("I have removed "+str(foundchan)+" from the list of command-invoke ignored channels. I am now listening to it for commands.", delete_after=15)
                ignored_ids.append(str(foundchan.id))
                setting.modify("Features", "nocommandchans_IDs", " ".join(ignored_ids))
                return await ctx.send("I have added "+str(foundchan)+" to the list of command-invoke ignored channels. I will no longer listen to it for commands.", delete_after=15)
            if the_feature == "nologgingchans":
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (nologgingchans)")
                ignored_ids = setting.features["nologgingchans_IDs"].split()
                if str(foundchan.id) in ignored_ids:
                    ignored_ids.remove(str(foundchan.id))
                    setting.modify("Features", "nologgingchans_IDs", " ".join(ignored_ids))
                    return await ctx.send("I have removed "+str(foundchan)+" from the list of logging-ignored channels. I am now watching it for any changes.", delete_after=15)
                ignored_ids.append(str(foundchan.id))
                setting.modify("Features", "nologgingchans_IDs", " ".join(ignored_ids))
                return await ctx.send("I have added "+str(foundchan)+" to the list of logging-ignored channels. I will no longer watch it for changes.", delete_after=15)
            if the_feature == "logging":
                if msg.content.lower() == "t" or msg.content.lower() == "logging":
                    if setting.features["logging_Enabled"] == "1":
                        setting.modify("Features", "logging_Enabled", "0")
                        return await ctx.send("I have disabled logging for this server.", delete_after=15)
                    else:
                        setting.modify("Features", "logging_Enabled", "1")
                        return await ctx.send("I have enabled logging for this server.", delete_after=15)
                to_work = None
                finalstr = None
                if msg.content.lower() == "tts":
                    to_work = "log_tts_Enabled"
                    finalstr = "Logging TTS Usage"
                if msg.content.lower() == "deletes":
                    to_work = "log_deletes_Enabled"
                    finalstr = "Logging Deletions"
                elif msg.content.lower() == "edits":
                    to_work = "log_edits_Enabled"
                    finalstr = "Logging Edits"
                elif msg.content.lower() == "leaves":
                    to_work = "log_leaves_Enabled"
                    finalstr = "Logging User Leaves"
                elif msg.content.lower() == "kicks":
                    to_work = "log_kicks_Enabled"
                    finalstr = "Logging User Kicks"
                elif msg.content.lower() == "bans":
                    to_work = "log_bans_Enabled"
                    finalstr = "Logging User Bans"
                elif msg.content.lower() == "joins":
                    to_work = "log_joins_Enabled"
                    finalstr = "Logging User Joins"
                elif msg.content.lower() == "chansetting":
                    to_work = "log_chanSettingChange_Enabled"
                    finalstr = "Logging Channel Setting Changes"
                elif msg.content.lower() == "serversetting":
                    to_work = "log_srvrSettingChange_Enabled"
                    finalstr = "Logging Server Setting Changes"
                elif msg.content.lower() == "userroles":
                    to_work = "log_userRoleChange_Enabled"
                    finalstr = "Logging User Role Changes"
                elif msg.content.lower() == "usernick":
                    to_work = "log_userNickChange_Enabled"
                    finalstr = "Logging User Nickname Changes"
                elif msg.content.lower() == "rolechange":
                    to_work = "log_roleChange_Enabled"
                    finalstr = "Logging Role Setting Changes"
                elif msg.content.lower() == "capsspam":
                    to_work = "log_capsSpam_Enabled"
                    finalstr = "Logging Caps Spam Triggers (If Caps Spam is enabled)"
                elif msg.content.lower() == "filtered":
                    to_work = "log_filteredWords_Enabled"
                    finalstr = "Logging Filtered Word Usage (If Filtered Words is enabled)"
                elif msg.content.lower() == "invcreate":
                    to_work = "log_inviteCreate_Enabled"
                    finalstr = "Logging Invite Creation"
                elif msg.content.lower() == "invdelete":
                    to_work = "log_inviteDelete_Enabled"
                    finalstr = "Logging Invite Deletion"
                elif msg.content.lower() == "prefixes":
                    # we do it differently here :)
                    ignored_dels_list = setting.features["log_deletes_Ignores"].split()
                    ignored_dels =  ", ".join(ignored_dels_list)
                    additional_msg = await ctx.send("The current prefixes the Delete Logger ignores are:\n"+ignored_dels+"\n\nSay any from this list to remove it. Say a new one to add. Input must be 1 word. Not case sensitive. Wait 15 seconds or say `cancel` to exit.")
                    def check(message):
                        if message.author.id == ctx.author.id:
                            return True
                    try:
                        msg = await self.bot.wait_for("message", check=check, timeout=15)
                    except:
                        return await additional_msg.delete()
                    await additional_msg.delete()
                    if msg.content.lower() == "cancel":
                        await msg.delete()
                        return await ctx.send("Exited the feature editor without changing anything.", delete_after=15)
                    actual_param = msg.content.lower().split()[0]
                    if actual_param in ignored_dels:
                        ignored_dels_list.remove(actual_param)
                        ignored_dels = " ".join(ignored_dels_list)
                        print(setting.modify("Features", "log_deletes_Ignores", ignored_dels))
                        return await ctx.send("I have removed '"+actual_param+"' from the list.", delete_after=15)
                    else:
                        ignored_dels_list.append(actual_param)
                        ignored_dels = " ".join(ignored_dels_list)
                        print(setting.modify("Features", "log_deletes_Ignores", ignored_dels))
                        return await ctx.send("I have added '"+actual_param+"' to the list.", delete_after=15)


                if setting.features["logging_Enabled"] == "0":
                    setting.toggle("Features", "logging_Enabled")
                setting.toggle("Features", to_work)
                return await ctx.send(finalstr+" has been toggled to: "+setting.num_to_bool("Features", to_work), delete_after=15)
            if the_feature == "modchan":
                if msg.content.lower() == "0":
                    setting.modify("Features", "modchan_ID", "0")
                    return await ctx.send("I have disabled the Moderator/Admin channel.", delete_after=15)
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (modchan)")
                setting.modify("Features", "modchan_ID", str(foundchan.id))
                return await ctx.send("I have set the Moderator/Admin channel to "+str(foundchan), delete_after=15)
            if the_feature == "logchan":
                if msg.content.lower() == "0":
                    setting.modify("Features", "logchan_ID", "0")
                    return await ctx.send("I have disabled the Logging channel.", delete_after=15)
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (logchan)")
                setting.modify("Features", "logchan_ID", str(foundchan.id))
                return await ctx.send("I have set the Logging channel to "+str(foundchan), delete_after=15)
            if the_feature == "filterwords":
                if msg.content.lower() == "t":
                    setting.toggle("Features", "filterwords_Enabled")
                    return await ctx.send("Enforcing Filtered Words has been toggled to "+setting.num_to_bool("Features", "filterwords_Enabled"), delete_after=15)
                if msg.content.lower() == "harsh":
                    setting.toggle("Features", "filterwords_Harsh")
                    return await ctx.send("Harsh Enforcing of Filtered Words has been toggled to "+setting.num_to_bool("Features", "filterwords_Harsh"), delete_after=15)
                filteredwords = setting.features["filterwords_Words"].split()
                if msg.content.lower() in filteredwords:
                    filteredwords.remove(msg.content.lower())
                    setting.modify("Features", "filterwords_Words", " ".join(filteredwords))
                    return await ctx.send("I have removed "+msg.content.lower()+" from the filtered word list.", delete_after=15)
                filteredwords.append(msg.content.lower())
                setting.modify("Features", "filterwords_Words", " ".join(filteredwords))
                finalstr = "."
                if setting.features["filterwords_Enabled"] == "0":
                    setting.modify("Features", "filterwords_Enabled", "1")
                    finalstr = " and turned enforcing filtered words on."
                return await ctx.send("I have added "+msg.content.lower()+" to the filtered word list"+finalstr, delete_after=15)
            if the_feature == "capsspam":
                if msg.content.lower() == "t":
                    setting.toggle("Features", "capsSpam_Enabled")
                    return await ctx.send("All Caps Spam Triggering has been toggled to "+setting.num_to_bool("Features", "capsSpam_Enabled"), delete_after=15)
                if msg.content.lower() == "harsh":
                    setting.toggle("Features", "capsSpam_Harsh")
                    return await ctx.send("Harsh Enforcement of All Caps Spam has been toggled to "+setting.num_to_bool("Features", "capsSpam_Harsh"), delete_after=15)
                finalstr = "."
                if setting.features["capsSpam_Enabled"] == '0':
                    setting.modify("Features", "capsSpam_Enabled", "1")
                    finalstr = " and turned caps spam triggering on."
                setting.modify("Features", "capsSpam_Limit", msg.content.lower())
                return await ctx.send("I have set the Caps Spam Threshold to "+msg.content+finalstr)
            if the_feature == "bar":
                if msg.content.lower() == "t":
                    setting.toggle("Features", "bar_Enabled")
                    return await ctx.send("Bar has been toggled "+setting.num_to_bool("Features", "bar_Enabled"), delete_after=15)
                foundchan = None
                founduser = None
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    try:
                        founduser = await commands.MemberConverter().convert(await self.bot.get_context(msg), msg.content)
                    except:
                        pass
                if foundchan is not None:
                    listened_chans = [str(discord.utils.get(ctx.guild.text_channels, id=int(x)).id) for x in setting.features["bar_listenchan_IDs"].split()]
                    if str(foundchan.id) in listened_chans:
                        listened_chans.remove(str(foundchan.id))
                        setting.modify("Features", "bar_listenchan_IDs", " ".join(listened_chans))
                        return await ctx.send("Bar is no longer listening to the channel "+str(foundchan), delete_after=15)
                    listened_chans.append(str(foundchan.id))
                    setting.modify("Features", "bar_listenchan_IDs", " ".join(listened_chans))
                    return await ctx.send("Bar is now listening to the channel "+str(foundchan), delete_after=15)
                if founduser is not None:
                    ignored_users = [str(ctx.guild.get_member(x).id) for x in setting.features["bar_ignoreuser_IDs"].split()]
                    if str(founduser.id) in ignored_users:
                        ignored_users.remove(str(founduser.id))
                        setting.modify("Features", "bar_ignoreuser_IDs", " ".join(ignored_users))
                        return await ctx.send("Bar is no longer ignoring the user "+str(founduser), delete_after=15)
                    ignored_user.append(str(founduser.id))
                    setting.modify("Features", "bar_ignoreuser_IDs", " ".join(ignored_users))
                    return await ctx.send("Bar is now ignoring the user "+str(founduser), delete_after=15)
                setting.modify("Features", 'bar_cooldown', msg.content)
                return await ctx.send("Bar's cooldown is now set to "+msg.content+" seconds.", delete_after=15)
            if the_feature == "filterlinks":
                if msg.content.lower() == "t":
                    setting.toggle("Features", "filterlinks_Enabled")
                    return await ctx.send("Link Filtering has been toggled to "+setting.num_to_bool("Features", "filterlinks_Enabled"), delete_after=15)
                if msg.content.lower() == "harsh":
                    setting.toggle("Features", "filterlinks_Harsh")
                    return await ctx.send("Harsh Link Filtering has been toggled to "+setting.num_to_bool("Features", 'filterlinks_Harsh'), delete_after=15)
                links = setting.features["filterlinks_Links"].split()
                if msg.content.lower() in links:
                    links.remove(msg.content.lower())
                    setting.modify("Features", "filterlinks_Links", " ".join(links))
                    return await ctx.send("The domain "+msg.content.lower()+" has been removed from the list of filtered links.", delete_after=15)
                links.append(msg.content.lower())
                setting.modify("Features", "filterlinks_Links", ' '.join(links))
                finalstr = "."
                if setting.features["filterlinks_Enabled"] == "0":
                    finalstr = " and link filtering has been turned on."
                    setting.modify("Features", "filterlinks_Enabled", '1')
                return await ctx.send("The domain "+msg.content.lower()+" has been added to the list of filtered links"+finalstr, delete_after=15)
            if the_feature == 'sublists':
                if msg.content.lower() == "t":
                    setting.toggle("Features", "sublists_Enabled")
                    return await ctx.send("Subscription Lists have been toggled to "+setting.num_to_bool("Features", "sublists_Enabled"), delete_after=15)
                sub_roles = [str(discord.utils.get(ctx.guild.roles, id=int(x)).id) for x in setting.features["sublists_IDs"].split()]
                try:
                    foundrole = await commands.RoleConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. The most likely problem is related to capitalization. (sublists)")
                if str(foundrole.id) in sub_roles:
                    sub_roles.remove(str(foundrole.id))
                    setting.modify("Features", 'sublists_IDs', " ".join(sub_roles))
                    return await ctx.send("I have removed that role from the list of roles that can be subscribed to.", delete_after=15)
                finalstr = "."
                if setting.features["sublists_Enabled"] == "0":
                    setting.toggle("Features", 'sublists_Enabled')
                    finalstr = " and turned sublists on."
                sub_roles.append(str(foundrole.id))
                setting.modify("Features", 'sublists_IDs', " ".join(sub_roles))
                return await ctx.send("I have added that role to the list of roles that can be subscribed to"+finalstr, delete_after=15)
            if the_feature == 'colors':
                if msg.content.lower() == "t":
                    setting.toggle("Features", "colors_Enabled")
                    return await ctx.send("Color Roles has been toggled to "+setting.num_to_bool("Features", "colors_Enabled"), delete_after=15)
                color_roles = [str(discord.utils.get(ctx.guild.roles, id=int(x)).id) for x in setting.features["colors_IDs"].split()]
                try:
                    foundrole = await commands.RoleConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    return await ctx.send("Something is broken. Report to dev. (colors)")
                if str(foundrole.id) in color_roles:
                    color_roles.remove(str(foundrole.id))
                    setting.modify("Features", 'colors_IDs', " ".join(color_roles))
                    return await ctx.send("I have removed that role from the list of roles considered colors.", delete_after=15)
                finalstr = "."
                if setting.features["colors_Enabled"] == "0":
                    setting.toggle("Features", 'colors_Enabled')
                    finalstr = " and turned color roles on."
                color_roles.append(str(foundrole.id))
                setting.modify("Features", 'colors_IDs', " ".join(color_roles))
                return await ctx.send("I have added that role to the list of roles considered colors"+finalstr, delete_after=15)
            if the_feature == "rpg":
                if msg.content.lower() == "t":
                    try:
                        foundchan = discord.utils.get(ctx.guild.text_channels,id=int(setting.features["rpg_channel_ID"]))
                    except:
                        foundchan = None
                    if foundchan is None:
                        return await ctx.send("I could not enable the Idle RPG because a channel was not set. Set a channel first.", delete_after=15)
                    setting.toggle("Features", "rpg_Enabled")
                    return await ctx.send("Idle RPG has been toggled to "+setting.num_to_bool("Features", "rpg_Enabled"), delete_after=15)
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    foundchan = None
                if foundchan is not None:
                    setting.modify("Features", "rpg_channel_ID", str(foundchan.id))
                    if setting.features["rpg_Enabled"] != "1":
                        setting.toggle("Features", "rpg_Enabled")
                        return await ctx.send("Idle RPG has been toggled on and I've set the channel to "+foundchan.name, delete_after=15)
                    return await ctx.send("I have changed the Idle RPG channel to "+foundchan.name, delete_after=15)
            if the_feature == 'stream':
                if msg.content.lower() == "t":
                    try:
                        foundchan = discord.utils.get(ctx.guild.text_channels, id=int(setting.features["stream_channel_ID"]))
                    except:
                        foundchan = None
                    if foundchan is None:
                        return await ctx.send("I could not enable Stream Alerts because a channel was not set. Set a channel first.", delete_after=15)
                    setting.toggle("Features", "stream_Enabled")
                    return await ctx.send("Stream Alerts have been toggled to "+setting.num_to_bool("Features", "stream_Enabled"), delete_after=15)
                try:
                    foundchan = await commands.TextChannelConverter().convert(await self.bot.get_context(msg), msg.content)
                except:
                    foundchan = None
                if foundchan is not None:
                    setting.modify("Features", "stream_channel_ID", str(foundchan.id))
                    if setting.features["stream_Enabled"] != "1":
                        setting.toggle("Features", "stream_Enabled")
                        return await ctx.send("Stream Alerts have been toggled on and I've set the channel to "+foundchan.name, delete_after=15)
                    return await ctx.send("I have changed the Stream Alert channel to "+foundchan.name, delete_after=15)





        except:
            traceback.print_exc()







    @commands.group(name="roles", aliases=["perm", "role"], invoke_without_command=True)
    async def role_(self, ctx):
        '''The main command for managing the server roles
        This is useful for creating and deleting roles.
        This is useful for granting and taking roles lazily.
        This is the way to assign roles to mod levels (0 - 3)

        Use '!role make Role' to create an empty role at the bottom of the hierarchy.
        Use '!role make Role 1' to create a role with typical Server Mod permissions - at the bottom of the hierarchy.
        Use '!role delete Role' to delete a role.
        Use '!role perm Role 1' to assign a role to a specific mod level without modifying the role itself.
        Use '!role give Role @user' to give a role to a user.
        Use '!role take Role @user' to take a role from a user.
        If the role already exists, it is possible to @ the role for speed.

        Using !role perm is useful for giving a set of commands to a group of people without having to grant them certain permissions.
            Normally, level 1 would require granting a user the ability to delete messages. This is the way around it.
        Permission errors:
            You can't do any operations involving roles which are at or above your level of permissions or higher than your highest role in the hierarchy.'''
        raise specific_error("You need to specify a subcommand to get anywhere with this command.\nUse !help role")

    @role_.command(aliases=["create"], usage="[Role Name] [Permission Level]")
    async def make(self, ctx, *args):
        '''- Create a Role
        Simply using this command and not providing any permission level at the end will make an empty role at the bottom of the hierarchy.
        To create a role with more than one word in the name, use quotes.
        Providing a permission level after the role name does not put the role in the group, but does give them typical permissions of that caliber.
            As a result of having those permissions, however, the role will still be in the given permission level.
        Note: Colors and Hoist (appearing separate from the others) must be done manually.'''
        if len(args) == 0:
            raise specific_error("Usage: !role make [Role Name] [Permission Level]")
        if len(args) == 1:
            permission_level = -1
        else:
            try:
                permission_level = int(args[1])
                if permission_level < 0 or permission_level > 3:
                    raise specific_error("You must specify an integer from 0-3 to set pre-determined premissions on a new role.")
            except:
                raise specific_error("You must specify an integer from 0-3 to set pre-determined permissions on a new role.")
        role_name = args[0]
        if len(role_name) > 90:
            raise specific_error("The name of your role can't be so long. (about 90-100 characters)")
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_perms = Perms.get_custom_perms(ctx, setting)
        if executor_perms <= permission_level:
            raise specific_error("You can't create a role with pre-determined permissions at or above your permission level.")

        if role_name in [role.name for role in ctx.guild.role_hierarchy]:
            raise specific_error("You can't create a role which already exists. Modify it yourself instead.")

        role_perms = discord.Permissions(permissions=0)
        endStr = "Empty"
        role_perms_specific = {}
        if permission_level == 0:
            endStr = "Default"
            role_perms_specific = {
                "add_reactions":True,
                "read_messages":True,
                "send_messages":True,
                "embed_links":True,
                "attach_files":True,
                "read_message_history":True,
                "external_emojis":True,
                "connect":True,
                "speak":True,
                "use_voice_activation":True,
                "change_nickname":True
            }
        elif permission_level == 1:
            endStr = "Server Moderator"
            role_perms_specific = {
                "create_instant_invite":True,
                "kick_members":True,
                "add_reactions":True,
                "read_messages":True,
                "send_messages":True,
                "manage_messages":True,
                "embed_links":True,
                "attach_files":True,
                "read_message_history":True,
                "external_emojis":True,
                "connect":True,
                "speak":True,
                "mute_members":True,
                "deafen_members":True,
                "move_members":True,
                "use_voice_activation":True,
                "change_nickname":True,
                "manage_nicknames":True,
                "manage_emojis":True
            }
        elif permission_level == 2:
            endStr = "Server Admin"
            role_perms_specific = {
                "create_instant_invite":True,
                "kick_members":True,
                "ban_members":True,
                "manage_guild":True,
                "manage_channels":True,
                "view_audit_log":True,
                "mention_everyone":True,
                "manage_roles":True,
                "add_reactions":True,
                "read_messages":True,
                "send_messages":True,
                "manage_messages":True,
                "embed_links":True,
                "attach_files":True,
                "read_message_history":True,
                "external_emojis":True,
                "connect":True,
                "speak":True,
                "mute_members":True,
                "deafen_members":True,
                "move_members":True,
                "use_voice_activation":True,
                "change_nickname":True,
                "manage_nicknames":True,
                "manage_emojis":True
            }
        elif permission_level == 3:
            endStr = "Server Superadmin"
            role_perms_specific = {
                "create_instant_invite":True,
                "kick_members":True,
                "ban_members":True,
                "manage_guild":True,
                "manage_channels":True,
                "view_audit_log":True,
                "mention_everyone":True,
                "manage_roles":True,
                "add_reactions":True,
                "read_messages":True,
                "send_messages":True,
                "manage_messages":True,
                "embed_links":True,
                "attach_files":True,
                "read_message_history":True,
                "external_emojis":True,
                "connect":True,
                "speak":True,
                "mute_members":True,
                "deafen_members":True,
                "move_members":True,
                "use_voice_activation":True,
                "change_nickname":True,
                "manage_nicknames":True,
                "manage_emojis":True,
                "administrator":True
            }
        try:
            role_perms.update(**role_perms_specific)
            await ctx.guild.create_role(name=role_name, permissions=role_perms)
        except:
            raise specific_error("Something went wrong trying to modify the permission object or create the role. The most likely reason is that I don't have permissions...")
        await ctx.send("I have created the requested "+endStr+" role named "+role_name+". It is at the bottom of the hierarchy.")



    @role_.command(usage="[Role Name]")
    async def delete(self, ctx, *, Role : discord.Role):
        '''- Delete a Role
        Exactly what it says it does.
        Deleting a role with more than one word in the name does NOT require surrounding the name with quotes.
        Capitalization DOES matter.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        role_lvl = Perms.get_perm_level_for_role(Role, setting)
        if executor_lvl <= role_lvl:
            raise specific_error("You can't delete a role worth an equal or greater power than your most powerful role.\n("+str(executor_lvl)+" <= "+str(role_lvl)+")")
        try:
            await Role.delete()
        except:
            raise specific_error("Something went wrong with deleting the role. Maybe I don't have permission to do that.")
        await ctx.send("I have deleted the role "+Role.name+".")

    @role_.command(usage="[Role Name]")
    async def empty(self, ctx, *, Role : discord.Role):
        '''- Empty a Role
        Unassigns the role from every user on the server.
        Capitalization DOES matter.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        role_lvl = Perms.get_perm_level_for_role(Role, setting)
        if executor_lvl <= role_lvl:
            raise specific_error("You can't unassign a role worth an equal or greater power than your most powerful role.\n("+str(executor_lvl)+" <= "+str(role_lvl)+")")
        try:
            member_list = Role.members
            count = 0
            for person in member_list:
                await person.remove_roles(Role)
                count += 1
            await ctx.send("I have removed the role from "+str(count)+" members.")
        except:
            raise specific_error("Something went wrong with unassigning the role. Maybe I don't have permission to do that.")


    @role_.command(name="perm", usage="[Role Name] [Permission Level]")
    async def perm__(self, ctx, Role : discord.Role, permlevel : int = -2):
        '''- Set the permission level for a Role
        If the name of the role is more than one word, surround the name in quotes.
        To negate any changes to a role and return settings back to default, input -1 as the second parameter.
        This does NOT modify the role. This only internally sets its permissions level, allowing multilayered command permissions.
        Capitalization DOES matter.'''
        # if no permlevel is provided: return the current level
        setting = self.BarryBot.settings[ctx.guild.id]
        if permlevel == -2:
            permlevel = Perms.get_perm_level_for_role(Role, setting)
            return ctx.send("The pre-determined or manually set permission level for the role '"+Role.name+"' is "+str(permlevel)+".")
        if permlevel == -1:
            setting.remove("Role Levels", Role.name)
            return ctx.send("The role '"+Role.name+"' has been set back to a default level of "+str(Perms.get_perm_level_for_role(Role, setting))+".")

        if setting.modify("Role Levels", Role.name, str(permlevel)):
            return ctx.send("The role '"+Role.name+"' has been manually set to level "+str(permlevel)+".")
        else:
            setting.add("Role Levels", Role.name, str(permlevel))
            return ctx.send("The role '"+Role.name+"' has been manually set to level "+str(permlevel)+".")


    @role_.command(usage="[Role Name] [@user]")
    async def give(self, ctx, Role : discord.Role, user : discord.Member):
        '''- Give a user a Role
        If the name of the role is more than one word, surround the name in quotes.
        Capitalization DOES matter.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        role_lvl = Perms.get_perm_level_for_role(Role, setting)
        if executor_lvl <= role_lvl:
            raise specific_error("You can't assign a role worth an equal or greater power than your most powerful role,\n("+str(executor_lvl)+" <= "+str(role_lvl)+")")
        if Role in user.roles:
            raise specific_error("They already have that role.")
        try:
            await user.add_roles(Role)
            await ctx.send("I have assigned the role "+Role.name+" to "+user.name+".")
        except:
            raise specific_error("Something went wrong with assigning the role. Maybe I don't have permission to do that.")

    @role_.command(usage="[Role Name] [@user]")
    async def take(self, ctx, Role : discord.Role, user : discord.Member):
        '''- Take a Role from a user
        If the name of the role is more than one word, surround the name in quotes.
        Capitalization DOES matter.'''
        setting = self.BarryBot.settings[ctx.guild.id]
        executor_lvl = Perms.get_custom_perms(ctx, setting)
        role_lvl = Perms.get_perm_level_for_role(Role, setting)
        if executor_lvl <= role_lvl:
            raise specific_error("You can't remove a role worth an equal or greater power than your most powerful role,\n("+str(executor_lvl)+" <= "+str(role_lvl)+")")
        if Role not in user.roles:
            raise specific_error("They don't have that role.")
        try:
            await user.remove_roles(Role)
            await ctx.send("I have unassigned the role "+Role.name+" from "+user.name+".")
        except:
            raise specific_error("Something went wrong with removing the role. Maybe I don't have permission to do that.")

    @role_.command(usage="[Role Name]")
    async def purge(self, ctx, Role : discord.Role):
        '''- Delete every Role under the indicated Role
        This cannot be undone. Use this wisely.
        Normally, only server owners can do this.'''
        try:
            the_flag = False
            deleted = []
            for role_pos in ctx.guild.role_hierarchy:
                if role_pos == Role:
                    the_flag = True
                if the_flag:
                    await role_pos.delete()
                    deleted.append(role_pos.name)
            await ctx.send("I have deleted "+str(len(deleted))+" roles...\n```Here is a list:\n"+"\n".join(deleted))
        except:
            await ctx.send("I could not purge the roles... Is it a permission issue?")





    @commands.group(invoke_without_command=True)
    @commands.check(Perms.is_guild_superadmin)
    async def settings(self, ctx):
        '''The main command for managing the server settings (rare usage)
        This is useful for resetting all the settings or verifying to make sure nothing is broken.
        This should only be used if something is probably broken.'''
        raise specific_error("Specify a subcommand.")

    @settings.command(aliases=["check"])
    async def verify(self, ctx):
        '''- Verify the server's settings against the example again'''
        try:
            amount = self.BarryBot.settings[ctx.guild.id].verify()
            await ctx.send("I have made my best attempts to check for anything missing between the default config and this server's. Total changes made: "+str(amount), delete_after=15)
        except:
            traceback.print_exc()

    @settings.command(aliases=["reset"])
    async def recopy(self, ctx):
        '''- Reset the entire server's settings using the example'''
        defaults = configparser.ConfigParser(interpolation=None)
        serversettings = self.BarryBot.guild_settings(ctx)
        default_path = os.path.dirname(os.path.dirname(serversettings.config_filepath))+"/example_server.ini"

        defaults.read(default_path, encoding='utf-8')

        serversettings.features = defaults["Features"]
        serversettings.moderation = defaults["Moderation"]
        serversettings.commands = defaults["Commands"]
        serversettings.aliases = defaults["Aliases"]
        serversettings.roles = defaults["Role Levels"]

        with open(serversettings.config_filepath, "w") as file:
            serversettings.config.write(file)
        self.BarryBot.settings[ctx.guild.id] = serversettings
        await ctx.send("All server settings have been reset to default.", delete_after=15)
        
class ServerSettings:
    # this is the object which describes each servers settings
    # it parses a .ini file given by the server id and so forth
    
    def __init__(self, serverID, config):
        self.serverID = str(serverID)
        self.config_filepath = os.path.dirname(config.options)+"/settings/"+str(serverID)+".ini"
        self.config = configparser.ConfigParser(interpolation=None)
        if not self.config.read(self.config_filepath, encoding='utf-8'):
            try:
                shutil.copy(os.path.dirname(config.options)+"/example_server.ini", self.config_filepath)
            except:
                self.fallback_vars()
                print("failure")
    
        self.config.read(self.config_filepath, encoding='utf-8')
        
        #self.clearChannel_list = self.config.get("Features", "clr_channel_ids", fallback=SettingDefaults.clearChannel_list).split()  #a list of ids (updated when the channels are cleared
        #self.clearChannel_frequency = self.config.get("Features", "clr_channel_freq", fallback=SettingDefaults.clearChannel_frequency)#an int of seconds at least 12 hours long
        #... more to come

        try:
            self.features = self.config["Features"]         # Server Features
            self.moderation = self.config["Moderation"]     # Server Mod Command Permissions
            self.commands = self.config["Commands"]         # Server Command Permissions
            self.aliases = self.config["Aliases"]           # Server Command Aliases
            self.roles = self.config["Role Levels"]         # Server Role Permissions
            # TODO add sanity check for ID specific settings (as a function so it is called by the repeat-loop in the bot for cleanup)
        except:
            print("I had to verify a server's settings: "+self.serverID)
            self.verify()

    def verify(self):
        #to check back to the example ini and copy over missing settings in case of an update
        # the Commands section does not need to be checked due to its extreme flexibility
        # same with aliases section

        # this function should probably be run every time something is modified and on every bot restart per server
        # as well as on a server join

        example_config_path = os.path.dirname(os.path.dirname(self.config_filepath))+"/example_server.ini"
        configger = configparser.ConfigParser(interpolation=None)

        configger.read(example_config_path, encoding='utf-8')

        changes_made = 0

        try:
            for key, value in configger["Features"].items():
                if key not in self.config["Features"]:
                    self.config["Features"][key] = value
                    changes_made += 1
        except:
            self.config["Features"] = configger["Features"]
            print("Verify error: Missing feature could not be defaulted, all server features reset.")
            changes_made += len(configger["Features"])
        try:
            for key, value in configger["Moderation"].items():
                if key not in self.config["Moderation"]:
                    self.config["Moderation"][key] = value
                    changes_made += 1
        except:
            self.config["Moderation"] = configger["Moderation"]
            print("Verify error: Missing moderation setting could not be defaulted, all server moderation settings reset.")
            changes_made += len(configger["Moderation"])

        try:
            self.features
        except:
            self.features = configger["Features"]
            self.config["Features"] = configger["Features"]
            print("Verify error: Features do not exist on this server. Reset to default.")
            changes_made += len(self.features)
        try:
            self.moderation
        except:
            self.moderation = configger["Moderation"]
            self.config["Moderation"] = configger["Moderation"]
            print("Verify error: Moderation does not exist on this server. Reset to default.")
            changes_made += len(self.moderation)
        try:
            self.commands
        except:
            self.commands = configger["Commands"]
            self.config["Commands"] = configger["Commands"]
            print("Verify error: Commands does not exist on this server. Reset to default.")
            changes_made += len(self.commands)
        try:
            self.aliases
        except:
            self.aliases = configger["Aliases"]
            self.config["Aliases"] = configger["Aliases"]
            print("Verify error: Aliases do not exist on this server. Reset to default.")
            changes_made += len(self.aliases)
        try:
            self.roles
        except:
            self.roles = configger["Role Levels"]
            self.config["Role Levels"] = configger["Role Levels"]
            print("Verify error: Roles do not exist on this server. Reset to default.")
            changes_made += len(self.roles)

        if len(self.commands) != len(configger["Commands"]):
            for key in configger["Commands"]:
                if key not in self.commands: #example command missing from final
                    self.commands[key] = configger["Commands"][key]
                    print("Set default command for missing: "+key)
                    changes_made += 1
            for key in self.commands:
                if key not in configger["Commands"]: #example command doesnt exist
                    del self.commands[key]
                    print("Deleted deprecated command: "+key)
                    changes_made += 1
        if len(self.features) != len(configger["Features"]):
            for key in configger["Features"]:
                if key not in self.features:
                    self.features[key] = configger["Features"][key]
                    print("Set default feature for missing: "+key)
                    changes_made += 1
            for key in self.features:
                if key not in configger["Features"]:
                    del self.features[key]
                    print("Deleted deprecated feature: "+key)
                    changes_made += 1


        with open(self.config_filepath, "w") as file:
                self.config.write(file)
        return changes_made

    def sanity_check(self):
        '''Check all specific settings which reference IDs to make sure they still point to something and also to make sure all settings which should be IDs are IDs'''
        pass

    def validateID(self, chanID, guild):
        '''Check a given channel ID in a server to see if it is legitimate'''
        return chanID in [chan.id for chan in guild.channels]

    def validateIDType(self, chanID, guild, chantype):
        '''Check a given channel ID in a server against a type'''
        if chantype == 'text':
            return int(chanID) in [chan.id for chan in guild.text_channels]
        elif chantype == 'voice':
            return int(chanID) in [chan.id for chan in guild.voice_channels]
        elif chantype == 'category':
            return int(chanID) in [chan.id for chan in guild.categories]
        return False

    def get_default(self, section, name):
        '''Find the default value for a setting'''
        configger = configparser.ConfigParser(interpolation=None)
        example_config_path = os.path.dirname(os.path.dirname(self.config_filepath))+"/example_server.ini"
        configger.read(example_config_path, encoding="utf-8")
        return configger[section][name]

    def get_command_from_alias(self, name, format=True):
        '''Find the real command name for an alias in the bot.
        This must be a last resort after having used .get_command(name)'''
        checkName = None
        for c,a in self.aliases.items():
            if name in a.split():
                checkName = c
                break
        if checkName is None:
            return None
        if format:
            return re.sub("_", " ", checkName)
        return checkName

    def num_to_bool(self, section, name, truefalse="on off"):
        '''Return a conversion of 1 or 0 to True or False, basically.
        By default, it converts all cases of 0 to off and 1 to on.
        Supplying a different string like "true false" will make it return true for 1 and false for 0.
        This will return None if something goes wrong.'''
        cases = truefalse.split()
        try:
            if self.config[section][name] == "1":
                return cases[0]
            elif self.config[section][name] == "0":
                return cases[1]
            else:
                return None
        except:
            print("There was an error converting number to boolean cases.")
            return None

    def input_to_bool(self, input, truefalse="on off"):
        '''Essentially the same as num_to_bool except it must be given an input and it determines whether it is true or false from that'''
        cases = truefalse.split()
        try:
            if input == "0" or input == 0 or input == "false" or input == "False" or input == 'no' or input == "No":
                return cases[1]
            elif input == '1' or input == 1 or input == "true" or input == "True" or input == "yes" or input == "Yes":
                return cases[0]
            else:
                return None
        except:
            print("There was an error converting input to boolean cases.")
            return None


    def add(self, section, name, value):
        '''Add a setting to a section in the server setting ini
        Section is the [section]
        name is the name of the setting
        value is what to set the setting to
        Returns false if an error occurs'''
        try:
            self.config[section][name] = value
            with open(self.config_filepath, "w") as file:
                self.config.write(file)
            return True
        except:
            return False

    def remove(self, section, name, value=None):
        '''Remove a setting to a section in the server setting ini
        ... same as add but reversed and doesnt need a value
        If a value is given, it removes it from the list (assuming it should be a list)'''
        if value: #this is for removing an element from a list
            try:
                if len(self.config[section][name].split()) == 1:
                    del self.config[section][name]
                    with open(self.config_filepath, "w") as file:
                        self.config.write(file)
                    return True
                tmpSet = set(self.config[section][name].split())
                tmpSet.remove(value)
                self.config[section][name] = " ".join(tmpSet)
                with open(self.config_filepath, "w") as file:
                    self.config.write(file)
                return True
            except:
                return False
        try:
            del self.config[section][name]
            with open(self.config_filepath, "w") as file:
                self.config.write(file)
            return True
        except:
            return False

    def modify(self, section, name, value):
        ''' change a setting
        if its a setting that holds a list, make sure its the right kind of value'''
        try:
            checks = {"defaultchannel_ID", "defaultrole_ID", "quotesfrompins_Ignored_IDs", "ignoredchans_IDs", "nocommandchans_IDs", "nologgingchans_IDs", "bar_listenchan_IDs", "bar_ignoreuser_IDs", "sublists_IDs", "colors_IDs", "rpg_channel_ID", "stream_channel_ID"}
            if name in checks:
                to_remove = []
                for x in value.split():
                    try:
                        int(x)
                    except:
                        to_remove.append(x)
                valuelist = value.split()
                for x in to_remove:
                    valuelist.remove(x)
                value = " ".join(valuelist)
            self.config[section][name] = value
            with open(self.config_filepath, "w") as file:
                self.config.write(file)
            return True
        except:
            traceback.print_exc()
            return False

    def toggle(self, section, name):
        '''Basically modify, except toggles a 1 to a 0 and a 0 to a 1
        Returns what we toggled to unless it didnt work'''
        try:
            if self.config[section][name] == '0':
                self.config[section][name] = "1"
                with open(self.config_filepath, "w") as file:
                    self.config.write(file)
                return 1
            elif self.config[section][name] == "1":
                self.config[section][name] = "0"
                with open(self.config_filepath, "w") as file:
                    self.config.write(file)
                return 0
            return None
        except:
            return None


    def fallback_vars(self):
        # obsoleted by example_server.ini and self.verify
        pass
        
class SettingDefaults:
    # this has been obsoleted by simply editing the example_server.ini and praying it works
    clearChannel_list = 0
    clearChannel_frequency = 43200