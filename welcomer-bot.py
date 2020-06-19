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
                ret[key] = getattr(self, key)
        return ret


def loader(fname):
    if '/' not in fname:
        fname = __cwd__ + '/' + fname.strip('.py')
    listoffiles = glob.glob(f'{fname}.*')
    fname = max(listoffiles, key=os.path.getctime)
    print(f'Running on file: {fname}')

    if fname.endswith('.pickle'):
        try:
            with open(fname, 'rb') as f:
                cf = pickle.load(f)
            cf['filename'] = fname
            return Config(cf)
        except Exception as e:
            print(f'Error loading pickle: {e}')
            try:
                os.remove(fname)
            except Exception as e:
                pass

    try:
        if __version__ >= 3.5:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", fname)
            cf = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cf)
        elif __version__ >= 3.3:
            from importlib.machinery import SourceFileLoader
            cf = SourceFileLoader("config", fname).load_module()
        elif __version__ <= 3.0:
            import imp
            cf = imp.load_source('config', fname)
    except Exception as e:
        print('File not found or incorrect <{}>'.format(fname))
        print('Try using python {} yourself'.format(fname))
        print(e)
        exit(1)
    with open(fname.replace('.py', '.pickle'), 'wb') as f:
        cf.filename = fname
        pickle.dump(Config(cf).to_dict(), f)
    return Config(cf)


class Welcomer(commands.Bot):
    def __init__(self, config, logger):
        """Initialization."""
        self._loaded_extensions = []
        self.start_time = datetime.datetime.utcnow()
        self.logger = logger
        self.status = ['with Python', 'prefix <<']
        self.config = config
        super().__init__(command_prefix=config.prefix)

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


    async def on_message(self, message):
        permis = False
        channel = message.channel
        if channel.id in self.config.clear_channel:  # read the rules
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
        with open(self.config.filename.replace('.py', '.pickle'), 'wb') as f:
            pickle.dump(self.config.to_dict(), f)
        pass

    def refresh_config(self):
        with open(self.config.filename.replace('.py', '.pickle'), 'rb') as f:
            cf = pickle.load(f)
        self.config = Config(cf)

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
    for cog in ['cogs.welcome', ]:
        bot.load_extension(cog)
        bot._loaded_extensions.append(cog)

    try:
        loop.run_until_complete(bot.run(config.token, reconnect=True))
    except KeyboardInterrupt as e:
        _ = loop.run_until_complete(shutdown(bot, reason=e))
        exit(1)

    print(config.clear_channel)
    client.run(config.token)


