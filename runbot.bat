@ECHO off

CMD /k "cd %~dp0\bot-env\Scripts & activate & cd %~dp0 & python run.py"

EXIT