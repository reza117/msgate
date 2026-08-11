---
title: Capacity alerts
---

# Capacity alerts

When queue depth, age, or the circuit breaker looks unhealthy, msgate shows a yellow/red **banner** in the Web UI.

## Setup

1. Open **Account**.
2. Set **Admin alert email**, enable email alerts, Save.
3. On **critical**, msgate emails that address via Exchange (EWS credentials must be configured in Settings). Cooldown default: 15 minutes.

Use existing `MSGATE_WEBHOOK_URLS` for chat hooks until UI webhook wiring is extended.
