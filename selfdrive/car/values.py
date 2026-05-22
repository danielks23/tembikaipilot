from typing import cast
from openpilot.selfdrive.car.honda.values import CAR as HONDA
from openpilot.selfdrive.car.hyundai.values import CAR as HYUNDAI
from openpilot.selfdrive.car.mazda.values import CAR as MAZDA
from openpilot.selfdrive.car.nissan.values import CAR as NISSAN
from openpilot.selfdrive.car.subaru.values import CAR as SUBARU
from openpilot.selfdrive.car.toyota.values import CAR as TOYOTA
from openpilot.selfdrive.car.volkswagen.values import CAR as VOLKSWAGEN
from openpilot.selfdrive.car.proton.values import CAR as PROTON
from openpilot.selfdrive.car.dnga.values import CAR as DNGA
from openpilot.selfdrive.car.byd.values import CAR as BYD

Platform = HONDA | HYUNDAI | MAZDA | NISSAN | SUBARU | TOYOTA | VOLKSWAGEN | PROTON | DNGA | BYD
BRANDS = [HONDA, HYUNDAI, MAZDA, NISSAN, SUBARU, TOYOTA, VOLKSWAGEN, PROTON, DNGA, BYD]

PLATFORMS: dict[str, Platform] = {str(platform): platform for brand in BRANDS for platform in cast(list[Platform], brand)}
