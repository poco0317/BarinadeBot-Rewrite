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
        To access settings for a specific feature, use this command again, also supplying the feature name.

        If there are no extra settings for a feature, it will be toggled on or off instead of displaying options.
        If there are extra settings for a feature, I will indicate that you need to reply with certain information.

        For example: >!feature autoclear
                     >add 231537900699910145
                     >!feature autoclear
                     >freq 231537900699910145 43200
        What that does: adds a channel by ID to the auto-clear list. Sets how often I will clear the channel.'''
        # this will get quite complicated.
        # many wait_fors and many checks
        # ifs to check what the reply was, what to do... etc
        raise unimplemented

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
        except:
            raise specific_error("Something went wrong with removing the role. Maybe I don't have permission to do that.")

    @role_.command(usage="[Role Name]")
    async def purge(self, ctx, Role : discord.Role):
        '''- Delete every Role under the indicated Role
        This cannot be undone. Use this wisely.
        Normally, only server owners can do this.'''
        the_flag = False
        deleted = []
        for role_pos in ctx.guild.role_hierarchy:
            if role_pos == Role:
                the_flag = True
            if the_flag:
                await role_pos.delete()
                deleted.append(role_pos.name)
        await ctx.send("I have deleted "+str(len(deleted))+" roles...\n```Here is a list:\n"+"\n".join(deleted))





    @commands.group(invoke_without_command=True)
    @commands.check(Perms.is_guild_superadmin)
    async def settings(self, ctx):
        '''This is for setting some stuff by force if we need to'''
        raise unimplemented

    @settings.command(aliases=["check"])
    async def verify(self, ctx):
        '''Verify the server's settings against the example again'''
        try:
            amount = self.BarryBot.settings[ctx.guild.id].verify()
            await ctx.send("I have made my best attempts to check for anything missing between the default config and this server's. Total changes made: "+str(amount), delete_after=15)
        except:
            traceback.print_exc()

    @settings.command(aliases=["reset"])
    async def recopy(self, ctx):
        '''Reset the entire server's settings using the example'''
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
        
        self.clearChannel_list = self.config.get("Features", "clr_channel_ids", fallback=SettingDefaults.clearChannel_list).split()  #a list of ids (updated when the channels are cleared
        self.clearChannel_frequency = self.config.get("Features", "clr_channel_freq", fallback=SettingDefaults.clearChannel_frequency)#an int of seconds at least 12 hours long
        #... more to come

        try:
            self.features = self.config["Features"]         # Server Features
            self.moderation = self.config["Moderation"]     # Server Mod Command Permissions
            self.commands = self.config["Commands"]         # Server Command Permissions
            self.aliases = self.config["Aliases"]           # Server Command Aliases
            self.roles = self.config["Role Levels"]         # Server Role Permissions
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
                    print("Deleted depreciated command: "+key)
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
                    print("Deleted depreciated feature: "+key)
                    changes_made += 1


        with open(self.config_filepath, "w") as file:
                self.config.write(file)
        return changes_made
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
        ''' change a setting'''
        try:
            self.config[section][name] = value
            with open(self.config_filepath, "w") as file:
                self.config.write(file)
            return True
        except:
            return False


    def fallback_vars(self):
        # obsoleted by example_server.ini and self.verify
        pass
        
class SettingDefaults:
    # this has been obsoleted by simply editing the example_server.ini and praying it works
    clearChannel_list = 0
    clearChannel_frequency = 43200