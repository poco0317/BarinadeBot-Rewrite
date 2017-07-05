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
            return is_owner(ctx)
        except:
            pass
        if ctx.message.author.id != ctx.message.guild.owner.id:
            raise not_server_owner
        return True
    
    def is_guild_superadmin(ctx):
        try:
            return is_guild_owner(ctx)
        except:
            pass
        perms = ctx.message.channel.permissions_for(ctx.message.author)
        if perms.administrator:
            return True
        raise not_a_superadmin
    
    def is_guild_admin(ctx):
        try:
            return is_guild_superadmin(ctx)
        except:
            pass
        perms = ctx.message.channel.permissions_for(ctx.message.author)
        if perms.manage_guild:
            return True
        raise not_an_admin
        
    def is_guild_mod(ctx):
        try:
            return is_guild_admin(ctx)
        except:
            pass
        perms = ctx.message.channel.permissions_for(ctx.message.author)
        if perms.manage_messages:
            return True
        raise not_a_mod
        
    def todo(ctx):
        pass
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
    
    
class player_error(commands.CommandError):
    def __init__(self):
        self.message = "This is a generic music player error."
        
class downloaderBroke(player_error):
    def __init__(self):
        self.message = "An error occurred when trying to download the file."
        
class alreadyJoined(player_error):
    def __init__(self):
        self.message = "I am already that voice channel."
        
class alreadyLeft(player_error):
    def __init__(self):
        self.message = "I am not in any voice channels on this server."
    
    
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
        self.message = "Is it not your turn."
        
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