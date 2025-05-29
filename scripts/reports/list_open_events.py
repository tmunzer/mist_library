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

| Script Event Options       | Mist Triggering Events                 | Mist Clearing Events                                          |
|----------------------------|----------------------------------------|---------------------------------------------------------------|
| AP_CONFIG                  | AP_CONFIG_FAILED                       | AP_CONFIGURED,AP_RECONFIGURED                                 |
| AP_DISCONNECTED            | AP_DISCONNECTED                        | AP_CONNECTED                                                  |
| AP_RADSEC                  | AP_RADSEC_FAILURE                      | AP_RADSEC_RECOVERY                                            |
| AP_UPGRADE                 | AP_UPGRADE_FAILED                      | AP_UPGRADED                                                   |
| GW_APPID_INSTALL           | GW_APPID_INSTALL_FAILED                | GW_APPID_INSTALLED                                            |
| GW_ARP                     | GW_ARP_UNRESOLVED                      | GW_ARP_RESOLVED                                               |
| GW_BGP_NEIGHBOR            | GW_BGP_NEIGHBOR_DOWN                   | GW_BGP_NEIGHBOR_UP                                            |
| GW_CONFIG                  | GW_CONFIG_FAILED,GW_CONFIG_LOCK_FAILED | GW_CONFIGURED,GW_RECONFIGURED                                 |
| GW_DISCONNECTED            | GW_DISCONNECTED                        | GW_CONNECTED                                                  |
| GW_FIB_COUNT               | GW_FIB_COUNT_THRESHOLD_EXCEEDED        | GW_FIB_COUNT_RETURNED_TO_NORMAL                               |
| GW_FLOW_COUNT              | GW_FLOW_COUNT_THRESHOLD_EXCEEDED       | GW_FLOW_COUNT_RETURNED_TO_NORMAL                              |
| GW_HA_CONTROL_LINK         | GW_HA_CONTROL_LINK_DOWN                | GW_HA_CONTROL_LINK_UP                                         |
| GW_HA_HEALTH_WEIGHT        | GW_HA_HEALTH_WEIGHT_LOW                | GW_HA_HEALTH_WEIGHT_RECOVERY                                  |
| GW_IDP_INSTALL             | GW_IDP_INSTALL_FAILED                  | GW_IDP_INSTALL                                                |
| GW_RECOVERY_SNAPSHOT       | GW_RECOVERY_SNAPSHOT_FAILED            | GW_RECOVERY_SNAPSHOT_SUCCEEDED,GW_RECOVERY_SNAPSHOT_NOTNEEDED |
| GW_TUNNEL                  | GW_TUNNEL_DOWN                         | GW_TUNNEL_UP                                                  |
| GW_UPGRADE                 | GW_UPGRADE_FAILED                      | GW_UPGRADED                                                   |
| GW_VPN_PATH                | GW_VPN_PATH_DOWN                       | GW_VPN_PATH_UP                                                |
| GW_VPN_PEER                | GW_VPN_PEER_DOWN                       | GW_VPN_PEER_UP                                                |
| GW_ZTP                     | GW_ZTP_FAILED                          | GW_ZTP_FINISHED                                               |
| SW_BFD_SESSION             | SW_BFD_SESSION_DISCONNECTED            | SW_BFD_SESSION_ESTABLISHED                                    |
| SW_BGP_NEIGHBOR            | SW_BGP_NEIGHBOR_DOWN                   | SW_BGP_NEIGHBOR_UP                                            |
| SW_CONFIG                  | SW_CONFIG_FAILED,SW_CONFIG_LOCK_FAILED | SW_CONFIGURED,SW_RECONFIGURED                                 |
| SW_DDOS_PROTOCOL_VIOLATION | SW_DDOS_PROTOCOL_VIOLATION_SET         | SW_DDOS_PROTOCOL_VIOLATION_CLEAR                              |
| SW_DISCONNECTED            | SW_DISCONNECTED                        | SW_CONNECTED                                                  |
| SW_EVPN_CORE_ISOLATION     | SW_EVPN_CORE_ISOLATED                  | SW_EVPN_CORE_ISOLATION_CLEARED                                |
| SW_FPC_POWER               | SW_FPC_POWER_OFF                       | SW_FPC_POWER_ON                                               |
| SW_MAC_LEARNING            | SW_MAC_LEARNING_STOPPED                | SW_MAC_LEARNING_RESUMED                                       |
| SW_MAC_LIMIT               | SW_MAC_LIMIT_EXCEEDED                  | SW_MAC_LIMIT_RESET                                            |
| SW_OSPF_NEIGHBOR           | SW_OSPF_NEIGHBOR_DOWN                  | SW_OSPF_NEIGHBOR_UP                                           |
| SW_PORT_BPDU               | SW_PORT_BPDU_BLOCKED                   | SW_PORT_BPDU_ERROR_CLEARED                                    |
| SW_RECOVERY_SNAPSHOT       | SW_RECOVERY_SNAPSHOT_FAILED            | SW_RECOVERY_SNAPSHOT_SUCCEEDED,SW_RECOVERY_SNAPSHOT_NOTNEEDED |
| SW_UPGRADE                 | SW_UPGRADE_FAILED                      | SW_UPGRADED                                                   |
| SW_VC_PORT                 | SW_VC_PORT_DOWN                        | SW_VC_PORT_UP                                                 |
| SW_ZTP                     | SW_ZTP_FAILED                          | SW_ZTP_FINISHED                                               |


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
-n, --no-resolve            disable the device (device name) resolution. This option should be
                            used for big Organizations where there resolution can generate too
                            many additional API calls
-v, --view=                 Type of report to display. Options are:
                                - event: show events per event type
                                - device: show events per device
                                - none: do not display the result (the result is only save in
                                the CSV file)
                            default: event
-c, --csv_file=             Path to the CSV file where to save the result
                            default: ./list_open_events.csv

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
import csv
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
CSV_FILE = "./list_open_events.csv"
LOG_FILE = "./script.log"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### CONSTANTS ####
EVENT_TYPES_DEFINITIONS= {
"AP_CONFIG": ["AP_CONFIG_FAILED","AP_CONFIGURED","AP_RECONFIGURED"],
"AP_DISCONNECTED": ["AP_DISCONNECTED","AP_CONNECTED"],
"AP_RADSEC": ["AP_RADSEC_FAILURE","AP_RADSEC_RECOVERY"],
"AP_UPGRADE": ["AP_UPGRADE_FAILED","AP_UPGRADED"],
"GW_APPID_INSTALL": ["GW_APPID_INSTALL_FAILED","GW_APPID_INSTALLED"],
"GW_ARP": ["GW_ARP_UNRESOLVED","GW_ARP_RESOLVED"],
"GW_BGP_NEIGHBOR": ["GW_BGP_NEIGHBOR_DOWN","GW_BGP_NEIGHBOR_UP"],
"GW_CONFIG": ["GW_CONFIG_FAILED","GW_CONFIG_LOCK_FAILED","GW_CONFIGURED"],
"GW_DISCONNECTED": ["GW_DISCONNECTED","GW_CONNECTED"],
"GW_FIB_COUNT": ["GW_FIB_COUNT_THRESHOLD_EXCEEDED","GW_FIB_COUNT_RETURNED_TO_NORMAL"],
"GW_FLOW_COUNT": ["GW_FLOW_COUNT_THRESHOLD_EXCEEDED","GW_FLOW_COUNT_RETURNED_TO_NORMAL"],
"GW_HA_CONTROL_LINK": ["GW_HA_CONTROL_LINK_DOWN","GW_HA_CONTROL_LINK_UP"],
"GW_HA_HEALTH_WEIGHT": ["GW_HA_HEALTH_WEIGHT_LOW","GW_HA_HEALTH_WEIGHT_RECOVERY"],
"GW_IDP_INSTALL": ["GW_IDP_INSTALL_FAILED","GW_IDP_INSTALLED"],
"GW_RECOVERY_SNAPSHOT": ["GW_RECOVERY_SNAPSHOT_FAILED","GW_RECOVERY_SNAPSHOT_SUCCEEDED","GW_RECOVERY_SNAPSHOT_NOTNEEDED"],
"GW_TUNNEL": ["GW_TUNNEL_DOWN","GW_TUNNEL_UP"],
"GW_UPGRADE": ["GW_UPGRADE_FAILED","GW_UPGRADED"],
"GW_VPN_PATH": ["GW_VPN_PATH_DOWN","GW_VPN_PATH_UP"],
"GW_VPN_PEER": ["GW_VPN_PEER_DOWN","GW_VPN_PEER_UP"],
"GW_ZTP": ["GW_ZTP_FAILED","GW_ZTP_FINISHED"],
"SW_BFD_SESSION": ["SW_BFD_SESSION_DISCONNECTED","SW_BFD_SESSION_ESTABLISHED"],
"SW_BGP_NEIGHBOR": ["SW_BGP_NEIGHBOR_DOWN","SW_BGP_NEIGHBOR_UP"],
"SW_CONFIG": ["SW_CONFIG_FAILED","SW_CONFIG_LOCK_FAILED","SW_CONFIGURED"],
"SW_DDOS_PROTOCOL_VIOLATION": ["SW_DDOS_PROTOCOL_VIOLATION_SET","SW_DDOS_PROTOCOL_VIOLATION_CLEAR"],
"SW_DISCONNECTED": ["SW_DISCONNECTED","SW_CONNECTED"],
"SW_EVPN_CORE_ISOLATION": ["SW_EVPN_CORE_ISOLATED","SW_EVPN_CORE_ISOLATION_CLEARED"],
"SW_FPC_POWER": ["SW_FPC_POWER_OFF","SW_FPC_POWER_ON"],
"SW_MAC_LEARNING": ["SW_MAC_LEARNING_STOPPED","SW_MAC_LEARNING_RESUMED"],
"SW_MAC_LIMIT": ["SW_MAC_LIMIT_EXCEEDED","SW_MAC_LIMIT_RESET"],
"SW_OSPF_NEIGHBOR": ["SW_OSPF_NEIGHBOR_DOWN","SW_OSPF_NEIGHBOR_UP"],
"SW_PORT_BPDU": ["SW_PORT_BPDU_ERROR_CLEARED","SW_PORT_BPDU_BLOCKED"],
"SW_RECOVERY_SNAPSHOT": ["SW_RECOVERY_SNAPSHOT_FAILED","SW_RECOVERY_SNAPSHOT_SUCCEEDED","SW_RECOVERY_SNAPSHOT_NOTNEEDED"],
"SW_UPGRADE": ["SW_UPGRADE_FAILED","SW_UPGRADED"],
"SW_VC_PORT": ["SW_VC_PORT_DOWN","SW_VC_PORT_UP"],
"SW_ZTP": ["SW_ZTP_FAILED","SW_ZTP_FINISHED"],
}

#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """
    PROGRESS BAR AND DISPLAY
    """
    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(
        self,
        message: str,
        result: str,
        inc: bool = False,
        size: int = 80,
        display_pbar: bool = True,
    ):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(
        self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True
    ):
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}")
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()

#####################################################################
#### FUNCTIONS ####
def _retrieve_events(
    mist_session: mistapi.APISession,
    org_id: str,
    event_types: str = None,
    duration: str = "1d",
    retry=False,
):
    message = "Retrieving list of Events"
    PB.log_message(message, display_pbar=False)
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
            PB.log_success(message, inc=False, display_pbar=False)
            return True, events
        elif not retry:
            PB.log_failure(message, inc=False, display_pbar=False)
            return _retrieve_events(mist_session, org_id, event_types, duration, True)
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
            return False, None
    except Exception as e:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        if not retry:
            return _retrieve_events(mist_session, org_id, event_types, duration, True)
        else:
            return False, None


###################################################################################################
###################################################################################################
##                                                                                               ##
##                                       COMMON                                                  ##
##                                                                                               ##
###################################################################################################
###################################################################################################
################################# COMMON PROCESSING
def _process_common(
        devices: dict,
        event_type: str,
        event: dict,
        event_category:str,
        trigger_events: list,
        clear_events: list
        ):
    LOGGER.debug(f"_process_common (category {event_category}): {event}")
    event_timestamp = event.get("timestamp")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        event_category,
        None,
        None
    )
    if event_type in trigger_events:
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type in clear_events:
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

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
            event_port_id = event_text.replace("\"", "").split("network-interface:")[1].strip().split(",")[0]
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
################################# GW_HA_HEALTH_WEIGHT_LOW
def _process_gw_health_weight(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_gw_health_weight: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_node = None
    if not event_node:
        try:
            event_node = event_text.split("Detected")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_gw_health_weight: Unable to extract node from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "GW_HA_HEALTH_WEIGHT_LOW",
        "Tunnel",
        event_node,
    )
    if event_type == "GW_HA_HEALTH_WEIGHT_LOW":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_HA_HEALTH_WEIGHT_RECOVERY":
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
################################# SW_DDOS_PROTOCOL_VIOLATION_SET
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
################################# SW_FPC_POWER
def _process_sw_fpc_power(devices: dict, event_type: str, event: dict) -> None:
    LOGGER.debug(f"_process_sw_fpc_power: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_fru_slot = event.get("fru_slot")
    if not event_fru_slot:
        try:
            event_fru_slot = event_text.split("jnxFruSlot")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_sw_fpc_power: Unable to extract interface name from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_DDOS_PROTOCOL_VIOLATION_SET",
        "FRU Slot",
        event_fru_slot,
    )

    if event_type == "SW_FPC_POWER_OFF":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_FPC_POWER_ON":
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
################################# SW_OSPF_NEIGHBOR
def _process_sw_ospf_neighbor(devices: dict, event_type: str, event: dict):
    LOGGER.debug(f"_process_sw_ospf_neighbor: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_neighbor = None
    if not event_neighbor:
        try:
            event_neighbor = event_text.split("neighbor")[1].strip().split(" ")[0]
        except:
            LOGGER.error(
                f"_process_sw_ospf_neighbor: Unable to extract peer from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_OSPF_NEIGHBOR_DOWN",
        "Neighbor",
        event_neighbor,
    )
    if event_type == "SW_OSPF_NEIGHBOR_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_OSPF_NEIGHBOR_UP":
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
################################# SW_VC_PORT_DOWN
def _process_sw_vc_port(devices: dict, event_type: str, event: dict) -> None:
    LOGGER.debug(f"_process_sw_vc_port: {event}")
    event_text = event.get("text")
    event_timestamp = event.get("timestamp")
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.split(" on ")[1].strip().split(",")[0]
        except:
            LOGGER.error(
                f"_process_sw_vc_port: Unable to extract interface name from {event_text}"
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type"),
        event.get("mac"),
        "SW_VC_PORT_DOWN",
        "Port ID",
        event_port_id,
    )

    if event_type == "SW_VC_PORT_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "SW_VC_PORT_UP":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))

###################################################################################################
###################################################################################################
##                                                                                               ##
##                                       RESOLVE                                                  ##
##                                                                                               ##
###################################################################################################
###################################################################################################
def _get_sites(apisession:mistapi.APISession, org_id:str) -> dict:
    message = "Retrieving list of Sites"
    sites = []
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
        if resp.status_code == 200:
            sites = mistapi.get_all(apisession, resp)
            PB.log_success(message, inc=False, display_pbar=False)
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
            sys.exit(2)
    except:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

    message = "Processing list of Sites"
    data = {}
    PB.log_message(message, display_pbar=False)
    for site in sites:
        site_id = site.get("id")
        site_name = site.get("name")
        if site_id and site_name:
            data[site_id] = site_name
        else:
            LOGGER.error(f"_get_sites: missing site data for site {site}")
    PB.log_success(message, inc=False, display_pbar=False)
    return data


def _get_devices(apisession:mistapi.APISession, org_id:str) -> dict:
    message = "Retrieving list of Devices"
    devices = []
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.devices.listOrgDevices(apisession, org_id)
        if resp.status_code == 200:
            devices = mistapi.get_all(apisession, resp)
            PB.log_success(message, inc=False, display_pbar=False)
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
            sys.exit(2)
    except:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

    message = "Processing list of Devices"
    data = {}
    PB.log_message(message, display_pbar=False)
    for device in devices:
        device_mac = device.get("mac")
        device_name = device.get("name")
        if device_mac and device_name:
            data[device_mac] = device_name
        else:
            data[device_mac] = device_mac
            LOGGER.warning(f"_get_devices: missing device data for device {device}")
    LOGGER.info(f"_get_devices: retrieved {len(data)} devices")
    PB.log_success(message, inc=False, display_pbar=False)
    return data

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
    message = "Processing list of Events"
    PB.log_message(message, display_pbar=False)
    device_events = {"gateway": {}, "switch": {}, "ap": {}}
    for event in events:
        event_type = event.get("type")
        ####### AP
        if event_type in ["AP_CONFIG_FAILED", "AP_CONFIGURED", "AP_RECONFIGURED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "AP_CONFIG_FAILED",
                ["AP_CONFIG_FAILED"],
                ["AP_CONFIGURED", "AP_RECONFIGURED"]
                )
        elif event_type in ["AP_DISCONNECTED", "AP_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "AP_DISCONNECTED",
                ["AP_DISCONNECTED"],
                ["AP_CONNECTED"]
                )
        elif event_type.startswith("AP_RADSEC"):
            _process_common(
                device_events,
                event_type,
                event,
                "AP_RADSEC_FAILURE",
                ["AP_RADSEC_FAILURE"],
                ["AP_RADSEC_RECOVERY"]
                )
        elif event_type.startswith("AP_UPGRADE"):
            _process_common(
                device_events,
                event_type,
                event,
                "AP_UPGRADE_FAILED",
                ["AP_UPGRADE_FAILED"],
                ["AP_UPGRADED"]
                )
        ####### GW
        elif event_type.startswith("GW_APPID_INSTALL"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_APPID_INSTALL_FAILED",
                ["GW_APPID_INSTALL_FAILED"],
                ["GW_APPID_INSTALLED"]
                )
        elif event_type.startswith("GW_ARP"):
            _process_gw_arp(device_events, event_type, event)
        elif event_type.startswith("GW_BGP_NEIGHBOR"):
            _process_gw_bgp_neighbor(device_events, event_type, event)
        elif event_type in ["GW_CONFIG_FAILED", "GW_CONFIGURED", "GW_RECONFIGURED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "GW_CONFIG_FAILED",
                ["GW_CONFIG_FAILED", "GW_CONFIG_LOCK_FAILED"],
                ["GW_CONFIGURED", "GW_RECONFIGURED"]
                )
        elif event_type in ["GW_DISCONNECTED", "GW_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "GW_DISCONNECTED",
                ["GW_DISCONNECTED"],
                ["GW_CONNECTED"]
                )
        elif event_type.startswith("GW_FIB_COUNT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_FIB_COUNT_THRESHOLD_EXCEEDED",
                ["GW_FIB_COUNT_THRESHOLD_EXCEEDED"],
                ["GW_FIB_COUNT_RETURNED_TO_NORMAL"]
                )
        elif event_type.startswith("GW_FLOW_COUNT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_FLOW_COUNT_THRESHOLD_EXCEEDED",
                ["GW_FLOW_COUNT_THRESHOLD_EXCEEDED"],
                ["GW_FLOW_COUNT_RETURNED_TO_NORMAL"]
                )
        elif event_type.startswith("GW_HA_CONTROL_LINK"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_HA_CONTROL_LINK_DOWN",
                ["GW_HA_CONTROL_LINK_DOWN"],
                ["GW_HA_CONTROL_LINK_UP"]
                )
        elif event_type.startswith("GW_HA_HEALTH_WEIGHT"):
            _process_gw_health_weight(device_events, event_type, event)
        elif event_type.startswith("GW_IDP_INSTALL"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_IDP_INSTALL_FAILED",
                ["GW_IDP_INSTALL_FAILED"],
                ["GW_IDP_INSTALLED"]
                )
        elif event_type.startswith("GW_RECOVERY_SNAPSHOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_RECOVERY_SNAPSHOT_FAILED",
                ["GW_RECOVERY_SNAPSHOT_FAILED"],
                ["GW_RECOVERY_SNAPSHOT_SUCCEEDED","GW_RECOVERY_SNAPSHOT_NOTNEEDED"]
                )
        elif event_type.startswith("GW_TUNNEL"):
            _process_gw_tunnel(device_events, event_type, event)
        elif event_type.startswith("GW_UPGRADE"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_UPGRADE_FAILED",
                ["GW_UPGRADE_FAILED"],
                ["GW_UPGRADED"]
                )
        elif event_type.startswith("GW_VPN_PATH"):
            _process_gw_vpn_path(device_events, event_type, event)
        elif event_type.startswith("GW_VPN_PEER"):
            _process_gw_vpn_peer(device_events, event_type, event)
        elif event_type.startswith("GW_ZTP"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ZTP_FAILED",
                ["GW_ZTP_FAILED"],
                ["GW_ZTP_FINISHED"]
                )
        ####### SW
        elif event_type in ["SW_CONFIG_FAILED", "SW_CONFIGURED", "SW_RECONFIGURED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "SW_CONFIG_FAILED",
                ["SW_CONFIG_FAILED", "SW_CONFIG_LOCK_FAILED"],
                ["SW_CONFIGURED", "SW_RECONFIGURED"]
                )
        elif event_type.startswith("SW_DDOS_PROTOCOL_VIOLATION"):
            _process_sw_ddos_protocol_violation(device_events, event_type, event)
        elif event_type in ["SW_DISCONNECTED", "SW_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "SW_DISCONNECTED",
                ["SW_DISCONNECTED"],
                ["SW_CONNECTED"]
                )
        elif event_type.startswith("SW_EVPN_CORE_ISO"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_EVPN_CORE_ISOLATED",
                ["SW_EVPN_CORE_ISOLATED"],
                ["SW_EVPN_CORE_ISOLATION_CLEARED"]
                )
        elif event_type.startswith("SW_FPC_POWER"):
            _process_sw_fpc_power(device_events, event_type, event)
        elif event_type.startswith("SW_MAC_LEARNING"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_MAC_LEARNING_STOPPED",
                ["SW_MAC_LEARNING_STOPPED"],
                ["SW_MAC_LEARNING_RESUMED"]
                )
        elif event_type.startswith("SW_MAC_LIMIT"):
            _process_sw_mac_limit(device_events, event_type, event)
        elif event_type.startswith("SW_OSPF_NEIGHBOR"):
            _process_sw_ospf_neighbor(device_events, event_type, event)
        elif event_type.startswith("SW_PORT_BPDU"):
            _process_sw_port_bpdu(device_events, event_type, event)
        elif event_type.startswith("SW_RECOVERY_SNAPSHOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_RECOVERY_SNAPSHOT_FAILED",
                ["SW_RECOVERY_SNAPSHOT_FAILED"],
                ["SW_RECOVERY_SNAPSHOT_SUCCEEDED","SW_RECOVERY_SNAPSHOT_NOTNEEDED"]
                )
        elif event_type.startswith("SW_UPGRADE"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_UPGRADE_FAILED",
                ["SW_UPGRADE_FAILED"],
                ["SW_UPGRADED"]
                )
        elif event_type.startswith("SW_VC_PORT"):
            _process_sw_vc_port(device_events, event_type, event)
        elif event_type.startswith("SW_ZTP"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ZTP_FAILED",
                ["SW_ZTP_FAILED"],
                ["SW_ZTP_FINISHED"]
                )
    PB.log_success(message, inc=False, display_pbar=False)
    return device_events

def _check_timeout(raised_timeout:int, last_change:datetime, status:str) -> bool:
    timeout = False
    now = datetime.now()
    delta_time = (now - last_change).total_seconds()
    if delta_time >= (raised_timeout * 60) and status=="triggered":
        timeout = True
    return timeout


def _display_device_results(device_events:dict, raised_timeout:int, resolve_sites:dict, resolve_devices:dict):
    headers = [
        "Event Type",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change"
    ]
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                data = []
                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    if event_data.get("identifier_header"):
                        for event_identifier, event_identifier_data in event_data.items():
                            if event_identifier == "identifier_header":
                                continue
                            if not event_identifier_data.get("triggered"):
                                continue
                            timeout = _check_timeout(
                                raised_timeout,
                                event_identifier_data.get("last_change"),
                                event_identifier_data.get("status")
                                )
                            if raised_timeout == 0 or timeout:
                                data.append([
                                    event_type,
                                    f"{event_data['identifier_header']} {event_identifier}",
                                    event_identifier_data.get("status"),
                                    event_identifier_data.get("triggered"),
                                    event_identifier_data.get("cleared"),
                                    event_identifier_data.get("last_change"),
                                ])
                    else:
                        if not event_data.get("triggered"):
                            continue
                        timeout = _check_timeout(
                            raised_timeout,
                            event_data.get("last_change"),
                            event_data.get("status")
                            )
                        if raised_timeout == 0 or timeout:
                            data.append([
                                event_type,
                                "",
                                event_data.get("status"),
                                event_data.get("triggered"),
                                event_data.get("cleared"),
                                event_data.get("last_change"),
                            ])
                if data:
                    site_id = device_data.get('site_id')
                    site_name = resolve_sites.get(site_id)
                    device_name = resolve_devices.get(device_mac)
                    print()
                    print()
                    print("".center(80, "─"))
                    print()
                    if site_name:
                        print(f"site {site_name} (site_id: {site_id})")
                    else:
                        print(f"site_id: {site_id}")
                    if device_name:
                        print(f"{device_type} {device_name} (mac: {device_mac}, model: {device_data.get('model')}, version: {device_data.get('version')})")
                    else:
                        print(f"{device_type} {device_mac} (model : {device_data.get('model')}, version: {device_data.get('version')})")
                    print()
                    print(mistapi.cli.tabulate(data, headers=headers, tablefmt="rounded_grid"))

def _display_event_results(device_events:dict, raised_timeout:int, resolve_sites:dict, resolve_devices:dict):
    headers = [
        "Site",
        "Device",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change"
    ]
    event_reports = {}
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                site_id = device_data.get('site_id')
                if resolve_sites.get(site_id):
                    site_entry = resolve_sites.get(site_id)
                else:
                    site_entry = site_id
                if resolve_devices.get(device_mac):
                    device_entry = f"{resolve_devices.get(device_mac)} ({device_mac})"
                else:
                    device_entry = device_mac

                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    timeout = False
                    if event_type not in event_reports:
                        event_reports[event_type] = []
                    if event_data.get("identifier_header"):
                        for event_identifier, event_identifier_data in event_data.items():
                            if event_identifier == "identifier_header":
                                continue
                            if not event_identifier_data.get("triggered"):
                                continue
                            timeout = _check_timeout(
                                raised_timeout,
                                event_identifier_data.get("last_change"),
                                event_identifier_data.get("status")
                                )
                            if raised_timeout == 0 or timeout:
                                event_reports[event_type].append([
                                    site_entry,
                                    device_entry,
                                    f"{event_data['identifier_header']} {event_identifier}",
                                    event_identifier_data.get("status"),
                                    event_identifier_data.get("triggered"),
                                    event_identifier_data.get("cleared"),
                                    event_identifier_data.get("last_change")
                                ])
                    else:
                        if not event_data.get("triggered"):
                            continue
                        timeout = _check_timeout(
                            raised_timeout,
                            event_data.get("last_change"),
                            event_data.get("status")
                            )
                        if raised_timeout == 0 or timeout:
                            event_reports[event_type].append([
                                    site_entry,
                                    device_entry,
                                    "",
                                    event_data.get("status"),
                                    event_data.get("triggered"),
                                    event_data.get("cleared"),
                                    event_data.get("last_change")
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

def _gen_device_insight_url(apisession:mistapi.APISession, org_id:str, device_type:str, device_mac:str, site_id:str):
    if device_type == "switch":
        d_type = "juniperSwitch"
    elif device_type == "gateway":
        d_type = "juniperGateway"
    else:
        d_type = "device"
    return f"https://{apisession.get_cloud().replace('api', 'manage')}/admin/?org_id={org_id}#!dashboard/insights/{d_type}/00000000-0000-0000-1000-{device_mac}/{site_id}"

def _export_to_csv(apisession:mistapi.APISession, org_id:str, csv_file:str, device_events:dict, raised_timeout:int, resolve_sites:dict, resolve_devices:dict):
    headers = [
        "Site Name",
        "Site ID",
        "Device Type",
        "Device Name",
        "Device Mac",
        "Event Type",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change",
        "Device Insight URL"
    ]
    data=[]
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                site_id = device_data.get('site_id')
                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    if event_data.get("identifier_header"):
                        for event_identifier, event_identifier_data in event_data.items():
                            if event_identifier == "identifier_header":
                                continue
                            if not event_identifier_data.get("triggered"):
                                continue
                            timeout = _check_timeout(
                                raised_timeout,
                                event_identifier_data.get("last_change"),
                                event_identifier_data.get("status")
                                )
                            if raised_timeout == 0 or timeout:
                                data.append([
                                    resolve_sites.get(site_id),
                                    site_id,
                                    device_type,
                                    resolve_devices.get(device_mac),
                                    device_mac,
                                    event_type,
                                    f"{event_data['identifier_header']} {event_identifier}",
                                    event_identifier_data.get("status"),
                                    event_identifier_data.get("triggered"),
                                    event_identifier_data.get("cleared"),
                                    event_identifier_data.get("last_change"),
                                    _gen_device_insight_url(apisession, org_id, device_type, device_mac, site_id)
                                ])
                    else:
                        if not event_data.get("triggered"):
                            continue
                        timeout = _check_timeout(
                            raised_timeout,
                            event_data.get("last_change"),
                            event_data.get("status")
                            )
                        if raised_timeout == 0 or timeout:
                            data.append([
                                        resolve_sites.get(site_id),
                                        site_id,
                                device_type,
                                resolve_devices.get(device_mac),
                                device_mac,
                                event_type,
                                "",
                                event_data.get("status"),
                                event_data.get("triggered"),
                                event_data.get("cleared"),
                                event_data.get("last_change"),
                                _gen_device_insight_url(apisession, org_id, device_type, device_mac, site_id)
                            ])
    with open(csv_file, 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)


###################################################################################################
################################# START
def start(
    mist_session: mistapi.APISession,
    org_id: str,
    event_types: str = None,
    duration: str = "1d",
    raised_timeout: int = 5,
    view: str = "event",
    csv_file: str = "./list_open_events.csv",
    no_resolve:bool = False
):
    """
    Start the process

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where the webhook guests be added. This parameter cannot be used if "site_id"
        is used. If no org_id and not site_id are defined, the script will show a menu to
        select the org/the site.
    event_types : str
        comma separated list of event types that should be retrieved from the Mist Org and
        processed. See the list in "Note 1" above.
        If not defined, all the supported Event Options will be retrieved and processed.
    duration : str, default 1d
        duration of the events to look at
    raised_timeout : int, default 5
        timeout (in minutes) before listing the event if it is not cleared. Set to 0 to list
        all the events (even the cleared ones)
    view : str, default event
        Type of report to display. Options are:
            - event: show events per event type
            - device: show events per device
            - none: do not display the result (the result is only save in the CSV file)
    csv_file : str
        Path to the CSV file where the guests information are stored.
        default is "./list_open_events.csv"
    no_resolve : bool, default False
        disable the device (device name) resolution. This option should be used for big
        Organizations where there resolution can generate too many additional API calls
    """
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]
    print()
    print()
    print()
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
        sites = _get_sites(mist_session, org_id)
        devices = {}
        if not no_resolve:
            devices = _get_devices(mist_session, org_id)

        device_events = _process_events(events)
        _export_to_csv(mist_session, org_id,csv_file, device_events, raised_timeout, sites, devices)
        if view.lower() == "device":
            _display_device_results(device_events, raised_timeout, sites, devices)
        elif view.lower() != "continue":
            _display_event_results(device_events, raised_timeout, sites, devices)


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

| Script Event Options       | Mist Triggering Events                 | Mist Clearing Events                                          |
|----------------------------|----------------------------------------|---------------------------------------------------------------|
| AP_CONFIG                  | AP_CONFIG_FAILED                       | AP_CONFIGURED,AP_RECONFIGURED                                 |
| AP_DISCONNECTED            | AP_DISCONNECTED                        | AP_CONNECTED                                                  |
| AP_RADSEC                  | AP_RADSEC_FAILURE                      | AP_RADSEC_RECOVERY                                            |
| AP_UPGRADE                 | AP_UPGRADE_FAILED                      | AP_UPGRADED                                                   |
| GW_ARP                     | GW_ARP_UNRESOLVED                      | GW_ARP_RESOLVED                                               |
| GW_BGP_NEIGHBOR            | GW_BGP_NEIGHBOR_DOWN                   | GW_BGP_NEIGHBOR_UP                                            |
| GW_CONFIG                  | GW_CONFIG_FAILED,GW_CONFIG_LOCK_FAILED | GW_CONFIGURED,GW_RECONFIGURED                                 |
| GW_DISCONNECTED            | GW_DISCONNECTED                        | GW_CONNECTED                                                  |
| GW_FIB_COUNT               | GW_FIB_COUNT_THRESHOLD_EXCEEDED        | GW_FIB_COUNT_RETURNED_TO_NORMAL                               |
| GW_FLOW_COUNT              | GW_FLOW_COUNT_THRESHOLD_EXCEEDED       | GW_FLOW_COUNT_RETURNED_TO_NORMAL                              |
| GW_HA_CONTROL_LINK         | GW_HA_CONTROL_LINK_DOWN                | GW_HA_CONTROL_LINK_UP                                         |
| GW_HA_HEALTH_WEIGHT        | GW_HA_HEALTH_WEIGHT_LOW                | GW_HA_HEALTH_WEIGHT_RECOVERY                                  |
| GW_RECOVERY_SNAPSHOT       | GW_RECOVERY_SNAPSHOT_FAILED            | GW_RECOVERY_SNAPSHOT_SUCCEEDED,GW_RECOVERY_SNAPSHOT_NOTNEEDED |
| GW_TUNNEL                  | GW_TUNNEL_DOWN                         | GW_TUNNEL_UP                                                  |
| GW_UPGRADE                 | GW_UPGRADE_FAILED                      | GW_UPGRADED                                                   |
| GW_VPN_PATH                | GW_VPN_PATH_DOWN                       | GW_VPN_PATH_UP                                                |
| GW_VPN_PEER                | GW_VPN_PEER_DOWN                       | GW_VPN_PEER_UP                                                |
| GW_ZTP                     | GW_ZTP_FAILED                          | GW_ZTP_FINISHED                                               |
| SW_BFD_SESSION             | SW_BFD_SESSION_DISCONNECTED            | SW_BFD_SESSION_ESTABLISHED                                    |
| SW_BGP_NEIGHBOR            | SW_BGP_NEIGHBOR_DOWN                   | SW_BGP_NEIGHBOR_UP                                            |
| SW_CONFIG                  | SW_CONFIG_FAILED,SW_CONFIG_LOCK_FAILED | SW_CONFIGURED,SW_RECONFIGURED                                 |
| SW_DDOS_PROTOCOL_VIOLATION | SW_DDOS_PROTOCOL_VIOLATION_SET         | SW_DDOS_PROTOCOL_VIOLATION_CLEAR                              |
| SW_DISCONNECTED            | SW_DISCONNECTED                        | SW_CONNECTED                                                  |
| SW_EVPN_CORE_ISOLATION     | SW_EVPN_CORE_ISOLATED                  | SW_EVPN_CORE_ISOLATION_CLEARED                                |
| SW_FPC_POWER               | SW_FPC_POWER_OFF                       | SW_FPC_POWER_ON                                               |
| SW_MAC_LEARNING            | SW_MAC_LEARNING_STOPPED                | SW_MAC_LEARNING_RESUMED                                       |
| SW_MAC_LIMIT               | SW_MAC_LIMIT_EXCEEDED                  | SW_MAC_LIMIT_RESET                                            |
| SW_OSPF_NEIGHBOR           | SW_OSPF_NEIGHBOR_DOWN                  | SW_OSPF_NEIGHBOR_UP                                           |
| SW_PORT_BPDU               | SW_PORT_BPDU_BLOCKED                   | SW_PORT_BPDU_ERROR_CLEARED                                    |
| SW_RECOVERY_SNAPSHOT       | SW_RECOVERY_SNAPSHOT_FAILED            | SW_RECOVERY_SNAPSHOT_SUCCEEDED,SW_RECOVERY_SNAPSHOT_NOTNEEDED |
| SW_UPGRADE                 | SW_UPGRADE_FAILED                      | SW_UPGRADED                                                   |
| SW_VC_PORT                 | SW_VC_PORT_DOWN                        | SW_VC_PORT_UP                                                 |
| SW_ZTP                     | SW_ZTP_FAILED                          | SW_ZTP_FINISHED                                               |


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
-n, --no-resolve            disable the device (device name) resolution. This option should be
                            used for big Organizations where there resolution can generate too
                            many additional API calls
-v, --view=                 Type of report to display. Options are:
                                - event: show events per event type
                                - device: show events per device
                                - none: do not display the result (the result is only save in
                                the CSV file)
                            default: event
-c, --csv_file=             Path to the CSV file where to save the result
                            default: ./list_open_events.csv

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
    mistapi_version = mistapi.__version__.split(".")
    min_version = MISTAPI_MIN_VERSION.split(".")
    if (
        int(mistapi_version[0]) < int(min_version[0])
        or int(mistapi_version[1]) < int(min_version[1])
        or int(mistapi_version[2]) < int(min_version[2])
        ):
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
            "he:o:a:d:t:r:l:v:c:n",
            [
                "help",
                "env_file=",
                "org_id=",
                "event_types=",
                "duration=",
                "trigger_timeout=",
                "log_file=",
                "view=",
                "csv_file=",
                "no-resolve"
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
    NO_RESOLVE=False
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-e", "--env_file"]:
            ENV_FILE = a
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-c", "--csv_file"]:
            CSV_FILE = a
        elif o in ["-n", "--no-resolve"]:
            NO_RESOLVE = True
        elif o in ["-t", "--event_types"]:
            for t in o.split(","):
                if EVENT_TYPES_DEFINITIONS.get(t.strip().upper()):
                    EVENT_TYPES += EVENT_TYPES_DEFINITIONS.get(t.strip().upper())
                else:
                    usage(f"Invalid -t / --event_type parameter value. Got \"{t}\".")
        elif o in ["-d", "--duration"]:
            if not a.endswith(("m", "h", "d", "w")):
                usage(f"Invalid -d / --duration parameter value, should be something like \"10m\", \"2h\", \"7d\", \"1w\". Got \"{a}\".")
            DURATION = a
        elif o in ["-v", "--view"]:
            if not a.lower() in ["event", "device"]:
                usage(f"Invalid -v / --view parameter value, must be \"event\" or \"device\". Got \"{a}\".")
            VIEW = a
        elif o in ["-r", "--trigger_timeout"]:
            try:
                TIMEOUT = int(a)
            except:
                usage(f"Invalid -r / --trigger_timeout parameter value, must be an integer. Got \"{a}\".")
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
    start(apisession, ORG_ID, EVENT_TYPES, DURATION, TIMEOUT, VIEW, CSV_FILE, NO_RESOLVE)
