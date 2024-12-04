"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to display the list of events/alarms that are not cleared. The 
script is trying to correlate the different events to identify the "opening"
and the "closing" events, and only display the event if it is not "cleared" for
more than the `trigger_timeout`.

NOTE 1: 
This script is working with the following event types (use the "Event Options" 
with the "-t"/"--event_types=" CLI parameter to configure the script):

| Event Options               | Mist Corresponding Events                                       |
|-----------------------------|-----------------------------------------------------------------|
| GW_ARP                      | GW_ARP_RESOLVED,GW_ARP_UNRESOLVED                               |
| GW_BGP_NEIGHBOR             | GW_BGP_NEIGHBOR_DOWN,GW_BGP_NEIGHBOR_UP                         |
| GW_CONFIG                   | GW_CONFIGURED,GW_CONFIG_FAILED                                  |
| GW_TUNNEL                   | GW_TUNNEL_DOWN,GW_TUNNEL_UP                                     |
| GW_VPN_PATH                 | GW_VPN_PATH_DOWN,GW_VPN_PATH_UP                                 |
| GW_VPN_PEER                 | GW_VPN_PEER_DOWN,GW_VPN_PEER_UP                                 |
| SW_CONFIG                   | SW_CONFIGURED,SW_CONFIG_FAILED                                  |
| SW_DDOS_PROTOCOL_VIOLATION  | SW_DDOS_PROTOCOL_VIOLATION_CLEAR,SW_DDOS_PROTOCOL_VIOLATION_SET |
| SW_MAC_LIMIT                | SW_MAC_LIMIT_EXCEEDED,SW_MAC_LIMIT_RESET                        |
| SW_PORT_BPDU                | SW_PORT_BPDU_ERROR_CLEARED,SW_PORT_BPDU_BLOCKED                 |


NOTE 2:
It is possible to leverage the linux `watch` command to get the list refreshed
every X sec/min. 
When using the `watch` command, all the script parameters should be passed as
arguments:

example: 
watch -n 30 python3 ./list_open_events.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t GW_ARP,GW_BGP_NEIGHBOR,GW_TUNNEL

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Set the org_id where the webhook must be create/delete/retrieved
                            This parameter cannot be used if -s/--site_id is used.
                            If no org_id and not site_id are defined, the script will show
                            a menu to select the org/the site.

-t, --event_types=          comma separated list of event types that should be retrieved from
                            the Mist Org and processed. See the list in "Note 1" above.
                            If not defined, all the supported Event Options will be retrieved
                            and processed.
-d, --duration              duration of the events to look at
                            default: 1d
-r, --trigger_timeout=      timeout (in minutes) before listing the event if it is not cleared.
                            Set to 0 to list all the events (even the cleared ones)
                            default: 5
-v, --view=                 Type of report to display. Options are:
                                - event (default): show events per event type
                                - device: show events per device

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation 
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./list_open_events.py             
python3 ./list_open_events.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t GW_ARP,GW_BGP_NEIGHBOR,GW_TUNNEL

"""

#### IMPORTS ####
import sys
import getopt
import logging
from datetime import datetime

MISTAPI_MIN_VERSION = "0.52.4"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
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
ENV_FILE = "~/.mist_env"
CSV_FILE = "./import_user_macs.csv"
LOG_FILE = "./script.log"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### CONSTANTS ####
EVENT_TYPES_DEFINITIONS= {
"GW_ARP": ["GW_ARP_RESOLVED", "GW_ARP_UNRESOLVED"],
"GW_BGP_NEIGHBOR": ["GW_BGP_NEIGHBOR_DOWN", "GW_BGP_NEIGHBOR_UP"],
"GW_CONFIG": ["GW_CONFIGURED", "GW_CONFIG_FAILED"],
"GW_TUNNEL": ["GW_TUNNEL_DOWN", "GW_TUNNEL_UP"],
"GW_VPN_PATH": ["GW_VPN_PATH_DOWN", "GW_VPN_PATH_UP"],
"GW_VPN_PEER": ["GW_VPN_PEER_DOWN", "GW_VPN_PEER_UP"],
"SW_CONFIG": ["SW_CONFIGURED", "SW_CONFIG_FAILED"],
"SW_DDOS_PROTOCOL_VIOLATION": ["SW_DDOS_PROTOCOL_VIOLATION_CLEAR", "SW_DDOS_PROTOCOL_VIOLATION_SET"],
"SW_MAC_LIMIT": ["SW_MAC_LIMIT_EXCEEDED","SW_MAC_LIMIT_RESET"],
"SW_PORT_BPDU": ["SW_PORT_BPDU_ERROR_CLEARED", "SW_PORT_BPDU_BLOCKED"],
}


#####################################################################
#### FUNCTIONS ####
def _retrieve_events(
    mist_session: mistapi.APISession,
    org_id: str,
    event_types: str = None,
    duration: str = "1d",
    retry=False,
):
    try:
        resp = mistapi.api.v1.orgs.devices.searchOrgDeviceEvents(
            mist_session,
            org_id,
            device_type="all",
            type=event_types,
            duration=duration,
            limit=1000
        )
        if resp.status_code == 200:
            events = mistapi.get_all(mist_session, resp)
            return True, events
        elif not retry:
            return _retrieve_events(mist_session, org_id, event_types, duration, True)
        else:
            return False, None
    except Exception as e:
        LOGGER.error("Exception occurred", exc_info=True)
        if not retry:
            return _retrieve_events(mist_session, org_id, event_types, duration, True)
        else:
            return False, None



###################################################################################################
###################################################################################################
##                                                                                               ##
##                                       GATEWAY                                                 ##
##                                                                                               ##
###################################################################################################
###################################################################################################
################################# GW_ARP_UNRESOLVED
def _process_gw_arp(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_arp: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.replace("\"", "").split("network-interface:")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_gw_arp: Unable to extract peer from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_ARP_UNRESOLVED",
        "Port ID",
        event_port_id,
    )
    if event_type == "GW_ARP_UNRESOLVED":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_ARP_RESOLVED":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# GW_BGP_NEIGHBOR_DOWN
def _process_gw_bgp_neighbor(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_bgp_neighbor: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_neighbor = None
    if not event_neighbor:
        try:
            event_neighbor = event_text.split("neighbor")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_gw_bgp_neighbor: Unable to extract peer from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_BGP_NEIGHBOR_DOWN",
        "Neighbor",
        event_neighbor,
    )
    if event_type == "GW_BGP_NEIGHBOR_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_BGP_NEIGHBOR_UP":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# GW_CONFIG_FAILED
def _process_gw_config(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_config: {event}")
    event_timestamp = event.get("timestamp")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_CONFIG_FAILED",
        None,
        None
    )
    if event_type == "GW_CONFIG_FAILED":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_CONFIGURED":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# GW_TUNNEL_DOWN
def _process_gw_tunnel(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_tunnel: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_tunnel = None
    if not event_tunnel:
        try:
            event_tunnel = event_text.split("Tunnel")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_gw_tunnel: Unable to extract peer from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_TUNNEL_DOWN",
        "Tunnel",
        event_tunnel,
    )
    if event_type == "GW_TUNNEL_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_TUNNEL_UP":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# GW_VPN_PATH_DOWN
def _process_gw_vpn_path(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_vpn_path: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_path = None
    if not event_path:
        try:
            event_path = event_text.split("path")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_gw_vpn_path: Unable to extract peer from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_VPN_PATH_DOWN",
        "Path",
        event_path,
    )
    if event_type == "GW_VPN_PATH_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_VPN_PATH_UP":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


###################################################################################################
################################# GW_VPN_PEER_DOWN
def _process_gw_vpn_peer(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_vpn_peer: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_peer = None
    if not event_peer:
        try:
            event_peer = event_text.split("peer")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_gw_vpn_peer: Unable to extract peer from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_VPN_PEER_DOWN",
        "Peer",
        event_peer,
    )
    if event_type == "GW_VPN_PEER_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_VPN_PEER_UP":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


###################################################################################################
###################################################################################################
##                                                                                               ##
##                                       SWITCH                                                  ##
##                                                                                               ##
###################################################################################################
###################################################################################################
################################# SW_CONFIG_FAILED
def _process_sw_config(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_sw_config: {event}")
    event_timestamp = event.get("timestamp")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_CONFIG_FAILED",
        None,
        None,
    )
    if event_type == "SW_CONFIG_FAILED":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_CONFIGURED":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# SW_PORT_BPDU_BLOCKED
def _process_sw_mac_limit(devices: dict, event_type: str, event: dict) -> None:
    LOGGER.debug(f"_process_sw_mac_limit: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.split(";")[0].split(" ")[-1]
        except:
            LOGGER.error(
                f"_process_sw_mac_limit: Unable to extract interface name from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_MAC_LIMIT_EXCEEDED",
        "Port ID",
        event_port_id,
    )
    
    if event_type == "SW_MAC_LIMIT_EXCEEDED":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_MAC_LIMIT_RESET":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# SW_PORT_BPDU_BLOCKED
def _process_sw_port_bpdu(devices: dict, event_type: str, event: dict) -> None:
    LOGGER.debug(f"_process_sw_port_bpdu: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.split("Interface")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_sw_port_bpdu: Unable to extract interface name from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_PORT_BPDU_BLOCKED",
        "Port ID",
        event_port_id,
    )
    
    if event_type == "SW_PORT_BPDU_BLOCKED":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_PORT_BPDU_ERROR_CLEARED":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
################################# SW_PORT_BPDU_BLOCKED
def _process_sw_ddos_protocol_violation(devices: dict, event_type: str, event: dict) -> None:
    LOGGER.debug(f"_process_sw_ddos_protocol_violation: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_protocol_name = event.get("protocol_name")
    if not event_protocol_name:
        try:
            event_protocol_name = event_text.split("protocol/exception")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_sw_ddos_protocol_violation: Unable to extract interface name from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_DDOS_PROTOCOL_VIOLATION_SET",
        "Protocol Name",
        event_protocol_name,
    )
    
    if event_type == "SW_DDOS_PROTOCOL_VIOLATION_SET":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_DDOS_PROTOCOL_VIOLATION_CLEAR":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
###################################################################################################
##                                                                                               ##
##                                       COMMON                                                  ##
##                                                                                               ##
###################################################################################################
###################################################################################################
def _check_device_events(
    devices: dict, 
    event_device_type: str, 
    event_device_mac: str, 
    event_type:str,
    event_identifier_header:str=None,
    event_identifier:str=None,
) -> dict:
    if event_identifier:
        if not devices[event_device_type][event_device_mac]["events"].get(event_type):
            devices[event_device_type][event_device_mac]["events"][event_type] = {"identifier_header": event_identifier_header}
        device_event = devices[event_device_type][event_device_mac]["events"][event_type]
        if not device_event.get(event_identifier):
            device_event[event_identifier] = {"status": None, "triggered": 0, "cleared": 0, "last_change": -1}
        return device_event[event_identifier]
    else:
        if not devices[event_device_type][event_device_mac]["events"].get(event_type):
            devices[event_device_type][event_device_mac]["events"][event_type] = {"identifier_header": event_identifier_header, "status": None, "triggered": 0, "cleared": 0, "last_change": -1 }
        return devices[event_device_type][event_device_mac]["events"][event_type]

def _check_device(
    devices: dict,
    event: dict,
):
    event_site_id = event.get("site_id")
    event_device_mac = event.get("mac")
    event_device_type = event.get("device_type")
    event_device_model = event.get("device_model")
    event_device_version = event.get("device_version")
    if not devices.get(event_device_type):
        devices[event_device_type] = {}
    if not devices[event_device_type].get(event_device_mac):
        devices[event_device_type][event_device_mac] = {"model": None, "version": None, "site_id":None, "events":{}}
    if event_device_model:
        devices[event_device_type][event_device_mac]["model"] = event_device_model
    if event_device_version:
        devices[event_device_type][event_device_mac]["version"] = event_device_version
    if event_site_id:
        devices[event_device_type][event_device_mac]["site_id"] = event_site_id


def _process_events(events: list) -> dict:
    device_events = {"gateway": {}, "switch": {}, "ap": {}}
    for event in events:
        event_type = event.get("type")
        if event_type.startswith("GW_ARP"):
            _process_gw_arp(device_events, event_type, event)
        elif event_type.startswith("GW_BGP_NEIGHBOR"):
            _process_gw_bgp_neighbor(device_events, event_type, event)
        elif event_type.startswith("GW_CONFIG"):
            _process_gw_config(device_events, event_type, event)
        elif event_type.startswith("GW_TUNNEL"):
            _process_gw_tunnel(device_events, event_type, event)
        elif event_type.startswith("GW_VPN_PATH"):
            _process_gw_vpn_path(device_events, event_type, event)
        elif event_type.startswith("GW_VPN_PEER"):
            _process_gw_vpn_peer(device_events, event_type, event)

        elif event_type.startswith("SW_CONFIG"):
            _process_sw_config(device_events, event_type, event)
        elif event_type.startswith("SW_DDOS_PROTOCOL_VIOLATION"):
            _process_sw_ddos_protocol_violation(device_events, event_type, event)
        elif event_type.startswith("SW_MAC_LIMIT"):
            _process_sw_mac_limit(device_events, event_type, event)
        elif event_type.startswith("SW_PORT_BPDU"):
            _process_sw_port_bpdu(device_events, event_type, event)
    return device_events

def _display_device_results(device_events:dict, raised_timeout:int):
    headers = [
        "Event Type",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change"
    ]
    now = datetime.now()
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                data = []
                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    if event_data.get("identifier_header"):
                        for event_identifier, event_identifier_data in event_data.items():
                            if event_identifier != "identifier_header":
                                delta_time = (now - event_identifier_data.get("last_change")).total_seconds()
                                if raised_timeout == 0 or (
                                    delta_time >= (raised_timeout * 60) and event_identifier_data.get("status")=="triggered"
                                    ):
                                    data.append([
                                        event_type,
                                        f"{event_data['identifier_header']} {event_identifier}",
                                        event_identifier_data.get("status"),
                                        event_identifier_data.get("triggered"),
                                        event_identifier_data.get("cleared"),
                                        event_identifier_data.get("last_change"),
                                    ])
                    else:
                        delta_time = (now - event_data.get("last_change")).total_seconds()
                        if raised_timeout == 0 or (
                            delta_time >= (raised_timeout * 60) and event_data.get("status")=="triggered" 
                            ):
                            data.append([
                                event_type,
                                "",
                                event_data.get("status"),
                                event_data.get("triggered"),
                                event_data.get("cleared"),
                                event_data.get("last_change"),
                            ])
                if data:
                    print()
                    print()
                    print("".center(80, "─"))
                    print()
                    print(f"site_id: {device_data.get('site_id')}")
                    print(f"{device_type} {device_mac} (model : {device_data.get('model')}, version: {device_data.get('version')})")
                    print()
                    print(mistapi.cli.tabulate(data, headers=headers, tablefmt="rounded_grid"))

def _display_event_results(device_events:dict, raised_timeout:int):    
    headers = [
        "Site ID",
        "Device MAC",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change"
    ]
    event_reports = {}
    now = datetime.now()
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    if event_type not in event_reports:
                        event_reports[event_type] = []
                    if event_data.get("identifier_header"):
                        for event_identifier, event_identifier_data in event_data.items():
                            if event_identifier != "identifier_header":
                                delta_time = (now - event_identifier_data.get("last_change")).total_seconds()
                                if raised_timeout == 0 or (
                                    delta_time >= (raised_timeout * 60) and event_identifier_data.get("status")=="triggered" 
                                    ):
                                    event_reports[event_type].append([
                                        device_data.get('site_id'),
                                        device_mac,
                                        f"{event_data['identifier_header']} {event_identifier}",
                                        event_identifier_data.get("status"),
                                        event_identifier_data.get("triggered"),
                                        event_identifier_data.get("cleared"),
                                        event_identifier_data.get("last_change"),
                                    ])
                    else:
                        delta_time = (now - event_data.get("last_change")).total_seconds()
                        if raised_timeout == 0 or (
                            delta_time >= (raised_timeout * 60) and event_data.get("status")=="triggered" 
                            ):
                            event_reports[event_type].append([
                                    device_data.get('site_id'),
                                    device_mac,
                                    "",
                                    event_data.get("status"),
                                    event_data.get("triggered"),
                                    event_data.get("cleared"),
                                    event_data.get("last_change"),
                                ])
    for event_type, report in event_reports.items():
        if report:
            print()
            print()
            print("".center(80, "─"))
            print()
            print(f"Event Type: {event_type}")
            print()
            print(mistapi.cli.tabulate(report, headers=headers, tablefmt="rounded_grid"))



###################################################################################################
################################# START
def start(
    mist_session: mistapi.APISession,
    org_id: str,
    event_types: str = None,
    duration: str = "1d",
    raised_timeout: int = 5,
    view: str = "event"
):
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]

    success, events = _retrieve_events(mist_session, org_id, event_types, duration)
    try:
        events = sorted(events, key=lambda x: x["timestamp"])
    except:
        CONSOLE.critical("Unable to process the Mist events")
        LOGGER.debug(events)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(255)

    if not success:
        CONSOLE.error("Unable to retrieve device events")
        sys.exit(0)
    else:
        device_events = _process_events(events)
        if view == "device":
            _display_device_results(device_events, raised_timeout)
        else:
            _display_event_results(device_events, raised_timeout)


def usage(error_message: str = None):
    """
    show script usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to display the list of events/alarms that are not cleared. The 
script is trying to correlate the different events to identify the "opening"
and the "closing" events, and only display the event if it is not "cleared" for
more than the `trigger_timeout`.

NOTE 1: 
This script is working with the following event types (use the "Event Options" 
with the "-t"/"--event_types=" CLI parameter to configure the script):

| Event Options               | Mist Corresponding Events                                       |
|-----------------------------|-----------------------------------------------------------------|
| GW_ARP                      | GW_ARP_RESOLVED,GW_ARP_UNRESOLVED                               |
| GW_BGP_NEIGHBOR             | GW_BGP_NEIGHBOR_DOWN,GW_BGP_NEIGHBOR_UP                         |
| GW_CONFIG                   | GW_CONFIGURED,GW_CONFIG_FAILED                                  |
| GW_TUNNEL                   | GW_TUNNEL_DOWN,GW_TUNNEL_UP                                     |
| GW_VPN_PATH                 | GW_VPN_PATH_DOWN,GW_VPN_PATH_UP                                 |
| GW_VPN_PEER                 | GW_VPN_PEER_DOWN,GW_VPN_PEER_UP                                 |
| SW_CONFIG                   | SW_CONFIGURED,SW_CONFIG_FAILED                                  |
| SW_DDOS_PROTOCOL_VIOLATION  | SW_DDOS_PROTOCOL_VIOLATION_CLEAR,SW_DDOS_PROTOCOL_VIOLATION_SET |
| SW_MAC_LIMIT                | SW_MAC_LIMIT_EXCEEDED,SW_MAC_LIMIT_RESET                        |
| SW_PORT_BPDU                | SW_PORT_BPDU_ERROR_CLEARED,SW_PORT_BPDU_BLOCKED                 |

NOTE 2:
It is possible to leverage the linux `watch` command to get the list refreshed
every X sec/min. 
When using the `watch` command, all the script parameters should be passed as
arguments:

example: 
watch -n 30 python3 ./list_open_events.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t GW_ARP,GW_BGP_NEIGHBOR,GW_TUNNEL

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Set the org_id where the webhook must be create/delete/retrieved
                            This parameter cannot be used if -s/--site_id is used.
                            If no org_id and not site_id are defined, the script will show
                            a menu to select the org/the site.

-t, --event_types=          comma separated list of event types that should be retrieved from
                            the Mist Org and processed. See the list in "Note 1" above.
                            If not defined, all the supported Event Options will be retrieved
                            and processed.
-d, --duration              duration of the events to look at
                            default: 1d
-r, --trigger_timeout=      timeout (in minutes) before listing the event if it is not cleared.
                            Set to 0 to list all the events (even the cleared ones)
                            default: 5
-v, --view=                 Type of report to display. Options are:
                                - event (default): show events per event type
                                - device: show events per device

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation 
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./list_open_events.py             
python3 ./list_open_events.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t GW_ARP,GW_BGP_NEIGHBOR,GW_TUNNEL
"""
    )
    if error_message:
        CONSOLE.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """
    check the current version of the mistapi package
    """
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
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
        LOGGER.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )


###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":

    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "he:o:a:d:t:r:l:v:",
            [
                "help",
                "env_file=",
                "org_id=",
                "event_types=",
                "duration=",
                "trigger_timeout=",
                "log_file=",
                "view="
            ],
        )
    except getopt.GetoptError as err:
        usage(err)

    ENV_FILE = None
    ORG_ID = None
    EVENT_TYPES = []
    DURATION = None
    TIMEOUT = 5
    VIEW = "event"
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-e", "--env_file"]:
            ENV_FILE = a
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-t", "--event_types"]:
            for t in o.split(","):
                if EVENT_TYPES_DEFINITIONS.get(t.strip().upper()):
                    EVENT_TYPES += EVENT_TYPES_DEFINITIONS.get(t.strip().upper())
                else:
                    usage(f"Invalid -t / --event_type parameter value. Event Type {t} is not supported")
        elif o in ["-d", "--duration"]:
            DURATION = a
        elif o in ["-v", "--view"]:
            if not a.lower() in ["event", "device"]:
                    usage(f"Invalid -v / --view parameter value. View {a} is not supported")
            VIEW = a
        elif o in ["-r", "--trigger_timeout"]:
            try:
                TIMEOUT = int(a)
            except:
                usage(f"Invalid -r / --trigger_timeout parameter value. {a} is not supported")
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    if not EVENT_TYPES:
        for k, v in EVENT_TYPES_DEFINITIONS.items():
            EVENT_TYPES += v
    EVENT_TYPES = ",".join(EVENT_TYPES)
    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    apisession.login()
    start(apisession, ORG_ID, EVENT_TYPES, DURATION, TIMEOUT, VIEW)
