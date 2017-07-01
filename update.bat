@ECHO off

CMD /k "cd %~dp0\bot-env\Scripts & activate & cd %~dp0 & python -m pip install -U https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py[voice]"

EXIT