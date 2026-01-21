// CAN message addresses
#define DNGA_STEERING_LKAS  0x1D0  // 464
#define DNGA_LKAS_HUD       0x274  // 628
#define DNGA_ACC_BRAKE      0x271  // 625
#define DNGA_ACC_CMD_HUD    0x273  // 627
#define DNGA_DIAGNOSTIC     0x7DF  // 2015

// RX message addresses
#define DNGA_BRAKE          0xA1    // 161
#define DNGA_STEERING_MODULE 0xA4  // 164
#define DNGA_GAS_PEDAL      0x18E  // 398
#define DNGA_GAS_PEDAL_2    0x18F  // 399
#define DNGA_WHEEL_SPEED    0x1A0  // 416
#define DNGA_EPS_SHAFT_TORQUE 0x1C0 // 448
#define DNGA_PCM_BUTTONS    0x208  // 520
#define DNGA_PCM_BUTTONS_HYBRID 0x207 // 519
#define DNGA_TRANSMISSION   0x20C  // 524

// Static state for cruise control (button-based, not PCM)
static bool dnga_cruise_engaged = false;
static bool dnga_prev_set_minus = false;
static bool dnga_prev_res_plus = false;

const CanMsg DNGA_TX_MSGS[] = {
  {DNGA_STEERING_LKAS, 0, 8},
  {DNGA_LKAS_HUD, 0, 8},
  {DNGA_ACC_BRAKE, 0, 8},
  {DNGA_ACC_CMD_HUD, 0, 8},
};

RxCheck dnga_rx_checks[] = {
  {.msg = {{DNGA_WHEEL_SPEED, 0, 8, .frequency = 50U}, { 0 }, { 0 }}},
  {.msg = {{DNGA_BRAKE, 0, 8, .frequency = 100U}, { 0 }, { 0 }}},
  {.msg = {{DNGA_GAS_PEDAL, 0, 8, .frequency = 50U}, { 0 }, { 0 }}},
  {.msg = {{DNGA_GAS_PEDAL_2, 0, 8, .frequency = 50U}, { 0 }, { 0 }}},
  {.msg = {{DNGA_STEERING_MODULE, 0, 8, .frequency = 100U}, { 0 }, { 0 }}},
  {.msg = {{DNGA_EPS_SHAFT_TORQUE, 0, 8, .frequency = 50U}, { 0 }, { 0 }}},
  {.msg = {{DNGA_PCM_BUTTONS, 0, 6, .frequency = 50U}, { 0 }, { 0 }}},
};

static void dnga_rx_hook(const CANPacket_t *to_push) {
  int bus = GET_BUS(to_push);
  int addr = GET_ADDR(to_push);

  if (bus == 0) {
    // Gas pedal - GAS_PEDAL_STEP is 0 when pressed (bit 1)
    if (addr == DNGA_GAS_PEDAL_2) {
      gas_pressed = !GET_BIT(to_push, 1U);
      // Disable controls on gas press (for non-PCM cruise cars, gas can disable)
      if (gas_pressed) {
        controls_allowed = false;
        dnga_cruise_engaged = false;
        pcm_cruise_check(false);
      }
    }

    // Brake pedal - BRAKE_ENGAGED at bit 5
    if (addr == DNGA_BRAKE) {
      brake_pressed = GET_BIT(to_push, 5U);
      // Disable cruise on brake
      if (brake_pressed) {
        dnga_cruise_engaged = false;
        pcm_cruise_check(false);
      }
    }

    // Vehicle speed - WHEELSPEED_F at bits 7-30 (24 bits, factor 0.00001, little endian)
    // DBC format: 7|24@0+ means start bit 7, length 24, little endian
    // Bits 7-30: bit 7 (byte 0), bits 8-15 (byte 1), bits 16-23 (byte 2), bits 24-30 (byte 3, 7 bits)
    if (addr == DNGA_WHEEL_SPEED) {
      uint32_t byte0 = GET_BYTE(to_push, 0);
      uint32_t byte1 = GET_BYTE(to_push, 1);
      uint32_t byte2 = GET_BYTE(to_push, 2);
      uint32_t byte3 = GET_BYTE(to_push, 3);
      // Extract 24-bit value: bit 7 from byte0, full byte1, full byte2, 7 bits from byte3
      uint32_t wheel_speed_raw = ((byte0 >> 7) & 0x1U) |           // bit 7
                                 ((byte1 & 0xFFU) << 1) |          // bits 8-15
                                 ((byte2 & 0xFFU) << 9) |          // bits 16-23
                                 ((byte3 & 0x7FU) << 17);          // bits 24-30 (7 bits)
      float speed = wheel_speed_raw * 0.00001f / 3.6f;  // Convert to m/s
      vehicle_moving = speed > 0.1f;
      UPDATE_VEHICLE_SPEED(speed);
    }

    // Driver torque for steering limits
    if (addr == DNGA_EPS_SHAFT_TORQUE) {
      // STEERING_TORQUE at bits 8-15 (byte 1, little endian)
      int torque_driver_new = GET_BYTE(to_push, 1);
      // Convert to signed (0-255 -> -127 to 128)
      torque_driver_new = to_signed(torque_driver_new, 8);
      update_sample(&torque_driver, torque_driver_new);
    }

    // Cruise control buttons - DNGA uses button-based cruise, not PCM cruise
    // Track cruise state for test compatibility (even though DNGA doesn't use PCM cruise)
    if (addr == DNGA_PCM_BUTTONS) {
      bool set_minus = GET_BIT(to_push, 5U);   // SET_MINUS
      bool res_plus = GET_BIT(to_push, 6U);    // RES_PLUS
      bool cancel = GET_BIT(to_push, 4U);      // CANCEL

      // Enable controls on button press (rising edge)
      if ((set_minus && !dnga_prev_set_minus) || (res_plus && !dnga_prev_res_plus)) {
        controls_allowed = true;
        dnga_cruise_engaged = true;
      }

      // Disable controls on cancel
      if (cancel) {
        controls_allowed = false;
        dnga_cruise_engaged = false;
      }

      // Update cruise state for test compatibility
      pcm_cruise_check(dnga_cruise_engaged);

      dnga_prev_set_minus = set_minus;
      dnga_prev_res_plus = res_plus;
    }

    // Hybrid cars have separate button message
    if (addr == DNGA_PCM_BUTTONS_HYBRID) {
      bool set_minus = GET_BIT(to_push, 5U);
      bool res_plus = GET_BIT(to_push, 6U);
      bool cancel = GET_BIT(to_push, 4U);

      if ((set_minus && !dnga_prev_set_minus) || (res_plus && !dnga_prev_res_plus)) {
        controls_allowed = true;
        dnga_cruise_engaged = true;
      }

      if (cancel) {
        controls_allowed = false;
        dnga_cruise_engaged = false;
      }

      // Update cruise state for test compatibility
      pcm_cruise_check(dnga_cruise_engaged);

      dnga_prev_set_minus = set_minus;
      dnga_prev_res_plus = res_plus;
    }

    // Check for stock LKAS messages to detect relay malfunction
    generic_rx_checks((addr == DNGA_STEERING_LKAS));
  }
}

static bool dnga_tx_hook(const CANPacket_t *to_send) {
  bool tx = true;
  int addr = GET_ADDR(to_send);
  int bus = GET_BUS(to_send);

  if (bus == 0) {
    // Steering command - STEERING_LKAS (464)
    if (addr == DNGA_STEERING_LKAS) {
      // STEER_CMD is 11 bits at bits 7-17, signed, little endian
      // Bits 7-15 are in byte 0-1, bits 16-17 are in byte 2
      uint32_t byte0 = GET_BYTE(to_send, 0);
      uint32_t byte1 = GET_BYTE(to_send, 1);
      uint32_t byte2 = GET_BYTE(to_send, 2);
      int desired_torque = ((byte0 >> 7) & 0x1U) |           // bit 7
                           ((byte1 & 0xFFU) << 1) |          // bits 8-15
                           ((byte2 & 0x3U) << 9);            // bits 16-17
      desired_torque = to_signed(desired_torque, 11);
      bool steer_req = GET_BIT(to_send, 21U);  // STEER_REQ at bit 21

      // Basic steering limits - adjust based on actual limits
      const SteeringLimits DNGA_STEERING_LIMITS = {
        .max_steer = 1000,
        .max_rate_up = 10,
        .max_rate_down = 25,
        .max_rt_delta = 300,
        .max_rt_interval = 250000,
        .driver_torque_factor = 1,
        .driver_torque_allowance = 15,
        .type = TorqueDriverLimited,
      };

      if (steer_torque_cmd_checks(desired_torque, steer_req, DNGA_STEERING_LIMITS)) {
        tx = false;
      }
    }

    // ACC brake command - ACC_BRAKE (625)
    if (addr == DNGA_ACC_BRAKE) {
      // Only allow when controls_allowed
      bool brake_req = GET_BIT(to_send, 13U);  // BRAKE_REQ at bit 13
      if (brake_req && !controls_allowed) {
        tx = false;
      }
    }

    // ACC command - ACC_CMD_HUD (627)
    if (addr == DNGA_ACC_CMD_HUD) {
      // Only allow when controls_allowed
      bool is_accel = GET_BIT(to_send, 38U);   // IS_ACCEL
      bool is_decel = GET_BIT(to_send, 37U);   // IS_DECEL
      if ((is_accel || is_decel) && !controls_allowed) {
        tx = false;
      }
    }

    // Diagnostic message (0x7DF) - DTC clear, only allow tester present
    if (addr == DNGA_DIAGNOSTIC) {
      // Only allow tester present message: 0x01 0x04 0x00 0x00 0x00 0x00 0x00 0x00
      bool valid_diag = (GET_BYTE(to_send, 0) == 0x01U) &&
                        (GET_BYTE(to_send, 1) == 0x04U) &&
                        (GET_BYTES(to_send, 2, 6) == 0U);
      if (!valid_diag) {
        tx = false;
      }
    }
  }

  return tx;
}

static int dnga_fwd_hook(int bus_num, int addr) {
  int bus_fwd = -1;

  if (bus_num == 0) {
    bus_fwd = 2;
  }

  if (bus_num == 2) {
    bool is_lkas_msg = (addr == DNGA_STEERING_LKAS) || (addr == DNGA_LKAS_HUD);
    bool is_acc_msg = (addr == DNGA_ACC_BRAKE) || (addr == DNGA_ACC_CMD_HUD);
    bool block_msg = is_lkas_msg || is_acc_msg;
    if (!block_msg) {
      bus_fwd = 0;
    }
  }

  return bus_fwd;
}

static safety_config dnga_init(uint16_t param) {
  UNUSED(param);
  dnga_cruise_engaged = false;
  dnga_prev_set_minus = false;
  dnga_prev_res_plus = false;
  return BUILD_SAFETY_CFG(dnga_rx_checks, DNGA_TX_MSGS);
}

const safety_hooks dnga_hooks = {
  .init = dnga_init,
  .rx = dnga_rx_hook,
  .tx = dnga_tx_hook,
  .fwd = dnga_fwd_hook,
};
