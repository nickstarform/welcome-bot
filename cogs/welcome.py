import asyncio
import discord
from discord.ext import commands
from discord.utils import snowflake_time
import random
import datetime


def check_staff(config, roles):
    return any([role.name.lower() in config.staff for role in roles])


def timediff(dt1, dt2):
    delta = dt2 - dt1 if dt2 > dt1 else dt1 - dt2
    micro = delta.microseconds
    micro += delta.seconds * 1e6
    micro += delta.days * 86400 * 1e6
    return micro / (1e6)


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_chan = self.bot.config.welcomer_chan # overflow (send welcome)
        self.welcome_prefix = self.bot.config.welcome_prefix
        self.welcome_suffix = self.bot.config.welcome_suffix
        self.welcome_repeat = self.bot.config.welcome_repeat
        self.check_roles = self.bot.config.check_roles
        self.exclude_roles = self.bot.config.exclude_roles
        self.welcome_on = True
        self.welcome_disable = self.bot.config.welcome_disable
        self.last_welcome = datetime.datetime(2004, 1, 1, 1, 1, 1)
        self.timer = self.bot.config.timer
        #self.loop = self.bot.loop.create_task(self.welcome_loop())
        self.mention = self.bot.config.mention
        super().__init__()


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            before_roles = list(map(lambda x: x.id, before.roles))
            if any([x in self.exclude_roles for x in before_roles]):
                return
            after_roles = list(map(lambda x: x.id, after.roles))
            if any([x in self.check_roles for x in after_roles]):
                channel = before.guild.get_channel(self.welcome_chan)
                await self.send_welcome(after, channel=channel)


    async def send_welcome(self, member, check: bool=False, channel = None):
        now = datetime.datetime.now()
        d = timediff(self.last_welcome, now)
        if not self.welcome_on and d > self.timer:
            self.welcome_on = not self.welcome_on
            self.bot.save_config()
        if self.welcome_on and not self.welcome_disable:
            self.last_welcome = now
            if d > 15:
                msg = random.choice(self.welcome_prefix) + random.choice(self.welcome_suffix)
            else:
                msg = random.choice(self.welcome_repeat)
            try:
                username = member.mention if self.mention else member.name
            except Exception as e:
                print(f'Cannot find user: {e}')
                return
            msg = msg.replace('$USER$', username).replace('$SERVER$', member.guild.name)
            if self.bot.config.testing and not check:
                bot_owner = self.bot.get_user(self.bot.config.bot_owner)
                if not bot_owner.dm_channel:
                    await bot_owner.create_dm()
                try:
                    channel = bot_owner.dm_channel
                except Exception as e:
                    print(f'Error getting dm welcome: {e}')
            elif check:
                msg = f"""***TESTING***
{msg}"""
            try:
                await channel.send(msg)
            except Exception as e:
                print(f'Error sending welcome: {e}')

    @commands.command()
    @commands.guild_only()
    async def welcome(self, ctx):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        await self.send_welcome(ctx.author, True, ctx.channel)

    @commands.group()
    @commands.guild_only()
    async def welcome_repeat(self, ctx):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('||'.join(self.welcome_repeat))
            return

    @welcome_repeat.command(name='add')
    async def _add_welcome_repeat(self, ctx, *, msg: str = ''):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_repeat.append(msg)
        self.welcome_repeat.append(msg)
        self.bot.save_config()

    @welcome_repeat.command(name='rem')
    async def _rem_welcome_repeat(self, ctx, *, msg: str = ''):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        try:
            ind = self.bot.config.welcome_repeat.index(msg)
            del self.welcome_repeat[ind]
            del self.bot.config.welcome_repeat[ind]
            self.bot.save_config()
        except Exception:
            pass

    @commands.group(aliases=['changewelcomeprefix',])
    @commands.guild_only()
    async def welcome_prefix(self, ctx):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('||'.join(self.welcome_prefix))
            return

    @welcome_prefix.command(name='add')
    async def _add_welcome_prefix(self, ctx, *, msg: str = ''):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_prefix.append(msg)
        self.welcome_prefix.append(msg)
        self.bot.save_config()

    @welcome_prefix.command(name='rem')
    async def _rem_welcome_prefix(self, ctx, *, msg: str = ''):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        try:
            ind = self.bot.config.welcome_prefix.index(msg)
            del self.welcome_prefix[ind]
            del self.bot.config.welcome_prefix[ind]
            self.bot.save_config()
        except Exception:
            pass

    @commands.group(aliases=['changewelcomesuffix',])
    @commands.guild_only()
    async def welcome_suffix(self, ctx):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('||'.join(self.welcome_suffix))
            return

    @welcome_suffix.command(name='add')
    async def _add_welcome_suffix(self, ctx, *, msg: str = ''):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_suffix.append(msg)
        self.welcome_suffix.append(msg)
        self.bot.save_config()

    @welcome_suffix.command(name='rem')
    async def _rem_welcome_suffix(self, ctx, *, msg: str = ''):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        try:
            ind = self.bot.config.welcome_suffix.index(msg)
            del self.welcome_suffix[ind]
            del self.bot.config.welcome_suffix[ind]
            self.bot.save_config()
        except Exception:
            pass

    @commands.command(aliases=['changewelcomechannel'])
    @commands.guild_only()
    async def change_welcome_channel(self, ctx, *, chan):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        chan = chan.strip(' ')
        if chan == '':
            return
        chan_id = int(filter(str.isdigit, chan))
        if chan_id == '':
            try:
                chan = [f for f in ctx.message.guild.channels if f.name.lower() == chan]
                if len(chan) == 0:
                    return
                chan_id = chan[0].id
            except Exception:
                return
        try:
            chan = ctx.message.guild.get_channel(chan_id)
            if not chan:
                return
        except Exception as e:
            return
        self.welcome_channel = chan.id
        self.bot.save_config()
        await ctx.send(f'Welcome channel set to: {chan.mention}', delete_after=10)
        pass

    @commands.command(alias=['togglemention'])
    @commands.guild_only()
    async def toggle_mention(self, ctx):
        if not ctx.author.id == self.bot.config.bot_owner:
            return
        self.mention = not self.mention 
        self.bot.save_config()
        await ctx.send(f'Welcome mention toggled to: {self.mention}')
        """
        if not self.welcome_disable and not self.welcome_on and self.loop.done():
            self.loop = self.bot.loop.create_task(self.welcome_loop())
        self.loop.current_task().cancel()
        """
        pass

    @commands.command(alias=['welcometimer'])
    @commands.guild_only()
    async def welcome_timer(self, ctx, timer: int = -1):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if timer < 0:
            await ctx.send(f'Timer set to {self.timer}s')
            return
        self.timer = timer
        self.bot.config.timer = timer
        self.bot.save_config()
        await ctx.send(f'Timer set to {timer}s')
        pass

    @commands.command(alias=['test'])
    async def toggle_test(self, ctx):
        if not ctx.author.id == self.bot.config.bot_owner:
            return
        self.bot.config.testing = not self.bot.config.testing
        self.bot.save_config()
        await ctx.send(f'Welcome message toggled to test mode: {self.bot.config.testing}')
        """
        if not self.welcome_disable and not self.welcome_on and self.loop.done():
            self.loop = self.bot.loop.create_task(self.welcome_loop())
        self.loop.current_task().cancel()
        """
        pass

    @commands.command(alias=['welcometoggle'])
    @commands.guild_only()
    async def toggle_welcomer(self, ctx, disable: bool = False):
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.welcome_disable = disable
        self.welcome_on = not self.welcome_on
        self.bot.save_config()
        now = datetime.datetime.now()
        self.last_welcome = now
        await ctx.send(f'Welcome message toggled: {self.welcome_on}')
        """
        if not self.welcome_disable and not self.welcome_on and self.loop.done():
            self.loop = self.bot.loop.create_task(self.welcome_loop())
        self.loop.current_task().cancel()
        """
        pass

    async def welcome_loop(self):
        try:
            await self.bot.wait_until_ready()
            coros = []
        except Exception:
            return
        coros.append(await self.__welcome_timer())
        await asyncio.gather(*coros)

    async def __welcome_checker(self):
        breaker = False
        while not breaker:
            breaker = self.welcome_on == True
        pass

    async def __welcome_sleep(self):
        await asyncio.sleep(self.timer)
        self.welcome_on = True
        self.bot.save_config()
        pass

    async def __welcome_timer(self):
        tasks = [self.__welcome_checker, self.__welcome_sleep]
        f, uf = self.bot.loop.run_until_complete(asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED))
        pass


def setup(bot):
    bot.add_cog(Welcome(bot))
    print('Loaded Welcome')

