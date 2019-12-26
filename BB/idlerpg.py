import sqlite3
import discord
import asyncio
import random
import shutil
import traceback
import decimal
from decimal import Decimal
from discord.ext import commands
from BB.permissions import *
from BB.misc import *



class RPGSession:
    def __init__(self, bot, GameServer, GameChannel, BarryBot):
        self.boundserver = GameServer
        self.BarryBot = BarryBot
        self.chan = GameChannel
        self.bot = bot
        self.loop = bot.loop
        #self.db = RPGDB()


        self.playerData = {}    # a dict of every player and their stats
        self.interval = 30      # the rate at which the game ticks for the idle part of the idle rpg
        self.mapEnum = None     # a short string for the mapStr creator
        self.mapStr = None      # literal ascii art

        self.save_filepath = os.path.dirname(os.path.dirname(BarryBot.config.options))+"/rpg/"+str(GameServer.id)+".save"

        self.loadData()
        self.saveData()
        #self.loop.create_task(self._tick_loop())




    def _load_file(self, dir, option="r", ext="save"):
        try:
            the_file = open(dir, option, encoding="utf-8")
            return the_file
        except:
            try:
                print("Created RPG data from default file.")
                print("It should exist here: " + dir)
                shutil.copy(os.path.dirname(self.save_filepath)+"/example_"+ext+"."+ext, self.save_filepath)
                the_file = open(dir, option, encoding="utf-8")
                return the_file
            except:
                print("Well... Somehow the default is gone too. Good luck.")
                traceback.print_exc()
                os._exit(2)

    def loadData(self):
        ''' Load the saved data of the game... if it exists'''
        file = self._load_file(self.save_filepath)
        for line in file:
            try:
                data = line.split(",")
                self.playerData[int(data[0])] = data[1:]
            except:
                pass
        file.close()
        self.interval = int(self.BarryBot.settings[self.boundserver.id].features["rpg_interval"])
        self.mapEnum = self.BarryBot.settings[self.boundserver.id].features["rpg_map"]

    def saveData(self):
        ''' Save the data for the game'''
        output = "userID,name,health,experience,weapon1,weapon2,helmet,body,hands,feet,trinket,str,dex,int,agi,con,luc,location,money\n"
        for k,v in self.playerData.items():
            output = output + str(k) + "," + ",".join(v) + "\n"
        file = self._load_file(self.save_filepath, option="w")
        file.write(output)
        file.close()



class RPG:
    def __init__(self, bot, config, loop, mainbot):
        self.bot = bot
        self.config = config
        self.loop = loop
        self.BarryBot = mainbot
        self.sessions = {}
        self.loop.create_task(self._tick_loop())
        self.db = RPGDB()
        decimal.getcontext().prec = 80
        self.bigcontext = decimal.Context(prec=80)
        self.smallcontext = decimal.Context(prec=5)

    async def _tick_loop(self):
        #self.interval = int(self.BarryBot.settings[self.boundserver.id].features["rpg_Interval"])
        await asyncio.sleep(5)
        if self.checkAllSessions():
            self.tickPlayers()
            #self.saveData()
        self.loop.create_task(self._tick_loop())

    def tickPlayers(self):
        ''' Increase XP and stuff for everyone'''
        # 5 xp per tick
        # strength and luck increase xp in some ways
        self.db.incrementColumn()
        players = self.db.getWholeTable(table="players")
        for row in players:
            xp = Decimal(row[6])
            lvl = Decimal(row[9])
            requirement = 100 ** (1 + lvl * Decimal(".05"))
            leftover = Decimal(xp - requirement)
            if leftover >= 0:
                lvl += 1
                levelpoints = str(int(row[23]) + 5)
                newhp = str(Decimal(row[7]).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN) + 5)
                newmaxhp = str(Decimal(row[8]).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN) + 5)
                self.db.updateStat(table="players", comparisonId=row[0], column='experience', new=str(Decimal(leftover)))
                self.db.updateStat(table="players", comparisonId=row[0], column='level', new=str(Decimal(lvl)))
                self.db.updateStat(table="players", comparisonId=row[0], column='levelpoints', new=levelpoints)
                self.db.updateStat(table="players", comparisonId=row[0], column='hp', new=newhp)
                self.db.updateStat(table="players", comparisonId=row[0], column='maxhp', new=newmaxhp)

    def new_player(self, member : discord.Member, name="Nameless", gender='agender', race='racist'):
        ''' Add a new player to the system'''
        # self.playerData[member.id] = [member.name, "100", "1", "0", "0", "0", "0", "0", "0", "0", "1", "1", "1", "1", "1", "1", "grass", "10"]
        # self.saveData()
        self.db.addPlayer(member.id, name, gender, race)

    def del_player(self, member: discord.Member):
        ''' Remove a player from the system'''
        # del self.playerData[member.id]
        # self.saveData()
        self.db.delPlayer(member.id)

    def checkSession(self, server):
        ''' quick check to see if a server can host the idle rpg'''
        on = False
        working = False
        try:
            foundchan = discord.utils.get(server.text_channels, id=int(self.BarryBot.settings[server.id].features["rpg_channel_ID"])).name
        except:
            foundchan = "NO CHANNEL"
        try:
            if self.BarryBot.settings[server.id].features["rpg_Enabled"] == "1":
                on = True
            if self.BarryBot.settings[server.id].features["rpg_channel_ID"] != "0" and foundchan != "NO CHANNEL":
                working = True
        except:
            traceback.print_exc()
            return False
        return on and working

    def checkAllSessions(self):
        ''' check every server to see if ANY of them will accept a player tick'''
        for g in self.bot.guilds:
            if self.checkSession(g):
                return True
        return False


    @commands.group(aliases=["r"])
    async def rpg(self, ctx):
        '''The group command for Idle RPG. All Idle RPG commands start with this.
        I dunno lol
        '''
        pass

    @rpg.command(aliases=["adv"])
    async def adventure(self, ctx):
        '''Go on an adventure'''
        try:
            if self.checkSession(ctx.guild):
                data = self.db.getPlayer(ctx.author.id)
                if data is not None:
                    w1name, w1desc, w1rarity, w1type, w1damage, w1element, w1stat, w1scale, w1levelreq = map(str, data[4].split("^"))
                    w2name, w2desc, w2rarity, w2type, w2damage, w2element, w2stat, w2scale, w2levelreq = map(str, data[5].split("^"))
                    helmname, helmdesc, helmrarity, helmtype, helmdef, helmelement, helmlevelreq = map(str, data[10].split("•"))
                    bodyname, bodydesc, bodyrarity, bodytype, bodydef, bodyelement, bodylevelreq = map(str, data[11].split("•"))
                    handname, handdesc, handrarity, handtype, handdef, handelement, handlevelreq = map(str, data[12].split("•"))
                    feetname, feetdesc, feetrarity, feettype, feetdef, feetelement, feetlevelreq = map(str, data[13].split("•"))
                    trinname, trindesc, trinrarity, trintype, trinval, trinelement, trinextra, trinlevelreq, trinstat, trinscale = map(str, data[14].split("◘"))
                    w1 = RPGWeapon(w1name, w1desc, w1rarity, w1type, w1damage, w1element, w1stat, w1scale, w1levelreq)
                    w2 = RPGWeapon(w2name, w2desc, w2rarity, w2type, w2damage, w2element, w2stat, w2scale, w2levelreq)
                    helm = RPGArmor(helmname, helmdesc, helmrarity, helmtype, helmdef, helmelement, helmlevelreq)
                    body = RPGArmor(bodyname, bodydesc, bodyrarity, bodytype, bodydef, bodyelement, bodylevelreq)
                    hand = RPGArmor(handname, handdesc, handrarity, handtype, handdef, handelement, handlevelreq)
                    feet = RPGArmor(feetname, feetdesc, feetrarity, feettype, feetdef, feetelement, feetlevelreq)
                    trin = RPGTrinket(trinname, trindesc, trinrarity, trintype, trinval, trinelement, trinextra, trinlevelreq, trinstat, trinscale)
                    you = RPGCharacter(id=ctx.author.id, name=data[1], gender=data[2], race=data[3], weaponL=w1, weaponR=w2, helmet=helm,
                                       body=body, hands=hand, feet=feet, trinket=trin, stren=int(data[15]), dex=int(data[16]), inte=int(data[17]),
                                       agi=int(data[18]), cons=int(data[19]), luck=int(data[20]), hp=int(data[7]), maxhp=int(data[8]), money=int(data[22]))
                    battle = RPGBattle(self.BarryBot, ctx, [you], [RPGCharacter()], db=self.db)
                    await battle.initBattle()
                else:
                    await ctx.send("You are not playing the Idle RPG.", delete_after=15)
            else:
                await ctx.send("The Idle RPG is not enabled on this server. Ask an Admin to enable it.", delete_after=15)
        except:
            traceback.print_exc()


    @rpg.command()
    async def shop(self, ctx):
        '''Shop for items'''
        pass

    @rpg.command()
    async def edit(self, ctx):
        '''Modify your character info'''
        pass

    @rpg.command(aliases=["boost", "levelup"])
    async def level(self, ctx):
        '''Open the stat leveling menu'''
        if self.checkSession(ctx.guild):
            data = self.db.getPlayer(ctx.author.id)
            if data is not None:
                m = RPGMenu(ctx.channel, self.BarryBot, ctx)
                points = str(data[23])
                def updatePoints():
                    datum = self.db.getPlayer(ctx.author.id)
                    self.db.updateStat(table="players", comparisonId=datum[0], column="levelpoints", new=str(int(datum[23])-1))
                    m.currentscreen.description = "Exchange your points for skills\nPoints: "+str(int(datum[23])-1)
                    #self.loop.create_task(m.refreshScreen())
                def checkPoints():
                    datum = self.db.getPlayer(ctx.author.id)
                    if int(datum[23]) <= 0:
                        return False
                    return True
                stren = str(data[15])
                def updateStrength():
                    if checkPoints():
                        updatePoints()
                        datum = self.db.getPlayer(ctx.author.id)
                        self.db.updateStat(table="players", comparisonId=datum[0], column='strength', new=str(int(datum[15])+1))

                        self.loop.create_task(m.modifyScreen(embedTitle="Strength (A)", embedChange=str(int(datum[15])+1)))
                def updateIntelligence():
                    if checkPoints():
                        updatePoints()
                        datum = self.db.getPlayer(ctx.author.id)
                        self.db.updateStat(table="players", comparisonId=datum[0], column='intelligence', new=str(int(datum[17])+1))
                        self.loop.create_task(m.modifyScreen(embedTitle="Intelligence (C)", embedChange=str(int(datum[17])+1)))
                def updateAgility():
                    if checkPoints():
                        updatePoints()
                        datum = self.db.getPlayer(ctx.author.id)
                        self.db.updateStat(table="players", comparisonId=datum[0], column='agility', new=str(int(datum[18])+1))
                        self.loop.create_task(m.modifyScreen(embedTitle="Agility (D)", embedChange=str(int(datum[18])+1)))
                def updateConstitution():
                    if checkPoints():
                        updatePoints()
                        datum = self.db.getPlayer(ctx.author.id)
                        self.db.updateStat(table="players", comparisonId=datum[0], column='constitution', new=str(int(datum[19])+1))
                        self.loop.create_task(m.modifyScreen(embedTitle="Constitution (E)", embedChange=str(int(datum[19])+1)))
                def updateDexterity():
                    if checkPoints():
                        updatePoints()
                        datum = self.db.getPlayer(ctx.author.id)
                        self.db.updateStat(table="players", comparisonId=datum[0], column='dexterity', new=str(int(datum[16])+1))
                        self.loop.create_task(m.modifyScreen(embedTitle="Dexterity (B)", embedChange=str(int(datum[16])+1)))
                def updateLuck():
                    if checkPoints():
                        updatePoints()
                        datum = self.db.getPlayer(ctx.author.id)
                        self.db.updateStat(table="players", comparisonId=datum[0], column='luck', new=str(int(datum[20])+1))
                        self.loop.create_task(m.modifyScreen(embedTitle="Luck (F)", embedChange=str(int(datum[20])+1)))
                dex = str(data[16])
                intel = str(data[17])
                agi = str(data[18])
                cons = str(data[19])
                luck = str(data[20])
                choices = [updateStrength, updateDexterity, updateIntelligence, updateAgility, updateConstitution, updateLuck]
                m.addScreen(text="Exchange your points for skills\nPoints: "+points, embedFields=[("Strength (A)", stren),("Dexterity (B)", dex),("Intelligence (C)",intel),("Agility (D)",agi),("Constitution (E)",cons),("Luck (F)",luck)], menuName="Stat Leveler", choices=choices, closeable=True)
                await m.initiateMenu()
            else:
                await ctx.send("You are not playing the Idle RPG.", delete_after=15)
        else:
            await ctx.send("The Idle RPG is not enabled on this server. Ask an Admin to enable it.", delete_after=15)



    @rpg.command(aliases=["j"])
    async def join(self, ctx):
        '''Join the Idle RPG'''
        try:
            if self.checkSession(ctx.guild):
                if self.db.getPlayer(ctx.author.id) is None:
                    def checkName(message):
                        return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id
                    def checkGender(message):
                        return checkName(message) and message.content.lower() in {"male", "female", "agender", "random"}
                    delete_later = await ctx.send("Welcome to the Idle RPG, "+ctx.author.mention+". We will now create your character.\nEnter a name or type `random`.\nIf you enter nothing for 60 seconds, I will cancel.")


                    try:
                        msg = await self.bot.wait_for("message", check=checkName, timeout=60)
                    except:
                        return await delete_later.delete()

                    if msg.content.lower() == "random":
                        name = random.choice(["name"])
                    else:
                        name = msg.content
                    await msg.delete()

                    await delete_later.edit(content="Welcome to the Idle RPG, "+ctx.author.mention+". We will now create your character.\nName: "+msg.content+"\nEnter a race or type `random`.\nIf you enter nothing for 60 seconds, I will cancel.")

                    try:
                        msg = await self.bot.wait_for("message", check=checkName, timeout=60)
                    except:
                        return await delete_later.delete()


                    if msg.content.lower() == "random":
                        race = random.choice(["race"])
                    else:
                        race = msg.content.capitalize()
                    await msg.delete()
                    await delete_later.edit(content="Welcome to the Idle RPG, "+ctx.author.mention+". We will now create your character.\nName: "+name+"\nRace: "+race+"\nEnter a gender from the list or type `random`: male, female, agender.\nIf you enter nothing for 60 seconds, I will cancel.")

                    try:
                        msg = await self.bot.wait_for("message", check=checkGender, timeout=60)
                    except:
                        return await delete_later.delete()

                    if msg.content.lower() == "random":
                        gender = random.choice(["Male", "Female", "Agender"])
                    else:
                        gender = msg.content.capitalize()
                    await msg.delete()

                    self.new_player(ctx.author, name=name, gender=gender, race=race)


                    await delete_later.edit(content="Welcome to the Idle RPG, "+ctx.author.mention+".\nName: "+name+"\nRace: "+race+"\nGender: "+gender+"\nYour XP ticks every 5 seconds. Good luck.")
                else:
                    await ctx.send("You are already a part of the Idle RPG.", delete_after=15)
            else:
                await ctx.send("The Idle RPG feature is not enabled on this server. Ask an Admin to enable it.", delete_after=15)
        except:
            traceback.print_exc()

    @rpg.command(aliases=["quit"])
    async def leave(self, ctx):
        '''Quit the Idle RPG'''
        if self.checkSession(ctx.guild):
            if self.db.getPlayer(ctx.author.id) is not None:

                def check_if_author(reaction, user):
                    return reaction.emoji == "👌" and user.id == ctx.author.id
                delete_later = await ctx.send("I will delete your user data from the Idle RPG. It cannot be recovered.\nHit me with a 👌 to confirm this.\n(You have 15 seconds to decide)")
                await delete_later.add_reaction("👌")
                try:
                    await self.bot.wait_for("reaction_add", check=check_if_author, timeout=15)
                except:
                    return await delete_later.delete()
                self.del_player(ctx.author)
                await delete_later.delete()
                await ctx.send("You have left the Idle RPG. "+ctx.author.mention+"'s player data has been deleted.")
            else:
                await ctx.send("You are not playing the Idle RPG.", delete_after=15)
        else:
            await ctx.send("The Idle RPG feature is not enabled on this server. Ask an Admin to enable it.", delete_after=15)

    @rpg.command(aliases=["stats", "character"])
    async def info(self, ctx, *, other : discord.Member = None):
        '''Grab your stats'''
        try:
            if other is None:
                other = ctx.author
            if self.checkSession(ctx.guild):
                data = self.db.getPlayer(other.id)
                if data is not None:
                    e = discord.Embed(description="Character Name: "+data[1]+"\nGender: "+data[2]+"\nRace: "+data[3], timestamp=ctx.message.created_at,color=discord.Color.blurple())
                    w1name, w1desc, w1rarity, w1type, w1damage, w1element, w1stat, w1scale, w1levelreq = map(str, data[4].split("^"))
                    w2name, w2desc, w2rarity, w2type, w2damage, w2element, w2stat, w2scale, w2levelreq = map(str, data[5].split("^"))
                    helmname, helmdesc, helmrarity, helmtype, helmdef, helmelement, helmlevelreq = map(str, data[10].split("•"))
                    bodyname, bodydesc, bodyrarity, bodytype, bodydef, bodyelement, bodylevelreq = map(str, data[11].split("•"))
                    handname, handdesc, handrarity, handtype, handdef, handelement, handlevelreq = map(str, data[12].split("•"))
                    feetname, feetdesc, feetrarity, feettype, feetdef, feetelement, feetlevelreq = map(str, data[13].split("•"))
                    trinname, trindesc, trinrarity, trintype, trinval, trinelement, trinextra, trinlevelreq, trinstat, trinscale = map(str, data[14].split("◘"))
                    w1 = RPGWeapon(w1name, w1desc, w1rarity, w1type, w1damage, w1element, w1stat, w1scale, w1levelreq)
                    w2 = RPGWeapon(w2name, w2desc, w2rarity, w2type, w2damage, w2element, w2stat, w2scale, w2levelreq)
                    helm = RPGArmor(helmname, helmdesc, helmrarity, helmtype, helmdef, helmelement, helmlevelreq)
                    body = RPGArmor(bodyname, bodydesc, bodyrarity, bodytype, bodydef, bodyelement, bodylevelreq)
                    hand = RPGArmor(handname, handdesc, handrarity, handtype, handdef, handelement, handlevelreq)
                    feet = RPGArmor(feetname, feetdesc, feetrarity, feettype, feetdef, feetelement, feetlevelreq)
                    trin = RPGTrinket(trinname, trindesc, trinrarity, trintype, trinval, trinelement, trinextra, trinlevelreq, trinstat, trinscale)
                    requiredXP = Decimal(100 ** (1 + Decimal(data[9]) * Decimal(".05")))
                    #xpstr = str(Decimal(data[6]).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN))
                    #rqstr = str(Decimal(requiredXP).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN))
                    if Decimal(data[6]) > 1000000:
                        xpstr = Decimal(data[6])
                        xpstr = format(xpstr, '.6e')
                    else:
                        xpstr = str(Decimal(data[6]).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN))
                    if Decimal(requiredXP) > 1000000:
                        rqstr = Decimal(requiredXP)
                        rqstr = format(rqstr, '.6e')
                    else:
                        rqstr = str(Decimal(requiredXP).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN))
                    e.set_author(name=other.name+"'s Character", icon_url=other.avatar_url)
                    e.set_footer(text="Idle RPG Stats",icon_url=self.bot.user.avatar_url)
                    e.add_field(name="HP", value=str(data[7]) + "/" + str(data[8]))
                    e.add_field(name="XP", value=xpstr + "/" + rqstr)
                    e.add_field(name="Level", value=str(Decimal(data[9]).quantize(Decimal("1."), rounding=decimal.ROUND_DOWN)))
                    e.add_field(name="Money", value="$"+str(data[22]))
                    e.add_field(name="Level Up Points", value=str(data[23]))
                    e.add_field(name="Left Hand Weapon", value=str(w1))
                    e.add_field(name="Right Hand Weapon", value=str(w2))
                    e.add_field(name="Helmet", value=str(helm))
                    e.add_field(name="Body", value=str(body))
                    e.add_field(name="Hands", value=str(hand))
                    e.add_field(name="Feet", value=str(feet))
                    e.add_field(name="Trinket", value=str(trin))
                    e.add_field(name="Strength", value=str(data[15]))
                    e.add_field(name="Dexterity", value=str(data[16]))
                    e.add_field(name="Intelligence", value=str(data[17]))
                    e.add_field(name="Agility", value=str(data[18]))
                    e.add_field(name="Constitution", value=str(data[19]))
                    e.add_field(name="Luck", value=str(data[20]))
                    #await ctx.send("Stats for "+ctx.author.mention+"\nName: {}\nHP: {}\nXP: {}\nMoney: ${}\nWeapon 1: {}\t Weapon 2: {}\nHelmet: {}\t Body: {}\nHands: {}\t Feet: {}\nTrinket: {}\nStrength: {}\t Dexterity: {}\nIntelligence: {}\t Agility: {}\nConstitution: {}\t Luck: {}".format(data[0], data[1], data[2], data[-1], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12], data[13], data[14], data[15]))
                    await ctx.send(embed=e)
                else:
                    await ctx.send("You are not playing the Idle RPG.", delete_after=15)
            else:
                await ctx.send("The Idle RPG is not enabled on this server. Ask an Admin to enable it.", delete_after=15)
        except:
            traceback.print_exc()

    @commands.check(Perms.is_owner)
    @rpg.command(hidden=True)
    async def rawSQL(self, ctx, *, words):
        ''' literally run raw sql '''
        statement = words
        self.db.rawExecute(statement)

    @commands.check(Perms.is_owner)
    @rpg.command(hidden=True)
    async def rawSQLSelect(self, ctx, *, words):
        ''' literally run raw sql '''
        statement = words
        self.db.rawGet(statement)

    @commands.check(Perms.is_owner)
    @rpg.command(hidden=True)
    async def rawSQLSelectOne(self, ctx, *, words):
        ''' literally run raw sql '''
        statement = words
        self.db.rawGetOne(statement)

    @commands.check(Perms.is_owner)
    @rpg.command(hidden=True)
    async def menutest(self, ctx):
        ''' test '''
        try:
            m = RPGMenu(ctx.channel, self.BarryBot, ctx)
            m.addScreen(menuLinks=["second"], text="test description", embedFields=[("test field", "test value"),("test other field", "test value 2")], menuName='main')
            m.addScreen(menuLinks=["main"], text="test second screen", embedFields=[("second screen", "value")], menuName="second")
            await m.initiateMenu()
        except:
            traceback.print_exc()

class RPGItem:
    def __init__(self, name="Item", description="A very special item.", rarity="1", itemType="body", value="0"):
        self.name = name                # the name of the item
        self.description = description  # flavor description if desired
        self.rarity = rarity            # rarity is a number from 1 to 5 (com, uncom, rare, epic, legend)
        self.type = itemType            # valid types: anything
        self.value = value              # Representative of some number

    def __conform__(self, protocol):
        ''' used for turning the item into a string form
        to bring it back, do this:

            name, description, rarity, type, value = map(str, s.split(b"@"))
            return RPGItem(name, description, rarity, type, value)
            s is a bytes object
        '''
        if protocol is sqlite3.PrepareProtocol:
            return "%s@%s@%s@%s@%s" % (self.name, self.description, self.rarity, self.type, self.value)

    def __repr__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + " " + self.description + " Rarity: "+self.getRarityString()+" Type: "+self.type+" Value: "+self.value

    def __str__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + " " + self.description + " Rarity: " + self.getRarityString() + " Type: " + self.type + " Value: " + self.value

    def getEmptySlot(self, itemType):
        ''' produces an empty item'''
        return RPGItem(name="Empty", description="", rarity="1", itemType=itemType, value="0")

    def getRarityString(self, rarity=None):
        ''' produce a string version of the "integer" rarity'''
        if rarity is None:
            rarity = self.rarity
        if rarity == "1":
            return "Common"
        elif rarity == "2":
            return "Uncommon"
        elif rarity == "3":
            return "Rare"
        elif rarity == "4":
            return "Epic"
        else:
            return "Legendary"

class RPGWeapon:
    def __init__(self, name="Fist", description="Probably five fingers", rarity="1", itemType="smash", baseDamage="1", element="None", stat="str", scale="1", levelreq="1"):
        self.name = name                    # name
        self.description = description      # flavor description
        self.rarity = rarity                # rarity 1 to 5 (com, uncom, rare, epic, legend) (multiplier to damage)
        self.type = itemType                # one of the following: stab, smash, magic, shoot
        self.baseDamage = baseDamage        # the base damage of the weapon, 0 to infinite
        self.element = element              # element of damage
        self.stat = stat                    # the stat which assists the damage calc (str, dex, int, agi, con, luc)
        self.scale = scale                  # scale amount along with the stat
        self.levelreq = levelreq            # level requirement to use

    def __conform__(self, protocol):
        ''' read the stuff above'''
        if protocol is sqlite3.PrepareProtocol:
            return "%s^%s^%s^%s^%s^%s^%s^%s^%s" % (self.name, self.description, self.rarity, self.type, self.baseDamage, self.element, self.stat, self.scale, self.levelreq)

    def __repr__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + "\nRarity: "+self.getRarityString()+"\nType: "+self.type+"\nBase Damage: "+self.baseDamage+"\nElement: "+self.element
    def __str__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + "\nRarity: " + self.getRarityString() + "\nType: " + self.type + "\nBase Damage: " + self.baseDamage + "\nElement: " + self.element

    def getEmptySlot(self):
        ''' produces an empty item'''
        return RPGWeapon()

    def getRarityString(self, rarity=None):
        ''' produce a string version of the "integer" rarity'''
        if rarity is None:
            rarity = self.rarity
        if rarity == "1":
            return "Common"
        elif rarity == "2":
            return "Uncommon"
        elif rarity == "3":
            return "Rare"
        elif rarity == "4":
            return "Epic"
        else:
            return "Legendary"

    def getElementalWorth(self, against):
        ''' get a number output for damage calculation for the weapon's element vs something else'''
        return 0

    def getHitWording(self):
        ''' return a random phrase for hitting something based on the type'''
        if self.type == "stab":
            return random.choice(["stabbed"])
        elif self.type == "smash":
            return random.choice(["smashed"])
        elif self.type == "magic":
            return random.choice(["told a spell at"])
        elif self.type == "shoot":
            return random.choice(["shot"])

class RPGArmor:
    def __init__(self, name="None", description="", rarity="1", itemType="head", baseDefense="0", element="None", levelreq="1"):
        self.name = name                    # name
        self.description = description      # flavor description
        self.rarity = rarity                # rarity 1 to 5 (com, uncom, rare, epic, legend)
        self.type = itemType                # one of the following: head, body, hands, feet
        self.baseDefense = baseDefense      # base damage 0 to infinite
        self.element = element              # element of defense/resistance
        self.levelreq = levelreq            # level requirement to use

    def __conform__(self, protocol):
        ''' read the stuff above
        This uses alt+7
        '''
        if protocol is sqlite3.PrepareProtocol:
            return "%s•%s•%s•%s•%s•%s•%s" % (self.name, self.description, self.rarity, self.type, self.baseDefense, self.element, self.levelreq)

    def __repr__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + "\nRarity: "+self.getRarityString()+"\nType: "+self.type+"\nBase Defense: "+self.baseDefense+"\nElement: "+self.element
    def __str__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + "\nRarity: "+self.getRarityString()+"\nType: "+self.type+"\nBase Defense: "+self.baseDefense+"\nElement: "+self.element

    def getEmptySlot(self, slot):
        ''' produces an empty item'''
        return RPGArmor(itemType=slot)

    def getRarityString(self, rarity=None):
        ''' produce a string version of the "integer" rarity'''
        if rarity is None:
            rarity = self.rarity
        if rarity == "1":
            return "Common"
        elif rarity == "2":
            return "Uncommon"
        elif rarity == "3":
            return "Rare"
        elif rarity == "4":
            return "Epic"
        else:
            return "Legendary"

class RPGTrinket:
    def __init__(self, name="None", description="", rarity="1", itemType="condition", baseAttribute="0", element="None", extra="None", levelreq="1", stat="str", scale="1"):
        self.name = name                    # name
        self.description = description      # flavor description
        self.rarity = rarity                # rarity 1 to 5 (com, uncom, rare, epic, legend)
        self.type = itemType                # one of the following: reactive, proactive, condition
        self.baseAttribute = baseAttribute  # base attribute 0 to infinite with type
        self.element = element              # element of use
        self.extra = extra                  # reserved
        self.levelreq = levelreq            # level requirement to use
        self.stat = stat                    # stat which assists attribute calculation (str, dex, int, agi, con, luc)
        self.scale = scale                  # scale with the stat

    def __conform__(self, protocol):
        ''' read the stuff above
        This uses alt+8
        '''
        if protocol is sqlite3.PrepareProtocol:
            return "%s◘%s◘%s◘%s◘%s◘%s◘%s◘%s◘%s◘%s" % (self.name, self.description, self.rarity, self.type, self.baseAttribute, self.element, self.extra, self.levelreq, self.stat, self.scale)

    def __repr__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + "\nRarity: "+self.getRarityString()+"\nType: "+self.type+"\nBase Stat: "+self.baseAttribute+"\nElement: "+self.element
    def __str__(self):
        if self.name.lower() == "none" or self.name.lower() == "empty":
            return self.name
        return self.name + "\nRarity: "+self.getRarityString()+"\nType: "+self.type+"\nBase Stat: "+self.baseAttribute+"\nElement: "+self.element

    def getEmptySlot(self):
        return RPGTrinket()

    def getRarityString(self, rarity=None):
        ''' produce a string version of the "integer" rarity'''
        if rarity is None:
            rarity = self.rarity
        if rarity == "1":
            return "Common"
        elif rarity == "2":
            return "Uncommon"
        elif rarity == "3":
            return "Rare"
        elif rarity == "4":
            return "Epic"
        else:
            return "Legendary"


class RPGMap:
    def __init__(self):
        return

class RPGBattle:
    def __init__(self, BarryBot, ctx, friendlyParticipants, enemyParticipants, db, interval=10):
        self.chan = ctx.channel
        self.BarryBot = BarryBot
        self.bot = BarryBot.bot
        self.loop = BarryBot.loop
        self.ctx = ctx
        self.db = db
        self.interval = interval        # defaults to 10 seconds
        self.friendlyParticipants = friendlyParticipants    # a list of character objects
        self.enemyParticipants = enemyParticipants          # a list of character objects
        self.menuController = None
        self.message = None
        self.runningLog = ["", "", "", "", "Pick an action! Fight, Inventory, or Run!"]        # 5 lines of text to display, the last index is the bottom row

    async def initBattle(self):
        ''' start the battle (the menus and stuff)'''
        def getHighestAliveStats(team):
            maxstats = [0,0,0,0,0,0]
            for char in team:
                if char.hp > 0:
                    if char.strength > maxstats[0]:
                        maxstats[0] = char.strength
                    if char.dexterity > maxstats[1]:
                        maxstats[1] = char.dexterity
                    if char.intelligence > maxstats[2]:
                        maxstats[2] = char.intelligence
                    if char.agility > maxstats[3]:
                        maxstats[3] = char.agility
                    if char.constitution > maxstats[4]:
                        maxstats[4] = char.constitution
                    if char.luck > maxstats[5]:
                        maxstats[5] = char.luck
            return maxstats
        def runFunc():
            if getHighestAliveStats(self.friendlyParticipants)[3] >= getHighestAliveStats(self.enemyParticipants)[3]:
                if random.randint(0,10) > 3:
                    self.loop.create_task(m.endMenu())
                    self.loop.create_task(self.chan.send("Your team has run away from the battle successfully!"))
                    return
                else:
                    self.loop.create_task(self.pushLog("Your team failed to run!"))
                    self.loop.create_task(self.tickTurn())
            else:
                self.loop.create_task(self.pushLog("Your team was too slow to run!"))
                self.loop.create_task(self.tickTurn())
            regenerateEmbedFields()
        def defendFunc():
            outcome = self.procOutcome(attackerChose="defend")
            if outcome is None:
                output = self.calculateDamage(self.friendlyParticipants[0], self.enemyParticipants[0], tie=True)
            elif outcome:
                output = self.calculateDamage(self.enemyParticipants[0], self.friendlyParticipants[0])
            else:
                output = self.calculateDamage(self.friendlyParticipants[0], self.enemyParticipants[0])
            regenerateEmbedFields()
            self.loop.create_task(self.pushLog(output))
            self.loop.create_task(self.tickTurn())
        def attackFunc():
            outcome = self.procOutcome(attackerChose="attack")
            if outcome is None:
                output = self.calculateDamage(self.friendlyParticipants[0], self.enemyParticipants[0], tie=True)
            elif outcome:
                output = self.calculateDamage(self.enemyParticipants[0], self.friendlyParticipants[0])
            else:
                output = self.calculateDamage(self.friendlyParticipants[0], self.enemyParticipants[0])
            regenerateEmbedFields()
            self.loop.create_task(self.pushLog(output))
            self.loop.create_task(self.tickTurn())
        def trickFunc():
            outcome = self.procOutcome(attackerChose="trick")
            if outcome is None:
                output = self.calculateDamage(self.friendlyParticipants[0], self.enemyParticipants[0], tie=True)
            elif outcome:
                output = self.calculateDamage(self.enemyParticipants[0], self.friendlyParticipants[0])
            else:
                output = self.calculateDamage(self.friendlyParticipants[0], self.enemyParticipants[0])
            regenerateEmbedFields()
            self.loop.create_task(self.pushLog(output))
            self.loop.create_task(self.tickTurn())
        def doNothing():
            pass
        m = RPGMenu(self.chan, self.BarryBot, self.ctx)

        def regenerateEmbedFields():
            tuples = []
            for friendly in self.friendlyParticipants:
                tuples.append(("Friendly: " + friendly.name, friendly.getVeryShortDescription()))
            for enemy in self.enemyParticipants:
                tuples.append(("Enemy: " + enemy.name, enemy.getVeryShortDescription()))
            m.currentscreen.embedFields = tuples

        tuples = []
        for friendly in self.friendlyParticipants:
            tuples.append(("Friendly: " + friendly.name, friendly.getVeryShortDescription()))
        for enemy in self.enemyParticipants:
            tuples.append(("Enemy: " + enemy.name, enemy.getVeryShortDescription()))
        invFields = []
        invFields.append(("Nothing","Here"))
        m.addScreen(menuLinks=["Attack", "Inventory"], text="Battle Log:\n"+self.getLogText(), embedFields=tuples, menuName="Battle", choices=[runFunc], decisionEmojis=["\N{CROSSED SWORDS}", "\N{OPEN FILE FOLDER}"], choiceEmojis=["\N{RUNNER}"], undoChoiceEmojis=False)
        m.addScreen(menuLinks=["Battle"], text="Battle Log:\n"+self.getLogText(), embedFields=tuples, menuName="Attack", choices=[defendFunc, attackFunc, trickFunc], decisionEmojis=["\N{LEFTWARDS BLACK ARROW}"], choiceEmojis=["\N{SHIELD}", "\N{BOW AND ARROW}", "\N{MONKEY}"], undoChoiceEmojis=False)
        m.addScreen(menuLinks=["Battle"], text="This is your inventory", embedFields=invFields, menuName="Inventory", choices=[doNothing, doNothing, doNothing], decisionEmojis=["\N{LEFTWARDS BLACK ARROW}"], undoChoiceEmojis=False)
        await m.initiateMenu()
        self.message = m.message
        self.menuController = m

    async def tickTurn(self):
        ''' push the turn forward
        reset the screen back to main menu'''
        await asyncio.sleep(0.5)
        self.menuController.screens["Battle"].description = "Battle Log:\n"+self.getLogText()
        self.menuController.screens["Attack"].description = "Battle Log:\n"+self.getLogText()
        tuples = []
        for friendly in self.friendlyParticipants:
            tuples.append(("Friendly: " + friendly.name, friendly.getVeryShortDescription()))
        for enemy in self.enemyParticipants:
            tuples.append(("Enemy: " + enemy.name, enemy.getVeryShortDescription()))
        self.menuController.screens["Battle"].fields = tuples
        self.menuController.screens["Attack"].fields = tuples
        await self.menuController.changeScreens("Battle", listen=False)
        if self.checkWon():
            await self.menuController.endMenu()
            await self.ctx.send("Your team has won! Here is the remaining battle log:\n`"+self.getLogText()+"`")
        elif self.checkLost():
            await self.menuController.endMenu()
            await self.ctx.send("Your team has lost. Here is the remaining battle log:\n`"+self.getLogText()+"`\nYou will need to regenerate health before fighting again.")

    def checkWon(self):
        ''' check to see if the game was won by the friendlyParticipants'''
        for enemy in self.enemyParticipants:
            if enemy.hp > 0:
                return False
        return True

    def checkLost(self):
        ''' check to see if the game was lost by the friendlyParticipants'''
        for friendly in self.enemyParticipants:
            if friendly.hp > 0:
                return False
        return True

    async def pushLog(self, text):
        ''' push a line to the log to be rotated forward
        the log appears as ["", "", "", "", ""]
        the last index appears lowest and is the newest info'''
        self.runningLog[0] = self.runningLog[1]
        self.runningLog[1] = self.runningLog[2]
        self.runningLog[2] = self.runningLog[3]
        self.runningLog[3] = self.runningLog[4]
        self.runningLog[4] = text

    def getLogText(self):
        ''' return the log text string'''
        output = ""
        for i in range(len(self.runningLog)):
            output = output + str(len(self.runningLog) - i) + ": " + self.runningLog[i] + "\n"
        return output

    def updateCharacterDB(self):
        ''' update the characters in the database
        basically for hp purposes'''
        for char in self.friendlyParticipants + self.enemyParticipants:
            try:
                self.db.updateStat(table="players", comparisonId=char.id, column="hp", new=int(char.hp))
            except:
                pass

    def procOutcome(self, attackerChose=None, defenderChose=None):
        ''' run a game of rock paper scissors to find out who wins the fight
        returns True or False depending on the outcome
        returns None if it is a tie'''
        choices = ["attack", "defend", "trick"]
        if attackerChose is None:
            attackerChose = random.choice(choices)
        if defenderChose is None:
            defenderChose = random.choice(choices)

        if attackerChose == "attack":
            if defenderChose == "defend":
                return False
            elif defenderChose == "trick":
                return True
            else:
                return None
        elif attackerChose == "defend":
            if defenderChose == "attack":
                return True
            elif defenderChose == "trick":
                return False
            else:
                return None
        else:
            if defenderChose == "attack":
                return False
            elif defenderChose == "defend":
                return True
            else:
                return None

    def calculateDamage(self, winner, loser, tie=False):
        ''' calculate damage based on many factors
        the given winner and loser are characters
        make those damage changes to hp for the characters
        return a string of what happened'''
        if tie:
            return "It was a tie!"
        damagesum = float(winner.weaponL.baseDamage) + float(winner.weaponL.scale) * winner.getStat(winner.weaponL.stat) + winner.weaponL.getElementalWorth(loser.helmet) + \
                    float(winner.weaponR.baseDamage) + float(winner.weaponR.scale) * winner.getStat(winner.weaponR.stat) + winner.weaponR.getElementalWorth(loser.helmet)
        defensesum = float(loser.helmet.baseDefense) + float(loser.body.baseDefense) + float(loser.hands.baseDefense) + float(loser.feet.baseDefense)

        overallsum = damagesum - defensesum

        winnerfriendly = False
        if loser in self.friendlyParticipants:
            pass
        else:
            winnerfriendly = True



        loser.hp = loser.hp - overallsum

        if winnerfriendly:
            try:
                self.enemyParticipants[self.enemyParticipants.index(winner)] = winner
            except:
                pass
            try:
                self.friendlyParticipants[self.friendlyParticipants.index(loser)] = loser
            except:
                pass
        else:
            try:
                self.enemyParticipants[self.enemyParticipants.index(loser)] = loser
            except:
                pass
            try:
                self.friendlyParticipants[self.friendlyParticipants.index(winner)] = winner
            except:
                pass
        self.updateCharacterDB()

        return winner.name + " " + winner.weaponL.getHitWording() + " " + loser.name + " for " + str(overallsum) + " damage!"




class RPGCharacter:
    def __init__(self, name="New Character", gender="agender", race="racist", weaponL=RPGWeapon(), weaponR=RPGWeapon(),
                 helmet=RPGArmor(itemType="head"), body=RPGArmor(itemType="body"), hands=RPGArmor(itemType="hands"),
                 feet=RPGArmor(itemType="feet"), trinket=RPGTrinket(),
                 stren=1, dex=1, inte=1, agi=1, cons=1, luck=1, id=69, hp=100, maxhp=100, level=1, money=100):
        self.name = name
        self.gender = gender
        self.race = race
        self.id = id    # 69 is a bogus ID. This is meant to be the player (discord) ID.

        self.hp = hp
        self.maxhp = maxhp
        self.level = level
        self.money = money

        self.weaponL = weaponL
        self.weaponR = weaponR

        self.helmet = helmet
        self.body = body
        self.hands = hands
        self.feet = feet
        self.trinket = trinket

        self.strength = int(stren)
        self.dexterity = int(dex)
        self.intelligence = int(inte)
        self.agility = int(agi)
        self.constitution = int(cons)
        self.luck = int(luck)

    def generateRandomCharacter(self):
        ''' generate a very random character'''
        return RPGCharacter()

    def getVeryShortDescription(self):
        ''' generates a short string for critical info'''
        return str(int(self.hp)) + "/" + str(int(self.maxhp))

    def getStat(self, statName):
        ''' string to number'''
        if statName.lower() == "strength":
            return self.strength
        elif statName.lower() == "dexterity":
            return self.dexterity
        elif statName.lower() == "intelligence":
            return self.intelligence
        elif statName.lower() == "agility":
            return self.agility
        elif statName.lower() == "constitution":
            return self.constitution
        else:
            return self.luck


class RPGMenu:
    def __init__(self, channel, BarryBot, ctx):
        self.chan = channel
        self.BarryBot = BarryBot
        self.bot = BarryBot.bot
        self.loop = BarryBot.loop
        self.ctx = ctx
        self.screens = {}       # keys are names of screens, values are MenuScreens
        self.currentscreen = None
        self.listeningemotes = set()
        self.message = None # this needs to be set either at some point or by initiateMenu()
        self.closeFunc = None
        self.reactionsToRemove = []


    def __repr__(self):
        return "rpg menu"

    def setCloseFunc(self, closer=None):
        ''' run this function when the menu closes'''
        self.closeFunc = closer

    def addScreen(self, menuLinks=None, text=None, embedFields=None, menuName="main", choices=None, closeable=False, screenFunc=None, decisionEmojis=None, choiceEmojis=None, undoChoiceEmojis=True):
        ''' create a menu screen which is made up of an embed with certain things within
        menuLinks must be provided as a list of links to other menus up to 6 long
            it is simply a list of names of other menus
        text goes in the Description section of the embed
        embedFields is a list of tuples (len 2 lists) for titles and descriptions of fields in the embed
        menuName is the name of the menu screen being created'''
        m = MenuScreen(self, links=menuLinks, text=text, embedFields=embedFields, name=menuName, choices=choices, closeable=closeable, screenFunc=screenFunc, decisionEmojis=decisionEmojis, choiceEmojis=choiceEmojis, undoChoiceEmojis=undoChoiceEmojis)
        if len(self.screens) == 0:
            self.currentscreen = m
        self.screens[menuName] = m

    async def initiateMenu(self):
        ''' a catch-all function so other things that create the menu dont have to run 5 different functions'''
        if self.message is None:
            e = self.currentscreen.generateEmbed()
            self.message = await self.ctx.send(embed=e)
        await self.addReactions()
        self.loop.create_task(self.waitForReactions())

    async def addReactions(self):
        ''' place the reactions for the current menu on the message'''
        await self.message.clear_reactions()
        #words = ["\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}"]
        #letters = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫"]
        letters = self.currentscreen.choiceEmojis
        words = self.currentscreen.decisionEmojis
        if self.currentscreen.closeable:
            self.listeningemotes.add("\N{CROSS MARK}")
            await self.message.add_reaction("\N{CROSS MARK}")
        for i in range(len(self.currentscreen.links)):
            self.listeningemotes.add(words[i])
        for i in range(len(self.currentscreen.choices)):
            self.listeningemotes.add(letters[i])
        for i in range(len(self.currentscreen.links)):
            await self.message.add_reaction(words[i])
        for i in range(len(self.currentscreen.choices)):
            await self.message.add_reaction(letters[i])

    async def undoReactions(self):
        ''' remove reactions not from the bot'''
        #await asyncio.sleep(.25)
        for t in self.reactionsToRemove:
            await self.message.remove_reaction(t[0], t[1])
        self.reactionsToRemove = []

    async def waitForReactions(self):
        #linkers = ["\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}"]
        #choices = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫"]
        choices = self.currentscreen.choiceEmojis
        linkers = self.currentscreen.decisionEmojis

        def check(moji, user):
            return moji.message.id == self.message.id and user.id == self.ctx.author.id and moji.emoji in self.listeningemotes
        try:
            reaction, u = await self.bot.wait_for("reaction_add", check=check, timeout=180)
        except:
            reaction = None
            await self.endMenu()
            # todo more things than this
            return
        self.reactionsToRemove.append((reaction.emoji, u))
        if reaction.emoji == "\N{CROSS MARK}":
            return await self.endMenu()
        if reaction.emoji in linkers:
            print("fsd")
            print(u)
            await self.changeScreens(self.currentscreen.links[linkers.index(reaction.emoji)])
        else:
            await self.doChoice(self.currentscreen.choices[choices.index(reaction.emoji)])

    async def changeScreens(self, screen, listen=True):
        ''' restart the menu with a new screen and set of choices based on the selected screen
        ( edit the message with the new parameters, reset the reactions, etc )'''
        print(screen)
        self.currentscreen = self.screens[screen]
        self.listeningemotes = set()
        self.reactionsToRemove = []
        await self.refreshScreen()
        await self.addReactions()
        await self.waitForReactions()

    async def doChoice(self, choice):
        ''' run a function based on the list of self.currentscreen.choices
        the choice function MUST return some string because it will be displayed in the message
        the format should be something along the lines of ["action being done", "result of the action"]'''
        output = choice()
        if self.currentscreen.undoChoiceEmojis: # meant for when the choice itself actually triggers a menu screen change using changeScreens
            await self.undoReactions()
            await self.waitForReactions()
        #await self.ctx.send("You chose "+output[0]+" "+output[1])

    async def endMenu(self):
        ''' kill the menu'''
        if self.closeFunc is not None:
            await self.closeFunc()
        await self.message.delete()
        self.screens = {}

    async def modifyScreen(self, text="", embedTitle=None, embedChange=None):
        ''' modify an element of the screen'''
        if text != "":
            self.currenscreen.description = text
        if embedTitle is not None:
            for i in range(len(self.currentscreen.fields)):
                if self.currentscreen.fields[i][0] == embedTitle:
                    self.currentscreen.fields[i] = (embedTitle, embedChange)
                    break
        await self.refreshScreen()

    async def refreshScreen(self):
        ''' refresh the screen by updating the message with the latest currentscreen embed'''
        await self.message.edit(embed=self.currentscreen.generateEmbed())


class MenuScreen:
    def __init__(self, parent, links=None, text="", embedFields=None, name="main", choices=None, closeable=False, screenFunc=None, decisionEmojis=None, choiceEmojis=None, undoChoiceEmojis=True):
        self.parent = parent        # the parent Menu that holds this all
        if links is None:
            self.links = []
        else:
            self.links = links          # list of other menus that this links to
        self.description = text     # the description of the embed
        if embedFields is None:
            self.fields = []
        else:
            self.fields = embedFields   # list of tuples (len 2 lists) for embed fields (titles and values)
        self.name = name            # name of the menu and also the Title of the embed
        if choices is None:
            self.choices = []
        else:
            self.choices = choices      # list of choices which are actually function calls
        self.closeable = closeable      # if True, a reaction related to closing the menu appears
        self.screenFunc = screenFunc    # called upon whenever desired
        if decisionEmojis is None:
            self.decisionEmojis = ["\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}"]
        else:
            self.decisionEmojis = decisionEmojis
        if choiceEmojis is None:
            self.choiceEmojis = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫"]
        else:
            self.choiceEmojis = choiceEmojis
        self.undoChoiceEmojis = undoChoiceEmojis


    def generateEmbed(self):
        e = discord.Embed(description=self.description, timestamp=self.parent.ctx.message.created_at, color=discord.Color.blurple())
        e.set_author(name=self.name, icon_url=self.parent.ctx.author.avatar_url)
        e.set_footer(text="Idle RPG Menu - Use the Reactions", icon_url=self.parent.bot.user.avatar_url)
        if self.fields is not None:
            for t in self.fields:
                e.add_field(name=t[0], value=t[1])
        return e


class RPGDB:
    def __init__(self):
        self.connection = None
        self.cursor = None

        self.verifyTables() # we need to make sure the tables exist to even play this


    def initCursor(self):
        ''' grab the cursor real quick'''
        self.connection = sqlite3.connect("RPG.db")
        self.cursor = self.connection.cursor()

    def closeCursor(self, save=True):
        ''' close the connection and maybe save the changes'''
        if self.connection is None:
            return
        if save:
            self.connection.commit()
            self.connection.close()
        else:
            self.connection.close()
        self.connection = None
        self.cursor = None

    def rawExecute(self, statement):
        ''' directly execute a command (unsafe to expose to users)'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute(statement)
            print("It appears there was no error.")
        except:
            traceback.print_exc()
        self.closeCursor()

    def rawGet(self, statement):
        ''' directory execute a select command (unsafe to expose to users)'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute(statement)
            print(self.cursor.fetchall())
        except:
            traceback.print_exc()
        self.closeCursor()

    def rawGetOne(self, statement):
        ''' directly execute a select command'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute(statement)
            print(self.cursor.fetchone())
        except:
            traceback.print_exc()
        self.closeCursor()

    def updateStat(self, table="players", comparisonId="1", column="name", new="newname"):
        ''' update a specific item in a table'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute("update {} set {} = ? where id = ?".format(table, column), (new, int(comparisonId),))
        except:
            traceback.print_exc()
        self.closeCursor()

    def incrementColumn(self, table="players", column="experience", amount="5"):
        ''' increment a whole column of numbers'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute("update {} set {} = {} + ".format(table, column, column)+amount)
        except:
            traceback.print_exc()
        self.closeCursor()

    def getWholeTable(self, table="players"):
        if self.connection is None:
            self.initCursor()
        output = None
        try:
            self.cursor.execute("select * from {}".format(table))
            output = self.cursor.fetchall()
        except:
            traceback.print_exc()
        self.closeCursor()
        return output

    def addPlayer(self, memberId, name, gender, race):
        ''' make a new player and put them in the db'''
        if self.connection is None:
            self.initCursor()
        try:
            info = (memberId, name, gender, race, RPGWeapon(), RPGWeapon(), RPGArmor(itemType="helmet"), RPGArmor(itemType="body"), RPGArmor(itemType="hands"), RPGArmor(itemType="feet"), RPGTrinket(),)
            self.cursor.execute("insert into players values (?,?,?,?,?,?,1,100,100,1,?,?,?,?,?,1,1,1,1,1,1,0,100,0)", info)
        except:
            traceback.print_exc()
        self.closeCursor()

    def getPlayer(self, memberId):
        ''' acquire a player via their id'''
        if self.connection is None:
            self.initCursor()
        output = None
        try:
            self.cursor.execute("select * from players where id=?", (int(memberId),))
            output = self.cursor.fetchone()
        except:
            traceback.print_exc()
        self.closeCursor()
        #print(output)
        return output

    def delPlayer(self, memberId):
        ''' delete a player'''
        self.delRow(table="players", comparedId=str(memberId))

    def delRow(self, table="players", comparedId="1"):
        ''' delete a row based on the id given'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute("delete from {} where id = ?".format(table), (int(comparedId),))
        except:
            traceback.print_exc()
        self.closeCursor()

    def getRandomItem(self, table="trinket"):
        ''' get a random item from a given table
        Item tables:
            weapon, helmet, body, hands, feet, trinket
        '''
        if self.connection is None:
            self.initCursor()
        the_list = None
        try:
            the_list = []
            for item in self.cursor.execute("select * from {}".format(table)):
                the_list.append(item)
        except:
            traceback.print_exc()
        self.closeCursor()
        return random.choice(the_list)

    def getItem(self, table="weapon", itemId=1):
        ''' get an item by its ID in an item table
        Item tables:
            weapon, helmet, body, hands, feet, trinket
        '''
        if table in {"weapon", "helmet", "body", "hands", "feet", "trinket"}:
            output = None
            if self.connection is None:
                self.initCursor()
            try:
                self.cursor.execute("select * from {} where id=?".format(table), (int(itemId),))
                output = self.cursor.fetchone()
            except:
                traceback.print_exc()
            self.closeCursor()
            return output

    def getPlayerStat(self, playerID, column="name"):
        ''' get a stat from the players table'''
        if self.connection is None:
            self.initCursor()
        output = None
        if column in {"name", "gender", "race", "weaponL", "weaponR", "experience", "hp", "maxhp", "level", "helmet", "body", "hands", "feet", "trinket", "strength", "dexterity", "intelligence", "agility", "constitution", "luck", "location", "money", "levelpoints"}:
            try:
                self.cursor.execute("select ? from players where id=?", (column, int(playerID),))
                output = self.cursor.fetchone()
                if column in {"weapon", "helmet", "body", "hands", "feet", "trinket"}:
                    if output == 0:
                        return ("Empty@@0@"+column+"@0")
            except:
                traceback.print_exc()
        self.closeCursor()
        return output

    def createTables(self):
        ''' create the initial tables for the game'''
        if self.connection is None:
            self.initCursor()
        try:
            try:
                self.cursor.execute("create table weapon (id, name, description, base damage, rarity)")
                print("Fixed weapon table")
            except:
                print("Weapon table already exists?")
            try:
                self.cursor.execute("create table players (id, name, gender, race, weaponL, weaponR, experience, hp, maxhp, level, helmet, body, hands, feet, trinket, strength, dexterity, intelligence, agility, constitution, luck, location, money, levelpoints)")
                info = (2,"dmmy2","g","g",'g','g','g','g','g','g','g',)
                self.cursor.execute("insert into players values (?,?,?,?,?,?,1,100,100,1,?,?,?,?,?,1,1,1,1,1,1,0,100,0)",
                                    info)
                info = (1,"dmmy","g","g",'g','g','g','g','g','g','g',)
                self.cursor.execute("insert into players values (?,?,?,?,?,?,1,100,100,1,?,?,?,?,?,1,1,1,1,1,1,0,100,0)",
                                    info)
                print("Fixed players table")
            except:
                print("Players table already exists?")
                traceback.print_exc()
            try:
                self.cursor.execute("create table helmet (id, name, description, protection, rarity)")
                print("Fixed helmet table")
            except:
                print("Helmet table already exists?")
            try:
                self.cursor.execute("create table body (id, name, description, protection, rarity)")
                print("Fixed body table")
            except:
                print("Body table already exists?")
            try:
                self.cursor.execute("create table hands (id, name, description, protection, rarity)")
                print("Fixed hands table")
            except:
                print("Hands table already exists?")
            try:
                self.cursor.execute("create table feet (id, name, description, protection, rarity)")
                print("Fixed feet table")
            except:
                print("Feet table already exists?")
            try:
                self.cursor.execute("create table trinket (id, name, description, protection, rarity)")
                print("Fixed trinket table")
            except:
                print("Trinket table already exists?")
        except:
            traceback.print_exc()
        self.closeCursor()

    def verifyTables(self):
        ''' verify that the tables all exist
        basically just quickly grab every table and the ones that dont work we remake'''
        if self.connection is None:
            self.initCursor()
        try:
            self.cursor.execute("select * from weapon")
            self.cursor.execute("select * from players")
            self.cursor.execute("select * from helmet")
            self.cursor.execute("select * from body")
            self.cursor.execute("select * from hands")
            self.cursor.execute("select * from feet")
            self.cursor.execute("select * from trinket")
        except:
            traceback.print_exc()
            self.createTables()
        self.closeCursor()
'''
    for weapon and armor:
        in character info, etc, the values inputted refer to weapon ids
        the weapon ids are the id in the weapon/armor tables
'''
'''
idea:
    characters:
        name
        health
        experience
        money
        equipment:
            weapon 1, weapon 2
            helmet
            body
            hands
            feet
            trinket
        stats:
            strength - damage and % chance to hit with melee
            dexterity -damage and % chance to hit with ranged
            intelligence - damage and % to hit with magic
            agility - determines first to move
            constitution - max health bonus
            luck - more loot
    enemies:
        name
        health
        stats:
            same
        equipment:
            weapon 1, 2, the rest

stats are probably out of 100 or 200
    battle:
        each round goes like this
        agility check (2d20 + 1/5 agility)
        higher number goes first
        roll to hit 1d20 + 1/5 strength against other character's 1d20 + 1/5 agility
        if roll is higher:
            deal 2d6 + 1/10 strength/dex/int damage
            
    in battle tickrate:
        2 seconds for "turn" for auto battles
        proc for random battles to have those battles on regular tickrate
    out of battle tickrate:
        5 seconds
        
    each tick:
        xp
        money

'''