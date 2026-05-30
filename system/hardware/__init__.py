import os
from typing import cast

from openpilot.system.hardware.base import HardwareBase
from openpilot.system.hardware.ka2.hardware import Ka2

KA2 = os.path.isfile('/KA2')
TICI = False
PC = not KA2
AGNOS = KA2

if KA2:
  HARDWARE = cast(HardwareBase, Ka2())
else:
  # Fallback for development/testing on non-ka2 hosts
  HARDWARE = cast(HardwareBase, HardwareBase())
