import contextlib
import os

from unittest import mock

import pytest

from denonavr_cli.__main__ import main
from denonavr import TEST_DATA


@contextlib.contextmanager
def save_envvar(key):
    old = os.environ.pop(key, None)
    yield
    if old is not None:
        os.environ[key] = old
    else:
        os.environ.pop(key, None)


@pytest.fixture
def save_cache_home():
    with save_envvar("XDG_CACHE_HOME"):
        yield


@pytest.fixture
def host_cache_file(tmp_path, save_cache_home):
    os.environ["XDG_CACHE_HOME"] = str(tmp_path)
    with open(tmp_path / "denonavr-cli.host", "w+") as f:
        yield f


class DiscoveryTest:
    async def run(self, args=["discover"], expected_exit=0,
                  expected_instances=0):
        TEST_DATA["discovery_result"] = self.discovery_result
        TEST_DATA["instance_counter"] = 0
        try:
            exit_code = await main(["denonavr-cli"] + list(args))
        except SystemExit as e:
            exit_code = e.code
        assert exit_code == expected_exit
        assert TEST_DATA["instance_counter"] == expected_instances
        TEST_DATA["discovery_result"] = None


class NoAVRDiscoveryTest(DiscoveryTest):
    __test__ = True

    discovery_result = []

    async def test_discover(self, capsys):
        await self.run(expected_exit=1)
        capture = capsys.readouterr()
        assert capture.out == ""
        assert capture.err != ""

    async def test_other_command(self, capsys):
        await self.run(args=["--host-cache=off"], expected_exit=2)
        assert "Autodiscovery found no receivers" in capsys.readouterr().err


class OneAVRDiscoveryTest(DiscoveryTest):
    __test__ = True

    discovery_result = [
        {'manufacturer': 'Mocker',
         'host': 'mocked-host',
         'modelName': 'Mocked AVR',
         'serialNumber': 'M0CK1234567890',
         'friendlyName': 'My Mocked AVR',
         },
    ]

    async def test_discover(self, capsys):
        await self.run()
        assert capsys.readouterr().out.splitlines() == [
            "mocked-host     My Mocked AVR (Mocked AVR M0CK1234567890)",
        ]

    async def test_other_command(self, capsys):
        await self.run(args=["--host-cache=off"], expected_instances=1)
        assert "Power:" in capsys.readouterr().out

    async def test_no_host_cache(self, capsys, tmp_path, save_cache_home):
        os.environ["XDG_CACHE_HOME"] = str(tmp_path)
        await self.run(args=["--host-cache=on"], expected_instances=1)
        with open(tmp_path / "denonavr-cli.host", "r") as f:
            assert f.read() == "mocked-host\n"
        assert "Power:" in capsys.readouterr().out

    async def test_bad_host_cache(self, capsys, host_cache_file):
        host_cache_file.write("foo\n")
        host_cache_file.flush()
        await self.run(args=["--host-cache=on"], expected_instances=2)
        host_cache_file.seek(0)
        assert host_cache_file.read() == "mocked-host\n"
        output = capsys.readouterr()
        assert "Power:" in output.out
        assert "failed to connect" in output.err

    async def test_host_cache_reset(self, capsys, host_cache_file):
        host_cache_file.write("ignore-me\n")
        host_cache_file.flush()
        await self.run(args=["--host-cache=reset"], expected_instances=1)
        host_cache_file.seek(0)
        assert host_cache_file.read() == "mocked-host\n"
        output = capsys.readouterr()
        assert "Power:" in output.out
        assert "failed to connect" not in output.err


class TwoAVRsDiscoveryTest(DiscoveryTest):
    __test__ = True

    discovery_result = [
        {'manufacturer': 'Mocker',
         'host': 'mocked-host',
         'modelName': 'Mocked AVR',
         'serialNumber': 'M0CK1234567890',
         'friendlyName': 'My Mocked AVR',
         },
        {'manufacturer': 'Mocktoo',
         'host': '127.0.0.1',
         'modelName': 'Another AVR',
         'serialNumber': 'M0CK0987654321',
         'friendlyName': 'Another Mocked AVR',
         },
    ]

    async def test_discover(self, capsys):
        await self.run()
        assert capsys.readouterr().out.splitlines() == [
            "mocked-host     My Mocked AVR (Mocked AVR M0CK1234567890)",
            "127.0.0.1       Another Mocked AVR (Another AVR M0CK0987654321)",
        ]

    async def test_other_command(self, capsys):
        await self.run(args=["--host-cache=off"], expected_exit=2)
        capture = capsys.readouterr()
        assert capture.out.splitlines() == [
            "mocked-host     My Mocked AVR (Mocked AVR M0CK1234567890)",
            "127.0.0.1       Another Mocked AVR (Another AVR M0CK0987654321)",
        ]
        assert "Autodiscovery found multiple receivers" in capture.err


class ValidHostCacheTests:
    __test__ = True

    async def run(self):
        TEST_DATA["instance_counter"] = 0
        assert await main(["denonavr-cli", "--host-cache=on"]) == 0
        assert TEST_DATA["instance_counter"] == 1

    async def test_valid_cache(self, capsys, host_cache_file):
        host_cache_file.write("mocked-host\n")
        host_cache_file.flush()
        await self.run()
        assert "Power:" in capsys.readouterr().out
        host_cache_file.seek(0)
        assert host_cache_file.read() == "mocked-host\n"

    async def test_home_fallback(self, capsys, tmp_path, save_cache_home):
        with save_envvar("HOME"):
            os.environ["HOME"] = str(tmp_path)
            os.mkdir(tmp_path / ".cache")
            with open(tmp_path / ".cache" / "denonavr-cli.host", "w") as f:
                f.write("mocked-host\n")
            await self.run()
            assert "Power:" in capsys.readouterr().out
            with open(tmp_path / ".cache" / "denonavr-cli.host", "r") as f:
                assert f.read() == "mocked-host\n"

    async def test_home_pwd_fallback(self, capsys, tmp_path, save_cache_home):
        with save_envvar("HOME"):
            with mock.patch("os.path.expanduser",
                            new=lambda x: x.replace("~", str(tmp_path))):
                os.mkdir(tmp_path / ".cache")
                with open(tmp_path / ".cache" / "denonavr-cli.host", "w") as f:
                    f.write("mocked-host\n")
                await self.run()
                assert "Power:" in capsys.readouterr().out
                with open(tmp_path / ".cache" / "denonavr-cli.host", "r") as f:
                    assert f.read() == "mocked-host\n"
