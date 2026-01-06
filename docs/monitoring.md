# Monitoring

Extended Firmware provides tools to expose printer metrics for integration with external monitoring systems. This allows you to track print progress, temperatures, and other operational data using dashboards like Grafana, Home Assistant, or DataDog.

All monitoring features added by Extended Firmware are disabled by default and require explicit enabling via `extended.cfg`.

## Available monitoring features

- **Moonraker API's Built-in Metrics**

  - Enabled on all printers running Moonraker API by default. We do not have a way to control it from firmware side.
  - This is a core Moonraker feature; it is required for all client applications to work. Examples of such applications:
    - Fluidd, Mainsail
    - Orca, Snapmaker Orca
    - Mobileraker, Octoapp, Octoprint
    - Homeassistant Moonraker integration.
  - You can also create your own custom metrics collection by talking to Moonraker API.

- **Klipper Metrics Exporter**

  - Exposes [Klipper metrics](https://github.com/scross01/prometheus-klipper-exporter.git) on a local HTTP endpoint for scraping by [OpenMetrics/Prometheus](https://github.com/prometheus/OpenMetrics)-compatible systems
  - This is an addon by Extended Firmware and it is NOT enabled by default. You have to enable it explicitly in `extended.cfg` by changing `[monitoring] klipper_exporter_enabled: true` and restarting printer

## Collecting Metrics using Homeassistant

You'll first need to install and configure:

- The [Home Assistant Community Store (HACS)](https://www.hacs.xyz/docs/use/)
- Using HACS, install the [Moonraker Integration](https://github.com/marcolivierarsenault/moonraker-home-assistant)
  - [Installation instructions](https://moonraker-home-assistant.readthedocs.io/en/latest/install.html)
- Add Moonraker integration to your Homeassistant using normal methods and connect it to Moonraker on your Snapmaker U1 printer.

Once you have Moonraker integration set up you can use Homeassistant to view various metrics. Or you can use other Homeassistant integrations to send those metrics to various other systems, such as [Datadog Agentless](https://github.com/kamaradclimber/datadog-integration-ha).

## Collecting Metrics using OpenMetrics/Prometheus compatible systems

### Collecting Metrics with Prometheus and Grafana

There are useful instructions on how to set up Prometheus and Grafana to collect and display Klipper metrics using the Prometheus Klipper Exporter in prometheus-klipper-exporter GitHub repository:
https://github.com/scross01/prometheus-klipper-exporter/tree/main/example
Note that in this case prometheus-klipper-exporter is already running on your Snapmaker U1 printer so you don't need to run it in Docker; only point Prometheus to the correct IP address and port of your printer.

### Collecting Metrics using DataDog Agent

Once you have the Prometheus metrics exporter enabled and running, you can use DataDog Agent on another computer on the network to collect those metrics and send them to DataDog.

To do that we like to use DataDog's built-in [DataDog OpenMetrics integration](https://docs.datadoghq.com/integrations/openmetrics/).

1. Create a configuration file for OpenMetrics DataDog integration on the computer running DataDog Agent `/etc/datadog-agent/conf.d/openmetrics.d/snapmaker_u1.yaml`

    You can find an example configuration file in overlay's examples directory: [overlays/firmware-extended/99-prometheus/examples/example_datadog_snapmaker_u1.yaml](../overlays/firmware-extended/99-monitoring/examples/example_datadog_snapmaker_u1.yaml).

2. Edit the configuration file to set the correct IP address of your Snapmaker U1 printer in place of `<PRINTER_IP>`.
3. Restart DataDog Agent to apply the changes and wait for metrics to appear in DataDog.

For in-depth instructions on setting up DataDog OpenMetrics integration, refer to DataDog documentation.

Example DataDog dashboard using metrics collected by both Homeassistant Moonraker integration and DataDog Agent via Prometheus Klipper Exporter: https://p.datadoghq.com/sb/750c84c6f-0e38a89ca620e6047171edbfb15b756e
