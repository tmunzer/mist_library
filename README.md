
# Mist_library
Examples of Python scripts using the [Mist APIs](https://www.mist.com)
These scripts are using the [mistapi Python package](https://pypi.org/project/mistapi/) to simplify the authentication process.

# Menu
1. [Description](#description)
1.1 [Usage](#usage)
1.2 [Environment File](#environment-file)
2. [Scripts](#scripts)
2.1 [Devices](#devices)
2.2 [Exports](#exports)
2.3 [Orgs](#orgs)
2.4 [Sites](#sites)
2.5 [Reports](#reports)

## MIT LICENSE
 
Copyright (c) 2023 Thomas Munzer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the  Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Description
## Usage
These scripts are using the [mistapi Python package](https://pypi.org/project/mistapi/) to manage the authentication process with the Mist Cloud.
This package can use API Token authentication or Login/Password:
- saved in a `.mist_env` file located in your home folder (see below for the env file description)
- saved in a file and passed with the `-e` or `--env` parameter to the script (see below for the env file description)
- if no env file is found, the script will ask for the Login/Passws

## Environment File
The environment file can be used to store all the information requested by the scripts. It can be used to easily store and used different environments and automate the excecution of the scripts without having to save credential information in the script itself.
| Variable Name | Type | Default | Comment |
| ------------- | ---- |  ------ | ------- |
MIST_HOST | string | None | The Mist Cloud to use. It must be the "api" one (e.g. `api.mist.com`, `api.eu.mist.com`, ...) |
MIST_APITOKEN | string | None | The API Token to use.  |
MIST_USER | string | None | The login to use if no API Token is provided (apitoken use is prefered) |
MIST_PASSWORD | string | None | The password to use if no API Token is provided (apitoken use is prefered) |
CONSOLE_LOG_LEVEL | int | 20 | The minimum log level to display on the console, using `logging` schema (0 = Disabled, 10 = Debug, 20 = Info, 30 = Warning, 40 = Error, 50 = Critical) |
LOGGING_LOG_LEVEL | int | 10 | The minimum log level to log on the file, using `logging` schema (0 = Disabled, 10 = Debug, 20 = Info, 30 = Warning, 40 = Error, 50 = Critical). This is only used when the script calling `mistapi` is using Python `logging` package and is configured to log to a file |

An example of the environment file content is:
```
MIST_HOST = api.mist.com
MIST_APITOKEN = xxxxxx
MIST_ORG_ID = 203d3d02-xxxx-xxxx-xxxx-76896a3330f4
```

# Scripts
The scripts are located in the `scripts` folder. They can be used as-is, or customized if needed.
There is a short desccription at the beginning of each script explaining the purpose of the script, the available options, and how to use it. They are also accepting the `-h` option which will display the script help.

## Devices
- APs
    - **configure_ap_mgmt_vlan.py**: Python script reconfigure Management VLAN on all the Mist APs from one or multiple sites.
- Switches
    - **toggle_poe.py**: Python script to enable/disable/toggle PoE for a specified Port Profile in a Switch Template.
## Exports
- **export_inventory.py**: Python script to export the inventory from an organization. The export will include all the information available from the org inventory, including the claim codes.
- **export_search.py**: Python script to export historical data from Mist API and save the result in CSV of JSON format.
## Orgs
- **admin_import.py**: Python script to invite/add adminsitrators from a CSV file.
- **configure_ap_auto_upgrade.py**: Python script update the Mist AP Auto_upgrade parameters in the site settings
- **configure_auto_site_assignment.py**: Python script to update the org auto assignement rules
- **org_conf_backup.py**: Python script to backup a whole organization.
- **org_conf_deploy.py**: Python script to deploy organization backup/template file.
- **org_conf_zeroize.py**: Python script to zeroise an organization. This scrip will remove all the configuration, all the sites and all the objects from the organization.
- **org_inventory_backup.py**: Python script to backup all the devices from an organization. It will backup the devices claim codes (if any), configuration (including position on the maps) and pictures.
- **org_inventory_deploy.py**: Python script to deploy organization inventory backup file. By default, this script can run in "Dry Run" mode to validate the destination org configuration and raise warning if any object from the source org is missing in the destination org.
## Sites
- **import_sites.py**: Python script automate the sites creation in a Mist Org from a CSV file.
- **site_conf_backup.py**: Python script to backup a whole site.
- **site_conf_psk_import_csv.py**: This script will import PSKs from a CSV file to one or multiple sites.
- **site_conf_psk.py**:  
- **site_conf_webhook.py**: This script can be used to list/add/delete Webhooks from Org/Site
- **site_conf_wlan.py**: This script can be used to list/add/delete an SSID from Org/Site
## Reports
- **report_app_usage.py**: Python script to generate a report of the application usage on a specific site
- **report_bssids.py**: Python script to list all Access Points from orgs/sites and their associated BSSIDs. 
- **report_rogues.py**: Python script to gerenate a Rogue AP report.
- **report_switch_snapshot.py**: Python script to gerenates a list of all the switches for a specified org/site
- **report_wlans.py**: Python script to list all WLANs from orgs/sites and their parameters, and save it to a CSV file.

