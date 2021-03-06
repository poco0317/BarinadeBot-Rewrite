import random
import discord
import asyncio
import traceback
from discord.ext import commands

import uuid

class EmbedFooter: #for picking a funny embed footer message
    def __init__(self):
        self.message = self.setRandom()
    def __repr__(self):
        return self.message
    def __str__(self):
        return self.message
    def setRandom(self):
        lest = {"Produced with precision", "You ever just put butter on saltine crackers?", "Look at me now", "Filled with love", "Made with love", "Produced with no care", "Produced by the producer", "Produced carefully", "Created by hand", "Created by the hand of God", "Baked to perfection", "Created carefully", "Carelessly made", "Organically produced", "Molded by Picasso himself", "I'm not an artist", "Don't judge", "Dali would have been proud", "Look at my doge face", "how did this get here", "Over 3 man-seconds were spent creating this", "oh god i am not good with computer", "Carefully constructed by an artist", "This was easier than it sounds", "hi"}
        return random.sample(lest, 1)[0]

class ReactionMessage:
    '''
    This is a message with a list of reactions and a set of functions that take place
    depending on which reaction is pressed.
    The message is periodically checked to see if the reactions are broken or need to be removed.
    '''
    def __init__(self, msg, bot, uuid = uuid.uuid4()):
        self.uniqueID = str(uuid)
        self.message = msg
        self.content = "Placeholder Text"
        self.reactiondict = {} # Keys are unicode strings, values are functions
        self.bot = bot.bot
        self.loop = bot.bot.loop
        self.BarryBot = bot

    def initialize(self):
        '''Run other initialization things required for this to function'''
        self.loop.create_task(self.startWaiting())
        self.loop.create_task(self.setMessage())
        self.loop.create_task(self.addReactions())

    def setEvent(self, reaction, function):
        '''Set a reaction in the dictionary and assign a function'''
        self.reactiondict[reaction] = function

    def delEvent(self, reaction):
        '''Delete a reaction from the dictionary'''
        del self.reactiondict[reaction]

    def setContent(self, content):
        '''Set the content'''
        self.content = content

    async def addReactions(self):
        '''Place the initial reactions'''
        for key in self.reactiondict.keys():
            await self.message.add_reaction(key)

    async def startWaiting(self):
        '''Begin the waiting game'''
        self.loop.create_task(self._reallyWait())

    async def _reallyWait(self):
        '''This actually does the work for waiting'''
        def check(moji, user):
            return moji.message.id == self.message.id and moji.emoji in self.reactiondict.keys() and not user.bot
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check)
        except:
            print("Something broke really bad.")
            traceback.print_exc()
            return
        await self.message.remove_reaction(reaction.emoji, user)
        try:
            await self.handleReaction(reaction.emoji, user)
        except:
            traceback.print_exc()

        self.loop.create_task(self._reallyWait())

    async def handleReaction(self, reaction, user):
        '''Do the work involving functions for each reaction'''
        await self.reactiondict[reaction](user)

    async def setMessage(self):
        '''Set up the message'''
        await self.message.edit(content=self.content)

class SubMessage(ReactionMessage):
    '''
    This is a ReactionMessage that is built for sublists.
    '''
    def __init__(self, msg, bot, uuid = uuid.uuid4()):
        super().__init__(msg, bot, uuid)

class ColorMessage(ReactionMessage):
    '''
    This is a ReactionMessage that is built for colors.
    '''
    def __init__(self, msg, bot, uuid = uuid.uuid4()):
        super().__init__(msg, bot, uuid)

class GenericPaginator(commands.Paginator):
    '''
    because i simply could not understand the use of the other paginators provided by the api (and i think im supposed to write my own)

    heres what a standard usage looks like

    p = GenericPaginator(self, ctx)
    setting = self.BarryBot.settings[ctx.guild.id]
    for x in setting.commands:
        p.add_line(line=x + " " + setting.commands[x])
    msg = await ctx.send(p)
    p.msg = msg
    p.original_msg = (anything that it outside the paginator and shouldnt be changed)
    await p.add_reactions()
    await p.start_waiting()
    '''

    def __init__(self, bot, ctx, page_header=None, markdown="Error", timeout=30):
        super().__init__(prefix="```"+markdown)
        self.totalpages = len(self.pages)
        self.pagenum = 0
        self.reactions = False
        self.lines_on_a_page = 0

        self.msg = None
        self.original_msg = None
        self.BarryBot = bot
        self.bot = bot.bot
        self.ctx = ctx
        self.loop = bot.loop
        self.page_header = page_header  # for clarity per page
        self.markdown = markdown        # for coloring overall
        self.timeout = timeout          # for timing out after no reaction received

        self.BarryBot.paginators.add(self)
        self.ended = False  # check this in the main bot loop every once in a while to garbage collect
                            # check BarryBot.Paginators (made of self) and delete the ones which have self.ended
        if self.page_header is not None:
            self.add_line(line=self.page_header)
            self.lines_on_a_page = 0



    def __repr__(self):
        self.update_values()
        if self.totalpages > 1:
            return "Use the reactions to nagivate the pages."+self.current_page()
        else:
            return self.current_page()

    def add_line(self, line='', *, empty=False):
        super().add_line(line=line, empty=empty)
        self.lines_on_a_page += 1
        if self.lines_on_a_page == 20:
            self.close_page()


    def close_page(self):
        super().close_page()

        if self.page_header is not None:
            self.add_line(line=self.page_header)
        self.lines_on_a_page = 0

    def update_values(self):
        self.totalpages = len(self.pages)
        if self.totalpages > 1:
            self.reactions = True

    def current_page(self):
        return self.pages[self.pagenum]

    async def move_page(self, direction="Up"):
        ''' alternate: direction="Down"'''
        if direction == "Up":
            self.pagenum += 1
        else:
            self.pagenum -= 1

        if self.pagenum >= self.totalpages:
            self.pagenum = 0
        elif self.pagenum < 0:
            self.pagenum = self.totalpages - 1

        await self.msg.edit(content=self.original_msg+"Use the reactions to nagivate the pages."+self.pages[self.pagenum])

    async def add_reactions(self):
        if self.totalpages == 1:
            return False
        if self.msg is None:
            return False

        await self.msg.add_reaction("\N{LEFTWARDS BLACK ARROW}")
        await self.msg.add_reaction("\N{BLACK RIGHTWARDS ARROW}")

    async def start_waiting(self):
        ''' weird way to make the function not block the entire bot'''
        if self.totalpages == 1:
            return False
        if self.msg is None:
            return False
        self.update_values()

        self.loop.create_task(self._really_wait())

    async def _really_wait(self):
        await asyncio.sleep(0.25)
        def check(moji, user):
            return moji.message.id == self.msg.id and user.id == self.ctx.author.id and moji.emoji in ["\N{LEFTWARDS BLACK ARROW}", "\N{BLACK RIGHTWARDS ARROW}"]
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=self.timeout)
        except:
            return await self.close_paginator()
        await self.msg.remove_reaction(reaction.emoji, self.ctx.author)
        if reaction.emoji == "\N{LEFTWARDS BLACK ARROW}":
            await self.move_page(direction="not up")
        else:
            await self.move_page()


        self.loop.create_task(self._really_wait())

    async def close_paginator(self):
        self.ended = True
        await self.msg.delete()

class ChanOrMember(commands.Converter):
    '''Converts a string to a member or a channel'''

    async def convert(self, ctx, argument):
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except:
            try:
                return await commands.TextChannelConverter().convert(ctx, argument)
            except:
                return None