# Mist_library

Examples of Python scripts using the [Mist APIs](https://www.mist.com)
These scripts are using the [mistapi Python package](https://pypi.org/project/mistapi/) to simplify the authentication process.

# Menu

- [MIT LICENSE](#mit-license)
- 1 [Description](#description)
  - 1.1 [Usage](#usage)
  - 1.2 [Environment File](#environment-file)
- 2 [Scripts](#scripts)
 - 2.1 [Configuration](#configuration)
 - 2.2 [Backup & Restore](#backup--restore)
 - 2.3 [Devices](#devices)
 - 2.4 [Imports](#imports)
 - 2.5 [Reports](#reports)

## MIT LICENSE

Copyright (c) 2023 Thomas Munzer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Description

## Usage

These scripts are using the [mistapi Python package](https://pypi.org/project/mistapi/) to manage the authentication process with the Mist Cloud.
This package can use API Token authentication or Login/Password:

- saved in a `.mist_env` file located in your home folder (see below for the env file description)
- saved in a file and passed with the `-e` or `--env` parameter to the script (see below for the env file description)
- if no env file is found, the script will ask for the Login/Passwd

## Environment File

The environment file can be used to store all the information requested by the scripts. It can be used to easily store and used different environments and automate the execution of the scripts without having to save credential information in the script itself.
| Variable Name | Type | Default | Comment |
| ------------- | ---- | ------ | ------- |
MIST_HOST | string | None | The Mist Cloud to use. It must be the "api" one (e.g. `api.mist.com`, `api.eu.mist.com`, ...) |
MIST_APITOKEN | string | None | The API Token to use. |
MIST_USER | string | None | The login to use if no API Token is provided (apitoken use is preferred) |
MIST_PASSWORD | string | None | The password to use if no API Token is provided (apitoken use is preferred) |
CONSOLE_LOG_LEVEL | int | 20 | The minimum log level to display on the console, using `logging` schema (0 = Disabled, 10 = Debug, 20 = Info, 30 = Warning, 40 = Error, 50 = Critical) |
LOGGING_LOG_LEVEL | int | 10 | The minimum log level to log on the file, using `logging` schema (0 = Disabled, 10 = Debug, 20 = Info, 30 = Warning, 40 = Error, 50 = Critical). This is only used when the script calling `mistapi` is using Python `logging` package and is configured to log to a file |

An example of the environment file content is:

```
MIST_HOST = api.mist.com
MIST_APITOKEN = xxxxxx
```

# Scripts

The scripts are located in the `scripts` folder. They can be used as-is, or customized if needed.
There is a short description at the beginning of each script explaining the purpose of the script, the available options, and how to use it. They are also accepting the `-h` option which will display the script help.

> **IMPORTANT NOTE**:
Each script has description and documentation at the beginning of the file. Please check this information first, it is providing useful information on how to use each script.

## Configuration
| Category | Script | Description |
| ---- | ---- | ---- |
| Configuration | [config_ap_auto_upgrade.py](scripts/orgs/config_ap_auto_upgrade.py) | Python script update the Mist AP Auto_upgrade parameters in the site settings |
| Configuration | [config_auto_site_assignment.py](scripts/orgs/config_auto_site_assignment.py) | Python script to update the org auto assignment rules |
| Configuration | [config_webhook.py](scripts/sites/config_webhook.py) | This script can be used to list/add/delete Webhooks from Org/Site |
| Orgs | [clone_template.py](scripts/orgs/clone_template.py) | Python script to clone a specific template from an organization to another (or the same) organization. |
| Orgs - Inventory | [inventory_assign.py](scripts/orgs/inventory_assign.py) | Python script to assign devices to sites from a CSV file. The devices MUST already have been claimed on the org. |
| Orgs - Inventory | [inventory_claim.py](scripts/orgs/inventory_claim.py) | Python script to claim devices to an org from a CSV file. |
| Orgs | [validate_site_variables.py](scripts/orgs/validate_site_variables.py) | Python script to validate that all the variables used in the templates used by each site are configured at the site level. The result is displayed on the console and saved in a CSV file. |
| Sites| [fix_sites_geocoding.py](scripts/orgs/fix_sites_geocoding.py) | Python script check if all the sites have geo information configured (lat/lng, country_code, timezone), and update the site information when missing. |
| Sites | [site_conf_psk.py](scripts/sites/site_conf_psk.py) |  |
| Sites | [site_conf_wlan.py](scripts/sites/site_conf_wlan.py) | This script can be used to list/add/delete an SSID from Org/Site |
| Sites | [update_sites_templates.py](scripts/sites/update_sites_templates.py) | Python script update the templates assigned to Mist Sites based on a CSV file, and/or update the auto assignment rules based on IP Subnet. |

## Backup & Restore
| Category | Script | Description |
| ---- | ---- | ---- |
| Orgs | [org_clone.py](scripts/orgs/org_clone.py) | Python script to clone a whole organization to another one. The destination org can be an existing org, or it can be created during the process. |
| Orgs | [org_migration.py](scripts/orgs/org_migration.py) | Python script to migrate a whole organization and the devices to another one. The destination org can be an existing org, or it can be created during the process. |
| Orgs | [org_complete_backup.py](scripts/orgs/org_complete_backup.py) | Python script to backup a whole organization configuration and devices. |
| Orgs | [org_complete_backup_encrypted.py](scripts/orgs/org_complete_backup_encrypted.py) | Python script to backup a whole organization configuration and devices in AES encrypted file. |
| Orgs | [org_conf_backup.py](scripts/orgs/org_conf_backup.py) | Python script to backup a whole organization. |
| Orgs | [org_conf_backup_encrypted.py](scripts/orgs/org_conf_backup_encrypted.py) | Python script to backup a whole organization in AES encrypted file. |
| Orgs | [org_conf_deploy.py](scripts/orgs/org_conf_deploy.py) | Python script to deploy organization backup/template file. |
| Orgs | [org_conf_zeroize.py](scripts/orgs/org_conf_zeroize.py) | Python script to zeroise an organization. This scrip will remove all the configuration, all the sites and all the objects from the organization. |
| Orgs | [org_inventory_backup.py](scripts/orgs/org_inventory_backup.py) | Python script to backup all the devices from an organization. It will backup the devices claim codes (if any), configuration (including position on the maps) and pictures. |
| Orgs | [org_inventory_backup_encrypted.py](scripts/orgs/org_inventory_backup_encrypted.py) | Python script to backup all the devices from an organization in AES encrypted file. It will backup the devices claim codes (if any), configuration (including position on the maps) and pictures. |
| Orgs | [org_inventory_deploy.py](scripts/orgs/org_inventory_deploy.py) | Python script to deploy organization inventory backup file. By default, this script can run in "Dry Run" mode to validate the destination org configuration and raise warning if any object from the source org is missing in the destination org. |
| Orgs | [org_inventory_restore_pictures.py](scripts/orgs/org_inventory_restore_pictures.py) | Python script to restore device images from an inventory backup file. |
| Sites | [site_conf_backup.py](scripts/sites/site_conf_backup.py) | Python script to backup a whole site. |

## Devices
| Category | Script | Description |
| ---- | ---- | ---- |
| Devices | [rename_devices.py](scripts/devices/rename_devices.py) | Python script to rename devices (AP, Switch, Router) from a CSV file. The script will automatically locate the site where the device is assigned, and update its name. |
| Devices - AP | [configure_ap_mgmt_vlan.py](scripts/devices/aps/configure_ap_mgmt_vlan.py) | Python script reconfigure Management VLAN on all the Mist APs from one or multiple sites. |
| Devices - AP | [report_power_constrained_aps.py](scripts/devices/aps/report_power_constrained_aps.py) | Python script to list APs with power constraints (with limited power supply). The result is displayed on the console and saved in a CSV file. |
| Devices - AP | [report_bssids.py](scripts/devices/aps/report_bssids.py) | Python script to list all Access Points from orgs/sites and their associated BSSIDs. |
| Devices - Gateway | [fix_gateway_backup_firmware.py](scripts/devices/gateways/fix_gateway_backup_firmware.py) | Python script trigger a snapshot/firmware backup on SRX devices. This script is using the CSV report for the report_gateway_firmware.py script to identify the SRX on which the command must be triggered. |
| Devices - Gateway | [bgp_peers_peak_values.py](scripts/devices/gateways/bgp_peers_peak_values.py) | Python script to retrieve VPN Peers statistics for gateways assigned to a site. |
| Devices - Gateway | [cluster_node_check.py](scripts/devices/gateways/cluster_node_check.py) | Python script to retrieve the role of each Gateway Cluster nodes across a whole Organization. |
| Devices - Gateway | [report_gateway_firmware.py](scripts/devices/gateways/report_gateway_firmware.py) | Python script to report the firmware deployed on all the SRX for a specified org/site with, for each Module, the Running Version, the Backup version, the Pending version, and some other information |
| Devices - Switch | [check_local_commit_events.py](scripts/devices/switches/check_local_commit_events.py) | This script can be used to retrieve and save into a file the CLI Commit events (commit done locally one the switches) for all the switches belonging to a Mist Organization. |
| Devices - Gateway | [fix_switch_backup_firmware.py](scripts/devices/gateways/fix_switch_backup_firmware.py) | Python script trigger a snapshot/firmware backup on EX devices. This script is using the CSV report for the report_switch_firmware.py script to identify the EX on which the command must be triggered. |
| Devices - Switch | [update_port_config.py](scripts/devices/switches/update_port_config.py) | Python script to reconfigure switch interfaces based on a CSV file. The script will create or replace device override at the switch level to reconfigure the interfaces. |
| Devices - Switch | [toggle_poe.py](scripts/devices/switches/toggle_poe.py) | Python script to enable/disable/toggle PoE for a specified Port Profile in a Switch Template. |
| Devices - Switch | [report_switch_firmware.py](scripts/devices/switches/report_switch_firmware.py) | Python script to generates a list of all the switches for a specified org/site with the snapshot/backup status |

## Imports
| Category | Script | Description |
| ---- | ---- | ---- |
| Clients | [import_guest.py](scripts/clients/import_guests.py) | Python script import or update a list of Guests from a CSV file into a Mist Org or Mist Site |
| NAC | [import_client_macs.py](scripts/nac/import_client_macs.py) | Python script import import a list of MAC Address into "Client List" Mist NAC Labels from a CSV File. |
| NAC | [import_user_macs.py](scripts/nac/import_user_macs.py) | Python script import import a list of MAC Address as "NAC Endpoints" from a CSV File. |
| Orgs - Admins | [import_admins.py](scripts/orgs/admins/import_admins.py) | Python script to invite/add administrators from a CSV file. |
| Sites | [import_floorplans.py](scripts/orgs/import_floorplans.py) | Python script to import multiple Ekahau/iBwave project into Mist Organization. |
| Sites | [import_sites.py](scripts/orgs/import_sites.py) | Python script automate the sites creation in a Mist Org from a CSV file. |
| Sites | [import_psk.py](scripts/sites/import_psk.py) | This script will import PSKs from a CSV file to one or multiple sites. |

## Reports
| Category | Script | Description |
| ---- | ---- | ---- |
| Reports | [export_inventory.py](scripts/exports/export_inventory.py) | Python script to export the inventory from an organization. The export will include all the information available from the org inventory, including the claim codes. |
| Reports | [export_search.py](scripts/exports/export_search.py) | Python script to export historical data from Mist API and save the result in CSV of JSON format. |
| Reports | [list_open_events.py](https://github.com/tmunzer/mist_library/blob/master/scripts/reports/list_open_events.py) | Python script to display the list of events/alarms that are not cleared. The script is trying to correlate the different events to identify the "opening" and the "closing" events, and only display the event if it is not "cleared" for more than the `trigger_timeout`. |
| Reports | [report_app_usage.py](scripts/reports/report_app_usage.py) | Python script to generate a report of the application usage on a specific site |
| Reports | [report_rogues.py](scripts/reports/report_rogues.py) | Python script to generate a Rogue AP report. |
| Reports | [report_wlans.py](scripts/reports/report_wlans.py) | Python script to list all WLANs from orgs/sites and their parameters, and save it to a CSV file. |
