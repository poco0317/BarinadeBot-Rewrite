import os
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
        if command_check is None:
            command_check = ctx.command.name
        found = settings.commands[command_check]
        # this is intended to be used on a per-command basis where the syntax is:
        # -1 = disabled
        # 0 = default: using predefined permissions
        # 1 = mod+ (manage messages)
        # 2 = admin+ (manage server)
        # 3 = superadmin+ (administrator permission)
        # 4 = guild owner
        
        #this function either returns True, False (default), or throws an error.
        roleCheck = -2
        for role in ctx.author.roles: # this finds the highest permission role the user has according to my system
                if str(role.id) in settings.roles:
                    if int(settings.roles[str(role.id)]) > roleCheck:
                        roleCheck = int(settings.roles[str(role.id)])
        if roleCheck > -2:
            found = int(found)
            if found <= roleCheck and found > 0:
                return True
            if found == -1:
                raise disabled_command
            if found == 0:
                return False
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
            return False
        elif found == "1":
            return Perms.is_guild_mod(ctx)
        elif found == "2":
            return Perms.is_guild_admin(ctx)
        elif found == "3":
            return Perms.is_guild_superadmin(ctx)
        elif found == "4":
            return Perms.is_guild_owner(ctx)
        else:
            print("Something went wrong calculating permissions for a specific command: "+settings.serverID+" "+command_check)
            return False
    
        #functions for config and server specific checks whether to allow commands to all or just mods/admins
    
        
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
    
    
    
    
    
    
class player_error(commands.CommandError):
    def __init__(self, passed_ctx=None):
        self.message = "This is a generic music player error."
        self.passed_ctx = passed_ctx
        
class downloaderBroke(player_error):
    def __init__(self, passed_ctx):
        self.message = "An error occurred when trying to download the file."
        self.passed_ctx = passed_ctx
        
class alreadyJoined(player_error):
    def __init__(self):
        self.message = "I am already that voice channel."
        
class alreadyLeft(player_error):
    def __init__(self):
        self.message = "I am not in any voice channels on this server."
        
class entryFailure(player_error):
    def __init__(self):
        self.message = "An error occurred when trying to add the file to the queue.\nThe most likely issue is that the video was not found.\nIn a rare case, the file would still be added to the queue with no information."
        
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