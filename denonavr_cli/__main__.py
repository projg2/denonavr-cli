import argparse
import asyncio
import os.path
import sys

import denonavr

import denonavr_cli


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
    async def run(avr, args):
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


class mute(Subcommand):
    """Print and control mute"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("new_state",
                          choices=("off", "on", "toggle"),
                          nargs="?",
                          help="Requested state change")

    @staticmethod
    async def run(avr, args):
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
    async def run(avr, args):
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
    async def run(avr, args):
        BANNER = 'The AVR connection is available as "avr" object'

        if args.shell is None:
            try:
                from IPython import embed
                import nest_asyncio
            except ImportError:
                args.shell = "python"
            else:
                args.shell = "ipython"

        if args.shell == "ipython":
            from IPython import embed
            import nest_asyncio

            nest_asyncio.apply()
            embed(banner2=BANNER)
            return 0

        if args.shell == "python":
            from code import InteractiveConsole

            InteractiveConsole({"avr": avr}).interact(banner=BANNER)
            return 0


class volume(Subcommand):
    """Print and control volume"""

    @staticmethod
    def add_arguments(subc):
        subc.add_argument("-r", "--relative",
                          action="store_true",
                          help="Adjust the current volume by <value>")
        subc.add_argument("value",
                          nargs="?",
                          type=float,
                          help="New volume")

    @staticmethod
    async def run(avr, args):
        if args.value is not None:
            new_volume = args.value
            if args.relative:
                new_volume += avr.volume
            await avr.async_set_volume(new_volume)
            await avr.async_update()
        print(avr.volume)
        return 0


def add_subcommand(subp, cmd_class):
    subc = subp.add_parser(cmd_class.__name__,
                           help=cmd_class.__doc__)
    cmd_class.add_arguments(subc)


async def main(argv):
    argp = argparse.ArgumentParser(prog=os.path.basename(argv[0]),
                                   description=denonavr_cli.__doc__)
    argp.add_argument("-H", "--host",
                      help="Host to use (default: autodiscover)")
    argp.add_argument("-V", "--version",
                      action="store_true",
                      help="Print version and exit")

    subp = argp.add_subparsers(title="commands",
                               dest="command")
    subc = subp.add_parser("discover",
                           help="Print autodiscovered receivers and exit")
    add_subcommand(subp, input)
    add_subcommand(subp, mute)
    add_subcommand(subp, power)
    add_subcommand(subp, shell)
    add_subcommand(subp, volume)

    args = argp.parse_args(argv[1:])

    if args.version:
        print(f"denonavr-cli {denonavr_cli.__version__}")
        return 0

    discover = args.command == "discover"
    if args.host is None or discover:
        avrs = await denonavr.async_discover()
        if not avrs:
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

    avr = denonavr.DenonAVR(args.host)
    await avr.async_setup()
    await avr.async_update()

    if args.command is not None:
        return await globals()[args.command].run(avr, args)

    print(f"Power: {avr.power:7}  Volume: {avr.volume:5} dB "
          f"{'(muted)' if avr.muted else '       '} "
          f"Input: {avr.input_func}")

    return 0


def entry_point():
    sys.exit(asyncio.run(main(sys.argv)))


if __name__ == "__main__":
    entry_point()
