import sys

import praw
import asyncio
import discord
import random
from discord.ext import commands
import datetime

import config
from custom import *

bot = config.bot

reddit_client = praw.Reddit(
    client_id=config.R_CLIENT_ID,
    client_secret=config.R_CLIENT_SECRET,
    username=config.R_USERNAME,
    password=config.R_PASSWORD,
    user_agent=config.R_USER_AGENT
)


@bot.command(aliases=["latency"])
async def ping(ctx):
    latency = round(bot.latency, 3) * 1000  # in ms to 3 d.p.

    await ctx.send(f"Pong! ({latency}ms)")


# closes the bot (only bot owners)
@bot.command(hidden=True)
async def cease(ctx):
    if not await bot.is_owner(ctx.author):
        return

    await ctx.send("Farewell...")
    print("Done.")

    await bot.close()
    sys.exit()


@bot.command()
async def upvotes(ctx, link):
    post = reddit_client.submission(url=link)

    await ctx.send(f"This post has {post.ups} upvotes!")


@bot.command()
async def downvotes(ctx, link):
    post = reddit_client.submission(url=link)

    ratio = post.upvote_ratio
    score = post.score

    if ratio != 0.5:
        ups = round((ratio * score) / (2 * ratio - 1))
    else:
        ups = round(score / 2)

    downs = ups - score

    await ctx.send(f"This post has {downs} downvotes!")


@bot.command()
async def repeat(ctx, *, phrase):
    if '@everyone' in phrase:
        await ctx.send("Haha fuck you with your everyone ping nonsense!")
    elif '@here' in phrase:
        await ctx.send("There's nobody here I guess...")
    elif 'discord.gg' in phrase:
        await ctx.send("Trying to advertise another server, huh?")
    elif '@' in phrase:
        await ctx.send("No pinging!")
    else:
        await ctx.send(phrase)


@bot.command(aliases=["balance", "bal"])
async def balance_(ctx, user_attr=None):
    if not user_attr:
        user = ctx.author
    else:
        user = find_user(ctx, user_attr)
        if not user:
            await ctx.send("This user wasn't found!")

            return

    open_account(user)
    bank_data = get_bank_data()

    user_balance = bank_data[user]["balance"]

    embed = discord.Embed(
        title=f"{user.name}'s Beddit balance",
        color=0x96d35f
    )
    embed.add_field(name="Bedcoins:", value=user_balance)
    embed.set_thumbnail(url="https://i.imgur.com/vrtyPEN.png")

    await ctx.send(embed=embed)


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def gibcash(ctx):
    user = ctx.author

    open_account(user)
    bank_data = get_bank_data()

    bank_data[user]["balance"] += 1000

    store_bank_data(bank_data)

    await ctx.send("I deposited 1000 bedcoins to your bank account!")


@bot.command(pass_context=True)
@commands.cooldown(1, 60 * 60 * 24, commands.BucketType.user)
async def daily(ctx):
    user = ctx.author

    open_account(user)
    bank_data = get_bank_data()

    bank_data[user]["balance"] += 100

    store_bank_data(bank_data)

    await ctx.send("You collected your daily reward of 100 bedcoins!")


TRANSFER_TAX_RATE = 0.05  # 5%


@bot.command()
async def transfer(ctx, *, args):
    args_list = args.split()

    amount = args_list[-1]
    receiver_attr = " ".join(args_list[:-1])

    sender = ctx.author

    open_account(sender)
    bank_data = get_bank_data()

    if bank_data[sender]["active_bets"] > 0:
        await ctx.send("You can't transfer money while you have active bets!")

        return

    if not amount.isdigit():
        await ctx.send("That is not a valid money amount!")

        return
    amount = int(amount)

    if amount == 0:
        await ctx.send("That is not a valid money amount!")

        return

    receiver = find_user(ctx, receiver_attr)
    if not receiver:
        await ctx.send("This user wasn't found!")

        return

    if sender == receiver:
        await ctx.send("You can't transfer money to yourself!")

        return

    open_account(sender)
    open_account(receiver)

    bank_data = get_bank_data()

    if amount > bank_data[sender]["balance"]:
        await ctx.send("You don't have enough money for this transfer!")

        return

    bank_data[sender]["balance"] -= amount
    bank_data[receiver]["balance"] += int(
        amount - TRANSFER_TAX_RATE * amount
    )

    store_bank_data(bank_data)

    await ctx.send(
        f"Transfer successful! (Tax Rate: {int(TRANSFER_TAX_RATE * 100)}%)"
    )


@bot.command()
async def gamble(ctx, amount):
    user = ctx.author

    if not amount.isdigit():
        await ctx.send("You can't gamble that!")

        return
    amount = int(amount)

    open_account(user)
    bank_data = get_bank_data()

    if bank_data[user]["balance"] < amount:
        await ctx.send(
            "You do not have enough money to gamble that much! "
            "YOU ARE POOR LOL!!!"
        )

        return

    outcome = random.randint(0, 1)

    if outcome == 0:
        bank_data[user]["balance"] += amount

        store_bank_data(bank_data)

        await ctx.send("Yay! You doubled your gamble amount!")
    else:
        bank_data[user]["balance"] -= amount

        store_bank_data(bank_data)

        await ctx.send("HAHA YOU LOST!!! YOU IDIOT!")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def bet(ctx, link, amount, time, predicted_ups):
    user = ctx.author

    if not amount.isdigit() or not predicted_ups.isdigit():
        await ctx.send("You didn't input valid data!")

        return

    amount = int(amount)
    predicted_ups = int(predicted_ups)

    initial_post = reddit_client.submission(url=link)

    age = int(
        datetime.datetime.utcnow().timestamp() - initial_post.created_utc
    )

    if age > 86400:
        await ctx.send("You can't bet on posts older than 24 hours!")

        return

    if initial_post.archived or initial_post.locked:
        await ctx.send("You can't bet on archived or locked posts!")

        return

    # if not ctx.channel.is_nsfw() and initial_post.nsfw:
    #     await ctx.send("You can't bet on NSFW posts here!")
    #
    #     return

    initial_ups = initial_post.ups

    open_account(user)
    bank_data = get_bank_data()

    if predicted_ups <= initial_ups:
        await ctx.send(
            "Your predicted upvotes can't be lower than or equal to "
            "the current amount of upvotes!"
        )

        return

    if bank_data[user]["balance"] < amount:
        await ctx.send("You do not have enough chips to bet this much!")

        return

    if bank_data[user]["active_bets"] >= 3:
        await ctx.send("You already have 3 bets running!")

        return

    bank_data[user]["active_bets"] += 1

    store_bank_data(bank_data)

    # gets time unit, then removes it and converts time to seconds
    if "s" in time:
        time_in_seconds = time.rstrip("s")

        if not time_in_seconds.isdigit():
            await ctx.send("You can't use that as time!")

            return

        time_in_seconds = int(time_in_seconds)

    elif "m" in time:
        time_in_seconds = time.rstrip("m")

        if not time_in_seconds.isdigit():
            await ctx.send("You can't use that as time!")

            return

        time_in_seconds = int(time_in_seconds) * 60
    elif "h" in time:
        time_in_seconds = time.rstrip("h")

        if not time_in_seconds.isdigit():
            await ctx.send("You can't use that as time!")

            return

        time_in_seconds = int(time_in_seconds) * 3600
    elif time.isdigit():
        await ctx.send("Please specify a time unit.")

        return
    else:
        await ctx.send("You can't use that as time!")

        return

    # sends initial message with specifics
    await ctx.send(
        f"This post has {initial_ups} upvotes right now! You bet {amount} "
        f"{'bedcoins' if amount != 1 else 'bedcoin'} on it reaching "
        f"{predicted_ups} upvotes in {time}!"
    )

    # removes bet amount from bank balance
    bank_data[user]["balance"] -= amount

    store_bank_data(bank_data)

    # calculates the prediction multiplier based on the predicted upvotes
    predicted_ups_increase = predicted_ups - initial_ups

    if predicted_ups_increase < 40000:
        if predicted_ups_increase < 5000:
            if predicted_ups_increase < 1000:
                if predicted_ups_increase < 500:
                    prediction_multiplier = -1
                else:
                    prediction_multiplier = -0.5
            else:
                if predicted_ups_increase < 2500:
                    prediction_multiplier = 0
                else:
                    prediction_multiplier = 0.5
        else:
            if predicted_ups_increase < 20000:
                if predicted_ups_increase < 10000:
                    prediction_multiplier = 1
                else:
                    prediction_multiplier = 1.5
            else:
                if predicted_ups_increase < 30000:
                    prediction_multiplier = 2
                else:
                    prediction_multiplier = 2.5
    else:
        if predicted_ups_increase < 80000:
            if predicted_ups_increase < 60000:
                if predicted_ups_increase < 50000:
                    prediction_multiplier = 3
                else:
                    prediction_multiplier = 3.5
            else:
                if predicted_ups_increase < 70000:
                    prediction_multiplier = 4
                else:
                    prediction_multiplier = 5
        else:
            if predicted_ups_increase < 90000:
                prediction_multiplier = 6
            else:
                prediction_multiplier = 7.5

    # calculates the time multiplier based on the chosen time
    if time_in_seconds < 21600:
        if time_in_seconds < 7200:
            if time_in_seconds < 300:
                if time_in_seconds < 60:
                    time_multiplier = -10
                else:
                    time_multiplier = -4
            else:
                if time_in_seconds < 3600:
                    time_multiplier = -2
                else:
                    time_multiplier = 0
        else:
            if time_in_seconds < 14400:
                if time_in_seconds < 10800:
                    time_multiplier = 0.5
                else:
                    time_multiplier = 1
            else:
                if time_in_seconds < 18000:
                    time_multiplier = 1.5
                else:
                    time_multiplier = 2.3
    else:
        if time_in_seconds < 28800:
            if time_in_seconds < 25200:
                time_multiplier = 3.8
            else:
                time_multiplier = 4.5
        else:
            if time_in_seconds < 32400:
                time_multiplier = 6
            elif time_in_seconds < 36000:
                time_multiplier = 7.5
            else:
                time_multiplier = 10

    # waits until the chosen time runs out, then calculates the accuracy
    await asyncio.sleep(time_in_seconds)

    final_post = reddit_client.submission(url=link)
    final_ups = final_post.ups

    # pct means percent
    try:
        if predicted_ups > final_ups:
            accuracy = abs(final_ups / predicted_ups)
        else:
            accuracy = abs(predicted_ups / final_ups)
    except ZeroDivisionError:
        await ctx.send("Oops! Something went wrong.")

        return

    accuracy = round(accuracy, 3)
    accuracy_in_pct = accuracy * 100

    # determines the accuracy multiplier based on
    # how accurate the prediction was
    if accuracy_in_pct < 70:
        if accuracy_in_pct < 30:
            if accuracy_in_pct < 10:
                if accuracy_in_pct <= 0:
                    accuracy_multiplier = -2

                    await ctx.send("Hmm... Strange times.")
                else:
                    accuracy_multiplier = -2
            else:
                if accuracy_in_pct < 20:
                    accuracy_multiplier = -1.5
                else:
                    accuracy_multiplier = -1
        else:
            if accuracy_in_pct < 50:
                if accuracy_in_pct < 40:
                    accuracy_multiplier = -0.5
                else:
                    accuracy_multiplier = -0.3
            else:
                if accuracy_in_pct < 60:
                    accuracy_multiplier = 0
                else:
                    accuracy_multiplier = 0.5
    else:
        if accuracy_in_pct < 90:
            if accuracy_in_pct < 80:
                accuracy_multiplier = 1.5
            else:
                accuracy_multiplier = 3
        else:
            if accuracy_in_pct < 95:
                accuracy_multiplier = 4.5
            elif accuracy_in_pct < 100:
                accuracy_multiplier = 6.5
            else:
                accuracy_multiplier = 10

    # final calculations to determine payout
    ups_difference = final_ups - initial_ups

    multiplier = prediction_multiplier + time_multiplier + accuracy_multiplier
    winnings = int(amount * multiplier)

    open_account(user)
    bank_data = get_bank_data()

    if winnings > 0:
        await ctx.send(
            f"Hello {user.mention}! It's {time} later, and it has "
            f"{final_ups} upvotes right now! The difference is "
            f"{ups_difference} upvotes! You were {accuracy_in_pct}% accurate "
            f"and won {winnings} {'bedcoins' if winnings != 1 else 'bedcoin'}!"
        )
    elif winnings == 0:
        await ctx.send(
            f"Hello {user.mention}! It's {time} later, and it has "
            f"{final_ups} upvotes right now! The difference is "
            f"{ups_difference} upvotes! You were {accuracy_in_pct}% accurate "
            f"but won nothing."
        )
    else:
        await ctx.send(
            f"Hello {user.mention}! It's {time} later, and it has "
            f"{final_ups} upvotes right now! The difference is "
            f"{ups_difference} upvotes! You were {accuracy_in_pct}% accurate "
            f"and lost {abs(winnings)} "
            f"{'bedcoins' if abs(winnings) != 1 else 'bedcoin'}!"
        )

    bank_data[user]["balance"] += winnings
    bank_data[user]["active_bets"] -= 1
    bank_data[user]["mean_accuracy"] = calculate_mean_accuracy(
        bank_data[user]["mean_accuracy"],
        bank_data[user]["total_bets"],
        accuracy
    )
    bank_data[user]["total_bets"] += 1

    store_bank_data(bank_data)


@bot.command()
async def bets(ctx, user_attr=None):
    if not user_attr:
        user = ctx.author
    else:
        user = find_user(ctx, user_attr)
        if not user:
            await ctx.send("This user wasn't found!")

            return

    open_account(user)
    bank_data = get_bank_data()

    active_bets = bank_data[user]["active_bets"]

    await ctx.send(
        f"{'You' if user == ctx.author else f'**{str(user)}**'} currently "
        f"{'have' if user == ctx.author else 'has'} {active_bets} "
        f"{'bets' if active_bets != 1 else 'bet'} running!"
    )


@bot.command(aliases=["accuracy"])
async def accuracy_(ctx, user_attr=None):
    if not user_attr:
        user = ctx.author
    else:
        user = find_user(ctx, user_attr)
        if not user:
            await ctx.send("This user wasn't found!")

            return

    open_account(user)
    bank_data = get_bank_data()

    mean_accuracy = bank_data[user]["mean_accuracy"]

    if mean_accuracy:
        mean_accuracy_in_pct = mean_accuracy * 100
    else:
        mean_accuracy_in_pct = None

    total_bets = bank_data[user]["total_bets"]

    await ctx.send(
        f"**{str(user)}**'s mean accuracy: "
        f"{f'NaN' if not mean_accuracy_in_pct else f'{mean_accuracy_in_pct}%'}"
        f" (Total bets: {total_bets})"
    )


@bot.command(aliases=["baltop"])
async def balancetop(ctx, n=5):
    guild = ctx.guild

    bank_data = get_bank_data()

    # leaderboard is just sorted collection
    collection = {}
    leaderboard = {}

    for user in bank_data:
        if guild.get_member(user.id):
            balance = bank_data[user]["balance"]

            collection[user] = balance

    for user in sorted(collection, key=collection.get, reverse=True):
        leaderboard[user] = collection[user]

    embed = discord.Embed(
        title=f"Richest people on {str(guild)}:",
        description="Not on the list? Go bet on some posts!",
        color=0x96d35f
    )

    i = 1

    for user in leaderboard:
        embed.add_field(
            name=f"{i}. {str(user)}",
            value=f"{leaderboard[user]}",
            inline=False
        )

        if i == n:
            break
        else:
            i += 1

    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def changeprefix(ctx, prefix):
    with open('prefixes.json', 'r') as file:
        prefixes = json.load(file)

    prefixes[str(ctx.guild.id)] = prefix

    with open('prefixes.json', 'w') as file:
        json.dump(prefixes, file, indent=4)

    await ctx.send(f"You have changed the prefix to '{prefix}'!")


# error handling for commands
@upvotes.error
async def upvotes_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You must specify a Reddit post's URL!")


@downvotes.error
async def downvotes_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You must specify a Reddit post's URL!")


@daily.error
async def daily_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("You already claimed your daily reward today!")


@repeat.error
async def repeat_error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send("You must specify what to repeat!")


@balancetop.error
async def balancetop_error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send("That's not a valid argument!")


@bet.error
async def bet_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"You must specify arguments! Use: *{bot.command_prefix}bet "
            "[Reddit post link] [bet amount] [time (in s/m/h)] [predicted "
            "upvotes on that post after that time]* to bet."
        )
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("You have to wait a few seconds between bets!")


@gibcash.error
async def gibcash_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("You have to wait a few seconds!")


@changeprefix.error
async def changeprefix_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You must specify a prefix!")
