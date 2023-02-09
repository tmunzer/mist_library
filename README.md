# README NOT UP TO DATE YET


# Mist_library
Examples of Python scripts using the [Mist APIs](https://www.mist.com)
These scripts are using the [mistapi Python package](https://pypi.org/project/mistapi/) to simplify the authentication process.

## MIT LICENSE
 
Copyright (c) 2023 Thomas Munzer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the  Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Description
## Configuration
The configuration file located inside the root folder and it allows to store:
- Your Mist credentials (Login, Login/Pwd, Api Token)
- the host to reach depending on the Cloud used (US, EU) 
- the log level.

To use the configuration file, you'll have to create a file `config.py` in the root folder.
The format and explanation of the configuration file file can be found in the config_example.py file. 

## Console module 
`console.py` is a module created to easily use/test the Mist library from python CLI.

This module will:
- automatically start a session (i.e. authenticate the user based on the configuration stored in config.py or by asking credentials).
- Provide autocompletion to easily find the right syntax to use the Python3 Mist Library

This console is build to easily see the available API calls. For example:
- under ***`console.requests`*** you will find the `orgs`and `sites`parts.
- under ***`console.requests.orgs`*** you will find the different orgs objects you can call through APIs, which are `admins, licenses, settings, templates, alarmtemplates, mxclusters, sitegroups, webhooks, assetfilters, mxedges, sites, wlans, channels, mxtunnels, ssoroles, wxrules, deviceprofiles, psks, ssos, wxtags, info, rftemplates, stats, wxtunnels, inventory, secpolicies, subscriptions`
- under ***`console.requets.orgs.inventory`*** you will find the available action for this specific object, which are
`add, get, assign_macs_to_site, unassign, delete`

#### How to use it
Start the python interpreter from the Mist Library folder, and type `import console`. This will automatically initiate the library, and start the authentication (depending on your configuration).

## Demo scripts
It is a set of Python3 scripts using the Mist Library. 
The demo scripts are built to require a minimum input from the user, but they can also be totally automated and/or run by an external software.You will find some description and help at the beginning of each file.

#### Current scripts
- ***`org_admin_import.py`***
read a CSV file to automatically generate admin invitations
- ***`org_auto_site_assignment.py`***
use APIs to enable autoprovisionning feature
- ***`org_conf_backup.py`***
backup all the organisation object, maps, ... to files
- ***`org_conf_deploy.py`***
restore a backup (done with org_conf_backup.py) to an organisation
- ***`org_inventoy_backup.py`***
backup all the devices and their configuration, pictures, ... from an organisation to files
- ***`org_inventory_precheck.py`***
used to validate that the inventory restor can be done on a specific organisation. E.g. It will check that all the reqjired obejcts are present.
- ***`org_inventory_restore.py`***
restore an inventory backup (done with org_inventory_backup.py) to an organisation
- ***`org_report_rogue.py`***
generate a report (and save it as a CSV file) of all the rogue APs and clients from an organization or a site.
- ***`site_conf_psk_import_csv.py`***
read a CSV file to automatically create PSK 
- ***`site_conf_psk.py`***
use APIs to create a new PSK
- ***`site_conf_rogue.py`***
use APIs to configure Rogue detection
- ***`site_conf_webhook.py`***
use APIs to configure webhooks (org or site level). Useful to create a webhook configuration for Splunk.
- ***`site_conf_wlan.py`***
use APIs to create/delete a WLAN


