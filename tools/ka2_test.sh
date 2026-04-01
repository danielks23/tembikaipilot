#!/bin/bash
# Run openpilot on the KA2 device WITHOUT a car connected.
# Useful for verifying all processes start and function correctly.
#
# Usage (on device):
#   cd /data/openpilot && ./tools/ka2_test.sh

export PASSIVE="0"
export NOBOARD="1"         # skip pandad - no panda/CAN hardware needed
export SKIP_FW_QUERY="1"  # skip ECU firmware querying - no car needed
export FINGERPRINT="BYD ATTO 3"

# Block qcomgpsd to suppress GPS assist spam when no SIM is inserted.
# Remove "qcomgpsd" from BLOCK if you have a SIM and want GPS.
export BLOCK="${BLOCK},qcomgpsd"

SCRIPT_DIR=$(dirname "$0")
OPENPILOT_DIR=$SCRIPT_DIR/../

cd $OPENPILOT_DIR/selfdrive/manager && exec ./manager.py
