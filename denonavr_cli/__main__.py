# (c) 2022-2025 Michał Górny
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse
import asyncio
import importlib
import os
import os.path
import sys
import time

from typing import Callable

import denonavr
import denonavr.exceptions

import denonavr_cli


async def wait_for_update(avr: denonavr.DenonAVR,
                          callback: Callable[[], bool],
                          ) -> bool:
    """
    Wait for the update to take effect

    Repeatedly try updating AVR status, calling the callback to verify
    if the update took effect. If the callback succeeds, returns True.
    If it keeps failing until the timeout, returns False.
    """

    for attempt in range(20):
        await avr.async_update()
        if callback():
            return True
        time.sleep(0.2)
    return False


class Subcommand:
    @staticmethod
    def add_arguments(subc):
        pass


class input(Subcommand):
    """Print and control inputs"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("-l", "--list",
                          action="store_true",
                          help="List available inputs")
        subc.add_argument("new_input",
                          nargs="?",
                          help="Switch to another input")

    @staticmethod
    async def run(avr, argp, args):
        if args.list:
            for x in avr.input_func_list:
                print(x)
            return 0
        if args.new_input is not None:
            await avr.async_set_input_func(args.new_input)
            # we don't seem to be able to wait for the switch to actually
            # happen but denonavr verifies the new input name, so it should
            # work anyway
            print(args.new_input)
            return 0
        print(avr.input_func)
        return 0


class mute(Subcommand):
    """Print and control mute"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("new_state",
                          choices=("off", "on", "toggle"),
                          nargs="?",
                          help="Requested state change")

    @staticmethod
    async def run(avr, argp, args):
        if args.new_state is not None:
            if args.new_state == "toggle":
                args.new_state = "off" if avr.muted else "on"
            await avr.async_mute(True if args.new_state == "on" else False)
            await avr.async_update()
        print(avr.muted)
        return 0


class power(Subcommand):
    """Print and control power"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("new_state",
                          choices=("off", "on", "toggle"),
                          nargs="?",
                          help="Requested state change")

    @staticmethod
    async def run(avr, argp, args):
        if args.new_state is not None:
            if args.new_state == "toggle":
                args.new_state = "off" if avr.power == "ON" else "on"
            if args.new_state == "on":
                await avr.async_power_on()
            else:
                await avr.async_power_off()
            await avr.async_update()
        print(avr.power)
        return 0


class shell(Subcommand):
    """Launch a Python shell with AVR connection object"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("-s", "--shell",
                          choices=("ipython", "python"),
                          help="Shell to use (default: autodetect)")

    @staticmethod
    async def run(avr, argp, args):
        BANNER = 'The AVR connection is available as "avr" object'

        if args.shell is None:
            try:
                importlib.import_module("IPython")
                importlib.import_module("nest_asyncio")
            except ImportError:
                args.shell = "python"
            else:
                args.shell = "ipython"

        if args.shell == "ipython":
            IPython = importlib.import_module("IPython")
            nest_asyncio = importlib.import_module("nest_asyncio")

            nest_asyncio.apply()
            IPython.embed(banner2=BANNER)
            return 0

        if args.shell == "python":
            code = importlib.import_module("code")

            code.InteractiveConsole({"avr": avr}).interact(banner=BANNER)
            return 0


class volume(Subcommand):
    """Print and control volume"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("action",
                          nargs="?",
                          choices=("down", "set", "up"),
                          help="Change to perform")
        subc.add_argument("value",
                          nargs="?",
                          type=float,
                          help="New value or adjustment")

    @staticmethod
    async def run(avr, argp, args):
        if args.action is not None:
            if args.value is not None:
                new_volume = args.value
                if args.action == "down":
                    new_volume *= -1
                if args.action != "set":
                    new_volume += avr.volume
                await avr.async_set_volume(new_volume)
            else:
                if args.action == "down":
                    await avr.async_volume_down()
                elif args.action == "up":
                    await avr.async_volume_up()
                else:  # "set"
                    argp.error(
                        "New volume needs to be provided for 'set' action")
            await avr.async_update()
        print(avr.volume)
        return 0


class sound_mode(Subcommand):
    """Print and control sound mode"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("-l", "--list",
                          action="store_true",
                          help="List available sound modes")
        subc.add_argument("new_mode",
                          nargs="?",
                          help="Switch to another sound mode")

    @staticmethod
    async def run(avr, argp, args):
        if args.list:
            for x in avr.sound_mode_list:
                print(x)
            return 0

        if args.new_mode is not None:
            await avr.async_set_sound_mode(args.new_mode)
            ret = await wait_for_update(
                avr, lambda: avr.sound_mode == args.new_mode)
            print(avr.sound_mode)
            return 0 if ret else 1

        print(avr.sound_mode)
        return 0


def add_subcommand(subp, cmd_class):
    subc = subp.add_parser(cmd_class.__name__.replace("_", "-"),
                           help=cmd_class.__doc__)
    cmd_class.add_arguments(subc)


async def main(argv):
    argp = argparse.ArgumentParser(prog=os.path.basename(argv[0]),
                                   description=denonavr_cli.__doc__)
    argp.add_argument("-H", "--host",
                      help="Host to use (default: autodiscover)")
    argp.add_argument("--host-cache",
                      choices=("off", "on", "reset"),
                      default="on",
                      help="Whether to cache the last used hostname "
                           "(or reset the cached value)")
    argp.add_argument("-V", "--version",
                      action="store_true",
                      help="Print version and exit")

    subp = argp.add_subparsers(title="commands",
                               dest="command")
    subp.add_parser("discover",
                    help="Print autodiscovered receivers and exit")
    add_subcommand(subp, input)
    add_subcommand(subp, mute)
    add_subcommand(subp, power)
    add_subcommand(subp, shell)
    add_subcommand(subp, volume)
    add_subcommand(subp, sound_mode)

    args = argp.parse_args(argv[1:])

    if args.version:
        print(f"denonavr-cli {denonavr_cli.__version__}")
        return 0

    xdg_cache_home = os.path.expanduser(
        os.getenv("XDG_CACHE_HOME", "~/.cache"))
    host_cache = os.path.join(xdg_cache_home, "denonavr-cli.host")

    avr = None
    discover = args.command == "discover"
    if not discover and args.host_cache == "on":
        try:
            with open(host_cache, "r") as f:
                host = f.read().strip()
            try_avr = denonavr.DenonAVR(host)
            await try_avr.async_setup()
        except FileNotFoundError:
            pass
        except denonavr.exceptions.AvrNetworkError:
            print(f"Cached host {host} failed to connect, ignoring",
                  file=sys.stderr)
        else:
            args.host = host
            avr = try_avr
    if args.host is None or discover:
        avrs = await denonavr.async_discover()
        if not avrs:
            if discover:
                print("No AVRs discovered", file=sys.stderr)
                return 1
            else:
                argp.error("Autodiscovery found no receivers, please supply "
                           "--host")

        if len(avrs) > 1 or discover:
            for avr in avrs:
                print(f"{avr['host']:15} {avr['friendlyName']} "
                      f"({avr['modelName']} {avr['serialNumber']})")

            if discover:
                return 0
            else:
                argp.error("Autodiscovery found multiple receivers, please "
                           "select one via --host")
        args.host = avrs[0]["host"]

    if avr is None:
        avr = denonavr.DenonAVR(args.host)
        await avr.async_setup()
    await avr.async_update()

    if args.host_cache != "off":
        with open(host_cache, "w") as f:
            f.write(f"{args.host}\n")

    if args.command is not None:
        command_class = globals()[args.command.replace("-", "_")]
        return await command_class.run(avr, argp, args)

    print(f"Power: {avr.power:7}  Volume: {avr.volume:5} dB "
          f"{'(muted)' if avr.muted else '       '} "
          f"Input: {avr.input_func}")

    return 0


def entry_point():
    sys.exit(asyncio.run(main(sys.argv)))


if __name__ == "__main__":
    entry_point()
