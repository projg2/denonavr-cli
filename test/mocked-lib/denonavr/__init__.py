# (c) 2022-2025 Michał Górny
# SPDX-License-Identifier: GPL-2.0-or-later

from denonavr.exceptions import AvrNetworkError


TEST_DATA = {
    "instance_counter": 0,
    "discovery_result": None,
}

INITIAL_VALUES = {
    "input_func": "Game",
    "input_func_list": ["AUX", "Game", "TV Audio"],
    "muted": False,
    "power": "ON",
    "volume": -45.5,
}


class DenonAVR:
    def __init__(self, host):
        TEST_DATA["instance_counter"] += 1
        self.hostname = host
        self.new_values = {}
        self.setup_called = False

    async def async_mute(self, new_state):
        self.new_values["muted"] = new_state

    async def async_power_off(self):
        self.new_values["power"] = "OFF"

    async def async_power_on(self):
        self.new_values["power"] = "ON"

    async def async_setup(self):
        if self.hostname != "mocked-host":
            raise AvrNetworkError()
        assert not self.setup_called
        self.setup_called = True
        self.new_values = INITIAL_VALUES

    async def async_set_input_func(self, new_input):
        assert isinstance(new_input, str)
        # apparently input is not updated immediately
        TEST_DATA["input_func"] = new_input

    async def async_set_volume(self, new_volume):
        assert isinstance(new_volume, float)
        self.new_values["volume"] = new_volume

    async def async_update(self):
        assert self.setup_called
        self.__dict__.update(self.new_values)
        self.new_values = {}

    async def async_volume_down(self):
        self.new_values["volume"] = self.volume - 0.5

    async def async_volume_up(self):
        self.new_values["volume"] = self.volume + 0.5


async def async_discover():
    assert TEST_DATA["discovery_result"] is not None
    return TEST_DATA["discovery_result"]
