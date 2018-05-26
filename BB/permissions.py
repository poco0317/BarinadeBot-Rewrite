import os
import re
import discord
from discord.ext import commands
from BB.conf import Conf


class Perms:        #this also includes other things like musicplayer and uno permissions, etc
    #EZ Mod check: commands.has_permissions(manage_messages=True)
    #EZ Admin check: commands.has_permissions(manage_server=True)
    
    def is_owner(ctx):
        owner_id = Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+"\\config\\config.ini").owner_id
        if ctx.message.author.id != owner_id:
            raise not_owner
        return True
        
    def is_guild_owner(ctx):
        try:
            return Perms.is_owner(ctx)
        except:
            pass
        if ctx.message.author.id != ctx.message.guild.owner.id:
            raise not_server_owner
        return True
    
    def is_guild_superadmin(ctx):
        try:
            return Perms.is_guild_owner(ctx)
        except:
            pass
        perms = ctx.message.channel.permissions_for(ctx.message.author)
        if perms.administrator:
            return True
        raise not_a_superadmin
    
    def is_guild_admin(ctx):
        try:
            return Perms.is_guild_superadmin(ctx)
        except:
            pass
        perms = ctx.message.channel.permissions_for(ctx.message.author)
        if perms.manage_guild:
            return True
        raise not_an_admin
        
    def is_guild_mod(ctx):
        try:
            return Perms.is_guild_admin(ctx)
        except:
            pass
        perms = ctx.message.channel.permissions_for(ctx.message.author)
        if perms.manage_messages:
            return True
        raise not_a_mod
        
    def has_specific_set_perms(ctx, settings, command_check=None): #this is intended to be used via an import and not as a decorator function
        ''' settings is given as an object: self.settings[guild.id] ... it is a ServerSettings object
        command_check is the command name to check (found via context probably)
        settings and command_check are separated pretty much just for organization sake'''
        try:
            return Perms.is_owner(ctx)
        except:
            pass
        if command_check is None:
            if ctx.command.parent:
                command_check = ctx.command.parent.qualified_name
            else:
                command_check = ctx.command.qualified_name
        command_check = re.sub("\s", "_", command_check)
        try:
            found = settings.commands[command_check]
        except:
            try:
                if Perms.is_owner(ctx):
                    return True
            except:
                raise specific_error("You tried to use a command which does not have any permission defined.")
        # this is intended to be used on a per-command basis where the syntax is:
        # -1 = disabled
        # 0 = anyone can use it
        # 1 = mod+ (manage messages)
        # 2 = admin+ (manage server)
        # 3 = superadmin+ (administrator permission)
        # 4 = guild owner
        
        #this function either returns True, False (default), or throws an error.
        roleCheck = -3
        for role in ctx.author.roles: # this finds the highest permission role the user has according to my system
                if str(role.id) in settings.roles:
                    if int(settings.roles[str(role.id)]) > roleCheck:
                        roleCheck = int(settings.roles[str(role.id)])
        if roleCheck > -3:
            found = int(found)
            if found <= roleCheck and found > 0:
                return True
            if found == -1:
                raise disabled_command
            if found == 0:
                return True
            if found == 1:
                raise not_a_mod
            elif found == 2:
                raise not_an_admin
            elif found == 3:
                raise not_a_superadmin
            elif found == 4:
                raise not_server_owner
        if found == "-1":
            raise disabled_command
        elif found == "0":
            return True
        elif found == "1":
            return Perms.is_guild_mod(ctx)
        elif found == "2":
            return Perms.is_guild_admin(ctx)
        elif found == "3":
            return Perms.is_guild_superadmin(ctx)
        elif found == "4":
            return Perms.is_guild_owner(ctx)
        elif found == "5":
            return Perms.is_owner(ctx)
        else:
            print("Something went wrong calculating permissions for a specific command: "+settings.serverID+" "+command_check)
            return False

    def has_specific_set_perms_no_cmd(ctx, settings, command_check, checkDisabled = False):
        '''This is the same concept as the one above except its more for checking in really specific cases when making changes to the settings
        a command being disabled really shouldnt affect this which is why its disabled most of the time by default
        the error messages are customized particularly for one command but this can be used for more
        It returns the level of permissions required if it works
        It errors out if a permission check fails.'''
        try:
            Perms.is_owner(ctx)
            return 5
        except:
            pass
        found = settings.commands[command_check]
        roleCheck = -3
        for role in ctx.author.roles:
            if str(role.id) in settings.roles:
                if int(settings.roles[str(role.id)]) > roleCheck:
                    roleCheck = int(settings.roles[str(role.id)])
        if roleCheck > -3: # this means we will only be checking the fact that they have a role that gives them command-drive permissions (set by an admin)
            found = int(found)
            if 0 < found <= roleCheck:
                return roleCheck
            if found == -1 and checkDisabled:
                raise specific_error("This command is disabled.")
            if found == 0:
                return "This shouldnt happen"
            if found == 1:
                raise specific_error("You must be at least a Server Mod.")
            if found == 2:
                raise specific_error("You must be at least a Server Admin.")
            if found == 3:
                raise specific_error("You must be at least a Server Superadmin.")
            if found == 4:
                raise specific_error("You must be the owner of the server.")
        if found == "-1" and checkDisabled: # starting here, that means that none of their roles were defined so we have to do this the hard way.
            raise specific_error("This command is disabled.")
        elif found == "-1" and not checkDisabled:
            return int(settings.get_default("Commands", command_check))
        elif found == "0":
            return "This shouldnt happen"
        elif found == "1":
            try:
                if Perms.is_guild_mod(ctx):
                    try:
                        if Perms.is_guild_admin(ctx):
                            try:
                                if Perms.is_guild_superadmin(ctx):
                                    try:
                                        if Perms.is_guild_owner(ctx):
                                            return 4
                                    except:
                                        return 3
                            except:
                                return 2
                    except:
                        return 1
            except:
                raise specific_error("You must be at least a Server Mod.")
        else:
            return 5

    def get_custom_perms(ctx, settings):
        ''' Figure out what level of permissions the user from ctx should have.
        Returns a number of permissions, 5 is bot host, 0 is normie'''
        try:
            Perms.is_owner(ctx)
            return 5
        except:
            pass
        roleCheck = -3
        for role in ctx.author.roles:
            if str(role.id) in settings.roles:
                if int(settings.roles[str(role.id)]) > roleCheck:
                    roleCheck = int(settings.roles[str(role.id)])
        permFound = 0
        try:
            if Perms.is_guild_mod(ctx):
                try:
                    if Perms.is_guild_admin(ctx):
                        try:
                            if Perms.is_guild_admin(ctx):
                                try:
                                    if Perms.is_guild_owner(ctx): permFound = 4
                                except: permFound = 3
                        except: permFound = 2
                except: permFound = 1
        except: permFound = 0
        return max(permFound, roleCheck)

    def get_perm_level_for_role(role, settings):
        ''' Figure out what level of permissions the role itself has.'''
        if str(role.id) in settings.roles:
            return int(settings.roles[str(role.id)])
        role_perms = role.permissions
        if role_perms.administrator:
            return 3
        if role_perms.manage_guild:
            return 2
        if role_perms.manage_messages:
            return 1
        return 0

    def get_custom_perms_by_member(mbr, settings):
        ''' Figure out what level of permissions the user from a member object should have.
        Returns number of permissions, 5 is bot host, 0 is normie
        This is meant to be called with no context!!!'''
        owner_id = Conf(os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "\\config\\config.ini").owner_id
        if mbr.id == owner_id:
            return 5
        elif mbr.id == mbr.guild.owner.id:
            permFound = 4
        elif True in [chan.permissions_for(mbr).administrator for chan in mbr.guild.text_channels]:
            permFound = 3
        elif True in [chan.permissions_for(mbr).manage_guild for chan in mbr.guild.text_channels]:
            permFound = 2
        elif True in [chan.permissions_for(mbr).manage_messages for chan in mbr.guild.text_channels]:
            permFound = 1
        else:
            permFound = 0
        roleCheck = -3
        for role in mbr.roles:
            if str(role.id) in settings.roles:
                if int(settings.roles[str(role.id)]) > roleCheck:
                    roleCheck = int(settings.roles[str(role.id)])
        return max(permFound, roleCheck)

class not_owner(commands.CommandError):
    pass
class not_server_owner(commands.CommandError):
    pass
class not_a_mod(commands.CommandError):
    pass
class not_an_admin(commands.CommandError):
    pass
class not_a_superadmin(commands.CommandError):
    pass
    
    
class specific_permission_error(commands.CommandError):
    def __init__(self):
        self.message = "..." #on second thought i dont even need this but ill leave it as a reminder of what could have been
    
    
class unimplemented(commands.CommandError):
    def __init__(self):
        self.message = "This command is unimplemented"
class disabled_command(commands.CommandError):
    def __init__(self):
        self.message = "This command has been disabled for your server by an admin."
    
    

class cant_do_that(commands.CommandError): # gggggg
    pass
class invalid_command(cant_do_that): # oh man i just remembered i dont even need this too
    def __init__(self, custom):
        self.message = "No command or any alias with the name '"+custom+"' was found."
class specific_error(commands.CommandError):
    def __init__(self, custom):
        self.message = custom


class player_error(commands.CommandError):
    def __init__(self, passed_ctx=None):
        self.message = "This is a generic music player error."
        self.passed_ctx = passed_ctx
        
class downloaderBroke(player_error):
    def __init__(self, passed_ctx):
        self.message = "An error occurred when trying to download the file. This should never happen. I suggest you skip this song."
        self.passed_ctx = passed_ctx
        
class alreadyJoined(player_error):
    def __init__(self):
        self.message = "I am already that voice channel."
        
class alreadyLeft(player_error):
    def __init__(self):
        self.message = "I am not in any voice channels on this server."
        
class entryFailure(player_error):
    def __init__(self):
        self.message = "An error occurred when trying to add the file to the queue.\nThe most likely issue is that the video was not found.\nIn a rare case, the file would still be added to the queue with no information.\nThe most frequent cause of this error is an outdated library. Contact an admin or !report this issue in detail."

class unsupportedPlaylist(player_error):
    def __init__(self):
        self.message = "Playlist queueing is currently unsupported."
        
class playingError(player_error):
    def __init__(self):
        self.message = "An error occurred during playback of the song."
        
class currentlyPlaying(player_error):
    def __init__(self):
        self.message = "You are not allowed to move me while I'm playing music.\nServer mods may move me manually or with commands instead."
        
class contextNoQueue(player_error):
    def __init__(self):
        self.message = "You are not allowed to queue music from your position.\nServer mods can bypass this."

class noChannel(player_error):
    def __init__(self):
        self.message = "You are not in any voice channels on this server.\nServer mods can bypass this."
        
class impossible_noChannel(player_error):
    def __init__(self):
        self.message = "You are not in a voice channel."
        
class outsideChannel(player_error):
    def __init__(self):
        self.message = "You cannot queue music from a different voice channel while music is playing.\nServer mods can bypass this."
        
class modBypassAttempt(player_error):
    def __init__(self):
        self.message = "You cannot queue music if you are not in a voice channel and no voice channel has been established for the player."
        
class drasticChange(player_error):
    def __init__(self):
        self.message = "You attempted to change the volume by more than 30%.\nServer mods can bypass this."
        
class volOutOfBounds(player_error):
    def __init__(self):
        self.message = "Your new volume must be between 1 and 200."
        
class entryDoesntExist(player_error):
    def __init__(self):
        self.message = "No entry exists in the playlist at that position."
        
class alreadySkipped(player_error):
    def __init__(self):
        self.message = "You already voted to skip this entry."
        
class skipFailure(player_error):
    def __init__(self):
        self.message = "There was an error skipping the song. The player could not stop playing."
        
class songTooLong(player_error):
    def __init__(self):
        self.message = "The song you tried to queue is far too long. Try something less than 3 hours."
        
    
class uno_error(commands.CommandError):
    def __init__(self):
        self.message = "This is a generic Uno error. Here are some possible causes:\nError in reformatting your card. Try another way.\nYour card could not be discarded. This might have something to do with formatting.\nTrying to confuse the bot with unusual card inputs."
        
class inProgress(uno_error):
    def __init__(self):
        self.message = "An Uno game is already in progress or your command was not valid."
        
class notInProgress(uno_error):
    def __init__(self):
        self.message = "No Uno game exists in this channel or one has not started yet."
        
class joinTwice(uno_error):
    def __init__(self):
        self.message = "You cannot join an Uno game twice."
        
class maxPlayers(uno_error):
    def __init__(self):
        self.message = "The maximum number of players in this Uno game has been reached. (10)"

class notEnoughPlayers(uno_error):
    def __init__(self):
        self.message = "There are not enough players to start this Uno game."

class notGameOwner(uno_error):
    def __init__(self):
        self.message = "You are not the owner of this Uno game. Server mods can bypass this restriction."
        
class botAlreadyPlaying(uno_error):
    def __init__(self):
        self.message = "The bot is already playing this Uno game."
        
class notPlaying(uno_error):
    def __init__(self):
        self.message = "You are not in this Uno game."
        
class notPlaying_aimed(uno_error):
    def __init__(self):
        self.message = "That person is not in this Uno game."
        
class noPassing(uno_error):
    def __init__(self):
        self.message = "You can't pass in this game type."
        
class mustDraw(uno_error):
    def __init__(self):
        self.message = "You must draw a card before you can pass."
        
class notYourTurn(uno_error):
    def __init__(self):
        self.message = "It is not your turn."
        
class notACard(uno_error):
    def __init__(self):
        self.message = "That is not a valid card."
        
class notHoldingCard(uno_error):
    def __init__(self):
        self.message = "You do not have that card in your hand."
        
class notAColor(uno_error):
    def __init__(self):
        self.message = "That is not a valid color."
        
class notAMatch(uno_error):
    def __init__(self):
        self.message = "That does not match the top card."
        
class blacklisted(uno_error):
    def __init__(self):
        self.message = "You are blacklisted from rejoining this game! :("
        
class notBlacklisted(uno_error):
    def __init__(self):
        self.message = "That player is not blacklisted from this game."
        
class notAble_inProgress(uno_error):
    def __init__(self):
        self.message = "You cannot use this command when the game has started."
        
class outOfBounds(uno_error):
    def __init__(self):
        self.message = "Your number must be between 1 and 100."
        
class joinTwoGames(uno_error):
    def __init__(self):
        self.message = "You can't join two Uno games at once."

