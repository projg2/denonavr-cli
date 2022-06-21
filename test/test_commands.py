import contextlib

from denonavr_cli.__main__ import main
from denonavr import INITIAL_VALUES, TEST_DATA


@contextlib.contextmanager
def override_initial(key, value):
    old = INITIAL_VALUES[key]
    INITIAL_VALUES[key] = value
    yield
    INITIAL_VALUES[key] = old


class CommandTest:
    async def run(self, *args):
        assert await main(["denonavr-cli", "--host-cache", "off",
                           "--host", "mocked-host", self.command]
                          + list(args)) == 0

    async def test_print(self, capsys):
        await self.run()
        assert capsys.readouterr().out == f"{self.initial_value}\n"


class BooleanTest(CommandTest):
    off_value = "False"
    on_value = "True"
    initial_off_value = False
    initial_on_value = True

    async def test_off(self, capsys):
        with override_initial(self.initial_key, self.initial_on_value):
            await self.run("off")
            assert capsys.readouterr().out == f"{self.off_value}\n"

    async def test_on(self, capsys):
        with override_initial(self.initial_key, self.initial_off_value):
            await self.run("on")
            assert capsys.readouterr().out == f"{self.on_value}\n"

    async def test_toggle_off(self, capsys):
        with override_initial(self.initial_key, self.initial_on_value):
            await self.run("toggle")
            assert capsys.readouterr().out == f"{self.off_value}\n"

    async def test_toggle_on(self, capsys):
        with override_initial(self.initial_key, self.initial_off_value):
            await self.run("toggle")
            assert capsys.readouterr().out == f"{self.on_value}\n"


class TestInput(CommandTest):
    command = "input"
    initial_value = "Game"

    async def test_list(self, capsys):
        await self.run("--list")
        assert capsys.readouterr().out == "AUX\nGame\nTV Audio\n"

    async def test_set(self, capsys):
        await self.run("TV Audio")
        assert capsys.readouterr().out == "TV Audio\n"
        assert TEST_DATA["input_func"] == "TV Audio"


class TestMute(BooleanTest):
    command = "mute"
    initial_key = "muted"
    initial_value = "False"


class TestPower(BooleanTest):
    command = "power"
    initial_key = "power"
    initial_value = "ON"

    off_value = initial_off_value = "OFF"
    on_value = initial_on_value = "ON"


class TestVolume(CommandTest):
    command = "volume"
    initial_value = "-45.5"

    async def test_set(self, capsys):
        await self.run("set", "-40.0")
        assert capsys.readouterr().out == "-40.0\n"

    async def test_down(self, capsys):
        await self.run("down")
        assert capsys.readouterr().out == "-46.0\n"

    async def test_up(self, capsys):
        await self.run("up")
        assert capsys.readouterr().out == "-45.0\n"

    async def test_down_value(self, capsys):
        await self.run("down", "1")
        assert capsys.readouterr().out == "-46.5\n"

    async def test_up_value(self, capsys):
        await self.run("up", "1.5")
        assert capsys.readouterr().out == "-44.0\n"
