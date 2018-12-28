import re
import os
import traceback
import random
import discord

import matplotlib.pyplot as plt
import datetime

from BB.DB import *
from BB.permissions import *
from discord.ext import commands
from BB.misc import ChanOrMember


class BarTalk:

    def __init__(self, bot, config, mainbot):
        self.bot = bot
        self.loop = mainbot.loop
        self.BarryBot = mainbot
        self.config = config

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def rawsprint(self, ctx, *, statement):
        ''' raw sql'''
        try:
            out = self.BarryBot.BarTalk_sessions[ctx.guild.id].brainDB.rawExecuteAndPrint(statement)
        except:
            traceback.print_exc()
            out = "error."
        if len(out) > 1000:
            await ctx.send("```"+str(out)[:1000]+" TRUNCATED THE REST.```")
        else:
            await ctx.send("```"+str(out)+"```")

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def raws(self, ctx, *, statement):
        ''' raw sql'''
        try:
            self.BarryBot.BarTalk_sessions[ctx.guild.id].brainDB.rawExecuteAndPrint(statement)
        except:
            traceback.print_exc()

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def raw(self, ctx, *, statement):
        ''' raw sql'''
        try:
            self.BarryBot.BarTalk_sessions[ctx.guild.id].brainDB.rawExecute(statement)
        except:
            traceback.print_exc()

    @commands.command(hidden=True)
    @commands.check(Perms.is_owner)
    async def loadBrain(self, ctx, *given):
        ''' load an existing brain from text
        syntax: !command "path"'''
        try:
            f = open(given[0], "r")
            command = []
            for line in f:
                info = line.split("=")
                key = info[0]
                values = info[1]
                command.append((key.strip(), values.strip()))
            f.close()
            self.BarryBot.BarTalk_sessions[ctx.guild.id].brainDB.checkCursor()
            self.BarryBot.BarTalk_sessions[ctx.guild.id].brainDB.cursor.executemany('insert into memory(id, "words") values (?, ?)', command)
            self.BarryBot.BarTalk_sessions[ctx.guild.id].brainDB.closeCursor()
            print("Done")
        except:
            traceback.print_exc()


    @commands.group(aliases=["barry"])
    async def bar(self, ctx):
        '''The group command for Bar. Bar is a Markov Chain bot which listens to certain channels on command.
        Or it's me becoming sentient.
        The longer I listen, the more I know. Say 'bar' in a listened channel to get me to reply.
        You must first designate channels to be listened to, because I start off with no channels to listen to.
        '''
        pass

    @bar.group(aliases=["listen", "ig", "i"], invoke_without_command=True)
    @commands.check(Perms.is_guild_mod)
    async def ignore(self, ctx, optional_arg : ChanOrMember=None):
        ''' Toggle ignore on a channel or a person.
        You must mention the channel or person.
        If no arguments are given, toggles ignore on the current channel.
        Having a channel or person ignored means that I will not listen or respond to it. Commands still work.
        Note that all channels start off ignored by default.'''
        if optional_arg is None:
            if self.BarryBot.BarTalk_sessions[ctx.guild.id].toggleChannel(ctx.channel.id) == "REMOVED":
                return await ctx.send("I will no longer listen to this channel.")
            else:
                return await ctx.send("I am now listening to this channel.")
        if optional_arg.mention.startswith("<#"):
            if self.BarryBot.BarTalk_sessions[ctx.guild.id].toggleChannel(ctx.channel.id) == "REMOVED":
                return await ctx.send("I will no longer listen to "+optional_arg.name)
            else:
                return await ctx.send("I am now listening to "+optional_arg.name)
        elif optional_arg.mention.startswith("<@"):
            if self.BarryBot.BarTalk_sessions[ctx.guild.id].toggleUser(optional_arg.id) == "REMOVED":
                return await ctx.send("I am now able to hear user: "+optional_arg.name)
            else:
                return await ctx.send("I am now ignoring user: "+optional_arg.name)
        else:
            return await ctx.send("Something is very wrong and broken. Nothing changed. Report to a dev.")

    @ignore.command(aliases=["everything"])
    @commands.check(Perms.is_guild_mod)
    async def all(self, ctx):
        ''' Ignores all channels.
        This does not modify any users who are ignored.
        This will not set any channel to be listened to. They must be added one by one.'''
        for channel in ctx.guild.text_channels:
            if str(channel.id) in self.BarryBot.BarTalk_sessions[ctx.guild.id].listened_channels:
                self.BarryBot.BarTalk_sessions[ctx.guild.id].toggleChannel(channel.id)
        await ctx.send("I am no longer listening to any channel on this server.")

    @ignore.command(aliases=["channels", "chans"])
    async def listchannels(self, ctx):
        ''' Show the list of channels being listened to'''
        count_channels = len(ctx.guild.text_channels)
        count_listens = len(self.BarryBot.BarTalk_sessions[ctx.guild.id].listened_channels)
        if count_listens == 0:
            await ctx.send("I am not listening to any channels on this server.")
        else:
            finalstr = "I am listening to "+str(count_listens)+" out of "+str(count_channels)+" channels.\n```Here is a list:"
            for chan in ctx.guild.text_channels:
                if str(chan.id) in self.BarryBot.BarTalk_sessions[ctx.guild.id].listened_channels:
                    finalstr = finalstr + "\n" + chan.name
            finalstr = finalstr + "```"
            await ctx.send(finalstr)

    @ignore.command(aliases=["people", "members"])
    async def listusers(self, ctx):
        ''' Show the list of users being ignored'''
        count_users = len(self.BarryBot.BarTalk_sessions[ctx.guild.id].ignored_users)
        if count_users == 0:
            await ctx.send("I am not ignoring any users on this server.")
        else:
            finalstr = "I am ignoring the following users: "
            for userID in self.BarryBot.BarTalk_sessions[ctx.guild.id].ignored_users:
                try:
                    user = ctx.guild.get_member(userID)
                    finalstr = finalstr + "\n"+user.name
                except:
                    pass
            finalstr = finalstr + "```"
            await ctx.send(finalstr)

    @bar.command()
    async def stats(self, ctx):
        ''' Show general stats from My brain.'''
        the_id = ctx.guild.id
        try:
            unique_keys = len(self.BarryBot.BarTalk_sessions[the_id].big_list)  # 2 word phrases associated with words
            unique_values_set = set()
            repeated_values = 0
            repeat_dict = {}
            for _, v in self.BarryBot.BarTalk_sessions[the_id].big_list.items():
                repeated_values = repeated_values + len(v)
                for x in v:
                    unique_values_set.add(x)
                    if x in repeat_dict:
                        repeat_dict[x] += 1
                    else:
                        repeat_dict[x] = 1
            unique_values = len(unique_values_set)
            biggestrepeat = list(repeat_dict)[0]
            for k, v in repeat_dict.items():
                if v > repeat_dict[biggestrepeat]:
                    biggestrepeat = k
            sorted_repeats = sorted(repeat_dict, key=repeat_dict.get, reverse=True)
            to_remove = set()
            for x in sorted_repeats:
                if x.lower() in self.config.stopwords:
                    to_remove.add(x)
            for x in to_remove:
                sorted_repeats.remove(x)
            endStr = ""
            for x in sorted_repeats[-14:]:
                endStr = endStr + " " + x
            plt.bar(range(len([int(repeat_dict[sorted_repeats[x]]) for x in range(15)])),
                    [int(repeat_dict[sorted_repeats[x]]) for x in range(15)])
            plt.xticks(range(15), [sorted_repeats[x] for x in range(15)], rotation=-39)
            plt.ylabel("Occurrences")
            plt.title("Top 15 Single Words")
            plt.savefig("graphs/" + str(ctx.guild.id) + "statsgraph.png", bbox_inches='tight')
            plt.clf()
            await ctx.send("Bar Stats:\nUnique Keys (2 word phrases to associate with words): " + str(
                unique_keys) + "\nUnique Single Words (words associated with phrases): " + str(
                unique_values) + "\nTotal Single Words (with repeats): " + str(
                repeated_values) + "\nMost common word, not counting keys, but including all possible words (" + str(
                repeat_dict[
                    biggestrepeat]) + " occurrences): " + biggestrepeat + "\nHere are the last 15 words I found in the list sorted by uses: `" + endStr + "`\nHere is a graph of the top 15 most common words, with common words like 'a' or 'the' removed:",
                           file=discord.File("graphs/" + str(ctx.guild.id) + "statsgraph.png"))
        except:
            traceback.print_exc()

    @bar.command()
    async def phrase(self, ctx, *, words: str):
        ''' Search My brain for a phrase
        If only 1 word is given, you count every occurrence of the word.
        If only 2 words are given, you count every key occurrence of the word.
        If more words are given, it tries to match the sentence or at least the first few words.'''

        # this will work by splitting the phrase up into a regular list
        # if the first 2 words are found, we can continue into phase 2 (repeat phase)
        # the 3rd word has to be a value of the key (first 2 words)
        # if true, set the current key to the 2nd and 3rd words and repeat

        # for just 1 word: search everything for every occurrence of the word
        # for just 2 words: search all keys for the key
        #       also search each key's second word against the first word and if it matches, check the values
        try:
            wordlist = words.lower().split()
            count = 0
            if len(wordlist) == 1:
                edit_later = await ctx.send(
                    "I'm looking for the word '" + words.lower() + "' anywhere in my brain...", delete_after=30)
                for k, v in self.BarryBot.BarTalk_sessions[ctx.guild.id].big_list.items():
                    if words.lower() in k.lower().split():
                        count += 1
                    if words.lower() in v:
                        count += 1
                return await edit_later.edit(
                    content="I counted " + str(count) + " instances of '" + words.lower() + "'.")
            if len(wordlist) == 2:
                edit_later = await ctx.send(
                    "I'm looking for the phrase '" + words.lower() + "' anywhere in my brain...",
                    delete_after=30)
                for k, v in self.BarryBot.BarTalk_sessions[ctx.guild.id].big_list.items():
                    if k == words.lower():
                        count += 1
                    if k.split()[1].lower() == wordlist[0]:
                        for val in v:
                            if wordlist[1] == val:
                                count += 1
                return await edit_later.edit(
                    content="I counted " + str(count) + " instances of '" + words.lower() + "'.")
            edit_later = await ctx.send(
                "I'm looking for the phrase '" + words.lower() + "' anywhere in my brain...", delete_after=30)
            foundList = []
            regularMethod = False
            for k in self.BarryBot.BarTalk_sessions[ctx.guild.id].big_list:  # match first 2 words to a key
                if k.lower() == " ".join(wordlist[:2]).lower():
                    foundList.append(k)
                    count += 1
                    regularMethod = True
                    break

            if not regularMethod:
                for k, v in self.BarryBot.BarTalk_sessions[
                    ctx.guild.id].big_list.items():  # match first 2 words to a key-val
                    if regularMethod:
                        break
                    for val in v:
                        if k.lower().split()[1] + " " + val.lower() == " ".join(wordlist[:2]).lower():
                            foundList.append(" ".join(wordlist[:2]).lower())
                            count += 1
                            regularMethod = True
                            break
            if len(wordlist) == 3:
                for k, v in self.BarryBot.BarTalk_sessions[ctx.guild.id].big_list.items():
                    if k.lower() == wordlist[1].lower() + " " + wordlist[2].lower():
                        foundList.append(" ".join(wordlist).lower())
                        count += 1
                        break
                    for val in v:
                        if k.lower().split()[1] + " " + val.lower() == wordlist[1].lower() + wordlist[
                            2].lower():
                            foundList.append(" ".join(wordlist).lower())
                            count += 1
                            break
                if count > 0:
                    return await edit_later.edit(content="I counted " + str(
                        count) + " instances of '" + words.lower() + "'.\nThe following phrases were found:\n" + "\n".join(
                        foundList))
                else:
                    return await edit_later.edit(content="I did not find any instances of that phrase.")
            if len(wordlist) > 3:
                if not regularMethod:
                    return await edit_later.edit(content="I did not find any instances of that phrase.")
                i = 2
                keyVal_found = True
                while i < len(wordlist) and i - 2 < len(foundList) and (
                                wordlist[i].lower() + " " + foundList[i - 2].lower().split()[-1] in
                        self.BarryBot.BarTalk_sessions[ctx.guild.id].big_list or keyVal_found):
                    kvf = False
                    for k, v in self.BarryBot.BarTalk_sessions[ctx.guild.id].big_list.items():
                        for val in v:
                            if k.lower().split()[1] + " " + val.lower() == wordlist[i - 1].lower() + " " + \
                                    wordlist[i].lower():
                                if (" ".join(wordlist[:i + 1]).lower()) == foundList[-1]:
                                    pass
                                else:
                                    foundList.append(" ".join(wordlist[:i + 1]).lower())
                                count += 1
                                kvf = True
                                break
                    if not kvf:
                        keyVal_found = False
                    i += 1
            return await edit_later.edit(
                content="I found the following phrases made up of your input phrase:\n" + "\n".join(foundList))
        except:
            traceback.print_exc()

class Brain:
    ''' a brain object per server to hold all the stuff'''
    def __init__(self, serverID, config):
        self.serverID = str(serverID)
        self.brainDB = GeneralDB("bar_"+self.serverID)  # sql db to hold everything about this server's bar instance
        self.verifyBarTables()
        self.big_list = {}

        #for row in self.brainDB.getTable("memory")[0]:
        #    self.big_list[row[0]] = row[1].split()
        self.compile()

        self.listened_channels = []
        self.ignored_users = []
        self.refreshSettings()
        #self.listened_channels = self.brainDB.getRow("config", "listened_channels")[1].split()
        #self.ignored_users = self.brainDB.getRow("config", "ignored_users")[1].split()


    def compile(self):
        ''' set up the main dictionary'''
        for row in self.brainDB.getTable("memory"):
            self.big_list[row[0]] = row[1].split()

    def removeIgnoredUser(self, userID):
        ''' remove an ID from the list'''
        self.removeIDFromFakeList("config", "ignored_users", userID)
        self.refreshSettings()

    def addIgnoredUser(self, userID):
        ''' add an ID to the list'''
        self.addIDToFakeList("config", "ignored_users", userID)
        self.refreshSettings()

    def removeListenedChannel(self, chanID):
        ''' remove an ID from the list'''
        self.removeIDFromFakeList("config", "listened_channels", chanID)
        self.refreshSettings()

    def addListenedChannel(self, chanID):
        ''' add an ID to the list'''
        self.addIDToFakeList("config", "listened_channels", chanID)
        self.refreshSettings()

    def addIDToFakeList(self, table, rowID, newItem):
        ''' add an ID to the list'''
        things = self.brainDB.getRow(table, rowID)[1].split()
        things.append(str(newItem))
        self.brainDB.replaceRow(table, rowID, ['"'+" ".join(things)+'"'])

    def removeIDFromFakeList(self, table, rowID, toRemove):
        ''' remove an ID from the list'''
        things = self.brainDB.getRow(table, rowID)[1].split()
        things.remove(str(toRemove))
        self.brainDB.replaceRow(table, rowID, ['"'+" ".join(things)+'"'])

    def toggleUser(self, userID):
        ''' toggle an ignored user'''
        userID = str(userID)
        if userId in self.ignored_users:
            self.removeIgnoredUser(userID)
            return "REMOVED"
        else:
            self.addIgnoredUser(userID)
            return "ADDED"

    def toggleChannel(self, chanID):
        ''' toggle a listened channel'''
        chanID = str(chanID)
        if chanID in self.listened_channels:
            self.removeListenedChannel(chanID)
            return "REMOVED"
        else:
            self.addListenedChannel(chanID)
            return "ADDED"

    def refreshSettings(self):
        ''' update the brain settings from the db'''
        listened_channels = self.brainDB.getRow("config", "listened_channels")[1]
        ignored_users = self.brainDB.getRow("config", "ignored_users")[1]
        try:
            self.listened_channels = listened_channels.split()
        except:
            self.listened_channels = []
        try:
            self.ignored_users = ignored_users.split()
        except:
            self.ignored_users = []


    def verifyBarTables(self):
        ''' make sure the necessary tables with the right info exist'''
        if not(self.brainDB.verifyTableExists("memory")):
            self.brainDB.createTable("memory", ["words text"])
            # each ID is a key pair
            # each "words" is a list of words that go with it
            self.brainDB.addRow("memory", ['"hello im"', '"bar"'])
            self.brainDB.addRow("memory", ['"im bar"', '"man"'])
        rowsMissingFromConfig = self.brainDB.verifyTableExistsWithRows("config", ['"listened_channels"', '"ignored_users"'])
        if len(rowsMissingFromConfig) > 0:
            try:
                self.brainDB.createTable("config", ['"setting text"'], suppress=True)
            except:
                pass
            # each ID is a setting name
            # each setting is the setting that goes with it, a string
            for row in rowsMissingFromConfig:
                try:
                    self.brainDB.addRow("config", [row, '""'])
                except:
                    pass

    def collect(self, key, value):
        ''' Take a key and a value, drop it in the dictionary, write it to the brain.'''
        if key in self.big_list:
            self.big_list[key].append(value)
        else:
            self.big_list[key] = [value]
        return self.brainwrite(key, value)

    def brainwrite(self, key, value):
        ''' write a key and value to the brain DB'''
        row = self.brainDB.getRow("memory", key)
        if row is None:
            self.brainDB.addRow("memory", ['"'+key+'"', '"'+value+'"'])
        else:
            self.brainDB.replaceRow("memory", key, ['"'+" ".join(row[1].split() + [value])+'"'])

    # noinspection PyTypeChecker,PyTypeChecker,PyCallByClass
    def get_weight(self, inputStr, Strict = None):
        '''
        Returns a random key from a given weight
        Expectedc input is "bar [etc etc...]"
        If Strict is anything, we check that index of the keys only for the weighting.
            This is only expected with an input with 1 word after the trigger
        '''

        inputStr = re.sub("[^a-zA-Z0-9\s]", "", inputStr.lower())
        inputList = inputStr.split()

        if len(inputList) <= 1: # no weight because nothing exists to generate one
            return random.choice(list(self.big_list))

        while len(inputList) > 0 and (str.startswith(inputList[0].lower(), "bar") or str.startswith(inputList[-1].lower(), "bar")):
        #while len(inputList) > 0 and inputList[0].lower().startswith("bar") or inputList[-1].lower().startswith("bar"):
            if inputList[0].lower().startswith("bar"):
                inputList.pop(0)
            elif inputList[-1].lower().startswith("bar"):
                inputList.pop(len(inputList)-1)

        inputStr = " ".join(inputList)

        if len(inputList) == 0:
            return random.choice(list(self.big_list))

        if len(inputList) == 1:
            keyset = set()
            if Strict is not None:
                for key in self.big_list:
                    if inputStr == key.split()[Strict]:
                        keyset.add(key)
            else:
                for key in self.big_list:
                    if inputStr.lower() in [re.sub("[^a-zA-Z0-9]", "", key.lower().split()[i]) for i in range(len(key.split()))]:
                        if not re.search("[.?!]", key):
                            keyset.add(key)
        else:
            keyset = set()
            for key in self.big_list:
                if inputStr.lower() == key.lower():
                    keyset.add(key)

        if len(keyset) == 0:
            return random.choice(list(self.big_list))
        return random.sample(keyset, 1)[0]

    def get_next(self, inputStr):
        '''
        Returns the next word and key from a given input
        Expected input is "a randomkey"
        Returns None if there was not a found match. (we stop at this point)
        Returns only one word if it ends with certain punctuations and no match is found (we stop at this point)
        Returns more than 2 words if the next key would contain a terminating punctuation and a useful match was found afterward
        '''
        currentkey = inputStr.lower()
        currentkeyList = currentkey.split()
        if len(currentkeyList) > 2: # to get rid of the rest of the input, the input may be more than 2 words
            currentkeyList = currentkeyList[-2:]
            currentkey = " ".join(currentkeyList)
        try:
            nextword = random.choice(self.big_list[currentkey])
        except:
            return None

        nextkeyList = [currentkeyList[1], nextword]
        nextkey = " ".join(nextkeyList)
        finalreturn = nextkey
        if re.search("[.!?]", nextkeyList[0][-1]):
            keyset = set()
            for key in self.big_list:
                if nextkeyList[1] == key.split()[0]:
                    keyset.add(key.split()[1])
            if len(keyset) > 0:
                finalreturn = finalreturn + " " + random.sample(keyset, 1)[0]
            else:
                finalreturn = nextkeyList[0]
        return finalreturn

    def response(self, inputStr, guild):
        ''' Returns a sentence to send as a response based on the given input
        We want the guild given because we might use it to give a random name from the guild'''

        finalResponse = ""
        finalResponseList = []
        custom_response = 45    # length limit

        randomkey = self.get_weight(inputStr)
        if len(inputStr.split()) > 1:
            if inputStr.split()[1].lower() in ["who", "who?"]:
                if random.randint(1,20) == 19:
                    pass
                else:
                    custom_response = 10
                    responses = ["the", "those"]
                    response = random.choice(responses)

                    if random.randint(1,15) == 11:
                        members = {member.name for member in guild.members}
                        randmember = random.sample(members, 1)[0]
                        return randmember+"."

                    randomkey = self.get_weight("bar "+response, 0)

            elif inputStr.split()[1].lower() in ["why", "why?", "how"]:
                if random.randint(1,30) == 19:
                    pass
                else:
                    custom_response = 20
                    responses = ["i", "his", "her", "because", "cause", "the"]
                    response = random.choice(responses)

                    randomkey = self.get_weight("bar "+response, 0)
            elif inputStr.split()[1].lower() in ["should", "would", "will", "is"]:
                if random.randint(1,30) > 3:
                    pass
                else:
                    responses = ["yes", "no", "probably", "maybe", "i dont know", "why are are you asking me", "i have no idea", "stop asking me", "dont ask", "what?", "i wouldnt know", "dont talk to me or my son ever again", "who would do that?", "yeah probably", "i bet", "definitely", "nope", "yeah no", "yeah", "nah", "no."]
                    return random.choice(responses)
            elif inputStr.split()[1].lower() in ["thanks", "thank", "sorry"]:
                if random.randint(1,30) > 2:
                    pass
                else:
                    responses = ["ok", "no problem", "youre welcome", "me too, thanks"]
                    return random.choice(responses)

        finalResponseList = [randomkey]
        addedwords = 0
        nextkey = randomkey

        if random.randint(1,50) == 49:  # rare chance to drop 1 word only because its funny
            return finalResponseList[0].split()[0]

        randomend = random.randint(4,custom_response)

        try:
            if inputStr.split()[1] == "nolengthlimit":
                randomend = 200
        except:
            pass

        while nextkey and addedwords < randomend:
            addedwords += 1
            nextkey = self.get_next(nextkey)
            if nextkey is None:
                break
            if len(nextkey.split()) == 1:
                finalResponseList.pop(len(finalResponseList)-1)
                break
            if len(nextkey.split()) > 2:
                finalResponseList = finalResponseList + nextkey.split()[1:]
            else:
                finalResponseList.append(nextkey.split()[1])
        finalResponse = " ".join(finalResponseList)

        if len(finalResponseList) == 0:
            return self.response(inputStr, guild)
        if finalResponse[-1] in [",", "'", "&", "-"]:
            return finalResponse[:-1]
        return finalResponse
