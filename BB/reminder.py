import os
import discord
import traceback
import datetime
import time
import asyncio
import uuid

from discord.ext import commands
from BB.permissions import *
from BB.misc import *
from BB.DB import *

class Reminders:
    def __init__(self, bot, config, loop, mainbot):
        self.bot = bot
        self.config = config
        self.loop = loop
        self.BarryBot = mainbot

        self.db = GeneralDB("reminders")
        self.verifyTables()

        self.big_list = []  # this is a list of reminder objects; we iterate over it and see if we should execute them
        self.compileReminders()

        self.beginLooping()

    def beginLooping(self):
        ''' start the big ole loop'''
        self.loop.create_task(self._hiddenloop())

    async def _hiddenloop(self):
        ''' this really does the work in an async way'''
        await asyncio.sleep(5)
        for reminder in self.big_list:
            try:
                await self.checkReminder(reminder)
            except:
                traceback.print_exc()
                print("Error working with reminder "+reminder.generalID+" for user "+str(reminder.fromID))
        self.loop.create_task(self._hiddenloop())

    def makeReminder(self, fromID, toID, contents, createdAt, fireAt):
        ''' set a reminder'''
        newreminder = ReminderObject(fromID, toID, contents, createdAt, fireAt)
        contents = contents.replace(";", "")
        contents = contents.replace("=", "")
        self.db.addRow("reminders", ['"'+newreminder.generalID+'"', '"'+str(newreminder.fromID)+'"', '"'+str(newreminder.toID)+'"', '"'+newreminder.contents+'"', '"'+str(newreminder.createdTimestamp)+'"', '"'+str(newreminder.fireTimestamp)+'"'])
        self.big_list.append(newreminder)

    def destroyReminder(self, reminder):
        ''' remove a reminder from existing anywhere'''
        outlist = []
        for r in self.big_list:
            if r.generalID != reminder.generalID:
                outlist.append(r)
        self.big_list = outlist
        print(reminder.generalID)
        self.db.delRow("reminders", str(reminder.generalID))

    async def checkReminder(self, reminder):
        if reminder.hasPassed():
            user = self.BarryBot.bot.get_user(reminder.toID)
            fromuser = self.BarryBot.bot.get_user(reminder.fromID)
            if user is not None and fromuser is not None:
                datemade = datetime.datetime.fromtimestamp(reminder.createdTimestamp)
                await user.send("You have a new reminder! It was set by "+fromuser.name+" at "+datemade.ctime()+"\nHere are contents:\n\n"+reminder.contents)
                self.destroyReminder(reminder)
            else:
                self.destroyReminder(reminder)

    def verifyTables(self):
        ''' just make sure everything exists'''
        if not self.db.verifyTableExists("reminders"):
            self.db.createTable("reminders", ["fromID integer", "toID integer", "contents text", "created text", "trigger text"])

    def compileReminders(self):
        ''' put all reminders from the db into the list'''
        for row in self.db.getTable("reminders"):
            self.big_list.append(ReminderObject(row[0], row[1],row[2],row[3],row[4],row[5]))

    def refreshReminders(self):
        ''' make sure the list matches the db exactly'''
        self.big_list = []
        self.compileReminders()

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def rraws(self, ctx, *, statement):
        ''' raw sql'''
        try:
            self.db.rawExecuteAndPrint(statement)
        except:
            traceback.print_exc()

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def rraw(self, ctx, *, statement):
        ''' raw sql'''
        try:
            self.db.rawExecute(statement)
        except:
            traceback.print_exc()

    @commands.group(invoke_without_command=True)
    async def remind(self, ctx):
        '''The group command for Reminders. A reminder is a private message that gets sent to
        you or someone else after a certain amount of time.'''
        await ctx.send("See !help remind for information.", delete_after=15)

    @remind.command(usage="remind me <amountoftime> <kindoftime> [content...]")
    async def me(self, ctx, amountOfTime, kindOfTime, *content):
        ''' Remind yourself of something.
        You must specify an amount of time and give a message.
        The format is !remind me x y contents
        The x is a number for the amount of time.
        The y is the kind of time from the following list: m (minutes), h (hours), d (days)'''
        createdAt = time.time()
        try:
            amountOfTime = int(amountOfTime)
        except:
            return await ctx.send("The amount of time you put is not a number or far too big to use. Try again.", delete_after=15)
        try:
            kindOfTime = str(kindOfTime).lower()
            if kindOfTime not in {"m", "minutes", "h", "hours", "d", "days", "minute", "hour", "day", "min", "mins"}:
                return await ctx.send("You did not enter a correct length of time. Check your formatting and try again.", delete_after=15)
        except:
            return await ctx.send("You did not enter a correct length of time. Check your formatting and try again.", delete_after=15)
        content = " ".join(content)
        if len(content) == 0:
            return await ctx.send("You did not enter anything to remind yourself of.", delete_after=15)

        if kindOfTime in {"m", "minutes", "min", "minute", "mins"}:
            seconds = amountOfTime * 60
        elif kindOfTime in {"h", "hours", "hour"}:
            seconds = amountOfTime * 3600
        elif kindOfTime in {"d", "days", "day"}:
            seconds = amountOfTime * 3600 * 24
        else:
            seconds = 1
        fireAt = time.time() + seconds
        try:
            datetime.datetime.fromtimestamp(fireAt).ctime()
        except:
            return await ctx.send("The amount of time you entered is far too large to fit in a reasonable timeframe.", delete_after=15)
        self.makeReminder(ctx.author.id, ctx.author.id, content, createdAt, fireAt)
        return await ctx.send("I created a reminder to send to you at "+datetime.datetime.fromtimestamp(fireAt).ctime()+"\nThe contents say:\n"+content, delete_after=15)

    @remind.command(name="send", usage="remind send @user <amountoftime> <kindoftime> [content...]")
    async def _send(self, ctx, sendTo : discord.Member, amountOfTime, kindOfTime, *content):
        ''' Remind someone of something.
        You must specify an amount of time and give a message.
        The format is !remind send @user x y contents
        The x is a number for the amount of time.
        The y is the kind of time from the following list: m (minutes), h (hours), d (days)'''
        createdAt = time.time()
        try:
            amountOfTime = int(amountOfTime)
        except:
            return await ctx.send("The amount of time you put is not a number or far too big to use. Try again.",
                                  delete_after=15)
        try:
            kindOfTime = str(kindOfTime).lower()
            if kindOfTime not in {"m", "minutes", "h", "hours", "d", "days", "minute", "hour", "day", "min", "mins"}:
                return await ctx.send(
                    "You did not enter a correct length of time. Check your formatting and try again.", delete_after=15)
        except:
            return await ctx.send("You did not enter a correct length of time. Check your formatting and try again.",
                                  delete_after=15)
        content = " ".join(content)
        if len(content) == 0:
            return await ctx.send("You did not enter anything to remind them of.", delete_after=15)
        if kindOfTime in {"m", "minutes", "minute", 'min', "mins"}:
            seconds = amountOfTime * 60
        elif kindOfTime in {"h", "hours", "hour"}:
            seconds = amountOfTime * 3600
        elif kindOfTime in {"d", "days", "day"}:
            seconds = amountOfTime * 3600 * 24
        else:
            seconds = 1
        fireAt = time.time() + seconds
        try:
            datetime.datetime.fromtimestamp(fireAt).ctime()
        except:
            return await ctx.send("The amount of time you entered is far too large to fit in a reasonable timeframe.", delete_after=15)
        self.makeReminder(ctx.author.id, sendTo.id, content, createdAt, fireAt)
        return await ctx.send("I created a reminder to send to "+sendTo.name+" at "+datetime.datetime.fromtimestamp(fireAt).ctime()+"\nThe contents say:\n"+content, delete_after=15)






class ReminderObject:
    def __init__(self, uuid = uuid.uuid4(), fromID="", toID="", contents="", createdTimestamp="", fireTimestamp=""):
        self.generalID = str(uuid)
        self.fromID = int(fromID)
        self.toID = int(toID)
        self.contents = str(contents)
        self.createdTimestamp = float(createdTimestamp)
        self.fireTimestamp = float(fireTimestamp)

    def hasPassed(self):
        ''' returns true if the current time has passed'''
        #timenow = time.localtime()
        #timecompared = time.localtime(fireTimestamp)
        return time.time() > float(self.fireTimestamp)
