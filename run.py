import discord
from BB.bot import Barry
from discord.ext import commands
import asyncio
from BB.permissions import *



bot = commands.Bot(command_prefix="~", description="I am a sunglasses-wearing shiba out and eager to steal your money and provide you services in return")
#all the bot events must go in this file
BarryBot = Barry(bot)


@bot.event
async def on_ready():
    print("\nI'm in.")
    print("Here is a list of servers I'm in:\n- ", end="")
    print("\n- ".join([guild.name for guild in bot.guilds]))
    print("\nI have access to "+str(sum([len(guild.text_channels) for guild in bot.guilds]))+" text channels.")
    print("I have access to "+str(sum([len(guild.voice_channels) for guild in bot.guilds]))+" voice channels.")
    print("I can see "+str(len(set(bot.get_all_members())))+" distinct members.")
    print("\n\nHere we gooooo! I'm ready to take commands.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild == None:
        return
    #to reply: message.channel.send("g")
    #throw extra on_message stuff here if needed
        
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    #print(error.__class__.__name__)
    if isinstance(error, uno_error):
        BarryBot.loop.create_task(BarryBot.delete_later(ctx.message, 15))
        return await ctx.send("```Error:\n"+error.message+"```", delete_after=15)
    
    
    

    
    
print("Barinade Bot Beginning...")
print("Let's try to connect.")


bot.run(BarryBot.THE_SECRET_TOKEN)
