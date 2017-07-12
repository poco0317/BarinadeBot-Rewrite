import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter

class Uno:
    def __init__(self, bot, config, loop, mainbot):
        self.bot = bot #commands related
        self.config = config
        self.loop = loop 
        self.BarryBot = mainbot #BarryBot for keeping data around
    def __repr__(self):
        return "Uno"
    def __str__(self):
        return "Uno."
        
        
    @commands.group(aliases=["u", "nou", "uon"], invoke_without_command=True)
    async def uno(self, ctx, *, gametype : str = "classic"):
        '''The group command for Uno. All Uno commands start with this.
        Using this command with no arguments will start a game of uno if one does not exist in this text channel.
        Starting a game of uno outside of the server's main channel will send a message to the main channel alerting them of the new game.
        
        Optional gametypes can be executed when creating a game instead with !uno type
        Type list: original, highcard, crazy
        Original uno has default draw behavior - 1 draw only
        Highcard uno draw behavior - Using the draw command forces you to draw until you can play
        Crazy uno draw behavior - Draw any number of cards within reason. There are unlimited cards.
            In a Crazy Uno game, you can use !uno draw # to draw that many cards. The limit is 100.
        All uno commands will start off with using this command.
        The play, draw, and pass commands can be used in PM.
        '''
        await ctx.message.delete()
        if ctx.channel.id in self.BarryBot.UnoGames:
            raise inProgress
        if gametype.lower() in ["classic", "class", "old", "original", "orig"]:
            game = The_Game(self.bot, ctx.guild, ctx.channel, ctx.author, "Regular", self.BarryBot)
        elif gametype.lower() in ["hicard", "hic", "highcard", "highroller", "high roller"]:
            game = The_Game(self.bot, ctx.guild, ctx.channel, ctx.author, "High Roller", self.BarryBot)
        elif gametype.lower() in ["crazy", "infinite", "unlimited", "nolimit"]:
            game = The_Game(self.bot, ctx.guild, ctx.channel, ctx.author, "Crazy", self.BarryBot)
        else:
            game = The_Game(self.bot, ctx.guild, ctx.channel, ctx.author, "Regular", self.BarryBot)
        self.BarryBot.UnoGames[ctx.channel.id] = game
        
        embed = discord.Embed(color = discord.Color(0xc27c0e), title=game.gameType+" Uno Game in "+ctx.channel.name+" started by "+ctx.author.name, description="Say '!uno join' to join")
        embed.add_field(name="Players", value="1")
        embed.add_field(name="Current Turn", value=ctx.author.name)
        embed.add_field(name="Top Card", value=" ".join(game.card_Converter(game.topCard[0].split())))
        embed.add_field(name="Next Turn", value="Nobody")
        embed.add_field(name="How to play a card", value="!u p value color")
        embed.add_field(name="Commands - Prefix with !u", value="start, quit, cards\ndraw, pass, bot")
        embed.add_field(name="Card Count", value="\n"+ctx.author.name+": 7")
        game.footer = EmbedFooter()
        embed.set_footer(text=game.footer, icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=game.colorURL)
        game.messageHolder = await ctx.send(embed=embed)
        if game.chan != ctx.guild.default_channel and gametype not in ["silent", "quiet", "unannounced"]:
            game.notifyMessage = await ctx.guild.default_channel.send("A game of "+game.gameType+" Uno is starting in "+game.chan.name+". Say '!uno join' in there to join the game.")
            #pass
            
    @uno.command(hidden=True)
    @commands.check(Perms.is_guild_mod)
    async def update(self, ctx):
        '''- Force the bot to update the uno message if necessary.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        await game.update_Message()
    @uno.command(hidden=True)
    @commands.check(Perms.is_guild_mod)
    async def repost(self, ctx):
        '''- Force the bot to repost the uno message if necessary.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        await game.repost_Message()
    @uno.command(hidden=True)
    @commands.check(Perms.is_guild_mod)
    async def clean(self, ctx):
        '''- Force the bot to remove all uno messages and update the original post.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        await game.repost_Message()
        await game.clean_Messages()
    @uno.command(hidden=True)
    @commands.check(Perms.is_guild_mod)
    async def debug(self, ctx):
        '''- Shows debug info in the channel'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        await game.chan.send("Debug info:\nServer: "+game.boundserver.name+"\nChan:"+game.chan.name+"\nAuthor:"+game.auth.name+"\nPlayersLength:"+str(len(game.players))+"\nCards:"+str(len(game.gameCards))+"\nType:"+game.gameType)
        
    @uno.command(aliases=["shuffle", "reorder"])
    async def shuffleplayers(self, ctx):
        '''- Randomly shuffle the player order of the game in the channel.
        Only the game owner and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id != game.auth.id and not is_mod:
            raise notGameOwner
        if game.gameLaunchedFlag:
            raise notAble_inProgress
        random.shuffle(game.players)
        await game.update_Message()
        await game.chan.send("The player order has been shuffled.", delete_after=10)
        
        
    @uno.command(aliases=["j", "jion", "jon", "joni"])
    async def join(self, ctx):
        '''- Bring you into an existing game of uno.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        if ctx.author.id in game.playerCards:
            raise joinTwice
        for ID,gayme in self.BarryBot.UnoGames.items():
            if ctx.author.id in gayme.playerCards and ID != ctx.channel.id:
                raise joinTwoGames
        if len(game.players) == 10:
            raise maxPlayers
        if ctx.author.id in game.blacklist:
            raise blacklisted
        game.players.append(ctx.author)
        game.playerCards[ctx.author.id] = game.card_Gen(7)
        await game.update_Message()
        await game.chan.send(ctx.author.name+" joined the game as player number "+str(len(game.players))+".", delete_after=10)
        
    @uno.command(aliases=["b", "bot", "bjg", "botjoin", "bjoin", "joinbot", "botjoingmae"])
    async def botjoingame(self, ctx):
        '''- Bring the bot into an existing game of uno.
        Only the game owner and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id != game.auth.id and not is_mod:
            raise notGameOwner
        if game.botFlag:
            raise botAlreadyPlaying
        if len(game.players) == 10:
            raise maxPlayers
        game.players.append(self.bot.user)
        game.playerCards[self.bot.user.id] = game.card_Gen(7)
        game.botFlag = True
        await game.update_Message()
        await game.chan.send(ctx.author.name+" made "+self.bot.user.name+" join the game as player number "+str(len(game.players))+".", delete_after=10)
        
    @uno.command(aliases=["go", "startgame", "begin"])
    async def start(self, ctx):
        '''- Start a game if one is initialized in the channel.
        Only the game owner and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id != game.auth.id and not is_mod:
            raise notGameOwner
        if len(game.players) < 2:
            raise notEnoughPlayers
        if game.gameLaunchedFlag:
            raise inProgress
        game.gameLaunchedFlag = True
        await game.repost_Message()
        await game.rotate_Messages(await ctx.send("The game is starting! It is currently "+game.players[game.currentTurn].name+"'s turn."))
        for person in game.players:
            if person.name != self.bot.user.name:
                await person.send("The game is starting!\n"+game.construct_Update(person.id, getLatest=False))
        
    @uno.command(aliases=["quituno", "leave", "exit", "bye", "kickme", "sucks"])
    async def quit(self, ctx):
        '''- Remove you from the game.
        You will be blacklisted from the game.
        To pardon someone from the blacklist, use !uno allow @user
        Only game owners and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        if ctx.author.id not in game.playerCards:
            raise notPlaying
        if ctx.author.id == game.auth.id:
            game.auth = game.players[game.next_turn(peekNext=True)]
        game.playerLeftText = game.remove_player(ctx.author.id)
        game.blacklist.add(ctx.author.id)
        if game.playerLeftText == "LACK OF PLAYERS":
            await game.messageHolder.delete()
            await game.chan.send("The Uno game must end in a stalemate due to a lack of players.", delete_after=60)
            del self.BarryBot.UnoGames[ctx.channel.id]
            return
        elif game.playerLeftText == "MOVETURN":
            await game.rotate_Messages(await game.chan.send(ctx.author.name+" has left the game and it is now "+game.players[game.currentTurn].name+"'s turn."))
            await game.update_Message()
            if game.players[game.currentTurn].id == self.bot.user.id:
                await game.bot_play()
            else:
                await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
            return
        else:
            await game.rotate_Messages(await game.chan.send(ctx.author.name+" has left the game."))
            await game.update_Message()
            
    @uno.command(aliases=["remove", "ban", "blacklist"], usage="!uno kick @user")
    async def kick(self, ctx, *, member : discord.Member):
        '''- Kick a player from the game, also blacklisting them.
        You must mention the player to kick.
        The kicked player may not rejoin unless allowed back in by the owner of the game or a server mod.
        To remove someone from the blacklist, use !uno allow @user
        Only game owners and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id != game.auth.id and not is_mod:
            raise notGameOwner
        if member.id not in game.playerCards:
            raise notPlaying_aimed
        game.playerLeftText = game.remove_player(member.id)
        game.blacklist.add(member.id)
        if game.playerLeftText == "LACK OF PLAYERS":
            await game.messageHolder.delete()
            await game.rotate_Messages(await game.chan.send("The Uno game must end in a stalemate due to a lack of players."))
            del self.BarryBot.UnoGames[ctx.channel.id]
            return
        elif game.playerLeftText == "MOVETURN":
            await game.rotate_Messages(await game.chan.send(member.mention+" was kicked and it is now "+game.players[game.currentTurn].name+"'s turn."))
            await game.update_Message()
            if game.players[game.currentTurn].id == self.bot.user.id:
                await game.bot_play()
            return
        else:
            await game.rotate_Messages(await game.chan.send(member.mention+" was kicked from the game. It is still "+game.players[game.currentTurn].name+"'s turn."))
            await game.update_Message()
            
    @uno.command(aliases=["unban", "pardon", "free"], usage="!uno allow @user")
    async def allow(self, ctx, *, member : discord.Member):
        '''- Remove a player from a game's blacklist.
        You must mention the player to pardon.
        Only game owners and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id != game.auth.id and not is_mod:
            raise notGameOwner
        if member.id not in game.blacklist:
            raise notBlacklisted
        game.blacklist.remove(member.id)
        await game.chan.send(ctx.author.name+" has allowed "+member.mention+" back into the game.", delete_after=15)
    
    @uno.command(aliases=["end", "halt", "endgame", "stopgame", "kill"])
    async def stop(self, ctx):
        '''- Instantly end the game.
        Only game owners and server mods can do this.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        try:
            is_mod = Perms.is_guild_mod(ctx)
        except:
            is_mod = False
        if ctx.author.id != game.auth.id and not is_mod:
            raise notGameOwner
        await game.messageHolder.delete()
        await game.clean_Messages()
        del self.BarryBot.UnoGames[ctx.channel.id]
        await ctx.channel.send("This uno game has been forcibly stopped.", delete_after=15)
        
    @uno.command(aliases=["cards", "show", "mycards"])
    async def showcards(self, ctx):
        '''- Show you your cards and the top card.'''
        await ctx.message.delete()
        if ctx.channel.id not in self.BarryBot.UnoGames:
            raise notInProgress
        game = self.BarryBot.UnoGames[ctx.channel.id]
        if ctx.author.id not in game.playerCards:
            raise notPlaying
        await ctx.author.send(game.construct_Update(ctx.author.id))
        
    @uno.command(aliases=["d", "getcard", "get", "darw", "ward"])
    async def draw(self, ctx, *, times : int = 1):
        '''- Draw a card if it is your turn.'''
        if ctx.channel.id not in self.BarryBot.UnoGames and ctx.guild:
            raise notInProgress
        if not ctx.guild:
            for ID,gayme in self.BarryBot.UnoGames.items():
                if ctx.author.id in gayme.playerCards:
                    theID = ID
        else:
            await ctx.message.delete()
            theID = ctx.channel.id
        game = self.BarryBot.UnoGames[theID]
        if ctx.author.id not in game.playerCards:
            raise notPlaying
        if ctx.author.id != game.players[game.currentTurn].id:
            raise notYourTurn
        if not game.gameLaunchedFlag:
            raise notInProgress
        if game.gameType == "High Roller":
            topArr = game.topCard[0].split(" ")
            topSimple = game.card_Converter(topArr, Simplify=True)
            for card in game.playerCards[ctx.author.id]:
                if card in ["w", "wd4"] or card.split()[0] == topSimple[0] or card.split()[1] == topSimple[1]:
                    await ctx.author.send("You can't draw because you have a playable card!")
                    await game.chan.send(ctx.author.name+" tried to draw, but has a playable card!", delete_after=10)
                    return
            def quickcheck(card):
                return card in ["w", "wd4"] or card.split()[0] == topSimple[0] or card.split()[1] == topSimple[1]
            game.playerCards[ctx.author.id] = game.playerCards[ctx.author.id]+game.card_Gen(1)
            broken = False
            draws = 1
            while not quickcheck(game.playerCards[ctx.author.id][-1]):
                try:
                    game.playerCards[ctx.author.id] = game.playerCards[ctx.author.id]+game.card_Gen(1)
                    draws += 1
                except:
                    broken = True
                    break
            if broken:
                await ctx.author.send("We have run out of cards to give you! You were forced to pass.")
                game.next_turn()
                await game.update_Message()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" drew so many cards, we ran out!"))
                if game.players[game.currentTurn].id != self.bot.user.id:
                    return await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
                else:
                    return await game.bot_play()
            await ctx.author.send("You drew "+str(draws)+" cards. You can play the last one: "+(" ".join(game.card_Converter(game.playerCards[ctx.author.id][-1].split())) if len(game.card_Converter(game.playerCards[ctx.author.id][-1].split())) == 2 else game.card_Converter([game.playerCards[ctx.author.id][-1]])))
            await game.chan.send(ctx.author.name+" drew "+str(draws)+" cards and has found a card to play.", delete_after=10)
            await game.update_Message()
            return
        if game.gameType == "Crazy":
            if times > 100 or times < 1:
                raise outOfBounds
            game.drawCounter = 1
            game.playerCards[ctx.author.id].extend(game.card_Gen(times))
            if times == 1:
                await game.chan.send(ctx.author.name+" drew 1 card.", delete_after=10)
                await ctx.author.send("You drew: "+(" ".join(game.card_Converter(game.playerCards[ctx.author.id][-1].split())) if len(game.card_Converter(game.playerCards[ctx.author.id][-1].split())) == 2 else game.card_Converter([game.playerCards[ctx.author.id][-1]])))
            else:
                await game.chan.send(ctx.author.name+" drew "+str(times)+" cards.", delete_after=10)
                cardStr = ""
                cardDict = {0:[], 1:[], 2:[], 3:[], 4:[], 5:[], 6:[], 7:[], 8:[]}
                for card in sorted(game.playerCards[ctx.author.id][-times:]):
                    if card == "w":
                        cardDict[7].append("Wild")
                    elif card == "wd4":
                        cardDict[8].append("Wild Draw 4")
                    elif game.card_Converter(card.split())[0] == "Reverse":
                        cardDict[5].append(" ".join(game.card_Converter(card.split())))
                    elif game.card_Converter(card.split())[0] == "Draw2":
                        cardDict[6].append(" ".join(game.card_Converter(card.split())))
                    elif game.card_Converter(card.split())[0] == "Skip":
                        cardDict[4].append(" ".join(game.card_Converter(card.split())))
                    elif game.card_Converter(card.split())[1] == "Red":
                        cardDict[0].append(" ".join(game.card_Converter(card.split())))
                    elif game.card_Converter(card.split())[1] == "Green":
                        cardDict[1].append(" ".join(game.card_Converter(card.split())))
                    elif game.card_Converter(card.split())[1] == "Blue":
                        cardDict[2].append(" ".join(game.card_Converter(card.split())))
                    else:
                        cardDict[3].append(" ".join(game.card_Converter(card.split())))
                for i in range(9):
                    cardStr = cardStr + "\n"
                    cardLine = ""
                    for card in cardDict[i]:
                        cardLine = cardLine + ", " + card
                    cardLine = cardLine[1:]
                    cardStr = cardStr + cardLine
                cardStr = re.sub("\n+", "\n", cardStr)
                await ctx.author.send("You drew:\n "+cardStr.strip())
            await game.update_Message()
            return
                
        if game.drawCounter:
            game.next_turn()
            await game.update_Message()
            game.drawCounter = 0
            await ctx.author.send("You can't draw again! You were forced to pass instead.")
            await game.rotate_Messages(await game.chan.send(ctx.author.name+" was forced to pass instead of drawing! It is now "+game.players[game.currentTurn].name+"'s turn."))
            if game.players[game.currentTurn].id != self.bot.user.id:
                return await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
            else:
                return await game.bot_play()
        if len(game.gameCards) == 0 and len(game.discardedCards) == 0:
            game.next_turn()
            await game.update_Message()
            game.drawCounter = 0
            await ctx.author.send("We ran out of cards! You didn't draw, and the turn was passed.")
            await game.rotate_Messages(await game.chan.send("We have run out of cards! The turn was forced forward. It is now "+game.players[game.currentTurn].name+"'s turn."))
            if game.players[game.currentTurn].id != self.bot.user.bot:
                return await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
            else:
                return await game.bot_play()
        game.playerCards[ctx.author.id] = game.playerCards[ctx.author.id]+game.card_Gen(1)
        if game.players[game.currentTurn].id != self.bot.user.id:
            await ctx.author.send("You drew: "+(" ".join(game.card_Converter(game.playerCards[ctx.author.id][-1].split())) if len(game.card_Converter(game.playerCards[ctx.author.id][-1].split())) == 2 else game.card_Converter([game.playerCards[ctx.author.id][-1]])))
            game.drawCounter += 1
            await game.chan.send(ctx.author.name+" drew a card. They must play it or pass.", delete_after=10)
            
    @uno.command(aliases=["pass", "endturn", "pa", "pas"])
    async def passturn(self, ctx):
        '''- Pass your turn if you drew a card.
        Due to limitations, this command could not be named "pass." Using !uno pass will still work, however.'''
        if ctx.channel.id not in self.BarryBot.UnoGames and ctx.guild:
            raise notInProgress
        if not ctx.guild:
            for ID,gayme in self.BarryBot.UnoGames.items():
                if ctx.author.id in gayme.playerCards:
                    theID = ID
        else:
            await ctx.message.delete()
            theID = ctx.channel.id
        game = self.BarryBot.UnoGames[theID]
        if ctx.author.id not in game.playerCards:
            raise notPlaying
        if ctx.author.id != game.players[game.currentTurn].id:
            raise notYourTurn
        if game.gameType == "High Roller":
            raise noPassing
        if game.drawCounter == 0:
            raise mustDraw
        game.drawCounter = 0
        game.next_turn()
        await game.rotate_Messages(await game.chan.send(ctx.author.name+" passed! It is now "+game.players[game.currentTurn].name+"'s turn."))
        if game.players[game.currentTurn].id != self.bot.user.id:
            await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
        else:
            await game.bot_play()
        
    @uno.command(aliases=["p", "plcard", "card", "use", "pclard", "carl"], usage="!uno play value color")
    async def play(self, ctx, value : str, color : str ):
        '''- Play a card if you have one and it is your turn.
        The command accepts most formats of a given card face and color.
        You may only play a card which matches the top card unless it is a wild.'''
        if ctx.channel.id not in self.BarryBot.UnoGames and ctx.guild:
            raise notInProgress
        if not ctx.guild:
            for ID,gayme in self.BarryBot.UnoGames.items():
                if ctx.author.id in gayme.playerCards:
                    theID = ID
        else:
            await ctx.message.delete()
            theID = ctx.channel.id
        game = self.BarryBot.UnoGames[theID]
        if ctx.author.id not in game.playerCards:
            raise notPlaying
        if ctx.author.id != game.players[game.currentTurn].id:
            raise notYourTurn
        if not game.gameLaunchedFlag:
            raise notInProgress
        cardArr = [value, color]
        topArr = game.topCard[0].split(" ")
        cardSimple = game.card_Converter(cardArr, Simplify=True)
        cardComplicated = game.card_Converter(cardArr)
        topSimple = game.card_Converter(topArr, Simplify=True)
        topComplicated = game.card_Converter(topArr)
        if not game.card_Checker(cardSimple):
            raise notACard
        if not cardSimple or not cardComplicated:
            raise uno_error
        if " ".join(cardSimple) not in game.playerCards[ctx.author.id] and cardSimple[0] not in ["w", "wd4"]:
            raise notHoldingCard
        if cardSimple[0] in ["w", "wd4"] or topSimple[0] == cardSimple[0] or topSimple[1] == cardSimple[1]:
            try:
                if cardSimple[0] in ["w", "wd4"]:
                    game.discard(cardSimple[0], ctx.author.id)
                else:
                    game.discard(" ".join(cardSimple), ctx.author.id)
            except:
                raise uno_error
            game.drawCounter = 0
            game.topCard = [" ".join(cardSimple)]
            if cardSimple[0] == "d2":
                game.next_turn()
                game.playerCards[game.players[game.currentTurn].id].extend(game.card_Gen(2))
                poorGuy = game.players[game.currentTurn]
                game.next_turn()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" skipped "+poorGuy.name+" and forced them to draw 2 cards. It is now "+game.players[game.currentTurn].name+"'s turn."))
            elif cardSimple[0] == "s":
                game.next_turn()
                poorGuy = game.players[game.currentTurn]
                game.next_turn()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" skipped "+poorGuy.name+". It is now "+game.players[game.currentTurn].name+"'s turn."))
            elif cardSimple[0] == "r":
                if game.reverseFlag:
                    game.reverseFlag = False
                else:
                    game.reverseFlag = True
                game.next_turn()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" used a Reverse. It is now "+game.players[game.currentTurn].name+"'s turn."))
            elif cardSimple[0] == "wd4":
                if cardSimple[1] not in ["r", "g", "b", "y"]:
                    raise notAColor
                game.next_turn()
                poorGuy = game.players[game.currentTurn]
                game.playerCards[poorGuy.id].extend(game.card_Gen(4))
                game.next_turn()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" played a Wild Draw 4. "+poorGuy.name+" got skipped and drew 4 cards. The color changed to "+cardComplicated[1]))
            elif cardSimple[0] == "w":
                if cardSimple[1] not in ["r", "g", "b", "y"]:
                    raise notAColor
                game.next_turn()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" played a Wild. The color changed to "+cardComplicated[1]))
            else:
                game.next_turn()
                await game.rotate_Messages(await game.chan.send(ctx.author.name+" played: "+" ".join(cardComplicated)+". It is now "+game.players[game.currentTurn].name+"'s turn."))
            await game.update_Message()
            #try:
            if len(game.playerCards[ctx.author.id]) == 1:
                await game.chan.send("Uno! "+ctx.author.name+" has 1 card left.", delete_after=15)
                if game.players[game.currentTurn].id == self.bot.user.id:
                    await game.bot_play()
                else:
                    await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
                return
            elif len(game.playerCards[ctx.author.id]) == 0:
                await game.clean_Messages()
                await game.chan.send("The game is over. "+ctx.author.name+" has won.")
                await ctx.author.send("You won; the game is over.")
                del self.BarryBot.UnoGames[game.chan.id]
                return
            try:
                if game.players[game.currentTurn].id == self.bot.user.id:
                    await game.bot_play()
                else:
                    await game.players[game.currentTurn].send(game.construct_Update(game.players[game.currentTurn].id))
            except:
                pass
        else:
            raise notAMatch
                
class The_Game:
    def __init__(self, bot, GameServer, GameChannel, GameAuthor, GameType, BarryBot):
        self.boundserver = GameServer
        self.BarryBot = BarryBot
        self.chan = GameChannel             #access name with self.chan.name
        self.auth = GameAuthor              #mostly just to keep track of who made the game
        self.players = [GameAuthor]         #required for most functions    THE MAX AMOUNT OF PLAYERS IS 10 DUE TO THE CONSTRAINT OF THERE BEING FINITE CARDS, 7 PER PERSON
        self.gameType = GameType
        self.gameLaunchedFlag = False       #to keep track of if the game has started (halting most commands)
        self.reverseFlag = True             #True = Normal Play, in the order of the players array.
        self.drawCounter = 0                #to keep track of the number of draws to force or allow a pass
        self.botFlag = False                #to keep track of whether or not the bot is playing
        self.currentTurn = 0                #to keep track of the current turn position in the array of players
        self.gameCards = ["1 b", "2 b", "3 b", "4 b", "5 b", "6 b", "7 b", "8 b", "9 b", "1 y", "2 y", "3 y", "4 y", "5 y", "6 y", "7 y", "8 y", "9 y", "1 g", "2 g", "3 g", "4 g", "5 g", "6 g", "7 g", "8 g", "9 g", "1 r", "2 r", "3 r", "4 r", "5 r", "6 r", "7 r", "8 r", "9 r", "1 b", "2 b", "3 b", "4 b", "5 b", "6 b", "7 b", "8 b", "9 b", "0 b", "1 y", "2 y", "3 y", "4 y", "5 y", "6 y", "7 y", "8 y", "9 y", "0 y", "1 g", "2 g", "3 g", "4 g", "5 g", "6 g", "7 g", "8 g", "9 g", "0 g", "1 r", "2 r", "3 r", "4 r", "5 r", "6 r", "7 r", "8 r", "9 r", "0 r", "wd4", "wd4", "wd4", "wd4", "d2 r", "d2 r", "d2 y", "d2 y", "d2 g", "d2 g", "d2 b", "d2 b", "s r", "s r", "s g", "s g", "s b", "s b", "s y", "s y", "r r", "r r", "r y", "r y", "r b", "r b", "r g", "r g", "w", "w", "w", "w"]
        random.shuffle(self.gameCards)
        random.shuffle(self.gameCards)  #double the shuffle :o
        self.playerLeftText = None          #a holder checked very quickly after it is set to determine the behavior of the next turn
        self.playerCards = {GameAuthor.id:self.card_Gen(7)}      #a dictionary of all players by ID and their cards
        self.topCard = self.card_Gen(1)     #this is actually an array of a single string
        
        if len(self.topCard[0].split()) == 1:       #for the oddball case that we get a wild card for first drawn card
            while len(self.topCard[0].split()) == 1:
                self.gameCards.append(self.topCard[0])
                self.topCard = self.card_Gen(1)
        
        self.discardedCards = [self.topCard[0]]
        
        self.botDrew = False
        
        self.messageHolder = None           #this will be assigned very quickly after the object is made, but not yet
        self.colorURL = self.get_color_url(self.topCard[0].split())
        self.cleanupCounter = 0             #upon reaching 10 this will delete and repost the main message via function. it increments for every noncommand.
        
        self.loop = bot.loop                #to be able to async with the bot
        self.bot = bot                      #to be able to mess with the self.messageHolder
        
        self.mostRecent = None
        self.secondRecent = None
        
        self.blacklist = set()  #a set of IDs
        self.footer = None
        



    def get_color_url(self, cardArr): #this assumes that the card has already been put into simplest terms
        ''' Provides a color URL based on the color of the card given (card must be in array form, [value,color]'''
        
        if cardArr[1].lower() in ["r", "red"]:
            return "http://i.imgur.com/ucyL7Qs.png"
        if cardArr[1].lower() in ["y", "yellow"]:
            return "http://i.imgur.com/kiSKSRp.png"
        if cardArr[1].lower() in ["b", "blue"]:
            return "http://i.imgur.com/r6iBRKF.png"
        if cardArr[1].lower() in ["g", "green"]:
            return "http://i.imgur.com/G1ZiS1G.png"
        
        
    def card_Gen(self, NumberOfCards):
        ''' Generates some cards to deal. It removes cards from the deck, taking from the discarded pile if needed'''

        if len(self.gameCards) < NumberOfCards:
            self.gameCards = self.gameCards + self.discardedCards
            random.shuffle(self.gameCards)
        givencards = []
        if self.gameType == "Crazy":
            for _ in range(NumberOfCards):
                givencards.append(self.gameCards[random.randrange(0,len(self.gameCards))])
        else:
            for _ in range(NumberOfCards):
                givencards.append(self.gameCards.pop(random.randrange(0,len(self.gameCards))))
        return givencards

        
    def card_Checker(self, cardArr):    #it's expected by this point that the card given is in the form of an array
        ''' Checks to see if a card, given as an array ["Value", "Color"], is legitimate'''
    
        if cardArr[0].lower() in ["w", "wd4", "s", "r", "d2", "wild", "wilddraw4", "draw4", "skip", "reverse", "draw2"]: 
            if cardArr[1].lower() in ["r", "g", "b", "y", "red", "green", "blue", "yellow"]:
                return True
        if cardArr[0].lower() in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]:
            if cardArr[1].lower() in ["r", "g", "b", "y", "red", "green", "blue", "yellow"]:
                return True
        return False
    

    def card_Converter(self, cardArr, ColorOnly=False, Simplify=False): #cardArr = ["value", "color"]
        ''' Converts the given card to hopefully a more usable type.
        This may look dirty, but trust me, it was probably must worse before.'''
        
        if ColorOnly:
            if cardArr[0] in ["r", "g", "b", "y"]:
                return ["Red", "Green", "Blue", "Yellow"][["r", "g", "b", "y"].index(cardArr[0].lower())]
            else:
                return cardArr[0].capitalize()
        finalret = ["",""]
        cardArr[0] = cardArr[0].lower()
        numtowords = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        nums = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        if Simplify:
            if len(cardArr) == 1:
                if cardArr[0] in ["wild", "wylde", "wilde", "wile", "will", "weld"]:
                    return "w"
                elif cardArr[0] in ["draw4", "wildraw4", "wilddraw4", "4", "draw 4"]:
                    return "wd4"
                if cardArr[0] in ["w", "wd4"]:
                    return cardArr[0]
                return None
            if cardArr[0] in ["wild", "wylde", "wilde", "wile", "will", "weld"]:
                finalret[0] = "w"
            elif cardArr[0] in ["draw4", "wildraw4", "wilddraw4", "draw 4"]:
                finalret[0] = "wd4"
            elif cardArr[0] in ["sip", "skip", "sep"]:
                finalret[0] = "s"
            elif cardArr[0] in ["draw2", "dr2", "wilddraw2", "wild2"]:
                finalret[0] = "d2"
            elif cardArr[0] in ["reverse", "rev", "revrese", "revrse", "reverses"]:
                finalret[0] = "r"
            elif cardArr[0] in numtowords:
                finalret[0] = str(numtowords.index(cardArr[0]))
            else:
                finalret[0] = cardArr[0]
            if cardArr[1] in ["re", "red", "rer"]:
                finalret[1] = "r"
            elif cardArr[1] in ["bleu", "blue", "bule"]:
                finalret[1] = "b"
            elif cardArr[1] in ["gren", "grenn", "green", "greeen"]:
                finalret[1] = "g"
            elif cardArr[1] in ["yelo", "yello", "yellow", "yeloh"]:
                finalret[1] = "y"
            else:
                finalret[1] = cardArr[1]
            return finalret
        else:
            if len(cardArr) == 1:
                if cardArr[0] == "w":
                    return "Wild"
                elif cardArr[0] in ["d4", "wd4", "wild4"]:
                    return "WildDraw4"
                if cardArr[0] in ["wild", "wilddraw4"]:
                    return cardArr[0].capitalize()
                return None
            if cardArr[0] in nums:
                finalret[0] = numtowords[nums.index(cardArr[0])].capitalize()
            elif cardArr[0] == "w":
                finalret[0] = "Wild"
            elif cardArr[0] in ["d4", "wd4", "w4"]:
                finalret[0] = "WildDraw4"
            elif cardArr[0] == "s":
                finalret[0] = "Skip"
            elif cardArr[0] == "r":
                finalret[0] = "Reverse"
            elif cardArr[0] == "d2":
                finalret[0] = "Draw2"
            else:
                finalret[0] = cardArr[0].capitalize()
            if cardArr[1] == "r":
                finalret[1] = "Red"
            elif cardArr[1] == "b":
                finalret[1] = "Blue"
            elif cardArr[1] == "g":
                finalret[1] = "Green"
            elif cardArr[1] == "y":
                finalret[1] = "Yellow"
            else:
                finalret[1] = cardArr[1].capitalize()
            return finalret
        
        
    def discard(self, card, playerID): #by this point, it is expected that the card is in string form
        ''' Send a card to the discard pile from a player's deck'''
    
        self.playerCards[playerID].remove(card)
        if self.gameType == "Crazy":
            return
        self.discardedCards.append(card)
        
        
    def remove_player(self, playerID):
        ''' Remove a player from the game and discard their cards. It returns a string used later on to determine what to do next'''
    
        self.discardedCards = self.discardedCards + self.playerCards[playerID]
        del self.playerCards[playerID]
        for i in range(len(self.players)):
            if self.players[i].id == playerID:
                self.players.pop(i)
                break
                
        if len(self.players) < 2:
            return "LACK OF PLAYERS"
            
        if i == self.currentTurn:
            self.next_turn()
            return "MOVETURN"
            
        if i < self.currentTurn: #this is a special case where the next time we move the turn, we might not be allowed to actually move the counter
            self.currentTurn -= 1
            return "HOLDTURN"
            
        return "PLAYERLEFT"
    
    
    def next_turn(self, peekNext = False):
        ''' Literally iterates the turn counter forward or backwards in a looping fashion'''
        if peekNext:
            fakeTurn = self.currentTurn
            if self.reverseFlag:
                fakeTurn += 1
            else:
                fakeTurn -= 1
            if fakeTurn >= len(self.players):
                fakeTurn = 0
            elif fakeTurn < 0:
                fakeTurn = len(self.players)-1
            return fakeTurn
        
        if self.reverseFlag:    #true = normal play
            self.currentTurn += 1
        else:
            self.currentTurn -= 1
        if self.currentTurn >= len(self.players):
            self.currentTurn = 0
        elif self.currentTurn < 0:
            self.currentTurn = len(self.players)-1
            
            
    async def update_Message(self):
        ''' Updates the main uno message with all necessary information'''
        
        cardCountListStr = ""
        for person in self.players:
            cardCountListStr = cardCountListStr + "   " + person.name + ": "+ str(len(self.playerCards[person.id]))
        cardCountListStr = cardCountListStr.strip()
        nextPlayer = self.players[self.next_turn(peekNext=True)]
        curPlayer = self.players[self.currentTurn]
        self.colorURL = self.get_color_url(self.topCard[0].split())
        if self.topCard[0].split()[1] in ["r", "b", "g", "y"]:
            topCardStr = " ".join(self.card_Converter(self.topCard[0].split()))
        else:
            topCardStr = self.topCard[0]
        embed = discord.Embed(color = discord.Color(0xc27c0e), title=self.gameType+" Uno Game in "+self.chan.name+" started by "+self.auth.name, description="Say '!uno join' to join")
        embed.add_field(name="Players", value=str(len(self.players)), inline=True)
        embed.add_field(name="Current Turn", value=curPlayer.name, inline=True)
        embed.add_field(name="Top Card", value=" ".join(self.card_Converter(self.topCard[0].split())), inline=True)
        embed.add_field(name="Next Turn", value=nextPlayer.name, inline=True)
        embed.add_field(name="How to play a card", value="!u p value color", inline=True)
        embed.add_field(name="Commands - Prefix with !u", value="start, quit, cards\ndraw, pass, bot", inline=True)
        embed.add_field(name="Card Count", value="\n"+cardCountListStr)
        embed.set_footer(text=self.footer, icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=self.colorURL)
        await self.messageHolder.edit(content=".", embed=embed)
        
        
    def construct_Update(self, ID, getLatest=True):
        ''' This will create a string used for PMing players their cards and the latest game updates'''
        
        finalStr = ""
        if self.mostRecent and self.players[self.currentTurn].id == ID and getLatest:
            finalStr = "Latest Status Message:\n"+self.mostRecent.content
        for player in self.players:
            alreadyPosted = False
            if player.id != ID and len(self.playerCards[player.id]) == 1 and alreadyPosted:
                finalStr = finalStr + " " + player.name
            if player.id != ID and len(self.playerCards[player.id]) == 1 and not alreadyPosted:
                finalStr = finalStr + "\nPlayers with 1 Card Left: "+player.name
        if self.players[self.currentTurn].id == ID:
            finalStr = finalStr + "\n**It is your turn!**"
        finalStr = finalStr + "\n\nTop Card: " + " ".join(self.card_Converter(self.topCard[0].split()))
     
        cardStr = ""
        cardDict = {0:[], 1:[], 2:[], 3:[], 4:[], 5:[], 6:[], 7:[], 8:[]}
        for card in sorted(self.playerCards[ID]):
            if card == "w":
                cardDict[7].append("Wild")
            elif card == "wd4":
                cardDict[8].append("Wild Draw 4")
            elif self.card_Converter(card.split())[0] == "Reverse":
                cardDict[5].append(" ".join(self.card_Converter(card.split())))
            elif self.card_Converter(card.split())[0] == "Draw2":
                cardDict[6].append(" ".join(self.card_Converter(card.split())))
            elif self.card_Converter(card.split())[0] == "Skip":
                cardDict[4].append(" ".join(self.card_Converter(card.split())))
            elif self.card_Converter(card.split())[1] == "Red":
                cardDict[0].append(" ".join(self.card_Converter(card.split())))
            elif self.card_Converter(card.split())[1] == "Green":
                cardDict[1].append(" ".join(self.card_Converter(card.split())))
            elif self.card_Converter(card.split())[1] == "Blue":
                cardDict[2].append(" ".join(self.card_Converter(card.split())))
            else:
                cardDict[3].append(" ".join(self.card_Converter(card.split())))
        for i in range(9):
            cardStr = cardStr + "\n"
            cardLine = ""
            for card in cardDict[i]:
                cardLine = cardLine + ", " + card
            cardLine = cardLine[1:]
            cardStr = cardStr + cardLine
        cardStr = re.sub("\n+", "\n", cardStr)
        finalStr = finalStr + "\nYour Cards:\n " + cardStr.strip()
        return finalStr.strip()
        
    
    async def clean_Messages(self, Latest=True, Alt=True):
        ''' Deletes existing queue of 2 messages from the bot if they exist'''
        
        if Latest:
            try:
                await self.mostRecent.delete()
            except:
                pass
        if Alt:
            try:
                await self.secondRecent.delete()
            except:
                pass
    
    
    async def rotate_Messages(self, Incoming):
        ''' Keeps the last 2 messages running through the game alive and deletes the older ones.
            The "Uno!" message runs on a separate timer.'''
            
        try:
            await self.secondRecent.delete()
        except:
            pass
        try:
            self.secondRecent = self.mostRecent
        except:
            pass
        self.mostRecent = Incoming
            
            
            
    async def repost_Message(self):
        ''' Updates and reposts the main uno message with all necessary information'''
         
        await self.messageHolder.delete()
        self.messageHolder = await self.chan.send(".")
        await self.update_Message()
    
    
    async def bot_play(self):
        ''' This runs every time it is the bot's turn and checks every possibility of something happening'''
        
        I_Can_Play = False
        topArr = self.topCard[0].split(" ")
        topSimple = self.card_Converter(topArr, Simplify=True)
        topComplicated = self.card_Converter(topArr)
        for card in self.playerCards[self.bot.user.id]:
            if card in ["w", "wd4"] or card.split()[0] == topSimple[0] or card.split()[1] == topSimple[1]:
                I_Can_Play = True
                print(topArr)
                print(card)
                print("___")
                break
        if not I_Can_Play:
            if len(self.gameCards) == 0 and len(self.discardedCards) == 0:
                self.next_turn()
                await self.update_Message()
                await self.rotate_Messages(await self.chan.send("We have run out of cards! The turn was forced forward."))
                await self.players[self.currentTurn].send(self.construct_Update(self.players[self.currentTurn].id))
                return
            if self.gameType == "High Roller":
                def quickcheck(card):
                    return card in ["w", "wd4"] or card.split()[0] == topSimple[0] or card.split()[1] == topSimple[1]
                broken = False
                draws = 1
                self.playerCards[self.bot.user.id] = self.playerCards[self.bot.user.id] + self.card_Gen(1)
                while not quickcheck(self.playerCards[self.bot.user.id][-1]):
                    try:
                        self.playerCards[self.bot.user.id] = self.playerCards[self.bot.user.id]+self.card_Gen(1)
                        draws += 1
                    except:
                        broken = True
                        break
                if broken:
                    self.next_turn()
                    await self.update_Message()
                    await self.rotate_Messages(await self.chan.send(self.bot.user.name+" drew so many cards, we ran out!"))
                    return await self.players[self.currentTurn].send(self.construct_Update(self.players[self.currentTurn].id))
                I_Can_Play = True
                card = self.playerCards[self.bot.user.id][-1]
                await self.chan.send(self.bot.user.name+" drew "+str(draws)+" cards and has found a card to play.", delete_after=10)
                await self.update_Message()
            else:
                self.playerCards[self.bot.user.id] = self.playerCards[self.bot.user.id] + self.card_Gen(1)
                await self.update_Message()
                for card in self.playerCards[self.bot.user.id]:
                    if card in ["w", "wd4"] or card.split()[0] == topSimple[0] or card.split()[1] == topSimple[1]:
                        I_Can_Play = True
                        print(topArr)
                        print(card)
                        print("___")
                        break
        if I_Can_Play:
            self.drawCounter = 0
            try:
                playedColor = card.split()[1]
            except:
                colors = ["r","b","g","y"]
                colors.pop(colors.index(topSimple[1]))
                playedColor = colors[random.randint(0,2)]
            self.discard(card, self.bot.user.id)
            if card in ["w", "wd4"]:
                self.topCard = [card+" "+playedColor]
            else:
                self.topCard = [card.split()[0]+" "+playedColor]
            cardArr = self.topCard[0].split()
            cardComplicated = self.card_Converter(cardArr)
            if cardArr[0] == "d2":
                self.next_turn()
                self.playerCards[self.players[self.currentTurn].id].extend(self.card_Gen(2))
                poorGuy = self.players[self.currentTurn]
                self.next_turn()
                await self.rotate_Messages(await self.chan.send(self.bot.user.name+" skipped "+poorGuy.name+" and forced them to draw 2 cards. It is now "+self.players[self.currentTurn].name+"'s turn."))
            elif cardArr[0] == "s":
                self.next_turn()
                poorGuy = self.players[self.currentTurn]
                self.next_turn()
                await self.rotate_Messages(await self.chan.send(self.bot.user.name+" skipped "+poorGuy.name+". It is now "+self.players[self.currentTurn].name+"'s turn."))
            elif cardArr[0] == "r":
                if self.reverseFlag:
                    self.reverseFlag = False
                else:
                    self.reverseFlag = True
                self.next_turn()
                await self.rotate_Messages(await self.chan.send(self.bot.user.name+" used a Reverse. It is now "+self.players[self.currentTurn].name+"'s turn."))
            elif cardArr[0] == "wd4":
                self.next_turn()
                poorGuy = self.players[self.currentTurn]
                self.playerCards[poorGuy.id].extend(self.card_Gen(4))
                self.next_turn()
                await self.rotate_Messages(await self.chan.send(self.bot.user.name+" played a Wild Draw 4. "+poorGuy.name+" got skipped and drew 4 cards. The color changed to "+cardComplicated[1]))
            elif cardArr[0] == "w":
                self.next_turn()
                await self.rotate_Messages(await self.chan.send(self.bot.user.name+" played a Wild. The color changed to "+cardComplicated[1]))
            else:
                self.next_turn()
                await self.rotate_Messages(await self.chan.send(self.bot.user.name+" played: "+" ".join(cardComplicated)+". It is now "+self.players[self.currentTurn].name+"'s turn."))
            await self.update_Message()
            
            
            if self.players[self.currentTurn].id == self.bot.user.id:
                await self.bot_play()
            else:
                await self.players[self.currentTurn].send(self.construct_Update(self.players[self.currentTurn].id))
            try:
                if len(self.playerCards[self.bot.user.id]) == 1:
                    delete_uno = await self.chan.send("UNO! "+self.bot.user.name+" has 1 card left.", delete_after=15)
                elif len(self.playerCards[self.bot.user.id]) == 0:
                    del self.BarryBot.UnoGames[self.chan.id]
                    return await self.chan.send("The game is over. "+self.bot.user.name+" has won.")
            except:
                pass
        else:
            self.drawCounter = 0
            self.next_turn()
            await self.rotate_Messages(await self.chan.send(self.bot.user.name+" passed. It is now "+self.players[self.currentTurn].name+"'s turn."))
            await self.players[self.currentTurn].send(self.construct_Update(self.players[self.currentTurn].id))
        
        
        
        
        
        
        
        
        
        
        
        
        

        
