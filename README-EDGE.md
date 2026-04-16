# ChikGuard Edge Computing Setup

This document describes how to deploy ChikGuard in an Edge Computing environment (e.g., an Intel NUC or Raspberry Pi).

## Hardware Acceleration

We have enabled hardware acceleration through ONNX Runtime and OpenVINO.

The system will automatically detect and load models based on their extension (`.onnx` or `.xml`).

## Setup using systemd

1. Copy the systemd service file:
   `sudo cp scripts/chikguard.service /etc/systemd/system/`
2. Start the service:
   `sudo systemctl daemon-reload`
   `sudo systemctl enable chikguard`
   `sudo systemctl start chikguard`
3. Auto-recovery:
   You can run `scripts/auto_recovery.sh` in the background (or setup another systemd unit for it) to monitor ChikGuard's health.
