from denonavr_cli.__main__ import main
from denonavr import TEST_DATA


class DiscoveryTest:
    async def run(self, args=["discover"], expected_exit=0,
                  expected_instance=False):
        TEST_DATA["discovery_result"] = self.discovery_result
        TEST_DATA["instance_counter"] = 0
        try:
            exit_code = await main(["denonavr-cli"] + list(args))
        except SystemExit as e:
            exit_code = e.code
        assert exit_code == expected_exit
        assert TEST_DATA["instance_counter"] == (1 if expected_instance else 0)
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
        await self.run(args=["--host-cache=off"], expected_instance=True)
        assert "Power:" in capsys.readouterr().out


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
