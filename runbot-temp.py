import asyncio
import discord
import os
from sys import exit, version
import argparse

__cwd__ = os.getcwd()
__version__ = float(version[:2])

def loader(fname):
    if '/' not in fname:
        fname = __cwd__ + '/' + fname
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
    return cf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Startup the bot')
    parser.add_argument('--input', type=str, help='name of the config file', dest='input')
    args = parser.parse_args()
    if args.input:
        print('Running on file: ' + args.input)
        config = loader(args.input)
    else:
        exit(1)

    client = discord.Client()

    @client.event
    async def on_message(message):
        channel = message.channel
        if channel.id in config.clear_channel:  # read the rules
            try:
                await message.delete()
            except Exception as e:
                print(e)

    print(config.clear_channel)
    client.run(config.token)

