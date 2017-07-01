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
        if ctx.message.author.id != ctx.message.guild.owner.id:
            raise not_server_owner
        return True
    
    def force_error(ctx):
        if ctx.message.content.split()[1] == "1":
            raise not_a_mod
            return False
        else:
            raise inProgress
            return False
        
        
        
    
    
    
    
    
class not_owner(commands.CommandError):
    pass
class not_server_owner(commands.CommandError):
    pass
class not_a_mod(commands.CommandError):
    pass
class not_an_admin(commands.CommandError):
    pass
    
    
class uno_error(commands.CommandError):
    def __init__(self):
        self.message = "An error related to the Uno system that cannot be resolved has occurred."
        
class inProgress(uno_error):
    def __init__(self):
        self.message = "The game is already in progress."
        
class notInProgress(uno_error):
    def __init__(self):
        self.message = "The game has not started yet."
        
class joinTwice(uno_error):
    def __init__(self):
        self.message = "You cannot join the game twice."
        
class maxPlayers(uno_error):
    def __init__(self):
        self.message = "The maximum number of players has been reached."
        
class notGameOwner(uno_error):
    def __init__(self):
        self.message = "You are not the owner of this game."
        
class botAlreadyPlaying(uno_error):
    def __init__(self):
        self.message = "The bot is already playing this game."
        
class notPlaying(uno_error):
    def __init__(self):
        self.message = "You are not in this game."
        
class notPlaying_aimed(uno_error):
    def __init__(self):
        self.message = "That person is not in this game."
        
class noPassing(uno_error):
    def __init__(self):
        self.message = "You cannot pass yet."
        
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