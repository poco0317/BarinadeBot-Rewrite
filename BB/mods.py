import os
import re
import discord
import asyncio
import traceback
import random
from discord.ext import commands
from BB.permissions import *
from BB.misc import EmbedFooter


class Moderation:
        #for things like linkblock or whatever
        #or maybe role specific muting

    def __init__(self, bot, config, loop, BarryBot):
        self.bot = bot
        self.loop = loop
        self.config = config
        self.BarryBot = BarryBot
        
    @commands.command(aliases=["silence"])
    async def mute(self, ctx):
        ''' unimplemented'''
        # if not Perms.has_specific_set_perms(ctx, self.BarryBot.settings[ctx.guild.id]):
        #     Perms.is_guild_mod(ctx)
        raise unimplemented