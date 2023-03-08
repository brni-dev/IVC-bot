import requests
import asyncio
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from random_user_agent.params import OperatingSystem
from discord.ext.commands import Bot
from discord import Game
from discord import Embed
from discord import Intents
from discord import Member
from json import dumps
from dotenv import load_dotenv
from os import getenv
from time import monotonic
from string import ascii_letters

load_dotenv()

READKEY=getenv('READKEY')
TOKEN=getenv('TOKEN')

user_agent_rotator = UserAgent(
    software_names=[SoftwareName.CHROME.value],
    operating_systems=[OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value],
    limit=None
)


PREFIX = "?!"
intents = Intents(guilds=True, guild_messages=True, messages=True)
intents.message_content=True
bot = Bot(command_prefix=PREFIX, help_command=None, intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print("active")
    await bot.change_presence(activity=Game(name=f"{PREFIX}help"))

@bot.command()
async def help(ctx):
    cmd_list=Embed(title="help", color=0x8c00ff)
    cmd_list.add_field(name="help", value=f"`{PREFIX}help`\nself explanatory", inline=False)
    cmd_list.add_field(name="mbti analysis", value=f"`{PREFIX}analyse @member [message limit]`\nfully analyse all of someones text messages to predict mbti",inline=False)

    await ctx.send(embed=cmd_list)

@bot.command()
async def analyse(ctx, member: Member, limit: int):
    REQUEST_LIMIT = 10
    TIME_PERIOD = 10

    # define a list to store the timestamps of recent requests
    recent_requests = []
    msg = await ctx.reply("analysing...")

    # rate limit solution
    now = monotonic()
    recent_requests.append(now)
    recent_requests = [t for t in recent_requests if t > now - TIME_PERIOD]
    if len(recent_requests) > REQUEST_LIMIT:
        delta = recent_requests[0] - (now - TIME_PERIOD)
        await asyncio.sleep(delta)

    # fetch messages
    total_messages = 0
    user_messages = []
    start_time = monotonic()
    last_update_time = start_time
    for channel in ctx.guild.text_channels:
        try:
            async for message in channel.history(limit=limit):
                # check if the message author in the channel history is equal to the mentioned member
                # also check if the first letter doesnt start with a special char (to remove command messages)
                if message.author == member and message.content[0] in " ".join(ascii_letters).split():
                    user_messages.append(message.content)
                    total_messages += 1
                    # calculate messages per second and estimated time left
                    time_elapsed = monotonic() - start_time
                    messages_per_second = total_messages / time_elapsed
                    messages_left = limit - total_messages
                    time_left = messages_left / messages_per_second
                    hours_left = time_left / 3600
                    # check if 30 seconds have elapsed since last update
                    current_time = monotonic()
                    if current_time - last_update_time >= 30:
                        last_update_time = current_time
                        # edit the message with the updated progress and estimated time left
                        await msg.edit(content=f"analysing...\n\n{total_messages} messages processed\n{messages_per_second:.2f} messages per second\nestimated time left: {hours_left:.2f} hour/s")
        except:
            continue

    
    # text combo
    text = str(" ".join(user_messages))

    # send the text to the analysis site
    api_url = 'https://api.uclassify.com/v1/g4mes543/myers-briggs-type-indicator-text-analyzer/classify'
    headers = {
        'User-Agent': user_agent_rotator.get_random_user_agent(),
        'Content-Type': 'application/json',
        'Authorization': 'Token ' + READKEY
    }
    data = dumps({'texts': [text]})
    response = requests.post(api_url, headers=headers, data=data)
    result = response.json()
    
    # sort the personality types based on their probability
    personality_types = sorted(result[0]['classification'], key=lambda x: x['p'], reverse=True)

    # build the response string
    response_str = "personality text analysis for {}: \n\n".format(member.display_name)
    for r in personality_types:
        response_str += "{}: {:.2%}\n".format(r['className'], r['p'])
    
    # edit the message with the final result and ping the message author
    await msg.edit(content=response_str)
    await msg.reply(content=ctx.author.mention)

bot.run(TOKEN)
