import discord 
from discord.ext import commands
import logging 
from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

secret_role = "Gay"

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event 
async def on_ready():
    print(f'We have logged in as {bot.user.name}')

@bot.command()
async def logout(ctx):
    await ctx.send("Logging out!")
    await bot.close()

# @bot.event 
# async def on_message(message):
#     if message.author == bot.user:
#         return 

#     # if "shit" in message.content.lower():
#     #     await message.delete()
#     #     await message.channel.send(f"{message.author.mention}, please watch your language!")
#     # await bot.process_commands(message)


@bot.command() 
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.mention}!')

@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name = secret_role)
    if role: 
        if role in ctx.author.roles:
            await ctx.send(f'You already have the role {secret_role}, {ctx.author.mention}!')
            return
        await ctx.author.add_roles(role)
        await ctx.send(f'Role {secret_role} has been assigned to {ctx.author.mention}')
    else:
        await ctx.send(f'Role does not exist.')
    
@bot.command()
async def remove(ctx):
    role = discord.utils.get(ctx.guild.roles, name = secret_role)
    if role in ctx.author.roles:
        await ctx.author.remove_roles(role)
        await ctx.send(f'Role {secret_role} has been removed from {ctx.author.mention}')
    else:
        await ctx.send(f'yo dumbass never had the role stupid.')



bot.run(token, log_handler= handler, log_level=logging.DEBUG)
