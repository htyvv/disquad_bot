import json
import logging
import os
from pathlib import Path
import platform
import random
import sys

import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

from database import DatabaseManager

# 현재 스크립트의 디렉토리 경로를 Path 객체로 설정
ROOT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = ROOT_DIR / "config.json"

if not CONFIG_PATH.is_file():
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open(CONFIG_PATH) as file:
        config = json.load(file)

"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


Default Intents:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True # `message_content` is required to get the content of the messages
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

Privileged Intents (Needs to be enabled on developer portal of Discord), please use them only if you need them:
intents.members = True
intents.message_content = True
intents.presences = True
"""
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# Setup both of the loggers
class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(config["prefix"]),
            intents=intents,
            help_command=None,
            description="이 봇은 롤 내전 일정 관리 및 경기 결과 저장과 MVP 투표 기능을 제공합니다."
        )
        """
        This creates custom bot variables so that we can access these variables in cogs more easily.

        For example, The config is available using the following code:
        - self.config # In this class
        - bot.config # In this file
        - self.bot.config # In cogs
        """
        self.logger = logger
        self.config = config
        self.database = None
        self.ROOT_DIR = ROOT_DIR
        self.DB_FILE_NAME = "database.db"
        self.SCHEMA_FILE_NAME = "schema.sql"
        self.DB_PATH = self.ROOT_DIR / "database" / self.DB_FILE_NAME
        self.SCHEMA_PATH = self.ROOT_DIR / "database" / self.SCHEMA_FILE_NAME
        self.default_activity = discord.CustomActivity(name="✋ DisQuadBot by 허태")

    async def init_db(self) -> None:
        async with aiosqlite.connect(self.DB_PATH) as db:
            with open(self.SCHEMA_PATH, encoding='utf-8') as file:
                await db.executescript(file.read())
            await db.commit()
            
    async def init_player_stats(self) -> None:
        for guild in self.guilds:
            for member in guild.members:
                # 데이터베이스에서 해당 유저의 정보가 있는지 확인
                existing_user = await self.database.get_user_id(member.id)
                
                # 정보가 없으면 추가
                if existing_user is None:
                    await self.database.add_user(member.id, member.display_name)

    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        cogs_dir = self.ROOT_DIR / "cogs"
        for file_path in cogs_dir.iterdir():
            if file_path.suffix == ".py":
                cog_name = file_path.stem
                try:
                    await self.load_extension(f"cogs.{cog_name}")
                    self.logger.info(f"Loaded extension '{cog_name}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {cog_name}\n❌ {exception}"
                    )

    # @tasks.loop(minutes=1.0)
    # async def status_task(self) -> None:
    #     """
    #     Setup the game status task of the bot.
    #     """
    #     statuses = ["with you!", "with Krypton!", "with humans!"]
    #     await self.change_presence(activity=discord.Game(random.choice(statuses)))

    # @status_task.before_loop
    # async def before_status_task(self) -> None:
    #     await self.wait_until_ready()

    # @tasks.loop(minutes=30.0)
    # async def update_nicknames(self) -> None:
    #     for guild in self.guilds:
    #         for member in guild.members:
    #             # 데이터베이스에서 닉네임 업데이트
    #             async with self.database.connection.cursor() as cursor:
    #                 await cursor.execute(
    #                     'UPDATE player_stats SET user_name = ? WHERE user_id = ?',
    #                     (member.display_name, member.id)
    #                 )
    #             await self.database.connection.commit()

    # @update_nicknames.before_loop
    # async def before_update_nicknames(self):
    #     await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        This will just be executed when the bot starts the first time.
        """
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        await self.init_db()
        await self.load_cogs()
        # self.status_task.start()
        self.database = DatabaseManager(
            connection=await aiosqlite.connect(self.DB_PATH)
        )
        # self.update_nicknames.start()
        await self.tree.sync()
        await self.set_avatar("asset/avatar.png") 

    # async def update_presence(self, context: Context) -> None:
    #     """
    #     명령어에 따라 봇 상태 메시지 자동 업데이트
    #     """
    #     command = context.command.qualified_name
    #     command2activity = {
    #         "내전일정생성": discord.CustomActivity(name="📝 내전 참가 투표 중"),
    #         "팀배정": discord.CustomActivity(name="🔥 팀 분배 완료"),
    #         "즉흥팀배정": discord.CustomActivity(name="🔥 팀 분배 완료"),
    #         "경기결과": discord.CustomActivity(name="📅 일정생성 대기 중"),
    #     }
        
    #     current_activity = command2activity.get(command)
    #     if current_activity:
    #         await self.change_presence(activity=current_activity)
        
    async def on_ready(self) -> None:
        await self.init_player_stats()
        self.logger.info(f"{self.user.name} has connected to Discord!")
        await self.change_presence(activity=self.default_activity)

    async def on_message(self, message: discord.Message) -> None:
        """
        The code in this event is executed every time someone sends a message, with or without the prefix

        :param message: The message that was sent.
        """
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )
        # await self.update_presence(context)

    async def on_command_error(self, context: Context, error) -> None:
        """
        The code in this event is executed every time a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                description="You are not the owner of the bot!", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                # We need to capitalize because the command arguments have no capital letter in the code and they are the first word in the error message.
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error

    async def set_avatar(self, avatar_path: str) -> None:
        """Set the bot's avatar."""
        with open(avatar_path, 'rb') as avatar_file:
            avatar_data = avatar_file.read()
            await self.user.edit(avatar=avatar_data)
            self.logger.info("Avatar has been updated.")


# .env 파일 경로를 Path 객체로 처리
env_path = ROOT_DIR / ".env"
load_dotenv(env_path)

bot = DiscordBot()
bot.run(os.getenv("TOKEN"))
