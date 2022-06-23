import contextlib

from unittest import mock

import pytest

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
        TEST_DATA["instance_counter"] = 0
        assert await main(["denonavr-cli", "--host-cache", "off",
                           "--host", "mocked-host", self.command]
                          + list(args)) == 0
        assert TEST_DATA["instance_counter"] == 1


class DataCommandTest(CommandTest):
    async def test_print(self, capsys):
        await self.run()
        assert capsys.readouterr().out == f"{self.initial_value}\n"


class BooleanCommandTest(DataCommandTest):
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


class TestInput(DataCommandTest):
    command = "input"
    initial_value = "Game"

    async def test_list(self, capsys):
        await self.run("--list")
        assert capsys.readouterr().out == "AUX\nGame\nTV Audio\n"

    async def test_set(self, capsys):
        await self.run("TV Audio")
        assert capsys.readouterr().out == "TV Audio\n"
        assert TEST_DATA["input_func"] == "TV Audio"


class TestMute(BooleanCommandTest):
    command = "mute"
    initial_key = "muted"
    initial_value = "False"


class TestPower(BooleanCommandTest):
    command = "power"
    initial_key = "power"
    initial_value = "ON"

    off_value = initial_off_value = "OFF"
    on_value = initial_on_value = "ON"


class TestVolume(DataCommandTest):
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


class TestShell(CommandTest):
    __test__ = False

    command = "shell"

    def mocked_import_module(self, name):
        if name not in self.successful_imports:
            raise ModuleNotFoundError(name)
        self.imported_modules[name] = mock.MagicMock()
        return self.imported_modules[name]

    @pytest.fixture(autouse=True)
    def mock_import_module(self):
        self.imported_modules = {}
        with mock.patch("importlib.import_module",
                        new=self.mocked_import_module):
            yield
        assert (self.imported_modules.keys() ==
                frozenset(self.successful_imports))

    async def test_shell_implicit(self):
        await self.run_shell()

    async def test_shell_explicit(self):
        await self.run_shell(f"--shell={self.shell}")


class TestPythonShell(TestShell):
    __test__ = True

    shell = "python"
    successful_imports = ["code"]

    async def run_shell(self, *args):
        await self.run(*args)
        (self.imported_modules["code"].InteractiveConsole().interact
            .assert_called())


class TestIPythonShell(TestShell):
    __test__ = True

    shell = "ipython"
    successful_imports = ["IPython", "nest_asyncio"]

    async def run_shell(self, *args):
        await self.run(*args)
        self.imported_modules["IPython"].embed.assert_called()
        self.imported_modules["nest_asyncio"].apply.assert_called()
