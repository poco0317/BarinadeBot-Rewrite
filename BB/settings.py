import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter
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
        
    @commands.group(aliases=["set", "setup"], invoke_without_command=True)
    @commands.check(Perms.is_guild_superadmin)
    async def settings(self, ctx):
        '''The main command for managing the server settings
        If no extra argument is given, this returns the current settings for the server.
        It is extremely recommended to read each !help menu for the commands before using them.'''
        raise unimplemented

    @settings.command(usage="[command name]")
    async def command(self, ctx, *, commandStr : str):
        '''- Allows changing the permissions required to use a command
        An alias of a command will work.

        You must reply with an integer in the following list when prompted after using the command:
        -1: DISABLE THE COMMAND
        0: Default to predefined permissions
        1: Mod - Manage Messages permissions
        2: Admin - Manage Server permissions
        3: Superadmin - Administrator permissions
        4: Server Owner Only

        You cannot set a level of permission higher than your own.
        '''
        # use wait_for to wait for a specific message containing an integer later on to do the permission thing (TODO)
        # a lot of checks...
        raise unimplemented

    @settings.command(usage="[command name]")
    async def alias(self, ctx, *, commandStr : str):
        '''- Allows creating or deleting an alias for a command
        If the alias already exists and is NOT hardcoded, then the alias is removed.
        The alias must be one word.

        You must reply with the alias after using this command to finish.'''
        # use wait_for to wait for specific message
        # a lot of checks...
        # there will be server specific aliases for each command, captured by the on_message event (it may get really complicated to invoke)
        raise unimplemented

    @commands.command(aliases=["feature", "feat"], usage="[feature name]")
    async def features(self, ctx, *, featureStr : str = "Show Features"):
        '''Display a list of features available to toggle
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

    @commands.group(name="role", aliases=["perm"], invoke_without_command=True)
    async def role_(self, ctx):
        '''The main command for managing the server roles
        This is useful for creating and deleting roles.
        This is useful for granting and taking roles lazily.
        This is the way to assign roles to mod levels (1 - 4)

        Use '!role make Role' to create an empty role at the bottom of the heirarchy.
        Use '!role make Role 1' to create a role with typical Server Mod permissions - at the bottom of the heirarchy.
        Use '!role delete Role' to delete a role.
        Use '!role perm Role 1' to assign a role to a specific mod level without modifying the role itself.
        Use '!role give Role @user' to give a role to a user.
        Use '!role take Role @user' to take a role from a user.
        If the role already exists, it is possible to @ the role for speed.

        Using !role perm is useful for giving a set of commands to a group of people without having to grant them certain permissions.
            Normally, level 1 would require granting a user the ability to delete messages. This is the way around it.
        Permission errors:
            You can't do any operations involving roles which are at or above your level of permissions or higher than your highest role in the heirarchy.'''
        raise unimplemented

    @role_.command(usage="[Role Name] [Permission Level]")
    async def make(self, ctx, *args):
        '''- Create a Role
        Simply using this command and not providing any permission level at the end will make an empty role at the bottom of the heirarchy.
        To create a role with more than one word in the name, use quotes.
        Providing a permission level after the role name does not put the role in the group, but does give them typical permissions of that caliber.
            As a result of having those permissions, however, the role will still be in the given permission level.'''
        raise unimplemented

    @role_.command(usage="[Role Name]")
    async def delete(self, ctx, *, Role : str):
        '''- Delete a Role
        Exactly what it says it does.
        Deleting a role with more than one word in the name does NOT require surrounding the name with quotes.'''
        raise unimplemented

    @role_.command(usage="[Role Name] [Permission Level]")
    async def perm(self, ctx, Role : str, permlevel : int = -2):
        '''- Set the permission level for a Role
        If the name of the role is more than one word, surround the name in quotes.'''
        # if no permlevel is provided: return the current level
        raise unimplemented

    @role_.command(usage="[Role Name] [@user]")
    async def give(self, ctx, Role : str, user : discord.Member):
        '''- Give a user a Role
        If the name of the role is more than one word, surround the name in quotes.'''
        raise unimplemented

    @role_.command(usage="[Role Name] [@user]")
    async def take(self, ctx, Role : str, user : discord.Member):
        '''- Take a Role from a user
        If the name of the role is more than one word, surround the name in quotes.'''
        raise unimplemented


        
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

        try:
            for key, value in configger["Features"].items():
                if key not in self.config["Features"]:
                    self.config["Features"][key] = value
        except:
            self.config["Features"] = configger["Features"]
        try:
            for key, value in configger["Moderation"].items():
                if key not in self.config["Moderation"]:
                    self.config["Moderation"][key] = value
        except:
            self.config["Moderation"] = configger["Moderation"]

        try:
            self.features
        except:
            self.features = configger["Features"]
            self.config["Features"] = configger["Features"]
        try:
            self.moderation
        except:
            self.moderation = configger["Moderation"]
            self.config["Moderation"] = configger["Moderation"]
        try:
            self.commands
        except:
            self.commands = configger["Commands"]
            self.config["Commands"] = configger["Commands"]
        try:
            self.aliases
        except:
            self.aliases = configger["Aliases"]
            self.config["Aliases"] = configger["Aliases"]
        try:
            self.roles
        except:
            self.roles = configger["Role Levels"]
            self.config["Role Levels"] = configger["Role Levels"]

        if len(self.commands) != len(configger["Commands"]):
            for key in configger["Commands"]:
                if key not in self.commands: #example command missing from final
                    self.commands[key] = configger["Commands"][key]
            for key in self.commands:
                if key not in configger["Commands"]: #example command doesnt exist
                    del self.commands[key]
        if len(self.features) != len(configger["Features"]):
            for key in configger["Features"]:
                if key not in self.features:
                    self.features[key] = configger["Features"][key]
            for key in self.features:
                if key not in configger["Features"]:
                    del self.features[key]


        with open(self.config_filepath, "w") as file:
                self.config.write(file)

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