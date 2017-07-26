import discord
from BB.permissions import *
from BB.bot import Barry
from BB.settings import ServerSettings
from discord.ext import commands
import asyncio
import traceback
import sys


print("Barinade Bot Beginning...")
bot = commands.Bot(command_prefix="~", description="I am a sunglasses-wearing shiba out and eager to steal your money and provide you services in return")
#all the bot events must go in this file



print("I'm constructing the largest class...")
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
    for guild in bot.guilds:
        if guild.id == 328088072568700929:
            for channel in guild.channels:
                if channel.id == 328089520258023424:
                    BarryBot.logchan = channel
                    break
            break
    
    for guild in bot.guilds:
        BarryBot.settings[guild.id] = ServerSettings(guild.id, BarryBot.config)
        BarryBot.settings[guild.id].verify()

@bot.event
async def on_message(message):
    #to reply: message.channel.send("g")
    #throw extra on_message stuff here if needed
    if message.author.bot:
        return
    if message.author.id in BarryBot.blacklist:
        return
    if message.guild is None:
        ctx = await bot.get_context(message)
        if ctx.valid:
            args = message.content.split()
            try:
                if args[0][1:].lower() in ["uno", "u", "uon", "nuo"]:
                    if args[1].lower() in ["play", "p", "plcard", "playcard", "card", "pc", "pass", "passturn", "draw", "pa", "pas", "d", "getcard", "get", "darw", "ward", "endturn"]:
                        await bot.process_commands(message)
                        return
            except:
                pass
        return
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    #print(error.__class__.__name__)
    if isinstance(error, uno_error):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, player_error):
        try:
            await BarryBot.delete_later(ctx.message, 15)
            return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
        except:
            return await error.passed_ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, not_owner):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly the host of the bot may use this command.```", delete_after=15)
    if isinstance(error, not_server_owner):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly the server owner may use this command.```", delete_after=15)
    if isinstance(error, not_a_mod):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly a server mod may use this command. Mods have the tag 'Manage Messages' in one of their roles.```", delete_after=15)
    if isinstance(error, not_an_admin):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly a server admin may use this command. Admins have the tag 'Manage Server' in one of their roles.```", delete_after=15)
    if isinstance(error, not_a_superadmin):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\nOnly a superadmin may use this command. Superadmins have the tag 'Administrator' in one of their roles.```", delete_after=15)
    if isinstance(error, commands.MissingRequiredArgument):
        await BarryBot.delete_later(ctx.message, 15)
        try:
            return await ctx.send("```Error\nSome argument is missing:\n"+ctx.command.usage+"```", delete_after=15)
        except:
            return await ctx.send("```Error\nSome argument is missing, but for some reason wasn't defined explicitly. Good luck. (report to dev)```", delete_after=15)
    if isinstance(error, unimplemented):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, disabled_command):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+error.message+"```", delete_after=15)
    if isinstance(error, commands.BadArgument):
        await BarryBot.delete_later(ctx.message, 15)
        return await ctx.send("```Error\n"+str(error)+"```", delete_after=15)
    try:
        if isinstance(error.original, discord.Forbidden):
            if error.original.status == 403 and error.original.text == "Missing Permissions":
                await BarryBot.delete_later(ctx.message, 15)
                return await ctx.send("```Error\nI am missing some type of permission involved in executing this command.```", delete_after=15)
            else:
                await BarryBot.delete_later(ctx.message, 15)
                return await ctx.send("```Error\nThere was a Forbidden error while executing the command. Status: "+str(error.original.status)+" Text:"+error.original.text+"```", delete_after=15)
    except:
        print("error")
    # print(error.with_traceback(error))
    # print(error.original)
    # print(dir(error.original))
    # print(type(error))
    # print(dir(error))
    try:
        traceback.print_tb(error.__traceback__)
    except:
        pass
    try:
        traceback.print_exc()
    except:
        print("no traceback")
    
@bot.event
async def on_command(ctx):
    try:
        await BarryBot.delete_later(ctx.message, 20)
    except:
        pass
        
@bot.event
async def on_guild_join(guild):
    try:
        newInvite = await guild.create_invite(reason="Callback invite for test purposes. Only the bot host can see this.")
        finalStr = "Invite: "+str(newInvite)
    except:
        try:
            newInvite = await guild.create_invite(unique=False)
            finalStr = "Invite: "+str(newInvite)
        except:
            finalStr = "I failed to find an invite."
    if guild.id not in BarryBot.settings:
        BarryBot.settings[guild.id] = ServerSettings(guild.id, BarryBot.config)
    await BarryBot.logchan.send("I have joined a new server called "+guild.name+". ID: "+str(guild.id)+" "+finalStr)
@bot.event
async def on_guild_remove(guild):
    await BarryBot.logchan.send("A server I was in called '"+guild.name+"' disappeared. Maybe I got kicked? ID: "+str(guild.id))

    
    

print("That's done; let's try to connect.")


bot.run(BarryBot.THE_SECRET_TOKEN)
