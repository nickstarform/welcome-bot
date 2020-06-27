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


def timediff(dt1, dt2):
    delta = dt2 - dt1 if dt2 > dt1 else dt1 - dt2
    micro = delta.microseconds
    micro += delta.seconds * 1e6
    micro += delta.days * 86400 * 1e6
    return micro / (1e6)


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcomer_on = True
        self.short_counter = 1e9  # number of non bot messages
        self.long_counter = 1e9  # number of short welcomes
        self.last_welcome = datetime.datetime(2004, 1, 1, 1, 1, 1)
        super().__init__()


    @commands.Cog.listener()
    async def on_message(self, ctx):
        if (ctx.channel.id != self.bot.config.welcomer_chan) or ctx.author.bot:
            return
        self.short_counter += 1


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            before_roles = list(map(lambda x: x.id, before.roles))
            after_roles = list(map(lambda x: x.id, after.roles))
            diff_roles = set(after_roles) - set(before_roles)
            if any([role in self.bot.config.exclude_roles for role in after_roles]):
                return
            if any([role in self.bot.config.exclude_roles for role in before_roles]):
                return
            if any([x in self.bot.config.check_roles for x in after_roles]) and any([x in self.bot.config.check_roles for x in before_roles]):
                return
            if any([x in self.bot.config.check_roles for x in diff_roles]):
                channel = before.guild.get_channel(self.bot.config.welcomer_chan)
                await self.send_welcome(after, channel=channel, guild=before.guild)


    async def send_welcome(self, member, check: bool=False, channel = None, guild = None):
        now = datetime.datetime.now()
        d = timediff(self.last_welcome, now)
        if not self.welcomer_on and d > self.bot.config.timer:
            self.welcomer_on = not self.welcomer_on
            self.bot.save_config()
        if self.welcomer_on and not self.bot.config.welcome_disable:
            self.last_welcome = now
            if (self.short_counter > self.bot.config.welcome_message_frequency) or (self.long_counter > self.bot.config.welcome_message_long_frequency) :
                prefix = random.choice(self.bot.config.welcome_prefix)
                suffix = random.choice(self.bot.config.welcome_suffix)
                prefix = prefix if self.bot.config.welcome_prefix_on else ''
                suffix = suffix if self.bot.config.welcome_suffix_on else ''
                msg = ''.join([prefix, suffix])
                self.long_counter = 0
            else:
                msg = random.choice(self.bot.config.welcome_repeat)
                self.long_counter += 1
            try:
                username = member.mention if self.bot.config.mention else member.name
            except Exception as e:
                print(f'Cannot find user: {e}')
            msg = msg.replace('$USER$', username).replace('$SERVER$', member.guild.name)
            if '<#' in msg:
                regex = r'(\<\#)([0-9]*)(\>)'
                matches = re.finditer(regex, msg, re.MULTILINE)
                for mnum, match in enumerate(matches, start=1):
                    try:
                        mention_channel = guild.get_channel(int(match.group().strip('<#').strip('>')))
                        msg = f'{msg[:match.start()]}{mention_channel.mention}{msg[match.end():]}'.replace('\\', '')
                    except Exception:
                        continue
            if '<:' in msg:
                regex = r'(\<\:)(.*)(\:)([0-9]*)(\>)'
                matches = re.finditer(regex, msg, re.MULTILINE)
                emojis = dict([[e.id, e] for e in guild.emojis])
                for mnum, match in enumerate(matches, start=1):
                    try:
                        emoji = int(match.group().split(':')[-1].strip('>'))
                        emoji = emojis[emoji]
                        if not emoji.is_usable():
                            continue
                        msg = f'{msg[:match.start()]}{emoji}{msg[match.end():]}'.replace('\\', '')
                    except Exception:
                        continue
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
            self.short_counter = 0

    @commands.command()
    @commands.guild_only()
    async def config(self, ctx):
        """Check the current config.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        embed = discord.Embed(title='Configuration',
                              type='rich', desc='',
                              color=0xAC91F5)
        for i, c in ({
                     'clear_channel': self.bot.config.clear_channel,
                     'welcomer_chan': self.bot.config.welcomer_chan,
                     'timer': self.bot.config.timer,
                     'welcome_time_frequency': self.bot.config.welcome_time_frequency,
                     'welcome_message_frequency': self.bot.config.welcome_message_frequency,
                     'welcome_message_long_frequency': self.bot.config.welcome_message_long_frequency,
                     'mention': self.bot.config.mention,
                     'welcome_prefix_on': self.bot.config.welcome_prefix_on,
                     'welcome_prefix': self.bot.config.welcome_prefix,
                     'welcome_suffix_on': self.bot.config.welcome_suffix_on,
                     'welcome_suffix': self.bot.config.welcome_suffix,
                     'welcome_repeat': self.bot.config.welcome_repeat,
                     'check_roles': self.bot.config.check_roles,
                     'exclude_roles': self.bot.config.exclude_roles,
                     }).items():
            embed.add_field(name=i,
                            value=c)
        await ctx.channel.send(embed=embed)
        await self.send_welcome(ctx.author, True, ctx.channel, guild=ctx.channel.guild)


    @commands.command()
    @commands.guild_only()
    async def welcome(self, ctx):
        """Test welcome message.

        Welcome message is constructed as such: random(prefix) + random(suffix)
            unless the message count frequency and time frequency both fail
            then it is random(repeat)

        Prefix, suffix, repeat can have special strings $USER$, $SERVER$,
            and <@channel_id> and the bot will try to grab the corresponding
            values automatically.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        await self.send_welcome(ctx.author, True, ctx.channel, guild=ctx.channel.guild)

    @commands.group()
    @commands.guild_only()
    async def welcome_repeat(self, ctx):
        """Short welcome message.

        This message is used if the message frequency and message time
            frequency both don't trigger AND if messages aren't being rolled.

        Prefix, suffix, repeat can have special strings $USER$, $SERVER$,
            and <@channel_id> and the bot will try to grab the corresponding
            values automatically.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('|'.join(self.bot.config.welcome_repeat))
            return

    @welcome_repeat.command(name='add')
    async def _add_welcome_repeat(self, ctx, *, msg: str = ''):
        """Add to the list of short welcome messages.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_repeat.append(msg)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])

    @welcome_repeat.command(name='rem')
    async def _rem_welcome_repeat(self, ctx, *, msg: str = ''):
        """Remove from the list of short welcome messages.

        Must match the string to remove exactly as shown.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        try:
            ind = self.bot.config.welcome_repeat.index(msg)
            del self.bot.config.welcome_repeat[ind]
            self.bot.save_config()
            await add_react(ctx.message, reacts=['yes'])
        except Exception:
            pass

    @commands.group(aliases=['changewelcomeprefix',])
    @commands.guild_only()
    async def welcome_prefix(self, ctx):
        """Prefix to the welcome message.

        Prefix, suffix, repeat can have special strings $USER$, $SERVER$,
            and <@channel_id> and the bot will try to grab the corresponding
            values automatically.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('|'.join(self.bot.config.welcome_prefix))
            return

    @welcome_prefix.command(name='add')
    async def _add_welcome_prefix(self, ctx, *, msg: str = ''):
        """Add a prefix to the welcome message.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_prefix.append(msg)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])

    @welcome_prefix.command(name='rem')
    async def _rem_welcome_prefix(self, ctx, *, msg: str = ''):
        """Remove a to the welcome message.

        Message must match exactly to the prefix shown.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        try:
            ind = self.bot.config.welcome_prefix.index(msg)
            del self.bot.config.welcome_prefix[ind]
            self.bot.save_config()
            await add_react(ctx.message, reacts=['yes'])
        except Exception:
            pass

    @welcome_prefix.command(name='toggle')
    async def _toggle_welcome_prefix(self, ctx):
        """Toggle prefix on and off.

        The react will say what the new status is
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_prefix_on = not self.bot.config.welcome_prefix_on
        self.bot.save_config()
        await add_react(ctx.message, reacts=[self.bot.config.welcome_prefix_on])

    @commands.group(aliases=['changewelcomesuffix',])
    @commands.guild_only()
    async def welcome_suffix(self, ctx):
        """Suffix to the welcome message.

        Prefix, suffix, repeat can have special strings $USER$, $SERVER$,
            and <@channel_id> and the bot will try to grab the corresponding
            values automatically.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('|'.join(self.bot.config.welcome_suffix))
            return

    @welcome_suffix.command(name='add')
    async def _add_welcome_suffix(self, ctx, *, msg: str = ''):
        """Add a suffix to the welcome message.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_suffix.append(msg)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])

    @welcome_suffix.command(name='rem')
    async def _rem_welcome_suffix(self, ctx, *, msg: str = ''):
        """Remove a suffix to the welcome message.

        Message must match exactly to the string shown.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        try:
            ind = self.bot.config.welcome_suffix.index(msg)
            del self.bot.config.welcome_suffix[ind]
            self.bot.save_config()
            await add_react(ctx.message, reacts=['yes'])
        except Exception:
            pass

    @welcome_suffix.command(name='toggle')
    async def _toggle_welcome_suffix(self, ctx):
        """Toggle the suffix on and off.

        The react will show what the new status is.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_suffix_on = not self.bot.config.welcome_suffix_on
        self.bot.save_config()
        await add_react(ctx.message, reacts=[self.bot.config.welcome_suffix_on])

    @commands.group()
    @commands.guild_only()
    async def exclude_roles(self, ctx):
        """Exclusionary roles to welcome.

        If the user has any roles in this list, they will not be welcomed
            (by the bot at least).
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('|'.join(map(str, self.bot.config.exclude_roles)))
            return

    @exclude_roles.command(name='add')
    async def _exclude_roles_add(self, ctx, *, roles):
        """Add to the exlusionary roles list.

        These can be role mentions or just their ids. Separate them by a space
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        roles = roles.split(' ')
        roles = [r for r in roles if r.strip(' ') != '']
        if len(roles) == 0:
            return
        role_ids = [int(''.join([r for r in role if str.isdigit(r)])) for role in roles]
        self.bot.config.exclude_roles.extend(role_ids)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        pass

    @exclude_roles.command(name='rem')
    async def _exclude_roles_rem(self, ctx, *, roles):
        """Remove from the exlusionary roles list.

        These can be role mentions or just their ids. Separate them by a space
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        roles = roles.split(' ')
        roles = [r for r in roles if r.strip(' ') != '']
        if len(roles) == 0:
            return
        role_ids = [int(''.join([r for r in role if str.isdigit(r)])) for role in roles]
        fail = []
        for role_id in role_ids:
            try:
                idx = self.bot.config.exclude_roles.index(role_id)
                del self.bot.config.exclude_roles[idx]
            except Exception:
                fail.append(role_id)
                continue
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        await ctx.send(f'Removed roles from exclude list. Failed on: {fail}')
        pass

    @commands.group()
    @commands.guild_only()
    async def check_roles(self, ctx):
        """Roles to check for welcoming a user.

        If a user is in any of these roles AND NOT in more than one of these
            roles AND NOT in the exlusion list, welcome the user.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if ctx.invoked_subcommand is None:
            await ctx.send('|'.join(map(str, self.bot.config.check_roles)))
            return

    @check_roles.command(name='add')
    async def _check_roles_add(self, ctx, *, roles):
        """Add to the check roles list.

        These can be role mentions or just their ids. Separate them by a space
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        roles = roles.split(' ')
        roles = [r for r in roles if r.strip(' ') != '']
        if len(roles) == 0:
            return
        role_ids = [int(''.join([r for r in role if str.isdigit(r)])) for role in roles]
        self.bot.config.check_roles.extend(role_ids)
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        await ctx.send(f'Added roles to check list')
        pass

    @check_roles.command(name='rem')
    async def _check_roles_rem(self, ctx, *, roles):
        """Remove from the roles list.

        These can be role mentions or just their ids. Separate them by a space
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        roles = roles.split(' ')
        roles = [r for r in roles if r.strip(' ') != '']
        if len(roles) == 0:
            return
        role_ids = [int(''.join([r for r in role if str.isdigit(r)])) for role in roles]
        fail = []
        for role_id in role_ids:
            try:
                idx = self.bot.config.check_roles.index(role_id)
                del self.bot.config.check_roles[idx]
            except Exception:
                fail.append(role_id)
                continue
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        await ctx.send(f'Removed roles from check list. Failed on: {fail}')
        pass

    @commands.command(aliases=['changewelcomechannel'])
    @commands.guild_only()
    async def change_welcome_channel(self, ctx, *, chan):
        """The channel to welcome to.

        Give a channel mention or id. Can only be a single channel. The bot
            must have read, send, read history, and react perms for the channel.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        chan = chan.strip(' ')
        if chan == '':
            return
        chan_id = [int(''.join([r for r in role if str.isdigit(r)])) for role in roles]
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
        self.bot.config.welcomer_channel = chan.id
        self.bot.save_config()
        await add_react(ctx.message, reacts=['yes'])
        await ctx.send(f'Welcome channel set to: {chan.mention}', delete_after=10)
        pass

    @commands.command(alias=['resetcounters'])
    @commands.guild_only()
    async def reset_counter(self, ctx):
        """Reset all message counters.

        This will force reset all message counters for the bot including, long
            short, and timing based counters.
        """
        if not ctx.author.id == self.bot.config.bot_owner:
            return
        self.long_counter = 1e9
        self.short_counter = 1e9
        self.last_welcome = datetime.datetime(2004, 1, 1, 1, 1, 1)
        await add_react(ctx.message, reacts=['yes'])
        pass

    @commands.command(alias=['togglemention'])
    @commands.guild_only()
    async def toggle_mention(self, ctx):
        """Toggle mentioning the user on and off.

        If set to off, will use the username instead of a mention.
        The react will be what the new status is.
        """
        if not ctx.author.id == self.bot.config.bot_owner:
            return
        self.bot.config.mention = not self.bot.config.mention 
        self.bot.save_config()
        await add_react(ctx.message, reacts=[self.bot.config.mention])
        pass

    @commands.command(alias=['welcometimefrequency'])
    @commands.guild_only()
    async def welcome_time_frequency(self, ctx, timer: int = 15):
        """Set the welcome message count frequency.

        The bot will wait for at least #s of time before doing 
            another long form reponse.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if timer < 0:
            await ctx.send(f'Time frequency set to {self.bot.config.welcome_time_frequency}s')
            return
        self.bot.config.welcome_time_frequency = timer
        self.bot.save_config()
        await ctx.send(f'Timer set to {timer}s')
        pass

    @commands.command(alias=['welcomemessagelongfrequency'])
    @commands.guild_only()
    async def welcome_message_long_frequency(self, ctx, msg: int = -1):
        """Set the welcome message count frequency for long welcomes.

        An additional 
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if msg < 0:
            await ctx.send(f'Message freq set to {self.bot.config.welcome_message_long_frequency}')
            return
        self.bot.config.welcome_message_long_frequency = msg
        self.bot.save_config()
        await ctx.send(f'Message freq set to {msg}')
        pass

    @commands.command(alias=['welcomemessagefrequency'])
    @commands.guild_only()
    async def welcome_message_frequency(self, ctx, msg: int = -1):
        """Set the welcome message count frequency.

        The bot will wait for at least # of messages to be sent before doing 
            another long form reponse.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if msg < 0:
            await ctx.send(f'Message freq set to {self.bot.config.welcome_message_frequency}')
            return
        self.bot.config.welcome_message_frequency = msg
        self.bot.save_config()
        await ctx.send(f'Message freq set to {msg}')
        pass

    @commands.command(alias=['welcometimer'])
    @commands.guild_only()
    async def welcome_timer(self, ctx, timer: int = -1):
        """Set the welcome_timer.

        If the bot is temporarily disabled, it will wait for `timer` amount of
            time before auto turning back on again.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        if timer < 0:
            await ctx.send(f'Timer set to {self.bot.config.timer}s')
            return
        self.bot.config.timer = timer
        self.bot.save_config()
        await ctx.send(f'Timer set to {timer}s')
        pass

    @commands.command(alias=['test'])
    async def toggle_test(self, ctx):
        """BOT OWNER ONLY. Toggle the testing.

        The react will be what the new status is.
        """
        if not ctx.author.id == self.bot.config.bot_owner:
            return
        self.bot.config.testing = not self.bot.config.testing
        self.bot.save_config()
        await add_react(ctx.message, reacts=[self.bot.config.testing])
        pass

    @commands.command(alias=['welcometoggle'])
    @commands.guild_only()
    async def toggle_welcomer(self, ctx, disable: bool = False):
        """Toggle the welcome bot on and off.

        If no argument given, this is a temporary turn off given by the
            `welcome_timer`. If argument `True` is given, will disable the bot
            indefinitely
        The react will be what the new status is.
        """
        if not check_staff(self.bot.config, ctx.author.roles):
            return
        self.bot.config.welcome_disable = disable
        self.welcomer_on = not self.welcomer_on
        self.bot.save_config()
        now = datetime.datetime.now()
        self.last_welcome = now
        status = self.bot.config.welcome_disable
        status = not (status if status else not self.welcomer_on)
        await add_react(ctx.message, reacts=[status])
        pass


def setup(bot):
    bot.add_cog(Welcome(bot))
    print('Loaded Welcome')

