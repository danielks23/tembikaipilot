# TODO: these are also defined in a header

# GPIO pin definitions
class GPIO:
  # GPIO_STM_RST_N is misnamed, they are high to reset
  STM_RST_N = 124
  STM_BOOT0 = 134

  SOM_ST_IO = 4   # GPIO4_B2_u / P26

  # EC25-EM GNSS power (integrated in modem, not a separate pin)
  GNSS_PWR_EN = -1
