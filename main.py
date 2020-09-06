# Note: If you host the bot on Heroku (https://heroku.com/), you
# need to assign your Discord bot token to a Config Var named "TOKEN".

import setup
import events
import commands


def run_bot():
    from config import bot, D_TOKEN

    bot.run(D_TOKEN)


run_bot()