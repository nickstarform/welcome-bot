import asyncio
import discord
import datetime
import string
import time
from discord.ext import commands
import os, glob
from sys import exit, version
import argparse
from asyncio import get_event_loop
from logging import Formatter, INFO, StreamHandler, getLogger
import pickle
import json
import importlib

__cwd__ = os.getcwd()
__version__ = float(version[:3])

print(f'Python Version: {__version__}, CWD: {__cwd__}')


class Config:
    def __init__(self, inp):
        self.base = dir(self)
        if isinstance(inp, dict):
            for key, value in inp.items():
                setattr(self, key, value)
        else:
            for key in dir(inp):
                if '__' not in key and key not in self.base:
                    setattr(self, key, getattr(inp, key))

    def to_dict(self):
        ret = {}
        for key in dir(self):
            if '__' not in key and key not in self.base:
                val = getattr(self, key)
                ret[key] = val if not isinstance(val, set) else list(val)
        return ret


def loader(basename):
    basename = basename.strip('.pkl').strip('.pickle')
    assert '.py' not in basename
    if '/' not in basename:
        basename = __cwd__ + '/' + basename
    listoffiles = glob.glob(f'{basename}.p*k*')
    fname = max(listoffiles, key=os.path.getctime)
    print(f'Running on file: {fname}')

    try:
        with open(fname, 'rb') as f:
            cf = pickle.load(f)
        cf['filename'] = basename
        save_py(basename, cf)
        return Config(cf)
    except Exception as e:
        print(f'Error loading pickle. Try following the example and then use refreshpickle.py to make the pickle file: {e}')
        return


def save_pkl(basename, cf):
    with open(basename + '.pickle', 'wb') as f:
        pickle.dump(cf, f)
    pass


def save_py(basename, cf):
    with open(basename + '.py', 'w') as f:
        for key, val in cf.items():
            if isinstance(val, str):
                val = f'''"""{val}"""'''
            f.write(f"""{key} = {val}\n""")
    pass


class Welcomer(commands.Bot):
    def __init__(self, config, logger):
        """Initialization."""
        self._loaded_extensions = []
        self.start_time = datetime.datetime.utcnow()
        self.logger = logger
        self.status = ['with Python', 'prefix <<']
        self.config = config
        self.spammers = {}
        prefix = '<<' if 'prefix' not in dir(config) else config.prefix
        super().__init__(command_prefix=prefix)

    @classmethod
    async def get_instance(cls, config):
        """Generator for db/cache."""
        # setup logger
        logger = getLogger('star-bot')
        console_handler = StreamHandler()
        console_handler.setFormatter(Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))  # noqa
        logger.addHandler(console_handler)
        logger.setLevel(INFO)
        return cls(config, logger)

    def check_spam(self, message):
        if message.author.id in [369362004458078208,]: # people to exclude: yin,
            return False
        if message.author.id not in self.spammers:
            self.spammers[message.author.id] = {'date': datetime.datetime.now(), 'count': 1}
            return False
        if self.spammers[message.author.id]['date'] < datetime.datetime.now() - datetime.timedelta(hours=24):
            self.spammers[message.author.id] = {'date': datetime.datetime.now(), 'count': 1}
            return False
        self.spammers[message.author.id]['count'] += 1
        if self.spammers[message.author.id]['count'] % 5 == 0:
            return self.spammers[message.author.id]['count']
        return False

    async def on_message(self, message):
        permis = False
        channel = message.channel
        if message.guild.id != 148606162810568704:
            return
        if channel.id in self.config.clear_channel:  # read the rules
            try:
                spam = self.check_spam(message)
                if spam:
                    # user is spamming, send mesage to staff channel
                    chan = message.guild.get_channel(259728514914189312)
                    ret = f"""***{message.author.name}#{message.author.discriminator} | {message.author.id}*** has spammed {spam} messages in read the rules."""
                    await chan.send(ret)
                    self.logger.info(ret)
            except Exception as e:
                self.logger.warning(f'Error checking for spammers: {e}')
            try:
                await message.delete()
            except Exception as e:
                self.logger.info(f'Error deleting message: {e}')
            async for msg in channel.history(limit=99999):
                if msg.author.id not in config.allowed_users:
                    try:
                        await msg.delete()
                    except Exception as e:
                        print(e)
        else:
            if self.config.client in [f.id for f in message.mentions] and ('prefix' in message.content or 'help' in message.content):
                await channel.send(f'The bot prefix is {self.config.prefix}')
                return
        if not permis:
            resolved = message.channel.permissions_for(message.author)
            if getattr(resolved, 'administrator', None) or getattr(resolved, 'kick_members', None):  # noqa
                permis = True
        if permis:
            await self.process_commands(message)
        return

    def save_config(self):
        save_pkl(self.config.filename, self.config.to_dict())
        save_py(self.config.filename, self.config.to_dict())
        pass

    def refresh_config(self):
        cf = loader(self.config.filename)
        self.config = cf

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Startup the bot')
    parser.add_argument('--input', type=str, help='name of the config file', dest='input')
    args = parser.parse_args()
    if args.input:
        config = loader(args.input)
    else:
        exit(1)

    loop = get_event_loop()
    try:
        bot = loop.run_until_complete(Welcomer.get_instance(config))
    except Exception as e:
        print('Error on startup:', str(e))
        _ = loop.run_until_complete(shutdown(bot, reason=e))
        exit(1)
    # bot.add_cog(Extension(bot))
    for cog in ['cogs.welcome', 'cogs.guildreset', 'cogs.filtering']:
        bot.load_extension(cog)
        bot._loaded_extensions.append(cog)

    try:
        loop.run_until_complete(bot.run(config.token, reconnect=True))
    except KeyboardInterrupt as e:
        _ = loop.run_until_complete(shutdown(bot, reason=e))
        exit(1)

    print(config.clear_channel)
    client.run(config.token)


