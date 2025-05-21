# (c) 2022-2025 Michał Górny
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import os.path
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mocked-lib"))
os.environ["XDG_CACHE_HOME"] = "/dev/null"
