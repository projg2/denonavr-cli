TEST_DATA = {}

INITIAL_VALUES = {
    "input_func": "Game",
    "input_func_list": ["AUX", "Game", "TV Audio"],
    "muted": False,
    "power": "ON",
    "volume": -45.5,
}


class DenonAVR:
    def __init__(self, host):
        self.new_values = {}
        assert host == "mocked-host"

    async def async_mute(self, new_state):
        self.new_values["muted"] = new_state

    async def async_power_off(self):
        self.new_values["power"] = "OFF"

    async def async_power_on(self):
        self.new_values["power"] = "ON"

    async def async_setup(self):
        self.new_values = INITIAL_VALUES

    async def async_set_input_func(self, new_input):
        assert isinstance(new_input, str)
        # apparently input is not updated immediately
        TEST_DATA["input_func"] = new_input

    async def async_set_volume(self, new_volume):
        assert isinstance(new_volume, float)
        self.new_values["volume"] = new_volume

    async def async_update(self):
        self.__dict__.update(self.new_values)
        self.new_values = {}

    async def async_volume_down(self):
        self.new_values["volume"] = self.volume - 0.5

    async def async_volume_up(self):
        self.new_values["volume"] = self.volume + 0.5
