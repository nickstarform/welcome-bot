import asyncio
import discord
from discord.ext import commands
from discord.utils import snowflake_time
import random
import datetime
import re

reactions = {
    'yes': r'✅',
    'no': r'❌',
    True: r'🔔',
    False: r'🔕',
}


async def add_react(message, reacts: list=[]):
    for react in reacts:
        if react not in reactions:
            continue
        await message.add_reaction(reactions[react])


def check_staff(config, roles):
    return any([role.name.lower() in config.staff for role in roles])


def parse(msg, regexes):
    for regex in regexes:
        search = re.search(regex, msg)
        if search:
            print(search)
            return True
    return False


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.guild is None:
            return
        if self.bot.config.filter_on and parse(ctx.clean_content, self.bot.config.regex):
            self.bot.logger.info(f'Filtered message {ctx}')
            await ctx.delete()

    @commands.command()
    @commands.guild_only()
    async def filter(self, ctx):
        """Check the current config.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        embed = discord.Embed(title='Filter Config',
                              type='rich', desc='',
                              color=0xAC91F5)
        for i, c in ({
                     'Filter Enabled?': self.bot.config.filter_on,
                     'Filters': self.bot.config.regex,
                     }).items():
            embed.add_field(name=i,
                            value=c)
        await ctx.channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def toggle_filter(self, ctx, disable: bool = False):
        """Toggle the filter bot on and off.

        The react will be what the new status is.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.filter_on = not self.bot.config.filter_on
        self.bot.save_config()
        await add_react(ctx.message, reacts=[self.bot.config.filter_on ])
        pass

    @commands.command()
    @commands.guild_only()
    async def add_filter_regex(self, ctx, *, regex: str):
        """Toggle the filter bot on and off.

        The react will be what the new status is.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if not await confirm(ctx, f'You are enabling `{regex}`.', timeout=25):
            return
        self.bot.config.regex.append(regex)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        pass

    @commands.command()
    @commands.guild_only()
    async def rem_filter_regex(self, ctx, regex: int = -1):
        """Remove a regex filter by index.

        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        content = '`' + '`\n`'.join([f"{i}: {r}"for i, r in enumerate(self.bot.config.regex)]) + '`'
        res = await ctx.send(f"""The following regexes are in effect:
            {content}
            Rerun the command with the index to remove.""")
        if regex == -1:
            return
        if regex != -1 and not await confirm(ctx, f'You are removing `{self.bot.config.regex[regex]}`.', timeout=25):
            return
        try:
            del self.bot.config.regex[regex]
        except Exception as e:
            self.bot.logger.warning(e)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        pass

def setup(bot):
    bot.add_cog(Filter(bot))
    print('Loaded Filter')



async def confirm(ctx: commands.Context, message: str, timeout: int):
    """Generic confirmation embedder.

    Serves as a confirm/deny embed builder with a Xs timeout

    Parameters
    ----------
    ctx: :func: commands.Context
        the context command object
    message: str
        the message to display
    timeout: int
        the timeout in seconds before cancel

    Returns
    -------
    bool
        success true false
    """
    confirmdialog = f'\nAttempting to **{ctx.command}**:\n'\
                    f'{message}'\
                    f'\n➡️ Type `confirm` to **{ctx.command}**'\
                    ' or literally anything else to cancel.'\
                    f'\n\n**You have {timeout}s...**'
    embed = discord.Embed(title=r'❗ Confirmation Request ❗',
                            description=confirmdialog, color=0x9ED031)
    embed.set_footer(text=datetime.datetime.now())
    request = await ctx.send(embed=embed, delete_after=timeout)
    try:
        message = await ctx.bot.wait_for("message",
                                         timeout=timeout,
                                         check=lambda message:
                                         message.author == ctx.message.author)
    except asyncio.TimeoutError:
        try:
            await respond(ctx, False)
        except Exception:
            pass
        return False
    try:
        await respond(ctx, message.content.lower() == 'confirm')
        await request.delete()
        await message.delete()
    except Exception as e:
        print(f'Error in deleting message: {e}')
    return message.content.lower() == 'confirm'


async def respond(ctx: commands.Context, status: bool, message: discord.Message=None):
    """Respond/react to message.

    Parameters
    ----------
    ctx: :func: commands.Context
        the context command object
    status: bool
        status to react with

    Returns
    -------
    bool
        success true false
    """
    try:
        if status:
            if not isinstance(message, type(None)):
                await message.add_reaction(r'✅')
            else:
                await ctx.message.add_reaction(r'✅')
        else:
            if not isinstance(message, type(None)):
                await message.add_reaction(r'❌')
            else:
                await ctx.message.add_reaction(r'❌')
        return True
    except Exception as e:
        print(f'Error in responding to message message: {e}')
        return False
        pass
