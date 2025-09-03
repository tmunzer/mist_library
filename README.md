# mist_library

Utilities and example Python scripts that use the Mist Cloud APIs (via the [`mistapi`](https://pypi.org/project/mistapi/) package) to automate configuration, backups, imports and reporting for Mist organizations and sites.

This repository collects small, focused scripts that are ready to run and easy to adapt for your environment.


## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Highlights

- Collection of scripts for: configuration, EVPN, device operations, org/site backups & restores, imports, and reports.
- Uses the [`mistapi`](https://pypi.org/project/mistapi/) Python package for authentication and API calls.
- Scripts accept an environment file or interactive credentials and support dry-run modes where applicable.

## Quick start

Prerequisites:

- Python 3.8+ (recommend 3.9+)
- A Mist API token or username/password with appropriate privileges
- Repository checked out locally

Install dependencies (recommended in a virtualenv):

```bash
python -m pip install -r requirements.txt
```

Run a script example (prints help):

```bash
python scripts/orgs/org_conf_deploy.py -h
```

Or run with a specific environment file:

```bash
python scripts/orgs/org_conf_deploy.py -e my_env_file
```

## Environment file

You can store credentials and common options in an environment file. By default the scripts look for `~/.mist_env` (scripts commonly use `ENV_FILE = "~/.mist_env"`) but you can pass `-e /path/to/env` to use a different file.

Authoritative env vars:

- `MIST_HOST` — Mist API host (for example `api.mist.com`).
- `MIST_APITOKEN` — API token (preferred authentication).
- `MIST_USER` / `MIST_PASSWORD` — username / password fallback when no token is provided.
- `MIST_VAULT_MOUNT_POINT`, `MIST_VAULT_PATH`, `MIST_VAULT_TOKEN`, `MIST_VAULT_URL` — Vault integration variables used by `mistapi` when retrieving secrets from a HashiCorp Vault instance.
- `CONSOLE_LOG_LEVEL`, `LOGGING_LOG_LEVEL` — optional numeric logging levels used in several scripts (not required by `mistapi` itself, but useful to control verbosity).

If no credentials are present in the env file, most scripts will prompt interactively for missing values or fall back to the `mistapi` login flow.

Example `~/.mist_env` (minimal):

```ini
# Required: set either MIST_APITOKEN or the user/password pair
MIST_HOST=api.mist.com
MIST_APITOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Or, alternatively:
# MIST_USER=your.username@example.com
# MIST_PASSWORD=yourpassword

# Optional logging controls used by some scripts
CONSOLE_LOG_LEVEL=20
LOGGING_LOG_LEVEL=10

# Optional: Vault integration (only if you use HashiCorp Vault with mistapi)
# MIST_VAULT_URL=https://vault.example.com
# MIST_VAULT_TOKEN=xxxxx
# MIST_VAULT_MOUNT_POINT=secret
# MIST_VAULT_PATH=secret/data/mist
```

Notes:

- The list above for [`mistapi`](https://pypi.org/project/mistapi/) env vars was verified against the installed `mistapi` package (v0.57.x). If you pin or use an older `mistapi` version, the available behavior may differ; several scripts in this repo include a `MISTAPI_MIN_VERSION` constant — check the script header for compatibility notes.

## Repository layout

- `scripts/` — main scripts grouped by topic (configuration, orgs, sites, devices, exports, reports, nac, clients)
- `utils/` — helper utilities (e.g. encryption)
- `v-tool/` — additional tooling included for convenience
- `requirements.txt` — Python dependencies

Each script contains a short header describing purpose, options and examples. Run any script with `-h` for usage details.

## Example workflows

- Backup an organization configuration:

```bash
python scripts/orgs/org_conf_backup.py -e ~/.mist_env --org-id <ORG_ID>
```

- Deploy a saved org configuration (dry-run first):

```bash
python scripts/orgs/org_conf_deploy.py -e ~/.mist_env --file backup.json --dry-run
```

- Import guests from CSV into a site:

```bash
python scripts/clients/import_guests.py -e ~/.mist_env --site <SITE_ID> --csv guests.csv
```

## Finding scripts

There are many scripts. Here are a few high-level categories (see `scripts/` for the full list):

- Configuration: `scripts/configuration/` (webhooks, auto-assignment, AP auto-upgrade)
- EVPN helpers: `scripts/configuration/evpn_topology/`
- Orgs / Backups: `scripts/orgs/` (backup, deploy, clone, inventory)
- Devices: `scripts/devices/` (AP, gateway, switch helpers)
- Imports: `scripts/clients/`, `scripts/nac/`, `scripts/sites/` (CSV-driven imports)
- Reports / Exports: `scripts/reports/`, `scripts/exports/`


## Scripts index

Below is a full index of scripts included in this repository. Each entry contains a short description and a relative link to the script.

### Organization / backup / deploy

- [scripts/orgs/org_complete_backup.py](scripts/orgs/org_complete_backup.py) — Backup an entire organization configuration and devices (combines conf + inventory backups).
- [scripts/orgs/org_complete_backup_encrypted.py](scripts/orgs/org_complete_backup_encrypted.py) — Same as `org_complete_backup.py` but writes an AES-encrypted backup.
- [scripts/orgs/org_conf_backup.py](scripts/orgs/org_conf_backup.py) — Backup organization configuration objects (sites, templates, policies, etc.).
- [scripts/orgs/org_conf_backup_encrypted.py](scripts/orgs/org_conf_backup_encrypted.py) — AES-encrypted organization configuration backup.
- [scripts/orgs/org_conf_deploy.py](scripts/orgs/org_conf_deploy.py) — Deploy an organization configuration backup/template to a destination org (supports dry-run).
- [scripts/orgs/org_conf_deploy_only.py](scripts/orgs/org_conf_deploy_only.py) — Deploy configuration objects only (helper used during deploy flows).
- [scripts/orgs/org_conf_zeroize.py](scripts/orgs/org_conf_zeroize.py) — Zeroize an organization (remove config, sites and objects).
- [scripts/orgs/org_inventory_backup.py](scripts/orgs/org_inventory_backup.py) — Backup all devices from an organization (claims, config, map positions, pictures).
- [scripts/orgs/org_inventory_backup_encrypted.py](scripts/orgs/org_inventory_backup_encrypted.py) — AES-encrypted inventory backup.
- [scripts/orgs/org_inventory_deploy.py](scripts/orgs/org_inventory_deploy.py) — Deploy inventory backup files to an organization (supports dry-run).
- [scripts/orgs/org_inventory_restore_pictures.py](scripts/orgs/org_inventory_restore_pictures.py) — Restore device images from an inventory backup.
- [scripts/orgs/org_clone.py](scripts/orgs/org_clone.py) — Clone a full organization to another org (configuration + optional creations).
- [scripts/orgs/org_migration.py](scripts/orgs/org_migration.py) — Migrate an organization and optionally its devices to another org (supports unclaim options).
- [scripts/orgs/inventory_claim.py](scripts/orgs/inventory_claim.py) — Claim devices to an org from a CSV list of claim codes.
- [scripts/orgs/inventory_assign.py](scripts/orgs/inventory_assign.py) — Assign claimed devices to sites from a CSV.
- [scripts/orgs/clone_template.py](scripts/orgs/clone_template.py) — Clone a single template (WLAN/LAN/WAN/HUB) between orgs.
- [scripts/orgs/validate_site_variables.py](scripts/orgs/validate_site_variables.py) — Validate that variables used by templates are configured at the site level.

#### Org admins

- [scripts/orgs/admins/import_admins.py](scripts/orgs/admins/import_admins.py) — Invite/add administrators from a CSV.
- [scripts/orgs/admins/uninvite_admins.py](scripts/orgs/admins/uninvite_admins.py) — Remove/uninvite administrators.


### Configuration

- [scripts/configuration/config_webhook.py](scripts/configuration/config_webhook.py) — List/add/delete org/site webhooks.
- [scripts/configuration/config_webhook_settings.json](scripts/configuration/config_webhook_settings.json) — Example/default webhook settings used by the webhook scripts.
- [scripts/configuration/config_ap_auto_upgrade.py](scripts/configuration/config_ap_auto_upgrade.py) — Update AP auto-upgrade parameters in site settings.
- [scripts/configuration/config_auto_site_assignment.py](scripts/configuration/config_auto_site_assignment.py) — Update org auto-assignment rules (IP subnet based site assignment).

#### EVPN helpers

- [scripts/configuration/evpn_topology/provision_evpntoplogy_vlans.py](scripts/configuration/evpn_topology/provision_evpntoplogy_vlans.py) — Generate VLANs and VRFs for EVPN topologies.
- [scripts/configuration/evpn_topology/update_evpn_switch_ip.py](scripts/configuration/evpn_topology/update_evpn_switch_ip.py) — Update switch IP addresses inside an EVPN topology.


### Devices

- [scripts/devices/rename_devices.py](scripts/devices/rename_devices.py) — Rename devices (AP, Switch, Router) from a CSV; finds site automatically.

#### AP helpers

- [scripts/devices/aps/configure_ap_mgmt_vlan.py](scripts/devices/aps/configure_ap_mgmt_vlan.py) — Reconfigure management VLAN on APs across sites.
- [scripts/devices/aps/report_power_constrained_aps.py](scripts/devices/aps/report_power_constrained_aps.py) — Report APs with power constraints; output CSV.
- [scripts/devices/aps/report_bssids.py](scripts/devices/aps/report_bssids.py) — List APs and their BSSIDs for orgs/sites.

#### Gateway helpers

- [scripts/devices/gateways/report_gateway_firmware.py](scripts/devices/gateways/report_gateway_firmware.py) — Report SRX firmware versions and snapshot/backup status.
- [scripts/devices/gateways/cluster_node_check.py](scripts/devices/gateways/cluster_node_check.py) — Report cluster node roles across an org.
- [scripts/devices/gateways/fix_gateway_backup_firmware.py](scripts/devices/gateways/fix_gateway_backup_firmware.py) — Trigger snapshot/firmware backup on SRX devices.
- [scripts/devices/gateways/bgp_peers_peak_values.py](scripts/devices/gateways/bgp_peers_peak_values.py) — Retrieve VPN peer statistics for gateways.

#### Switch helpers

- [scripts/devices/switches/check_local_commit_events.py](scripts/devices/switches/check_local_commit_events.py) — Retrieve CLI commit events from switches in an org.
- [scripts/devices/switches/fix_switch_backup_firmware.py](scripts/devices/switches/fix_switch_backup_firmware.py) — Trigger snapshot/firmware backup on EX switches.
- [scripts/devices/switches/update_port_config.py](scripts/devices/switches/update_port_config.py) — Reconfigure switch interfaces from a CSV by creating/updating device overrides.
- [scripts/devices/switches/toggle_poe.py](scripts/devices/switches/toggle_poe.py) — Enable/disable/toggle PoE for a port profile in a switch template.
- [scripts/devices/switches/report_switch_firmware.py](scripts/devices/switches/report_switch_firmware.py) — Generate report of switch snapshot/backup status.


### Clients / NAC / Imports

- [scripts/clients/import_guests.py](scripts/clients/import_guests.py) — Import or update Guests from a CSV into an org or site.
- [scripts/nac/import_client_macs.py](scripts/nac/import_client_macs.py) — Import client MAC addresses into NAC labels from CSV.
- [scripts/nac/import_user_macs.py](scripts/nac/import_user_macs.py) — Import MAC addresses as NAC endpoints from CSV.


### Sites

- [scripts/sites/import_sites.py](scripts/sites/import_sites.py) — Create sites in an org from a CSV.
- [scripts/sites/import_floorplans.py](scripts/sites/import_floorplans.py) — Import Ekahau / iBwave floorplans into Mist.
- [scripts/sites/import_psk.py](scripts/sites/import_psk.py) — Import PSKs for sites from a CSV.
- [scripts/sites/site_conf_backup.py](scripts/sites/site_conf_backup.py) — Backup a single site's configuration.
- [scripts/sites/site_conf_psk.py](scripts/sites/site_conf_psk.py) — Site PSK configuration helper.
- [scripts/sites/site_conf_wlan.py](scripts/sites/site_conf_wlan.py) — Manage SSIDs (list/add/delete) at org/site level.
- [scripts/sites/site_conf_wlan_settings.json](scripts/sites/site_conf_wlan_settings.json) — Example WLAN settings used by scripts.
- [scripts/sites/update_sitegroups.py](scripts/sites/update_sitegroups.py) — Update the sitegroups assigned to sites from a CSV (append or replace).
- [scripts/sites/update_sites_templates.py](scripts/sites/update_sites_templates.py) — Update templates assigned to sites and auto-assignment rules from a CSV.
- [scripts/sites/fix_sites_geocoding.py](scripts/sites/fix_sites_geocoding.py) — Ensure sites have geo info (lat/lng, country_code, timezone) and fix missing data.
- [scripts/sites/not_migrated_to_mistapi/site_conf_restore.py](scripts/sites/not_migrated_to_mistapi/site_conf_restore.py) — Legacy/site-specific restore helper (not migrated to mistapi).


### Exports & Reports

- [scripts/exports/export_inventory.py](scripts/exports/export_inventory.py) — Export org inventory to CSV/JSON (includes claim codes).
- [scripts/exports/export_search.py](scripts/exports/export_search.py) — Export historical data from Mist API to CSV/JSON.
- [scripts/exports/export_org_events.py](scripts/exports/export_org_events.py) — Export organization events.
- [scripts/exports/compare_org_events_summary.py](scripts/exports/compare_org_events_summary.py) — Helper to compare/aggregate exported org event summaries.

#### Reports

- [scripts/reports/report_sites.py](scripts/reports/report_sites.py) — Generate a report of sites (resolves site group names); CSV output.
- [scripts/reports/report_sites_sles.py](scripts/reports/report_sites_sles.py) — Generate Site SLE (Service Level Expectations) reports.
- [scripts/reports/report_wlans.py](scripts/reports/report_wlans.py) — List all WLANs and parameters for orgs/sites; CSV output.
- [scripts/reports/report_inventory_site_notes.py](scripts/reports/report_inventory_site_notes.py) — Inventory report augmented with site notes and metadata.
- [scripts/reports/report_rogues.py](scripts/reports/report_rogues.py) — Generate Rogue AP reports.
- [scripts/reports/report_app_usage.py](scripts/reports/report_app_usage.py) — Application usage report for a site (hours/duration based).
- [scripts/reports/report_wlans.py](scripts/reports/report_wlans.py) — WLANs report (duplicate listing for quick access).
- [scripts/reports/list_open_events.py](scripts/reports/list_open_events.py) — Display events/alarms that are still open (tries to correlate open/close events).
- [scripts/reports/list_webhook_deliveries.py](scripts/reports/list_webhook_deliveries.py) — Extract and filter webhook deliveries; CSV export.


### Utilities

- [scripts/utils/encryption.py](scripts/utils/encryption.py) — Utility functions for AES encryption/decryption used by encrypted backups.



## Contributing

Contributions are welcome. Good ways to help:

- Open issues for bugs or feature requests
- Send small, focused pull requests that include a short description and example usage
- Add or update script documentation at the top of the script file

When editing scripts, keep backwards compatibility where possible and include tests or a smoke-check if you add complex logic.