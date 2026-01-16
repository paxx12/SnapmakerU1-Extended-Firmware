---
title: Monitoring
---

# Monitoring

**Available in: Extended firmware**

Expose printer metrics for integration with monitoring systems like Grafana, Home Assistant, or DataDog. Track print progress, temperatures, and operational data.

## Available Features

### Moonraker API Built-in Metrics

Always enabled on all printers running Moonraker. This is a core feature required by client applications:
- Fluidd, Mainsail
- Orca, Snapmaker Orca
- Mobileraker, Octoapp, OctoPrint
- Home Assistant Moonraker integration

You can create custom metrics collection using the Moonraker API.

### Klipper Metrics Exporter

Exposes [Klipper metrics](https://github.com/scross01/prometheus-klipper-exporter) via HTTP endpoint for [OpenMetrics/Prometheus](https://github.com/prometheus/OpenMetrics) systems.

**Disabled by default.** Enable in `extended.cfg`:
```ini
[monitoring]
klipper_exporter_enabled: true
```
Then reboot the printer.

## Collecting Metrics with Home Assistant

**Setup:**
1. Install [Home Assistant Community Store (HACS)](https://www.hacs.xyz/docs/use/)
2. Install [Moonraker Integration](https://github.com/marcolivierarsenault/moonraker-home-assistant) via HACS
   - [Installation instructions](https://moonraker-home-assistant.readthedocs.io/en/latest/install.html)
3. Add Moonraker integration and connect to your Snapmaker U1

Once configured, you can view metrics in Home Assistant or forward them to other systems like [DataDog](https://github.com/kamaradclimber/datadog-integration-ha).

## Collecting Metrics with OpenMetrics/Prometheus

### Prometheus and Grafana

The prometheus-klipper-exporter is already running on your printer when enabled. Setup instructions:
https://github.com/scross01/prometheus-klipper-exporter/tree/main/example

Point Prometheus to your printer's IP address and port (no Docker setup needed on the printer).

### DataDog Agent

Use DataDog's [OpenMetrics integration](https://docs.datadoghq.com/integrations/openmetrics/) to collect Prometheus metrics.

**Setup:**
1. Create `/etc/datadog-agent/conf.d/openmetrics.d/snapmaker_u1.yaml` on the computer running DataDog Agent
   - Example config: [overlays/firmware-extended/99-monitoring/examples/example_datadog_snapmaker_u1.yaml](../overlays/firmware-extended/99-monitoring/examples/example_datadog_snapmaker_u1.yaml)
2. Edit config to set your printer's IP address
3. Restart DataDog Agent

**Example Dashboard:** https://p.datadoghq.com/sb/750c84c6f-0e38a89ca620e6047171edbfb15b756e
