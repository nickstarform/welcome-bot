import asyncio
import discord
from discord.ext import commands

mains = {
    'clover': 248674295394467850,
    'member': 363797042172264460,
}
exproles = {
    375012312773558283: 1,
    385928334426505246: 1,
    375012268930498561: 1,
    375012329701638145: 1,
    375012282897399809: 1}
key = 375012340401176586
reactions = {
    'yes': r'✅',
    'no': r'❌',
    True: r'🔔',
    False: r'🔕',}


async def add_react(message, reacts: list=[]):
    for react in reacts:
        if react not in reactions:
            continue
        await message.add_reaction(reactions[react])


class Reset(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_users = {}
        self.reset = False
        super().__init__()

    @commands.group()
    @commands.guild_only()
    async def resettoggle(self, ctx):
        """Short welcome message.

        This message is used if the message frequency and message time
            frequency both don't trigger AND if messages aren't being rolled.

        Prefix, suffix, repeat can have special strings $USER$, $SERVER$,
            and <@channel_id> and the bot will try to grab the corresponding
            values automatically.
        """
        if not ctx.author.id == self.bot.config.bot_owner:
            return
        self.reset = not self.reset
        await add_react(ctx.message, reacts=[self.reset])

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if not self.reset:
            return
        if not ctx.guild:
            return
        if ctx.author.id in self.reset_users:
            return
        self.reset_users[ctx.author.id] = 1
        roles = dict([[x.id, x] for x in ctx.author.roles])
        rolelen = len(roles)
        if any([mains[x] in roles for x in mains]):
            return
        for rid in exproles:
            if rid in roles:
                del roles[rid]
        if rolelen != len(roles):
            try:
                await ctx.author.edit(roles=[roles[r] for r in roles])
            except Exception as e:
                print('Error editing roles:', e)
            try:
                await add_react(ctx, reacts=['yes'])
            except Exception as e:
                print('Error reacting:', e)
        pass


def setup(bot):
    bot.add_cog(Reset(bot))
    print('Loaded Reset')
