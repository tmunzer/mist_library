"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to export historical data from Mist API and save the result 
in CSV of JSON format.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-m, --msp_id=       required for MSP reports. Set the msp_id    
-o, --org_id=       required for Org reports. Set the org_id    
-s, --site_id=      required for Site reports. Set the site_id    
-r, --report=       select the report to generate. Possibilities are:
                    - for MSP: 
                        orgs
                    - for Org: 
                        assets, ports, client_events, client_sessions_wireless,
                        client_wired, device_events, devices, device_last_config,
                        guests_authorizsations, alarms, sites
                    - for Site:
                        assets, calls, ports, switch_ports, 
                        client_sessions_wireless, client_events_wireless, 
                        clients_wireless, clients_wired, device_events, devices,
                        device_last_config, guests_authorizsations, alarms, 
                        device_config_history, system_events, rogues, skyatp_events, 
                        discovered_switches_metrics, discovered_switches
-q, --q_params=     list of query parameters. Please see the possible filters
                    in https://doc.mist-lab.fr
                    format: -q key1:value1 -q key2:value2 -q ...

--out_format=       define the output format (csv or json)
                    default is csv
-d, --datetime      append the current date and time (ISO format) to the
                    backup name 
-f, --file_prefix=  define the filepath/prefix filename of the file where to save
                    the data. The extension .csv or .json will automatically be 
                    added
                    default is "./export.csv"
-t, --timestamp     append the timestamp at the end of the report and summary files

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./export_search.py                  
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    --report=client_sessions_wireless \
    --q_params=duration:1w  \
    --q_params=type:GW_ARP_UNRESOLVED,GW_ARP_UNRESOLVED        

"""

#### IMPORTS ####
import sys
import json
import datetime
import csv
import os
import logging
import getopt

MISTAPI_MIN_VERSION = "0.45.1"

try:
    import mistapi
    from mistapi.__api_response import APIResponse
    from mistapi.__logger import console
except:
    print(
        """
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)


#### PARAMETERS #####

LOG_FILE = "./script.log"
ENV_FILE = os.path.join(os.path.expanduser("~"), ".mist_env")
OUT_FILE_FORMAT = "csv"
OUT_FILE_PREFIX = "./export"

#### LOGS ####
logger = logging.getLogger(__name__)
out = sys.stdout


def _query_param_input(query_param_name: str, query_param_type: type) -> any:  # type: ignore
    value = None
    while True:
        value = input(
            f"\"{query_param_name}\" ({str(query_param_type).replace('<class ', '').replace('>', '')}) : "
        )
        # TODO: process bool and int
        if type(value) is query_param_type or not value:
            return value


def _query_params(query_params_type: dict) -> dict:
    query_params_data = {}
    print()
    print("".center(80, "-"))
    resp = input("Do you want to add a query_param (y/N)? ")
    if resp.lower() == "y":
        i = 0
        query_params_list = []
        for query_param in query_params_type:
            query_params_list.append(query_param)
            print(f"{i}) {query_param}={query_params_data.get(query_param, 'Not set')}")
            i += 1
        while resp.lower() != "x":
            index = None
            print()
            resp = input(
                f'Please select a query_param to add to the request (0-{i-1}, "r" to reset the query_params, or "x" to finish): '
            )
            if resp.lower() == "r":
                query_params_data = {}
            elif resp.lower() != "x":
                try:
                    index = int(resp)
                    if index < 0 or index > i - 1:
                        console.error(
                            "Please enter a number between 0 and {i-1}, or x to finish.\r\n"
                        )
                    else:
                        query_param_name = query_params_list[index]
                        value = _query_param_input(
                            query_param_name, query_params_type[query_param_name]
                        )
                        if value:
                            query_params_data[query_param_name] = value
                except:
                    console.error("Please enter a number.\r\n")

        return query_params_data
    else:
        return query_params_data


########################################################################
#### COMMON FUNCTIONS ####
def _searchAssets(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "mac": str,
        "map_id": str,
        "device_name": str,
        "name": str,
        "ibeacon_uuid": str,
        "ibeacon_major": str,
        "ibeacon_minor": str,
        "eddystone_uid_namespace": str,
        "eddystone_uid_instance": str,
        "eddystone_url": str,
        "ap_mac": str,
        "beam": int,
        "rssi": int,
        "start": int,
        "end": int,
        "duration": str,
        "limit": int,
    }

    if func == "searchOrgAssets":
        query_params_type["site_id"] = str

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgAssets":
        return mistapi.api.v1.orgs.stats.searchOrgAssets(
            apisession,
            scope_id,
            site_id=query_params.get("site_id"),
            mac=query_params.get("mac"),
            map_id=query_params.get("map_id"),
            ibeacon_uuid=query_params.get("ibeacon_uuid"),
            ibeacon_major=query_params.get("ibeacon_major"),
            ibeacon_minor=query_params.get("ibeacon_minor"),
            eddystone_uid_namespace=query_params.get("eddystone_uid_namespace"),
            eddystone_uid_instance=query_params.get("eddystone_uid_instance"),
            eddystone_url=query_params.get("eddystone_url"),
            ap_mac=query_params.get("ap_mac"),
            beam=query_params.get("beam"),
            rssi=query_params.get("rssi"),
            start=query_params.get("start"),
            end=query_params.get("end"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteAssets":
        return mistapi.api.v1.sites.stats.searchSiteAssets(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            map_id=query_params.get("map_id"),
            ibeacon_uuid=query_params.get("ibeacon_uuid"),
            ibeacon_major=query_params.get("ibeacon_major"),
            ibeacon_minor=query_params.get("ibeacon_minor"),
            eddystone_uid_namespace=query_params.get("eddystone_uid_namespace"),
            eddystone_uid_instance=query_params.get("eddystone_uid_instance"),
            eddystone_url=query_params.get("eddystone_url"),
            ap_mac=query_params.get("ap_mac"),
            beam=query_params.get("beam"),
            rssi=query_params.get("rssi"),
            start=query_params.get("start"),
            end=query_params.get("end"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchSwOrGwPorts(
    apisession: mistapi.APISession,
    func: str,
    scope_id=None,
    query_params: dict | None = None,
):
    query_params_type = {
        "full_duplex": bool,
        "mac": str,
        "neighbor_mac": str,
        "neighbor_port_desc": str,
        "neighbor_system_name": str,
        "poe_disabled": bool,
        "poe_mode": str,
        "poe_on": bool,
        "port_id": str,
        "port_mac": str,
        "speed": int,
        "up": bool,
        "stp_state": str,
        "stp_role": str,
        "auth_state": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgSwOrGwPorts":
        return mistapi.api.v1.orgs.stats.searchOrgSwOrGwPorts(
            apisession,
            scope_id,
            full_duplex=query_params.get("full_duplex"),
            mac=query_params.get("mac"),
            neighbor_mac=query_params.get("neighbor_mac"),
            neighbor_port_desc=query_params.get("neighbor_port_desc"),
            neighbor_system_name=query_params.get("neighbor_system_name"),
            poe_disabled=query_params.get("poe_disabled"),
            poe_mode=query_params.get("poe_mode"),
            poe_on=query_params.get("poe_on"),
            port_id=query_params.get("port_id"),
            port_mac=query_params.get("port_mac"),
            speed=query_params.get("speed"),
            up=query_params.get("up"),
            stp_state=query_params.get("stp_state"),
            stp_role=query_params.get("stp_role"),
            auth_state=query_params.get("auth_state"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteSwOrGwPorts":
        return mistapi.api.v1.sites.stats.searchSiteSwOrGwPorts(
            apisession,
            scope_id,
            full_duplex=query_params.get("full_duplex"),
            mac=query_params.get("mac"),
            neighbor_mac=query_params.get("neighbor_mac"),
            neighbor_port_desc=query_params.get("neighbor_port_desc"),
            neighbor_system_name=query_params.get("neighbor_system_name"),
            poe_disabled=query_params.get("poe_disabled"),
            poe_mode=query_params.get("poe_mode"),
            poe_on=query_params.get("poe_on"),
            port_id=query_params.get("port_id"),
            port_mac=query_params.get("port_mac"),
            speed=query_params.get("speed"),
            up=query_params.get("up"),
            stp_state=query_params.get("stp_state"),
            stp_role=query_params.get("stp_role"),
            auth_state=query_params.get("auth_state"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteSwitchPorts":
        return mistapi.api.v1.sites.stats.searchSiteSwitchPorts(
            apisession,
            scope_id,
            full_duplex=query_params.get("full_duplex"),
            mac=query_params.get("mac"),
            neighbor_mac=query_params.get("neighbor_mac"),
            neighbor_port_desc=query_params.get("neighbor_port_desc"),
            neighbor_system_name=query_params.get("neighbor_system_name"),
            poe_disabled=query_params.get("poe_disabled"),
            poe_mode=query_params.get("poe_mode"),
            poe_on=query_params.get("poe_on"),
            port_id=query_params.get("port_id"),
            port_mac=query_params.get("port_mac"),
            speed=query_params.get("speed"),
            up=query_params.get("up"),
            stp_state=query_params.get("stp_state"),
            stp_role=query_params.get("stp_role"),
            auth_state=query_params.get("auth_state"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchClientWirelessSessions(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "ap": bool,
        "band": str,
        "client_family": str,
        "client_manufacture": str,
        "client_model": str,
        "client_os": str,
        "client_username": str,
        "ssid": str,
        "wlan_id": str,
        "psk_id": str,
        "psk_name": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgClientWirelessSessions":
        return mistapi.api.v1.orgs.clients.searchOrgWirelessClientSessions(
            apisession,
            scope_id,
            ap=query_params.get("ap"),
            band=query_params.get("band"),
            client_family=query_params.get("client_family"),
            client_manufacture=query_params.get("client_manufacture"),
            client_model=query_params.get("client_model"),
            client_os=query_params.get("client_os"),
            client_username=query_params.get("client_username"),
            ssid=query_params.get("ssid"),
            wlan_id=query_params.get("wlan_id"),
            psk_id=query_params.get("psk_id"),
            psk_name=query_params.get("psk_name"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteClientWirelessSessions":
        return mistapi.api.v1.sites.clients.searchSiteWirelessClientSessions(
            apisession,
            scope_id,
            ap=query_params.get("ap"),
            band=query_params.get("band"),
            client_family=query_params.get("client_family"),
            client_manufacture=query_params.get("client_manufacture"),
            client_model=query_params.get("client_model"),
            client_os=query_params.get("client_os"),
            client_username=query_params.get("client_username"),
            ssid=query_params.get("ssid"),
            wlan_id=query_params.get("wlan_id"),
            psk_id=query_params.get("psk_id"),
            psk_name=query_params.get("psk_name"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchClientEvents(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "type": bool,
        "reason_code": int,
        "ssid": str,
        "ap": str,
        "proto": str,
        "band": bool,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgClientEvents":
        return mistapi.api.v1.orgs.clients.searchOrgWirelessClientEvents(
            apisession,
            scope_id,
            type=query_params.get("type"),
            reason_code=query_params.get("reason_code"),
            ssid=query_params.get("ssid"),
            ap=query_params.get("ap"),
            proto=query_params.get("proto"),
            band=query_params.get("band"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteClientEvents":
        return mistapi.api.v1.sites.clients.searchSiteWirelessClientEvents(
            apisession,
            scope_id,
            type=query_params.get("type"),
            reason_code=query_params.get("reason_code"),
            ssid=query_params.get("ssid"),
            ap=query_params.get("ap"),
            proto=query_params.get("proto"),
            band=query_params.get("band"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchClientsWireless(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "mac": bool,
        "ip_address": int,
        "hostname": str,
        "device": str,
        "model": str,
        "ap": bool,
        "ssid": bool,
        "text": bool,
        "duration": str,
        "limit": int,
    }

    if func == "searchOrgAssets":
        query_params_type["site_id"] = str

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgClientsWireless":
        return mistapi.api.v1.orgs.clients.searchOrgWirelessClients(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            ip_address=query_params.get("ip_address"),
            hostname=query_params.get("hostname"),
            device=query_params.get("device"),
            model=query_params.get("model"),
            ap=query_params.get("ap"),
            ssid=query_params.get("ssid"),
            text=query_params.get("text"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteClientsWireless":
        return mistapi.api.v1.sites.clients.searchSiteWirelessClients(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            ip_address=query_params.get("ip_address"),
            hostname=query_params.get("hostname"),
            device=query_params.get("device"),
            model=query_params.get("model"),
            ap=query_params.get("ap"),
            ssid=query_params.get("ssid"),
            text=query_params.get("text"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchClientsWired(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "device_mac": bool,
        "mac": str,
        "port_id": str,
        "vlan": int,
        "site_id": str,
        "ip": str,
        "manufacture": str,
        "text": str,
        "duration": str,
        "limit": int,
    }

    if func == "searchOrgAssets":
        query_params_type["site_id"] = str

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgClientsWired":
        return mistapi.api.v1.orgs.wired_clients.searchOrgWiredClients(
            apisession,
            scope_id,
            site_id=query_params.get("site_id"),
            device_mac=query_params.get("device_mac"),
            mac=query_params.get("mac"),
            port_id=query_params.get("port_id"),
            vlan=query_params.get("vlan"),
            ip=query_params.get("ip"),
            manufacture=query_params.get("manufacture"),
            text=query_params.get("text"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteClientsWired":
        return mistapi.api.v1.sites.wired_clients.searchSiteWiredClients(
            apisession,
            scope_id,
            device_mac=query_params.get("device_mac"),
            mac=query_params.get("mac"),
            port_id=query_params.get("port_id"),
            vlan=query_params.get("vlan"),
            ip=query_params.get("ip"),
            manufacture=query_params.get("manufacture"),
            text=query_params.get("text"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchDeviceEvents(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "device_type": str,
        "mac": str,
        "model": str,
        "text": str,
        "type": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgDeviceEvents":
        return mistapi.api.v1.orgs.devices.searchOrgDeviceEvents(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            model=query_params.get("model"),
            text=query_params.get("text"),
            type=query_params.get("type"),
            device_type=query_params.get("device_type"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteDeviceEvents":
        return mistapi.api.v1.sites.devices.searchSiteDeviceEvents(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            model=query_params.get("model"),
            text=query_params.get("text"),
            type=query_params.get("type"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchDevices(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "hostname": str,
        "site_id": str,
        "model": str,
        "mac": str,
        "version": str,
        "power_constrained": bool,
        "ip_address": str,
        "mxtunnel_status": str,
        "mxedge_id": str,
        "lldp_system_name": str,
        "lldp_system_desc": str,
        "lldp_port_id": str,
        "lldp_mgmt_addr": str,
        "band_24_bandwith": int,
        "band_5_bandwith": int,
        "band_6_bandwith": int,
        "band_24_channel": int,
        "band_5_channel": int,
        "band_6_channel": int,
        "eth0_port_speed": int,
        "duration": str,
        "limit": int,
    }

    if func == "searchOrgDevices":
        query_params_type["site_id"] = str

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgDevices":
        return mistapi.api.v1.orgs.devices.searchOrgDevices(
            apisession,
            scope_id,
            site_id=query_params.get("site_id"),
            hostname=query_params.get("hostname"),
            model=query_params.get("model"),
            mac=query_params.get("mac"),
            version=query_params.get("version"),
            power_constrained=query_params.get("power_constrained"),
            ip_address=query_params.get("ip_address"),
            mxtunnel_status=query_params.get("mxtunnel_status"),
            mxedge_id=query_params.get("mxedge_id"),
            lldp_system_name=query_params.get("lldp_system_name"),
            lldp_system_desc=query_params.get("lldp_system_desc"),
            lldp_port_id=query_params.get("lldp_port_id"),
            lldp_mgmt_addr=query_params.get("lldp_mgmt_addr"),
            band_24_bandwith=query_params.get("band_24_bandwith"),
            band_5_bandwith=query_params.get("band_5_bandwith"),
            band_6_bandwith=query_params.get("band_6_bandwith"),
            band_24_channel=query_params.get("band_24_channel"),
            band_5_channel=query_params.get("band_5_channel"),
            band_6_channel=query_params.get("band_6_channel"),
            eth0_port_speed=query_params.get("eth0_port_speed"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteDevices":
        return mistapi.api.v1.sites.devices.searchSiteDevices(
            apisession,
            scope_id,
            hostname=query_params.get("hostname"),
            model=query_params.get("model"),
            mac=query_params.get("mac"),
            version=query_params.get("version"),
            power_constrained=query_params.get("power_constrained"),
            ip_address=query_params.get("ip_address"),
            mxtunnel_status=query_params.get("mxtunnel_status"),
            mxedge_id=query_params.get("mxedge_id"),
            lldp_system_name=query_params.get("lldp_system_name"),
            lldp_system_desc=query_params.get("lldp_system_desc"),
            lldp_port_id=query_params.get("lldp_port_id"),
            lldp_mgmt_addr=query_params.get("lldp_mgmt_addr"),
            band_24_bandwith=query_params.get("band_24_bandwith"),
            band_5_bandwith=query_params.get("band_5_bandwith"),
            band_6_bandwith=query_params.get("band_6_bandwith"),
            band_24_channel=query_params.get("band_24_channel"),
            band_5_channel=query_params.get("band_5_channel"),
            band_6_channel=query_params.get("band_6_channel"),
            eth0_port_speed=query_params.get("eth0_port_speed"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchDeviceLastConfigs(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {"device_type": str, "mac": str, "duration": str, "limit": int}

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgDeviceLastConfigs":
        return mistapi.api.v1.orgs.devices.searchOrgDeviceLastConfigs(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteDeviceLastConfigs":
        return mistapi.api.v1.sites.devices.searchSiteDeviceLastConfigs(
            apisession,
            scope_id,
            mac=query_params.get("mac"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchGuestAuthorization(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "wlan_id": str,
        "auth_method": str,
        "ssid": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgGuestAuthorization":
        return mistapi.api.v1.orgs.guests.searchOrgGuestAuthorization(
            apisession,
            scope_id,
            wlan_id=query_params.get("wlan_id"),
            auth_method=query_params.get("auth_method"),
            ssid=query_params.get("ssid"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteGuestAuthorization":
        return mistapi.api.v1.sites.guests.searchSiteGuestAuthorization(
            apisession,
            scope_id,
            wlan_id=query_params.get("wlan_id"),
            auth_method=query_params.get("auth_method"),
            ssid=query_params.get("ssid"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


def _searchAlarms(
    apisession: mistapi.APISession,
    func: str,
    scope_id: str,
    query_params: dict | None = None,
):
    query_params_type = {"type": str, "duration": str, "limit": int}

    if func == "searchOrgAlarms":
        query_params_type["site_id"] = str

    if not query_params:
        query_params = _query_params(query_params_type)

    if func == "searchOrgAlarms":
        return mistapi.api.v1.orgs.alarms.searchOrgAlarms(
            apisession,
            scope_id,
            site_id=query_params.get("site_id"),
            type=query_params.get("type"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )
    elif func == "searchSiteAlarms":
        return mistapi.api.v1.sites.alarms.searchSiteAlarms(
            apisession,
            scope_id,
            type=query_params.get("type"),
            duration=query_params.get("duration", "1d"),
            limit=query_params.get("limit", 1000),
        )


########################################################################
#### ORG FUNCTIONS ####
def _searchOrgSites(
    apisession: mistapi.APISession, org_id: str, query_params: dict | None = None
):
    query_params_type = {
        "analytic_enabled": bool,
        "app_waking": bool,
        "asset_enabled": bool,
        "auto_upgrade_enabled": bool,
        "auto_upgrade_version": str,
        "country_code": str,
        "honeypot_enabled": bool,
        "locate_unconnected": bool,
        "mesh_enabled": bool,
        "rogue_enabled": bool,
        "remote_syslog_enabled": bool,
        "rtsa_enabled": bool,
        "vna_enabled": bool,
        "wifi_enabled": bool,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.orgs.sites.searchOrgSites(
        apisession,
        org_id,
        analytic_enabled=query_params.get("analytic_enabled"),
        app_waking=query_params.get("app_waking"),
        asset_enabled=query_params.get("asset_enabled"),
        auto_upgrade_enabled=query_params.get("auto_upgrade_enabled"),
        auto_upgrade_version=query_params.get("auto_upgrade_version"),
        country_code=query_params.get("country_code"),
        honeypot_enabled=query_params.get("honeypot_enabled"),
        locate_unconnected=query_params.get("locate_unconnected"),
        mesh_enabled=query_params.get("mesh_enabled"),
        rogue_enabled=query_params.get("rogue_enabled"),
        remote_syslog_enabled=query_params.get("remote_syslog_enabled"),
        rtsa_enabled=query_params.get("rtsa_enabled"),
        vna_enabled=query_params.get("vna_enabled"),
        wifi_enabled=query_params.get("wifi_enabled"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


########################################################################
#### SITE FUNCTIONS ####
def _searchSiteCalls(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {"mac": str, "app": str, "duration": str, "limit": int}

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.stats.searchSiteCalls(
        apisession,
        site_id,
        mac=query_params.get("mac"),
        app=query_params.get("app"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSiteDeviceConfigHistory(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {"device_type": str, "mac": str, "duration": str, "limit": int}

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.devices.searchSiteDeviceConfigHistory(
        apisession,
        site_id,
        mac=query_params.get("mac"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSiteSystemEvents(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {"type": str, "duration": str, "limit": int}

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.events.searchSiteSystemEvents(
        apisession,
        site_id,
        type=query_params.get("type"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSiteRogueEvents(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {
        "type": str,
        "ssid": str,
        "bssid": str,
        "ap_mac": str,
        "channel": int,
        "seen_on_lan": bool,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.rogues.searchSiteRogueEvents(
        apisession,
        site_id,
        type=query_params.get("type"),
        ssid=query_params.get("ssid"),
        bssid=query_params.get("bssid"),
        ap_mac=query_params.get("ap_mac"),
        channel=query_params.get("channel"),
        seen_on_lan=query_params.get("seen_on_lan"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSiteSkyatpEvents(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {
        "type": str,
        "mac": str,
        "device_mac": str,
        "threat_level": int,
        "ip_address": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.skyatp.searchSiteSkyatpEvents(
        apisession,
        site_id,
        type=query_params.get("type"),
        mac=query_params.get("mac"),
        device_mac=query_params.get("device_mac"),
        threat_level=query_params.get("threat_level"),
        ip_address=query_params.get("ip_address"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSiteDiscoveredSwitchesMetrics(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {"type": str, "duration": str, "limit": int}

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.stats.searchSiteDiscoveredSwitchesMetrics(
        apisession,
        site_id,
        type=query_params.get("type"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSiteDiscoveredSwitches(
    apisession: mistapi.APISession, site_id: str, query_params: dict | None = None
):
    query_params_type = {
        "adopted": bool,
        "system_name": str,
        "hostname": str,
        "vendor": str,
        "model": str,
        "version": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.sites.stats.searchSiteDiscoveredSwitches(
        apisession,
        site_id,
        adopted=query_params.get("adopted"),
        system_name=query_params.get("system_name"),
        hostname=query_params.get("hostname"),
        vendor=query_params.get("vendor"),
        model=query_params.get("model"),
        version=query_params.get("version"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


########################################################################
#### MSP FUNCTIONS ####
def _searchMspOrgs(
    apisession: mistapi.APISession, msp_id: str, query_params: dict | None = None
):
    query_params_type = {
        "name": str,
        "org_id": str,
        "sub_insufficient": bool,
        "trial_enabled": bool,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)

    return mistapi.api.v1.msps.orgs.searchMspOrgs(
        apisession,
        msp_id,
        name=query_params.get("name"),
        org_id=query_params.get("org_id"),
        sub_insufficient=query_params.get("sub_insufficient"),
        trial_enabled=query_params.get("trial_enabled"),
        limit=query_params.get("limit", 1000),
    )


#####################
def _search(
    scope: str,
    report: str,
    apisession: mistapi.APISession,
    scope_id: str,
    query_params: dict | None = None,
):
    if scope == "org":
        if report == "assets":
            return _searchAssets(apisession, "searchOrgAssets", scope_id, query_params)
        elif report == "ports":
            return _searchSwOrGwPorts(
                apisession, "searchOrgSwOrGwPorts", scope_id, query_params
            )
        elif report == "client_events":
            return _searchClientEvents(
                apisession, "searchOrgClientEvents", scope_id, query_params
            )
        elif report == "client_sessions_wireless":
            return _searchClientWirelessSessions(
                apisession, "searchOrgClientWirelessSessions", scope_id, query_params
            )
        elif report == "clients_wireless":
            return _searchClientsWireless(
                apisession, "searchOrgClientsWireless", scope_id, query_params
            )
        elif report == "client_wired":
            return _searchClientsWired(
                apisession, "searchOrgClientsWired", scope_id, query_params
            )
        elif report == "device_events":
            return _searchDeviceEvents(
                apisession, "searchOrgDeviceEvents", scope_id, query_params
            )
        elif report == "devices":
            return _searchDevices(
                apisession, "searchOrgDevices", scope_id, query_params
            )
        elif report == "device_last_config":
            return _searchDeviceLastConfigs(
                apisession, "searchOrgDeviceLastConfigs", scope_id, query_params
            )
        elif report == "guests_authorizsations":
            return _searchGuestAuthorization(
                apisession, "searchOrgGuestAuthorization", scope_id, query_params
            )
        elif report == "alarms":
            return _searchAlarms(apisession, "searchOrgAlarms", scope_id, query_params)
        elif report == "sites":
            return _searchOrgSites(apisession, scope_id, query_params)
    elif scope == "site":
        if report == "assets":
            return _searchAssets(apisession, "searchSiteAssets", scope_id, query_params)
        elif report == "calls":
            return _searchSiteCalls(apisession, scope_id)
        elif report == "ports":
            return _searchSwOrGwPorts(
                apisession, "searchSiteSwOrGwPorts", scope_id, query_params
            )
        elif report == "switch_ports":
            return _searchSwOrGwPorts(
                apisession, "searchSiteSwitchPorts", scope_id, query_params
            )
        elif report == "client_sessions_wireless":
            return _searchClientWirelessSessions(
                apisession, "searchSiteClientWirelessSessions", scope_id, query_params
            )
        elif report == "client_events_wireless":
            return _searchClientEvents(
                apisession, "searchSiteClientEvents", scope_id, query_params
            )
        elif report == "clients_wireless":
            return _searchClientsWireless(
                apisession, "searchSiteClientsWireless", scope_id, query_params
            )
        elif report == "clients_wired":
            return _searchClientsWired(
                apisession, "searchSiteClientsWired", scope_id, query_params
            )
        elif report == "device_events":
            return _searchDeviceEvents(
                apisession, "searchSiteDeviceEvents", scope_id, query_params
            )
        elif report == "devices":
            return _searchDevices(
                apisession, "searchSiteDevices", scope_id, query_params
            )
        elif report == "device_last_config":
            return _searchDeviceLastConfigs(
                apisession, "searchOrgDeviceLastConfigs", scope_id, query_params
            )
        elif report == "guests_authorizsations":
            return _searchGuestAuthorization(
                apisession, "searchSiteGuestAuthorization", scope_id, query_params
            )
        elif report == "alarms":
            return _searchAlarms(apisession, "searchSiteAlarms", scope_id, query_params)
        elif report == "device_config_history":
            return _searchSiteDeviceConfigHistory(apisession, scope_id, query_params)
        elif report == "system_events":
            return _searchSiteSystemEvents(apisession, scope_id, query_params)
        elif report == "rogues":
            return _searchSiteRogueEvents(apisession, scope_id, query_params)
        elif report == "skyatp_events":
            return _searchSiteSkyatpEvents(apisession, scope_id, query_params)
        elif report == "discovered_switches_metrics":
            return _searchSiteDiscoveredSwitchesMetrics(
                apisession, scope_id, query_params
            )
        elif report == "discovered_switches":
            return _searchSiteDiscoveredSwitches(apisession, scope_id, query_params)
    elif scope == "msp":
        if report == "orgs":
            return _searchMspOrgs(apisession, scope_id, query_params)


####################
## PROGRESS BAR
def _progress_bar_update(count: int, total: int, size: int):
    if total == 0:
        return
    elif count > total:
        count = total
    x = int(size * count / total)
    out.write(f"Progress: ".ljust(10))
    out.write(f"[{'█'*x}{'.'*(size-x)}]")
    out.write(f"{count}/{total}\r".rjust(19))
    out.flush()


def _progress_bar_end(total: int, size: int):
    if total == 0:
        return
    _progress_bar_update(total, total, size)
    out.write("\n")
    out.flush()


####################
## REQUEST
def _process_request(
    apisession: mistapi.APISession,
    scope: str,
    scope_id: str,
    report: str,
    query_params: dict | None = None,
):
    data = []
    start = None
    end = None

    print(" Retrieving Data from Mist ".center(80, "-"))
    print()

    # First request to get the number of entries
    response = _search(scope, report, apisession, scope_id, query_params)
    start = response.data.get("start", "N/A")
    end = response.data.get("end", "N/A")
    data = data + response.data["results"]

    # Variables and function for the progress bar
    size = 50
    i = 1
    total = response.data["total"]
    limit = response.data["limit"]
    if total:
        _progress_bar_update(i * limit, total, size)

        # request the rest of the data
        while response.next:
            response = mistapi.get_next(apisession, response)
            data = data + response.data["results"]
            i += 1
            _progress_bar_update(i * limit, total, size)
        # end the progress bar
        _progress_bar_end(total, size)
        print()
        return start, end, data
    else:
        console.warning("There is no results for this search...")
        sys.exit(0)


####################
## SAVE TO FILE
def _save_as_csv(start: float, end: float, data: list, report: str, query_params: dict, file_prefix:str,append_dt: bool, append_ts:bool):
    headers = []
    size = 50
    total = len(data)
    print(" Saving Data ".center(80, "-"))
    print()
    print("Generating CSV Headers ".ljust(80, "."))
    i = 0
    for entry in data:
        for key in entry:
            if not key in headers:
                headers.append(key)
        i += 1
        _progress_bar_update(i, total, size)
    _progress_bar_end(total, size)
    print()
    print("Saving to file ".ljust(80, "."))
    i = 0
    if append_dt:
        backup_name = f"{file_prefix}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')}.csv"
    elif append_ts:
        backup_name = f"{file_prefix}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}.csv"
    else:
        backup_name = (f"{file_prefix}.csv")
    with open(backup_name, "w", encoding="UTF8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(
            [
                f"#Report: {report}",
                f"Params: {query_params}",
                f"start: {start}",
                f"end:{end}",
            ]
        )
        csv_writer.writerow(headers)
        for entry in data:
            tmp = []
            for header in headers:
                tmp.append(entry.get(header, ""))
            csv_writer.writerow(tmp)
            i += 1
            _progress_bar_update(i, total, size)
        _progress_bar_end(total, size)
        print()


def _save_as_json(start: float, end: float, data: list, report: str, query_params: dict,file_prefix:str,append_dt: bool, append_ts:bool):
    print(" Saving Data ".center(80, "-"))
    print()
    json_data = {
        "report": report,
        "query_params": json.dumps(query_params),
        "start": start,
        "end": end,
        "data": data,
    }
    if append_dt:
        backup_name = f"{file_prefix}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')}.json"
    elif append_ts:
        backup_name = f"{file_prefix}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}.json"
    else:
        backup_name = (f"{file_prefix}.json")
    with open(os.path.abspath(backup_name), "w") as f:
        json.dump(json_data, f)
    print("Done.")


####################
## MENU


def _show_menu(header: str, menu: list):
    print()
    print("".center(80, "-"))
    resp = None
    while True:
        print(f"{header}")
        i = 0
        for entry in menu:
            print(f"{i}) {entry}")
            i += 1
        resp = input(f"Please select an option (0-{i-1}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp = int(resp)
                if resp < 0 or resp >= i:
                    console.error(f"Please enter a number between 0 and {i -1}.")
                else:
                    return menu[resp]
            except:
                console.error("Please enter a number\r\n ")


def _menu(
    apisession: mistapi.APISession,
    scope: str | None,
    scope_id: str | None,
    report: str | None,
):
    menu_1 = ["msp", "org", "site"]
    menu_2 = {
        "org": [
            "assets",
            "ports",
            "client_events",
            "client_sessions_wireless",
            "client_wired",
            "device_events",
            "devices",
            "device_last_config",
            "guests_authorizsations",
            "alarms",
            "sites",
        ],
        "site": [
            "assets",
            "calls",
            "ports",
            "switch_ports",
            "client_sessions_wireless",
            "client_events_wireless",
            "clients_wireless",
            "clients_wired",
            "device_events",
            "devices",
            "device_last_config",
            "guests_authorizsations",
            "alarms",
            "device_config_history",
            "system_events",
            "rogues",
            "skyatp_events",
            "discovered_switches_metrics",
            "discovered_switches",
        ],
        "msp": ["orgs"],
    }
    menu_2["org"].sort()
    menu_2["site"].sort()
    menu_2["msp"].sort()
    if not scope:
        scope = _show_menu("", menu_1)
    if not scope_id:
        if scope == "org":
            scope_id = mistapi.cli.select_org(apisession)[0]
        elif scope == "site":
            scope_id = mistapi.cli.select_site(apisession)[0]
    if not report:
        report = _show_menu("", menu_2[scope])  # type: ignore
    return scope, scope_id, report


def start(
    apisession,
    scope: str | None = None,
    scope_id: str | None = None,
    report: str | None = None,
    query_params: dict | None = None,
    file_prefix: str = OUT_FILE_PREFIX,
    append_dt: bool = False,
    append_ts: bool = False
):
    scope, scope_id, report = _menu(apisession, scope, scope_id, report)
    start, end, data = _process_request(apisession, scope, scope_id, report, query_params)  # type: ignore
    if OUT_FILE_FORMAT == "csv":
        _save_as_csv(start, end, data, report, query_params, file_prefix, append_dt,append_ts )  # type: ignore
    elif OUT_FILE_FORMAT == "json":
        _save_as_json(start, end, data, report, query_params, file_prefix, append_dt,append_ts)  # type: ignore
    else:
        console.error(f"file format {OUT_FILE_FORMAT} not supported")


def usage(message: str = None):
    """Function to display Help"""
    print(
        f"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to export historical data from Mist API and save the result 
in CSV of JSON format.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-m, --msp_id=       required for MSP reports. Set the msp_id    
-o, --org_id=       required for Org reports. Set the org_id    
-s, --site_id=      required for Site reports. Set the site_id    
-r, --report=       select the report to generate. Possibilities are:
                    - for MSP: 
                        orgs
                    - for Org: 
                        assets, ports, client_events, client_sessions_wireless,
                        client_wired, device_events, devices, device_last_config,
                        guests_authorizsations, alarms, sites
                    - for Site:
                        assets, calls, ports, switch_ports, 
                        client_sessions_wireless, client_events_wireless, 
                        clients_wireless, clients_wired, device_events, devices,
                        device_last_config, guests_authorizsations, alarms, 
                        device_config_history, system_events, rogues, skyatp_events, 
                        discovered_switches_metrics, discovered_switches
-q, --q_params=     list of query parameters. Please see the possible filters
                    in https://doc.mist-lab.fr
                    format: -q key1:value1 -q key2:value2 -q ...

--out_format=       define the output format (csv or json)
                    default is csv
-f, --file_prefix=  define the filepath/prefix filename of the file where to save
                    the data. The extension .csv or .json will automatically be 
                    added
                    default is {OUT_FILE_PREFIX}
-d, --datetime      append the current date and time (ISO format) to the
                    backup name 
-t, --timestamp     append the timestamp at the end of the report and summary files

-l, --log_file=     define the filepath/filename where to write the logs
                    default is {LOG_FILE}
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is {ENV_FILE}

-------
Examples:
python3 ./export_search.py                  
python3 ./export_searchs.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    --report=client_sessions_wireless \
    --q_params=duration:1w  \
    --q_params=type:GW_ARP_UNRESOLVED,GW_ARP_UNRESOLVED
    """
    )
    if message:
        console.error(message)
    sys.exit(0)


def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        logger.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hm:o:s:r:f:e:l:q:dt",
            [
                "help",
                "msp_id=",
                "org_id=",
                "site_id=",
                "report=",
                "out_format=",
                "file_prefix=",
                "env=",
                "log_file=",
                "q_params=",
                "timestamp",
                "datetime"
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    SCOPE = None
    SCOPE_ID = None
    REPORT = None
    QUERY_PARAMS = {}
    APPEND_TS = False
    APPEND_DT = False
    for o, a in opts:  # type: ignore
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-m", "--msp_id"]:
            if SCOPE:
                usage("Only one id can be configured")
            SCOPE = "msp"
            SCOPE_ID = a
        elif o in ["-o", "--org_id"]:
            if SCOPE:
                usage("Only one id can be configured")
            SCOPE = "org"
            SCOPE_ID = a
        elif o in ["-s", "--site_id"]:
            if SCOPE:
                usage("Only one id can be configured")
            SCOPE = "site"
            SCOPE_ID = a
        elif o in ["-r", "--report"]:
            REPORT = a
        elif o in ["--out_format"]:
            if a in ["csv", "json"]:
                OUT_FILE_FORMAT = a
            else:
                usage(f"Out format {a} not supported")
        elif o in ["-f", "--file_prefix"]:
            OUT_FILE_PREFIX = a
        elif o in ["-d", "--datetime"]:
            if APPEND_TS:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                APPEND_DT = True
        elif o in ["-t", "--timestamp"]:
            if APPEND_DT:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                APPEND_TS = True
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-q", "--q_params"]:
            if a.count(":") != 1:
                usage(f"Unable to process param {a}")
            else:
                QUERY_PARAMS[a.split(":")[0]] = a.split(":")[1]
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    start(apisession, SCOPE, SCOPE_ID, REPORT, QUERY_PARAMS, OUT_FILE_PREFIX, APPEND_DT, APPEND_TS)
