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

| Script Event Options          | Mist Triggering Events                                                            | Mist Clearing Events                                          |
|-------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------|
| AP_CONFIG                     | AP_CONFIG_FAILED                                                                  | AP_CONFIGURED,AP_RECONFIGURED                                 |
| AP_DISCONNECTED               | AP_DISCONNECTED                                                                   | AP_CONNECTED                                                  |
| AP_PORT                       | AP_PORT_DOWN                                                                      | AP_PORT_UP                                                    |
| AP_RADSEC                     | AP_RADSEC_FAILURE                                                                 | AP_RADSEC_RECOVERY                                            |
| AP_UPGRADE                    | AP_UPGRADE_FAILED                                                                 | AP_UPGRADED                                                   |
| ESL_HUNG                      | ESL_HUNG                                                                          | ESL_RECOVERED                                                 |
| GW_ALARM_CHASSIS_FAN          | GW_ALARM_CHASSIS_FAN                                                              | GW_ALARM_CHASSIS_FAN_CLEAR                                    |
| GW_ALARM_CHASSIS_HOT          | GW_ALARM_CHASSIS_HOT                                                              | GW_ALARM_CHASSIS_HOT_CLEAR                                    |
| GW_ALARM_CHASSIS_HUMIDITY     | GW_ALARM_CHASSIS_HUMIDITY                                                         | GW_ALARM_CHASSIS_HUMIDITY_CLEAR                               |
| GW_ALARM_CHASSIS_MGMT_LINK    | GW_ALARM_CHASSIS_MGMT_LINK_DOWN                                                   | GW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR                         |
| GW_ALARM_CHASSIS_PARTITION    | GW_ALARM_CHASSIS_PARTITION                                                        | GW_ALARM_CHASSIS_PARTITION_CLEAR                              |
| GW_ALARM_CHASSIS_PEM          | GW_ALARM_CHASSIS_PEM                                                              | GW_ALARM_CHASSIS_PEM_CLEAR                                    |
| GW_ALARM_CHASSIS_POE          | GW_ALARM_CHASSIS_POE                                                              | GW_ALARM_CHASSIS_POE_CLEAR                                    |
| GW_ALARM_CHASSIS_PSU          | GW_ALARM_CHASSIS_PSU                                                              | GW_ALARM_CHASSIS_PSU_CLEAR                                    |
| GW_ALARM_CHASSIS_WARM         | GW_ALARM_CHASSIS_WARM                                                             | GW_ALARM_CHASSIS_WARM_CLEAR                                   |
| GW_APPID_INSTALL              | GW_APPID_INSTALL_FAILED                                                           | GW_APPID_INSTALLED                                            |
| GW_ARP                        | GW_ARP_UNRESOLVED                                                                 | GW_ARP_RESOLVED                                               |
| GW_BGP_NEIGHBOR               | GW_BGP_NEIGHBOR_DOWN                                                              | GW_BGP_NEIGHBOR_UP                                            |
| GW_CONDUCTOR                  | GW_CONDUCTOR_DISCONNECTED                                                         | GW_CONDUCTOR_CONNECTED                                        |
| GW_CONFIG                     | GW_CONFIG_FAILED,GW_CONFIG_LOCK_FAILED,GW_CONFIG_ERROR_ADDTL_COMMAND              | GW_CONFIGURED,GW_RECONFIGURED                                 |
| GW_DHCP                       | GW_DHCP_UNRESOLVED                                                                | GW_DHCP_RESOLVED                                              |
| GW_DISCONNECTED               | GW_DISCONNECTED                                                                   | GW_CONNECTED                                                  |
| GW_FIB_COUNT                  | GW_FIB_COUNT_THRESHOLD_EXCEEDED                                                   | GW_FIB_COUNT_RETURNED_TO_NORMAL                               |
| GW_FLOW_COUNT                 | GW_FLOW_COUNT_THRESHOLD_EXCEEDED                                                  | GW_FLOW_COUNT_RETURNED_TO_NORMAL                              |
| GW_HA_CONTROL_LINK            | GW_HA_CONTROL_LINK_DOWN                                                           | GW_HA_CONTROL_LINK_UP                                         |
| GW_HA_HEALTH_WEIGHT           | GW_HA_HEALTH_WEIGHT_LOW                                                           | GW_HA_HEALTH_WEIGHT_RECOVERY                                  |
| GW_IDP_INSTALL                | GW_IDP_INSTALL_FAILED                                                             | GW_IDP_INSTALLED                                              |
| GW_OSPF_NEIGHBOR              | GW_OSPF_NEIGHBOR_DOWN                                                             | GW_OSPF_NEIGHBOR_UP                                           |
| GW_PORT                       | GW_PORT_DOWN                                                                      | GW_PORT_UP                                                    |
| GW_RECOVERY_SNAPSHOT          | GW_RECOVERY_SNAPSHOT_FAILED                                                       | GW_RECOVERY_SNAPSHOT_SUCCEEDED,GW_RECOVERY_SNAPSHOT_NOTNEEDED |
| GW_TUNNEL                     | GW_TUNNEL_DOWN                                                                    | GW_TUNNEL_UP                                                  |
| GW_UPGRADE                    | GW_UPGRADE_FAILED                                                                 | GW_UPGRADED                                                   |
| GW_VPN_PATH                   | GW_VPN_PATH_DOWN                                                                  | GW_VPN_PATH_UP                                                |
| GW_VPN_PEER                   | GW_VPN_PEER_DOWN                                                                  | GW_VPN_PEER_UP                                                |
| GW_ZTP                        | GW_ZTP_FAILED                                                                     | GW_ZTP_FINISHED                                               |
| ME_DISCONNECTED               | ME_DISCONNECTED                                                                   | ME_CONNECTED                                                  |
| ME_FAN                        | ME_FAN_UNPLUGGED                                                                  | ME_FAN_PLUGGED                                                |
| ME_POWERINPUT                 | ME_POWERINPUT_DISCONNECTED                                                        | ME_POWERINPUT_CONNECTED                                       |
| ME_PSU                        | ME_PSU_UNPLUGGED                                                                  | ME_PSU_PLUGGED                                                |
| ME_SERVICE                    | ME_SERVICE_CRASHED,ME_SERVICE_FAILED                                              | ME_SERVICE_STARTED                                            |
| SW_ALARM_CHASSIS_FAN          | SW_ALARM_CHASSIS_FAN                                                              | SW_ALARM_CHASSIS_FAN_CLEAR                                    |
| SW_ALARM_CHASSIS_HOT          | SW_ALARM_CHASSIS_HOT                                                              | SW_ALARM_CHASSIS_HOT_CLEAR                                    |
| SW_ALARM_CHASSIS_HUMIDITY     | SW_ALARM_CHASSIS_HUMIDITY                                                         | SW_ALARM_CHASSIS_HUMIDITY_CLEAR                               |
| SW_ALARM_CHASSIS_MGMT_LINK    | SW_ALARM_CHASSIS_MGMT_LINK_DOWN                                                   | SW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR                         |
| SW_ALARM_CHASSIS_PARTITION    | SW_ALARM_CHASSIS_PARTITION                                                        | SW_ALARM_CHASSIS_PARTITION_CLEAR                              |
| SW_ALARM_CHASSIS_PEM          | SW_ALARM_CHASSIS_PEM                                                              | SW_ALARM_CHASSIS_PEM_CLEAR                                    |
| SW_ALARM_CHASSIS_POE          | SW_ALARM_CHASSIS_POE                                                              | SW_ALARM_CHASSIS_POE_CLEAR                                    |
| SW_ALARM_CHASSIS_PSU          | SW_ALARM_CHASSIS_PSU                                                              | SW_ALARM_CHASSIS_PSU_CLEAR                                    |
| SW_ALARM_IOT                  | SW_ALARM_IOT_SET                                                                  | SW_ALARM_IOT_CLEAR                                            |
| SW_ALARM_VC_VERSION_MISMATCH  | SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH                                         | SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH_CLEAR               |
| SW_BFD_SESSION                | SW_BFD_SESSION_DISCONNECTED                                                       | SW_BFD_SESSION_ESTABLISHED                                    |
| SW_BGP_NEIGHBOR               | SW_BGP_NEIGHBOR_DOWN                                                              | SW_BGP_NEIGHBOR_UP                                            |
| SW_CONFIG                     | SW_CONFIG_FAILED,SW_CONFIG_LOCK_FAILED,SW_CONFIG_ERROR_ADDTL_COMMAND              | SW_CONFIGURED,SW_RECONFIGURED                                 |
| SW_DDOS_PROTOCOL_VIOLATION    | SW_DDOS_PROTOCOL_VIOLATION_SET                                                    | SW_DDOS_PROTOCOL_VIOLATION_CLEAR                              |
| SW_DISCONNECTED               | SW_DISCONNECTED                                                                   | SW_CONNECTED                                                  |
| SW_EVPN_CORE_ISOLATION        | SW_EVPN_CORE_ISOLATED                                                             | SW_EVPN_CORE_ISOLATION_CLEARED                                |
| SW_FPC_POWER                  | SW_FPC_POWER_OFF                                                                  | SW_FPC_POWER_ON                                               |
| SW_LACPD_TIMEOUT              | SW_LACPD_TIMEOUT                                                                  | SW_LACPD_TIMEOUT_CLEARED                                      |
| SW_LOOP                       | SW_LOOP_DETECTED                                                                  | SW_LOOP_CLEARED                                               |
| SW_MAC_LEARNING               | SW_MAC_LEARNING_STOPPED                                                           | SW_MAC_LEARNING_RESUMED                                       |
| SW_MAC_LIMIT                  | SW_MAC_LIMIT_EXCEEDED                                                             | SW_MAC_LIMIT_RESET                                            |
| SW_OSPF_NEIGHBOR              | SW_OSPF_NEIGHBOR_DOWN                                                             | SW_OSPF_NEIGHBOR_UP                                           |
| SW_PORT                       | SW_PORT_DOWN                                                                      | SW_PORT_UP                                                    |
| SW_PORT_BPDU                  | SW_PORT_BPDU_BLOCKED                                                              | SW_PORT_BPDU_ERROR_CLEARED                                    |
| SW_RECOVERY_SNAPSHOT          | SW_RECOVERY_SNAPSHOT_FAILED                                                       | SW_RECOVERY_SNAPSHOT_SUCCEEDED,SW_RECOVERY_SNAPSHOT_NOTNEEDED |
| SW_UPGRADE                    | SW_UPGRADE_FAILED                                                                 | SW_UPGRADED                                                   |
| SW_VC_PORT                    | SW_VC_PORT_DOWN                                                                   | SW_VC_PORT_UP                                                 |
| SW_VC_TRANSITION              | SW_VC_IN_TRANSITION                                                               | SW_VC_STABLE                                                  |
| SW_ZTP                        | SW_ZTP_FAILED                                                                     | SW_ZTP_FINISHED                                               |
| TT_MONITORED_RESOURCE         | TT_MONITORED_RESOURCE_FAILED                                                      | TT_MONITORED_RESOURCE_RECOVERED                               |
| TT_PORT_BLOCKED               | TT_PORT_BLOCKED                                                                   | TT_PORT_RECOVERY                                              |
| TT_PORT_LACP                  | TT_PORT_DROPPED_FROM_LACP,TT_PORT_LAST_DROPPED_FROM_LACP                          | TT_PORT_JOINED_LACP,TT_PORT_FIRST_JOIN_LACP                   |
| TT_PORT_LINK                  | TT_PORT_LINK_DOWN                                                                 | TT_PORT_LINK_RECOVERY                                         |
| TT_TUNNELS                    | TT_TUNNELS_LOST                                                                   | TT_TUNNELS_UP                                                 |


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
import argparse
import logging
import csv
from datetime import datetime

MISTAPI_MIN_VERSION = "0.52.4"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
except ImportError:
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
EVENT_TYPES_DEFINITIONS = {
    # AP Events
    "AP_CONFIG": ["AP_CONFIG_FAILED", "AP_CONFIGURED", "AP_RECONFIGURED"],
    "AP_DISCONNECTED": ["AP_DISCONNECTED", "AP_CONNECTED"],
    "AP_PORT": ["AP_PORT_DOWN", "AP_PORT_UP"],
    "AP_RADSEC": ["AP_RADSEC_FAILURE", "AP_RADSEC_RECOVERY"],
    "AP_UPGRADE": ["AP_UPGRADE_FAILED", "AP_UPGRADED"],
    # ESL Events
    "ESL_HUNG": ["ESL_HUNG", "ESL_RECOVERED"],
    # GW Events
    "GW_ALARM_CHASSIS_FAN": ["GW_ALARM_CHASSIS_FAN", "GW_ALARM_CHASSIS_FAN_CLEAR"],
    "GW_ALARM_CHASSIS_HOT": ["GW_ALARM_CHASSIS_HOT", "GW_ALARM_CHASSIS_HOT_CLEAR"],
    "GW_ALARM_CHASSIS_HUMIDITY": [
        "GW_ALARM_CHASSIS_HUMIDITY",
        "GW_ALARM_CHASSIS_HUMIDITY_CLEAR",
    ],
    "GW_ALARM_CHASSIS_MGMT_LINK": [
        "GW_ALARM_CHASSIS_MGMT_LINK_DOWN",
        "GW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR",
    ],
    "GW_ALARM_CHASSIS_PARTITION": [
        "GW_ALARM_CHASSIS_PARTITION",
        "GW_ALARM_CHASSIS_PARTITION_CLEAR",
    ],
    "GW_ALARM_CHASSIS_PEM": ["GW_ALARM_CHASSIS_PEM", "GW_ALARM_CHASSIS_PEM_CLEAR"],
    "GW_ALARM_CHASSIS_POE": ["GW_ALARM_CHASSIS_POE", "GW_ALARM_CHASSIS_POE_CLEAR"],
    "GW_ALARM_CHASSIS_PSU": ["GW_ALARM_CHASSIS_PSU", "GW_ALARM_CHASSIS_PSU_CLEAR"],
    "GW_ALARM_CHASSIS_WARM": ["GW_ALARM_CHASSIS_WARM", "GW_ALARM_CHASSIS_WARM_CLEAR"],
    "GW_APPID_INSTALL": ["GW_APPID_INSTALL_FAILED", "GW_APPID_INSTALLED"],
    "GW_ARP": ["GW_ARP_UNRESOLVED", "GW_ARP_RESOLVED"],
    "GW_BGP_NEIGHBOR": ["GW_BGP_NEIGHBOR_DOWN", "GW_BGP_NEIGHBOR_UP"],
    "GW_CONDUCTOR": ["GW_CONDUCTOR_DISCONNECTED", "GW_CONDUCTOR_CONNECTED"],
    "GW_CONFIG": [
        "GW_CONFIG_FAILED",
        "GW_CONFIG_LOCK_FAILED",
        "GW_CONFIG_ERROR_ADDTL_COMMAND",
        "GW_CONFIGURED",
    ],
    "GW_DHCP": ["GW_DHCP_UNRESOLVED", "GW_DHCP_RESOLVED"],
    "GW_DISCONNECTED": ["GW_DISCONNECTED", "GW_CONNECTED"],
    "GW_FIB_COUNT": [
        "GW_FIB_COUNT_THRESHOLD_EXCEEDED",
        "GW_FIB_COUNT_RETURNED_TO_NORMAL",
    ],
    "GW_FLOW_COUNT": [
        "GW_FLOW_COUNT_THRESHOLD_EXCEEDED",
        "GW_FLOW_COUNT_RETURNED_TO_NORMAL",
    ],
    "GW_HA_CONTROL_LINK": ["GW_HA_CONTROL_LINK_DOWN", "GW_HA_CONTROL_LINK_UP"],
    "GW_HA_HEALTH_WEIGHT": ["GW_HA_HEALTH_WEIGHT_LOW", "GW_HA_HEALTH_WEIGHT_RECOVERY"],
    "GW_IDP_INSTALL": ["GW_IDP_INSTALL_FAILED", "GW_IDP_INSTALLED"],
    "GW_OSPF_NEIGHBOR": ["GW_OSPF_NEIGHBOR_DOWN", "GW_OSPF_NEIGHBOR_UP"],
    "GW_PORT": ["GW_PORT_DOWN", "GW_PORT_UP"],
    "GW_RECOVERY_SNAPSHOT": [
        "GW_RECOVERY_SNAPSHOT_FAILED",
        "GW_RECOVERY_SNAPSHOT_SUCCEEDED",
        "GW_RECOVERY_SNAPSHOT_NOTNEEDED",
    ],
    "GW_TUNNEL": ["GW_TUNNEL_DOWN", "GW_TUNNEL_UP"],
    "GW_UPGRADE": ["GW_UPGRADE_FAILED", "GW_UPGRADED"],
    "GW_VPN_PATH": ["GW_VPN_PATH_DOWN", "GW_VPN_PATH_UP"],
    "GW_VPN_PEER": ["GW_VPN_PEER_DOWN", "GW_VPN_PEER_UP"],
    "GW_ZTP": ["GW_ZTP_FAILED", "GW_ZTP_FINISHED"],
    # ME Events
    "ME_DISCONNECTED": ["ME_DISCONNECTED", "ME_CONNECTED"],
    "ME_FAN": ["ME_FAN_UNPLUGGED", "ME_FAN_PLUGGED"],
    "ME_POWERINPUT": ["ME_POWERINPUT_DISCONNECTED", "ME_POWERINPUT_CONNECTED"],
    "ME_PSU": ["ME_PSU_UNPLUGGED", "ME_PSU_PLUGGED"],
    "ME_SERVICE": ["ME_SERVICE_CRASHED", "ME_SERVICE_FAILED", "ME_SERVICE_STARTED"],
    # SW Events
    "SW_ALARM_CHASSIS_FAN": ["SW_ALARM_CHASSIS_FAN", "SW_ALARM_CHASSIS_FAN_CLEAR"],
    "SW_ALARM_CHASSIS_HOT": ["SW_ALARM_CHASSIS_HOT", "SW_ALARM_CHASSIS_HOT_CLEAR"],
    "SW_ALARM_CHASSIS_HUMIDITY": [
        "SW_ALARM_CHASSIS_HUMIDITY",
        "SW_ALARM_CHASSIS_HUMIDITY_CLEAR",
    ],
    "SW_ALARM_CHASSIS_MGMT_LINK": [
        "SW_ALARM_CHASSIS_MGMT_LINK_DOWN",
        "SW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR",
    ],
    "SW_ALARM_CHASSIS_PARTITION": [
        "SW_ALARM_CHASSIS_PARTITION",
        "SW_ALARM_CHASSIS_PARTITION_CLEAR",
    ],
    "SW_ALARM_CHASSIS_PEM": ["SW_ALARM_CHASSIS_PEM", "SW_ALARM_CHASSIS_PEM_CLEAR"],
    "SW_ALARM_CHASSIS_POE": ["SW_ALARM_CHASSIS_POE", "SW_ALARM_CHASSIS_POE_CLEAR"],
    "SW_ALARM_CHASSIS_PSU": ["SW_ALARM_CHASSIS_PSU", "SW_ALARM_CHASSIS_PSU_CLEAR"],
    "SW_ALARM_IOT": ["SW_ALARM_IOT_SET", "SW_ALARM_IOT_CLEAR"],
    "SW_ALARM_VC_VERSION_MISMATCH": [
        "SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH",
        "SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH_CLEAR",
    ],
    "SW_BFD_SESSION": ["SW_BFD_SESSION_DISCONNECTED", "SW_BFD_SESSION_ESTABLISHED"],
    "SW_BGP_NEIGHBOR": ["SW_BGP_NEIGHBOR_DOWN", "SW_BGP_NEIGHBOR_UP"],
    "SW_CONFIG": [
        "SW_CONFIG_FAILED",
        "SW_CONFIG_LOCK_FAILED",
        "SW_CONFIG_ERROR_ADDTL_COMMAND",
        "SW_CONFIGURED",
    ],
    "SW_DDOS_PROTOCOL_VIOLATION": [
        "SW_DDOS_PROTOCOL_VIOLATION_SET",
        "SW_DDOS_PROTOCOL_VIOLATION_CLEAR",
    ],
    "SW_DISCONNECTED": ["SW_DISCONNECTED", "SW_CONNECTED"],
    "SW_EVPN_CORE_ISOLATION": [
        "SW_EVPN_CORE_ISOLATED",
        "SW_EVPN_CORE_ISOLATION_CLEARED",
    ],
    "SW_FPC_POWER": ["SW_FPC_POWER_OFF", "SW_FPC_POWER_ON"],
    "SW_LACPD_TIMEOUT": ["SW_LACPD_TIMEOUT", "SW_LACPD_TIMEOUT_CLEARED"],
    "SW_LOOP": ["SW_LOOP_DETECTED", "SW_LOOP_CLEARED"],
    "SW_MAC_LEARNING": ["SW_MAC_LEARNING_STOPPED", "SW_MAC_LEARNING_RESUMED"],
    "SW_MAC_LIMIT": ["SW_MAC_LIMIT_EXCEEDED", "SW_MAC_LIMIT_RESET"],
    "SW_OSPF_NEIGHBOR": ["SW_OSPF_NEIGHBOR_DOWN", "SW_OSPF_NEIGHBOR_UP"],
    "SW_PORT": ["SW_PORT_DOWN", "SW_PORT_UP"],
    "SW_PORT_BPDU": ["SW_PORT_BPDU_ERROR_CLEARED", "SW_PORT_BPDU_BLOCKED"],
    "SW_RECOVERY_SNAPSHOT": [
        "SW_RECOVERY_SNAPSHOT_FAILED",
        "SW_RECOVERY_SNAPSHOT_SUCCEEDED",
        "SW_RECOVERY_SNAPSHOT_NOTNEEDED",
    ],
    "SW_UPGRADE": ["SW_UPGRADE_FAILED", "SW_UPGRADED"],
    "SW_VC_PORT": ["SW_VC_PORT_DOWN", "SW_VC_PORT_UP"],
    "SW_VC_TRANSITION": ["SW_VC_IN_TRANSITION", "SW_VC_STABLE"],
    "SW_ZTP": ["SW_ZTP_FAILED", "SW_ZTP_FINISHED"],
    # TT Events
    "TT_MONITORED_RESOURCE": [
        "TT_MONITORED_RESOURCE_FAILED",
        "TT_MONITORED_RESOURCE_RECOVERED",
    ],
    "TT_PORT_BLOCKED": ["TT_PORT_BLOCKED", "TT_PORT_RECOVERY"],
    "TT_PORT_LACP": [
        "TT_PORT_DROPPED_FROM_LACP",
        "TT_PORT_LAST_DROPPED_FROM_LACP",
        "TT_PORT_JOINED_LACP",
        "TT_PORT_FIRST_JOIN_LACP",
    ],
    "TT_PORT_LINK": ["TT_PORT_LINK_DOWN", "TT_PORT_LINK_RECOVERY"],
    "TT_TUNNELS": ["TT_TUNNELS_LOST", "TT_TUNNELS_UP"],
}


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """Progress bar for long-running operations."""

    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print("Progress: ", end="")
        print(f"[{'█' * x}{'.' * (size - delta - x)}]", end="")
        print(f"{int(percent * 100)}%".rjust(5), end="")

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
        """Set the total number of steps for the progress bar."""
        self.steps_count = 0
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        """Log a message."""
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        """Log a success message."""
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        """Log a warning message."""
        LOGGER.warning("%s: Warning", message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        """Log a failure message."""
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        """Log a title message."""
        LOGGER.info("%s", message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


#####################################################################
#### FUNCTIONS ####
def _retrieve_events(
    mist_session: mistapi.APISession,
    org_id: str,
    event_types: str | None = None,
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
            limit=1000,
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
            return False, []
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        if not retry:
            return _retrieve_events(mist_session, org_id, event_types, duration, True)
        else:
            return False, []


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
    event_category: str,
    trigger_events: list,
    clear_events: list,
):
    LOGGER.debug("_process_common (category %s): %s", event_category, event)
    event_timestamp = event.get("timestamp", 0)
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        event_category,
        None,
        None,
    )
    if event_type in trigger_events:
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type in clear_events:
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


def _process_config(
    devices: dict,
    event_type: str,
    event: dict,
    event_category: str,
    trigger_events: list,
    clear_events: list,
):
    LOGGER.debug("_process_config (category %s): %s", event_category, event)
    event_text = ""
    for text in event.get("text", "").split("\n"):
        event_text += f"{text.strip()}\n"
    event_timestamp = event.get("timestamp", 0)
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        event_category,
        None,
        None,
    )
    device_entry["details"] = event_text
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
    LOGGER.debug("_process_gw_arp: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = (
                event_text.replace('"', "")
                .split("network-interface:")[1]
                .strip()
                .split(",")[0]
            )
        except Exception:
            LOGGER.error("_process_gw_arp: Unable to extract peer from %s", event_text)
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_gw_bgp_neighbor: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_neighbor = None
    if not event_neighbor:
        try:
            event_neighbor = event_text.split("neighbor")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_gw_bgp_neighbor: Unable to extract peer from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_gw_health_weight: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_node = None
    if not event_node:
        try:
            event_node = event_text.split("Detected")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_gw_health_weight: Unable to extract node from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_gw_tunnel: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_tunnel = None
    if not event_tunnel:
        try:
            event_tunnel = event_text.split("Tunnel")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_gw_tunnel: Unable to extract peer from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_gw_vpn_path: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_path = None
    if not event_path:
        try:
            event_path = event_text.split("path")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_gw_vpn_path: Unable to extract peer from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_gw_vpn_peer: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_peer = None
    if not event_peer:
        try:
            event_peer = event_text.split("peer")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_gw_vpn_peer: Unable to extract peer from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
################################# GW_OSPF_NEIGHBOR_DOWN
def _process_gw_ospf_neighbor(devices: dict, event_type: str, event: dict):
    LOGGER.debug("_process_gw_ospf_neighbor: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_neighbor = None
    if not event_neighbor:
        try:
            event_neighbor = event_text.split("neighbor")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_gw_ospf_neighbor: Unable to extract peer from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        "GW_OSPF_NEIGHBOR_DOWN",
        "Neighbor",
        event_neighbor,
    )
    if event_type == "GW_OSPF_NEIGHBOR_DOWN":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "GW_OSPF_NEIGHBOR_UP":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


###################################################################################################
################################# PORT EVENTS (generic for AP/GW/SW)
def _process_port_event(
    devices: dict,
    event_type: str,
    event: dict,
    event_category: str,
    trigger_events: list,
    clear_events: list,
):
    LOGGER.debug("_process_port_event (category %s): %s", event_category, event)
    event_timestamp = event.get("timestamp", 0)
    event_port_id = event.get("port_id")
    if not event_port_id:
        event_port_id = "unknown"
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        event_category,
        "Port ID",
        event_port_id,
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
##                                       MXEDGE                                                  ##
##                                                                                               ##
###################################################################################################
###################################################################################################
################################# ME_COMPONENT (FAN/PSU/POWERINPUT)
def _process_me_component(
    devices: dict, event_type: str, event: dict, event_category: str
):
    LOGGER.debug("_process_me_component (category %s): %s", event_category, event)
    event_timestamp = event.get("timestamp", 0)
    event_component = event.get("component", "unknown")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        event_category,
        "Component",
        event_component,
    )
    if "UNPLUGGED" in event_type or "DISCONNECTED" in event_type:
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if "PLUGGED" in event_type or "CONNECTED" in event_type:
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


###################################################################################################
################################# ME_SERVICE
def _process_me_service(devices: dict, event_type: str, event: dict):
    LOGGER.debug("_process_me_service: %s", event)
    event_timestamp = event.get("timestamp", 0)
    event_service = event.get("service", "unknown")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        "ME_SERVICE_FAILED",
        "Service",
        event_service,
    )
    if event_type in ["ME_SERVICE_CRASHED", "ME_SERVICE_FAILED"]:
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "ME_SERVICE_STARTED":
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
def _process_sw_ddos_protocol_violation(
    devices: dict, event_type: str, event: dict
) -> None:
    LOGGER.debug("_process_sw_ddos_protocol_violation: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_protocol_name = event.get("protocol_name")
    if not event_protocol_name:
        try:
            event_protocol_name = (
                event_text.split("protocol/exception")[1].strip().split(" ")[0]
            )
        except Exception:
            LOGGER.error(
                "_process_sw_ddos_protocol_violation: Unable to extract interface name from %s",
                event_text,
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_sw_fpc_power: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_fru_slot = event.get("fru_slot")
    if not event_fru_slot:
        try:
            event_fru_slot = event_text.split("jnxFruSlot")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_sw_fpc_power: Unable to extract interface name from %s",
                event_text,
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_sw_mac_limit: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.split(";")[0].split(" ")[-1]
        except Exception:
            LOGGER.error(
                "_process_sw_mac_limit: Unable to extract interface name from %s",
                event_text,
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_sw_ospf_neighbor: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_neighbor = None
    if not event_neighbor:
        try:
            event_neighbor = event_text.split("neighbor")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_sw_ospf_neighbor: Unable to extract peer from %s", event_text
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_sw_port_bpdu: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.split("Interface")[1].strip().split(" ")[0]
        except Exception:
            LOGGER.error(
                "_process_sw_port_bpdu: Unable to extract interface name from %s",
                event_text,
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
    LOGGER.debug("_process_sw_vc_port: %s", event)
    event_text = event.get("text", "")
    event_timestamp = event.get("timestamp", 0)
    event_port_id = event.get("port_id")
    if not event_port_id:
        try:
            event_port_id = event_text.split(" on ")[1].strip().split(",")[0]
        except Exception:
            LOGGER.error(
                "_process_sw_vc_port: Unable to extract interface name from %s",
                event_text,
            )
            return
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
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
##                                       TUNTERM                                                 ##
##                                                                                               ##
###################################################################################################
###################################################################################################
################################# TT_MONITORED_RESOURCE
def _process_tt_monitored_resource(devices: dict, event_type: str, event: dict):
    LOGGER.debug("_process_tt_monitored_resource: %s", event)
    event_timestamp = event.get("timestamp", 0)
    event_resource = event.get("resource", "unknown")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        "TT_MONITORED_RESOURCE_FAILED",
        "Resource",
        event_resource,
    )
    if event_type == "TT_MONITORED_RESOURCE_FAILED":
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type == "TT_MONITORED_RESOURCE_RECOVERED":
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


###################################################################################################
################################# TT_PORT
def _process_tt_port(
    devices: dict, event_type: str, event: dict, event_category: str
):
    LOGGER.debug("_process_tt_port (category %s): %s", event_category, event)
    event_timestamp = event.get("timestamp", 0)
    event_port = event.get("port", "unknown")
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        event_category,
        "Port",
        event_port,
    )
    if event_type in ["TT_PORT_BLOCKED", "TT_PORT_LINK_DOWN"]:
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type in ["TT_PORT_RECOVERY", "TT_PORT_LINK_RECOVERY"]:
        device_entry["status"] = "cleared"
        device_entry["cleared"] += 1
    device_entry["last_change"] = datetime.fromtimestamp(round(event_timestamp))


###################################################################################################
################################# TT_PORT_LACP
def _process_tt_port_lacp(devices: dict, event_type: str, event: dict):
    LOGGER.debug("_process_tt_port_lacp: %s", event)
    event_timestamp = event.get("timestamp", 0)
    event_port = event.get("port", "unknown")
    event_lag = event.get("lag", "")
    identifier = f"{event_lag}/{event_port}" if event_lag else event_port
    _check_device(devices, event)
    device_entry = _check_device_events(
        devices,
        event.get("device_type", ""),
        event.get("mac", ""),
        "TT_PORT_DROPPED_FROM_LACP",
        "LAG/Port",
        identifier,
    )
    if event_type in ["TT_PORT_DROPPED_FROM_LACP", "TT_PORT_LAST_DROPPED_FROM_LACP"]:
        device_entry["status"] = "triggered"
        device_entry["triggered"] += 1
    if event_type in ["TT_PORT_JOINED_LACP", "TT_PORT_FIRST_JOIN_LACP"]:
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
def _get_sites(apisession: mistapi.APISession, org_id: str) -> dict:
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
    except Exception:
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
            LOGGER.error("_get_sites: missing site data for site %s", site)
    PB.log_success(message, inc=False, display_pbar=False)
    return data


def _get_devices(apisession: mistapi.APISession, org_id: str) -> dict:
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
    except Exception:
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
            LOGGER.warning("_get_devices: missing device data for device %s", device)
    LOGGER.info("_get_devices: retrieved %d devices", len(data))
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
    event_type: str,
    event_identifier_header: str | None = None,
    event_identifier: str | None = None,
) -> dict:
    if event_identifier:
        if not devices[event_device_type][event_device_mac]["events"].get(event_type):
            devices[event_device_type][event_device_mac]["events"][event_type] = {
                "identifier_header": event_identifier_header
            }
        device_event = devices[event_device_type][event_device_mac]["events"][
            event_type
        ]
        if not device_event.get(event_identifier):
            device_event[event_identifier] = {
                "status": None,
                "triggered": 0,
                "cleared": 0,
                "last_change": -1,
                "details": "",
            }
        return device_event[event_identifier]
    else:
        if not devices[event_device_type][event_device_mac]["events"].get(event_type):
            devices[event_device_type][event_device_mac]["events"][event_type] = {
                "identifier_header": event_identifier_header,
                "status": None,
                "triggered": 0,
                "cleared": 0,
                "last_change": -1,
                "details": "",
            }
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
        devices[event_device_type][event_device_mac] = {
            "model": None,
            "version": None,
            "site_id": None,
            "events": {},
        }
    if event_device_model:
        devices[event_device_type][event_device_mac]["model"] = event_device_model
    if event_device_version:
        devices[event_device_type][event_device_mac]["version"] = event_device_version
    if event_site_id:
        devices[event_device_type][event_device_mac]["site_id"] = event_site_id


def _process_events(events: list) -> dict:
    message = "Processing list of Events"
    PB.log_message(message, display_pbar=False)
    device_events = {"gateway": {}, "switch": {}, "ap": {}, "mxedge": {}}
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
                ["AP_CONFIGURED", "AP_RECONFIGURED"],
            )
        elif event_type in ["AP_DISCONNECTED", "AP_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "AP_DISCONNECTED",
                ["AP_DISCONNECTED"],
                ["AP_CONNECTED"],
            )
        elif event_type.startswith("AP_RADSEC"):
            _process_common(
                device_events,
                event_type,
                event,
                "AP_RADSEC_FAILURE",
                ["AP_RADSEC_FAILURE"],
                ["AP_RADSEC_RECOVERY"],
            )
        elif event_type.startswith("AP_UPGRADE"):
            _process_common(
                device_events,
                event_type,
                event,
                "AP_UPGRADE_FAILED",
                ["AP_UPGRADE_FAILED"],
                ["AP_UPGRADED"],
            )
        elif event_type in ["AP_PORT_DOWN", "AP_PORT_UP"]:
            _process_port_event(
                device_events,
                event_type,
                event,
                "AP_PORT_DOWN",
                ["AP_PORT_DOWN"],
                ["AP_PORT_UP"],
            )
        ####### ESL
        elif event_type in ["ESL_HUNG", "ESL_RECOVERED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "ESL_HUNG",
                ["ESL_HUNG"],
                ["ESL_RECOVERED"],
            )
        ####### GW
        elif event_type.startswith("GW_ALARM_CHASSIS_FAN"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_FAN",
                ["GW_ALARM_CHASSIS_FAN"],
                ["GW_ALARM_CHASSIS_FAN_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_HOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_HOT",
                ["GW_ALARM_CHASSIS_HOT"],
                ["GW_ALARM_CHASSIS_HOT_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_HUMIDITY"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_HUMIDITY",
                ["GW_ALARM_CHASSIS_HUMIDITY"],
                ["GW_ALARM_CHASSIS_HUMIDITY_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_MGMT_LINK"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_MGMT_LINK_DOWN",
                ["GW_ALARM_CHASSIS_MGMT_LINK_DOWN"],
                ["GW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_PARTITION"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_PARTITION",
                ["GW_ALARM_CHASSIS_PARTITION"],
                ["GW_ALARM_CHASSIS_PARTITION_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_PEM"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_PEM",
                ["GW_ALARM_CHASSIS_PEM"],
                ["GW_ALARM_CHASSIS_PEM_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_POE"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_POE",
                ["GW_ALARM_CHASSIS_POE"],
                ["GW_ALARM_CHASSIS_POE_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_PSU"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_PSU",
                ["GW_ALARM_CHASSIS_PSU"],
                ["GW_ALARM_CHASSIS_PSU_CLEAR"],
            )
        elif event_type.startswith("GW_ALARM_CHASSIS_WARM"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_ALARM_CHASSIS_WARM",
                ["GW_ALARM_CHASSIS_WARM"],
                ["GW_ALARM_CHASSIS_WARM_CLEAR"],
            )
        elif event_type.startswith("GW_APPID_INSTALL"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_APPID_INSTALL_FAILED",
                ["GW_APPID_INSTALL_FAILED"],
                ["GW_APPID_INSTALLED"],
            )
        elif event_type.startswith("GW_ARP"):
            _process_gw_arp(device_events, event_type, event)
        elif event_type.startswith("GW_BGP_NEIGHBOR"):
            _process_gw_bgp_neighbor(device_events, event_type, event)
        elif event_type.startswith("GW_CONFIG_") or event_type in [
            "GW_CONFIGURED",
            "GW_RECONFIGURED",
        ]:
            _process_config(
                device_events,
                event_type,
                event,
                "GW_CONFIG_FAILED",
                [
                    "GW_CONFIG_FAILED",
                    "GW_CONFIG_LOCK_FAILED",
                    "GW_CONFIG_ERROR_ADDTL_COMMAND",
                ],
                ["GW_CONFIGURED", "GW_RECONFIGURED"],
            )
        elif event_type in ["GW_CONDUCTOR_DISCONNECTED", "GW_CONDUCTOR_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "GW_CONDUCTOR_DISCONNECTED",
                ["GW_CONDUCTOR_DISCONNECTED"],
                ["GW_CONDUCTOR_CONNECTED"],
            )
        elif event_type in ["GW_DHCP_UNRESOLVED", "GW_DHCP_RESOLVED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "GW_DHCP_UNRESOLVED",
                ["GW_DHCP_UNRESOLVED"],
                ["GW_DHCP_RESOLVED"],
            )
        elif event_type in ["GW_DISCONNECTED", "GW_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "GW_DISCONNECTED",
                ["GW_DISCONNECTED"],
                ["GW_CONNECTED"],
            )
        elif event_type.startswith("GW_FIB_COUNT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_FIB_COUNT_THRESHOLD_EXCEEDED",
                ["GW_FIB_COUNT_THRESHOLD_EXCEEDED"],
                ["GW_FIB_COUNT_RETURNED_TO_NORMAL"],
            )
        elif event_type.startswith("GW_FLOW_COUNT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_FLOW_COUNT_THRESHOLD_EXCEEDED",
                ["GW_FLOW_COUNT_THRESHOLD_EXCEEDED"],
                ["GW_FLOW_COUNT_RETURNED_TO_NORMAL"],
            )
        elif event_type.startswith("GW_HA_CONTROL_LINK"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_HA_CONTROL_LINK_DOWN",
                ["GW_HA_CONTROL_LINK_DOWN"],
                ["GW_HA_CONTROL_LINK_UP"],
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
                ["GW_IDP_INSTALLED"],
            )
        elif event_type.startswith("GW_OSPF_NEIGHBOR"):
            _process_gw_ospf_neighbor(device_events, event_type, event)
        elif event_type in ["GW_PORT_DOWN", "GW_PORT_UP"]:
            _process_port_event(
                device_events,
                event_type,
                event,
                "GW_PORT_DOWN",
                ["GW_PORT_DOWN"],
                ["GW_PORT_UP"],
            )
        elif event_type.startswith("GW_RECOVERY_SNAPSHOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "GW_RECOVERY_SNAPSHOT_FAILED",
                ["GW_RECOVERY_SNAPSHOT_FAILED"],
                ["GW_RECOVERY_SNAPSHOT_SUCCEEDED", "GW_RECOVERY_SNAPSHOT_NOTNEEDED"],
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
                ["GW_UPGRADED"],
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
                ["GW_ZTP_FINISHED"],
            )
        ####### ME
        elif event_type in ["ME_DISCONNECTED", "ME_CONNECTED"]:
            _process_common(
                device_events,
                event_type,
                event,
                "ME_DISCONNECTED",
                ["ME_DISCONNECTED"],
                ["ME_CONNECTED"],
            )
        elif event_type in ["ME_FAN_UNPLUGGED", "ME_FAN_PLUGGED"]:
            _process_me_component(device_events, event_type, event, "ME_FAN_UNPLUGGED")
        elif event_type in ["ME_POWERINPUT_DISCONNECTED", "ME_POWERINPUT_CONNECTED"]:
            _process_me_component(device_events, event_type, event, "ME_POWERINPUT_DISCONNECTED")
        elif event_type in ["ME_PSU_UNPLUGGED", "ME_PSU_PLUGGED"]:
            _process_me_component(device_events, event_type, event, "ME_PSU_UNPLUGGED")
        elif event_type in ["ME_SERVICE_CRASHED", "ME_SERVICE_FAILED", "ME_SERVICE_STARTED"]:
            _process_me_service(device_events, event_type, event)
        ####### SW
        elif event_type.startswith("SW_ALARM_CHASSIS_FAN"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_FAN",
                ["SW_ALARM_CHASSIS_FAN"],
                ["SW_ALARM_CHASSIS_FAN_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_HOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_HOT",
                ["SW_ALARM_CHASSIS_HOT"],
                ["SW_ALARM_CHASSIS_HOT_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_HUMIDITY"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_HUMIDITY",
                ["SW_ALARM_CHASSIS_HUMIDITY"],
                ["SW_ALARM_CHASSIS_HUMIDITY_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_MGMT_LINK"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_MGMT_LINK_DOWN",
                ["SW_ALARM_CHASSIS_MGMT_LINK_DOWN"],
                ["SW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_PARTITION"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_PARTITION",
                ["SW_ALARM_CHASSIS_PARTITION"],
                ["SW_ALARM_CHASSIS_PARTITION_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_PEM"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_PEM",
                ["SW_ALARM_CHASSIS_PEM"],
                ["SW_ALARM_CHASSIS_PEM_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_POE"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_POE",
                ["SW_ALARM_CHASSIS_POE"],
                ["SW_ALARM_CHASSIS_POE_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_CHASSIS_PSU"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_CHASSIS_PSU",
                ["SW_ALARM_CHASSIS_PSU"],
                ["SW_ALARM_CHASSIS_PSU_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_IOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_IOT_SET",
                ["SW_ALARM_IOT_SET"],
                ["SW_ALARM_IOT_CLEAR"],
            )
        elif event_type.startswith("SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH",
                ["SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH"],
                ["SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH_CLEAR"],
            )
        elif event_type.startswith("SW_CONFIG_") or event_type in [
            "SW_CONFIGURED",
            "SW_RECONFIGURED",
        ]:
            _process_config(
                device_events,
                event_type,
                event,
                "SW_CONFIG_FAILED",
                [
                    "SW_CONFIG_FAILED",
                    "SW_CONFIG_LOCK_FAILED",
                    "SW_CONFIG_ERROR_ADDTL_COMMAND",
                ],
                ["SW_CONFIGURED", "SW_RECONFIGURED"],
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
                ["SW_CONNECTED"],
            )
        elif event_type.startswith("SW_EVPN_CORE_ISO"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_EVPN_CORE_ISOLATED",
                ["SW_EVPN_CORE_ISOLATED"],
                ["SW_EVPN_CORE_ISOLATION_CLEARED"],
            )
        elif event_type.startswith("SW_FPC_POWER"):
            _process_sw_fpc_power(device_events, event_type, event)
        elif event_type.startswith("SW_LACPD_TIMEOUT"):
            _process_port_event(
                device_events,
                event_type,
                event,
                "SW_LACPD_TIMEOUT",
                ["SW_LACPD_TIMEOUT"],
                ["SW_LACPD_TIMEOUT_CLEARED"],
            )
        elif event_type.startswith("SW_LOOP"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_LOOP_DETECTED",
                ["SW_LOOP_DETECTED"],
                ["SW_LOOP_CLEARED"],
            )
        elif event_type.startswith("SW_MAC_LEARNING"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_MAC_LEARNING_STOPPED",
                ["SW_MAC_LEARNING_STOPPED"],
                ["SW_MAC_LEARNING_RESUMED"],
            )
        elif event_type.startswith("SW_MAC_LIMIT"):
            _process_sw_mac_limit(device_events, event_type, event)
        elif event_type.startswith("SW_OSPF_NEIGHBOR"):
            _process_sw_ospf_neighbor(device_events, event_type, event)
        elif event_type in ["SW_PORT_DOWN", "SW_PORT_UP"]:
            _process_port_event(
                device_events,
                event_type,
                event,
                "SW_PORT_DOWN",
                ["SW_PORT_DOWN"],
                ["SW_PORT_UP"],
            )
        elif event_type.startswith("SW_PORT_BPDU"):
            _process_sw_port_bpdu(device_events, event_type, event)
        elif event_type.startswith("SW_RECOVERY_SNAPSHOT"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_RECOVERY_SNAPSHOT_FAILED",
                ["SW_RECOVERY_SNAPSHOT_FAILED"],
                ["SW_RECOVERY_SNAPSHOT_SUCCEEDED", "SW_RECOVERY_SNAPSHOT_NOTNEEDED"],
            )
        elif event_type.startswith("SW_UPGRADE"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_UPGRADE_FAILED",
                ["SW_UPGRADE_FAILED"],
                ["SW_UPGRADED"],
            )
        elif event_type.startswith("SW_VC_PORT"):
            _process_sw_vc_port(device_events, event_type, event)
        elif event_type.startswith("SW_VC_IN_TRANSITION") or event_type.startswith("SW_VC_STABLE"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_VC_IN_TRANSITION",
                ["SW_VC_IN_TRANSITION"],
                ["SW_VC_STABLE"],
            )
        elif event_type.startswith("SW_ZTP"):
            _process_common(
                device_events,
                event_type,
                event,
                "SW_ZTP_FAILED",
                ["SW_ZTP_FAILED"],
                ["SW_ZTP_FINISHED"],
            )
        ####### TT
        elif event_type.startswith("TT_MONITORED_RESOURCE"):
            _process_tt_monitored_resource(device_events, event_type, event)
        elif event_type in ["TT_PORT_BLOCKED", "TT_PORT_RECOVERY"]:
            _process_tt_port(device_events, event_type, event, "TT_PORT_BLOCKED")
        elif event_type in [
            "TT_PORT_DROPPED_FROM_LACP",
            "TT_PORT_LAST_DROPPED_FROM_LACP",
            "TT_PORT_JOINED_LACP",
            "TT_PORT_FIRST_JOIN_LACP",
        ]:
            _process_tt_port_lacp(device_events, event_type, event)
        elif event_type in ["TT_PORT_LINK_DOWN", "TT_PORT_LINK_RECOVERY"]:
            _process_tt_port(device_events, event_type, event, "TT_PORT_LINK_DOWN")
        elif event_type in ["TT_TUNNELS_LOST", "TT_TUNNELS_UP"]:
            _process_common(
                device_events,
                event_type,
                event,
                "TT_TUNNELS_LOST",
                ["TT_TUNNELS_LOST"],
                ["TT_TUNNELS_UP"],
            )
    PB.log_success(message, inc=False, display_pbar=False)
    return device_events


def _check_timeout(raised_timeout: int, last_change: datetime, status: str) -> bool:
    timeout = False
    now = datetime.now()
    delta_time = (now - last_change).total_seconds()
    if delta_time >= (raised_timeout * 60) and status == "triggered":
        timeout = True
    return timeout


def _display_device_results(
    device_events: dict, raised_timeout: int, resolve_sites: dict, resolve_devices: dict
):
    headers = [
        "Event Type",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change",
        "Details",
    ]
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                data = []
                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    if event_data.get("identifier_header"):
                        for (
                            event_identifier,
                            event_identifier_data,
                        ) in event_data.items():
                            if event_identifier == "identifier_header":
                                continue
                            if not event_identifier_data.get("triggered"):
                                continue
                            timeout = _check_timeout(
                                raised_timeout,
                                event_identifier_data.get("last_change"),
                                event_identifier_data.get("status"),
                            )
                            if raised_timeout == 0 or timeout:
                                data.append(
                                    [
                                        event_type,
                                        f"{event_data['identifier_header']} {event_identifier}",
                                        event_identifier_data.get("status"),
                                        event_identifier_data.get("triggered"),
                                        event_identifier_data.get("cleared"),
                                        event_identifier_data.get("last_change"),
                                        event_identifier_data.get("details"),
                                    ]
                                )
                    else:
                        if not event_data.get("triggered"):
                            continue
                        timeout = _check_timeout(
                            raised_timeout,
                            event_data.get("last_change"),
                            event_data.get("status"),
                        )
                        if raised_timeout == 0 or timeout:
                            data.append(
                                [
                                    event_type,
                                    "",
                                    event_data.get("status"),
                                    event_data.get("triggered"),
                                    event_data.get("cleared"),
                                    event_data.get("last_change"),
                                    event_data.get("details"),
                                ]
                            )
                if data:
                    site_id = device_data.get("site_id")
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
                        print(
                            f"{device_type} {device_name} (mac: {device_mac}, model: {device_data.get('model')}, version: {device_data.get('version')})"
                        )
                    else:
                        print(
                            f"{device_type} {device_mac} (model : {device_data.get('model')}, version: {device_data.get('version')})"
                        )
                    print()
                    print(
                        mistapi.cli.tabulate(
                            data, headers=headers, tablefmt="rounded_grid"
                        )
                    )


def _display_event_results(
    device_events: dict, raised_timeout: int, resolve_sites: dict, resolve_devices: dict
):
    headers = [
        "Site",
        "Device",
        "Event Info",
        "Current Status",
        "Trigger Count",
        "Clear Count",
        "Last Change",
        "Details",
    ]
    event_reports = {}
    for _, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                site_id = device_data.get("site_id")
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
                        for (
                            event_identifier,
                            event_identifier_data,
                        ) in event_data.items():
                            if event_identifier == "identifier_header":
                                continue
                            if not event_identifier_data.get("triggered"):
                                continue
                            timeout = _check_timeout(
                                raised_timeout,
                                event_identifier_data.get("last_change"),
                                event_identifier_data.get("status"),
                            )
                            if raised_timeout == 0 or timeout:
                                event_reports[event_type].append(
                                    [
                                        site_entry,
                                        device_entry,
                                        f"{event_data['identifier_header']} {event_identifier}",
                                        event_identifier_data.get("status"),
                                        event_identifier_data.get("triggered"),
                                        event_identifier_data.get("cleared"),
                                        event_identifier_data.get("last_change"),
                                        event_identifier_data.get("details"),
                                    ]
                                )
                    else:
                        if not event_data.get("triggered"):
                            continue
                        timeout = _check_timeout(
                            raised_timeout,
                            event_data.get("last_change"),
                            event_data.get("status"),
                        )
                        if raised_timeout == 0 or timeout:
                            event_reports[event_type].append(
                                [
                                    site_entry,
                                    device_entry,
                                    "",
                                    event_data.get("status"),
                                    event_data.get("triggered"),
                                    event_data.get("cleared"),
                                    event_data.get("last_change"),
                                    event_data.get("details"),
                                ]
                            )
    for event_type, report in event_reports.items():
        if report:
            print()
            print()
            print("".center(80, "─"))
            print()
            print(f"Event Type: {event_type}")
            print()
            print(
                mistapi.cli.tabulate(report, headers=headers, tablefmt="rounded_grid")
            )


def _gen_device_insight_url(
    apisession: mistapi.APISession,
    org_id: str,
    device_type: str,
    device_mac: str,
    site_id: str,
):
    if device_type == "switch":
        d_type = "juniperSwitch"
    elif device_type == "gateway":
        d_type = "juniperGateway"
    else:
        d_type = "device"
    return f"https://{apisession.get_cloud().replace('api', 'manage')}/admin/?org_id={org_id}#!dashboard/insights/{d_type}/00000000-0000-0000-1000-{device_mac}/{site_id}"


def _export_to_csv(
    apisession: mistapi.APISession,
    org_id: str,
    csv_file: str,
    device_events: dict,
    raised_timeout: int,
    resolve_sites: dict,
    resolve_devices: dict,
):
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
        "Device Insight URL",
        "Details",
    ]
    data = []
    for device_type, devices in device_events.items():
        if devices:
            for device_mac, device_data in devices.items():
                site_id = device_data.get("site_id")
                events = device_data.get("events", {})
                for event_type, event_data in events.items():
                    if event_data.get("identifier_header"):
                        for (
                            event_identifier,
                            event_identifier_data,
                        ) in event_data.items():
                            if event_identifier == "identifier_header":
                                continue
                            if not event_identifier_data.get("triggered"):
                                continue
                            timeout = _check_timeout(
                                raised_timeout,
                                event_identifier_data.get("last_change"),
                                event_identifier_data.get("status"),
                            )
                            if raised_timeout == 0 or timeout:
                                data.append(
                                    [
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
                                        _gen_device_insight_url(
                                            apisession,
                                            org_id,
                                            device_type,
                                            device_mac,
                                            site_id,
                                        ),
                                        event_identifier_data.get(
                                            "details", ""
                                        ).replace("\n", " "),
                                    ]
                                )
                    else:
                        if not event_data.get("triggered"):
                            continue
                        timeout = _check_timeout(
                            raised_timeout,
                            event_data.get("last_change"),
                            event_data.get("status"),
                        )
                        if raised_timeout == 0 or timeout:
                            data.append(
                                [
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
                                    _gen_device_insight_url(
                                        apisession,
                                        org_id,
                                        device_type,
                                        device_mac,
                                        site_id,
                                    ),
                                    event_data.get("details", "").replace("\n", " "),
                                ]
                            )
    with open(csv_file, "w", encoding="UTF8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)


###################################################################################################
################################# START
def start(
    mist_session: mistapi.APISession,
    org_id: str,
    event_types: str | None = None,
    duration: str = "1d",
    raised_timeout: int = 5,
    view: str = "event",
    csv_file: str = "./list_open_events.csv",
    no_resolve: bool = False,
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
    if events:
        try:
            events = sorted(events, key=lambda x: x["timestamp"])
        except Exception:
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
        _export_to_csv(
            mist_session,
            org_id,
            csv_file,
            device_events,
            raised_timeout,
            sites,
            devices,
        )
        if view.lower() == "device":
            _display_device_results(device_events, raised_timeout, sites, devices)
        elif view.lower() != "continue":
            _display_event_results(device_events, raised_timeout, sites, devices)


def usage(error_message: str | None = None):
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

| Script Event Options          | Mist Triggering Events                                                            | Mist Clearing Events                                          |
|-------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------|
| AP_CONFIG                     | AP_CONFIG_FAILED                                                                  | AP_CONFIGURED,AP_RECONFIGURED                                 |
| AP_DISCONNECTED               | AP_DISCONNECTED                                                                   | AP_CONNECTED                                                  |
| AP_PORT                       | AP_PORT_DOWN                                                                      | AP_PORT_UP                                                    |
| AP_RADSEC                     | AP_RADSEC_FAILURE                                                                 | AP_RADSEC_RECOVERY                                            |
| AP_UPGRADE                    | AP_UPGRADE_FAILED                                                                 | AP_UPGRADED                                                   |
| ESL_HUNG                      | ESL_HUNG                                                                          | ESL_RECOVERED                                                 |
| GW_ALARM_CHASSIS_FAN          | GW_ALARM_CHASSIS_FAN                                                              | GW_ALARM_CHASSIS_FAN_CLEAR                                    |
| GW_ALARM_CHASSIS_HOT          | GW_ALARM_CHASSIS_HOT                                                              | GW_ALARM_CHASSIS_HOT_CLEAR                                    |
| GW_ALARM_CHASSIS_HUMIDITY     | GW_ALARM_CHASSIS_HUMIDITY                                                         | GW_ALARM_CHASSIS_HUMIDITY_CLEAR                               |
| GW_ALARM_CHASSIS_MGMT_LINK    | GW_ALARM_CHASSIS_MGMT_LINK_DOWN                                                   | GW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR                         |
| GW_ALARM_CHASSIS_PARTITION    | GW_ALARM_CHASSIS_PARTITION                                                        | GW_ALARM_CHASSIS_PARTITION_CLEAR                              |
| GW_ALARM_CHASSIS_PEM          | GW_ALARM_CHASSIS_PEM                                                              | GW_ALARM_CHASSIS_PEM_CLEAR                                    |
| GW_ALARM_CHASSIS_POE          | GW_ALARM_CHASSIS_POE                                                              | GW_ALARM_CHASSIS_POE_CLEAR                                    |
| GW_ALARM_CHASSIS_PSU          | GW_ALARM_CHASSIS_PSU                                                              | GW_ALARM_CHASSIS_PSU_CLEAR                                    |
| GW_ALARM_CHASSIS_WARM         | GW_ALARM_CHASSIS_WARM                                                             | GW_ALARM_CHASSIS_WARM_CLEAR                                   |
| GW_APPID_INSTALL              | GW_APPID_INSTALL_FAILED                                                           | GW_APPID_INSTALLED                                            |
| GW_ARP                        | GW_ARP_UNRESOLVED                                                                 | GW_ARP_RESOLVED                                               |
| GW_BGP_NEIGHBOR               | GW_BGP_NEIGHBOR_DOWN                                                              | GW_BGP_NEIGHBOR_UP                                            |
| GW_CONDUCTOR                  | GW_CONDUCTOR_DISCONNECTED                                                         | GW_CONDUCTOR_CONNECTED                                        |
| GW_CONFIG                     | GW_CONFIG_FAILED,GW_CONFIG_LOCK_FAILED,GW_CONFIG_ERROR_ADDTL_COMMAND              | GW_CONFIGURED,GW_RECONFIGURED                                 |
| GW_DHCP                       | GW_DHCP_UNRESOLVED                                                                | GW_DHCP_RESOLVED                                              |
| GW_DISCONNECTED               | GW_DISCONNECTED                                                                   | GW_CONNECTED                                                  |
| GW_FIB_COUNT                  | GW_FIB_COUNT_THRESHOLD_EXCEEDED                                                   | GW_FIB_COUNT_RETURNED_TO_NORMAL                               |
| GW_FLOW_COUNT                 | GW_FLOW_COUNT_THRESHOLD_EXCEEDED                                                  | GW_FLOW_COUNT_RETURNED_TO_NORMAL                              |
| GW_HA_CONTROL_LINK            | GW_HA_CONTROL_LINK_DOWN                                                           | GW_HA_CONTROL_LINK_UP                                         |
| GW_HA_HEALTH_WEIGHT           | GW_HA_HEALTH_WEIGHT_LOW                                                           | GW_HA_HEALTH_WEIGHT_RECOVERY                                  |
| GW_IDP_INSTALL                | GW_IDP_INSTALL_FAILED                                                             | GW_IDP_INSTALLED                                              |
| GW_OSPF_NEIGHBOR              | GW_OSPF_NEIGHBOR_DOWN                                                             | GW_OSPF_NEIGHBOR_UP                                           |
| GW_PORT                       | GW_PORT_DOWN                                                                      | GW_PORT_UP                                                    |
| GW_RECOVERY_SNAPSHOT          | GW_RECOVERY_SNAPSHOT_FAILED                                                       | GW_RECOVERY_SNAPSHOT_SUCCEEDED,GW_RECOVERY_SNAPSHOT_NOTNEEDED |
| GW_TUNNEL                     | GW_TUNNEL_DOWN                                                                    | GW_TUNNEL_UP                                                  |
| GW_UPGRADE                    | GW_UPGRADE_FAILED                                                                 | GW_UPGRADED                                                   |
| GW_VPN_PATH                   | GW_VPN_PATH_DOWN                                                                  | GW_VPN_PATH_UP                                                |
| GW_VPN_PEER                   | GW_VPN_PEER_DOWN                                                                  | GW_VPN_PEER_UP                                                |
| GW_ZTP                        | GW_ZTP_FAILED                                                                     | GW_ZTP_FINISHED                                               |
| ME_DISCONNECTED               | ME_DISCONNECTED                                                                   | ME_CONNECTED                                                  |
| ME_FAN                        | ME_FAN_UNPLUGGED                                                                  | ME_FAN_PLUGGED                                                |
| ME_POWERINPUT                 | ME_POWERINPUT_DISCONNECTED                                                        | ME_POWERINPUT_CONNECTED                                       |
| ME_PSU                        | ME_PSU_UNPLUGGED                                                                  | ME_PSU_PLUGGED                                                |
| ME_SERVICE                    | ME_SERVICE_CRASHED,ME_SERVICE_FAILED                                              | ME_SERVICE_STARTED                                            |
| SW_ALARM_CHASSIS_FAN          | SW_ALARM_CHASSIS_FAN                                                              | SW_ALARM_CHASSIS_FAN_CLEAR                                    |
| SW_ALARM_CHASSIS_HOT          | SW_ALARM_CHASSIS_HOT                                                              | SW_ALARM_CHASSIS_HOT_CLEAR                                    |
| SW_ALARM_CHASSIS_HUMIDITY     | SW_ALARM_CHASSIS_HUMIDITY                                                         | SW_ALARM_CHASSIS_HUMIDITY_CLEAR                               |
| SW_ALARM_CHASSIS_MGMT_LINK    | SW_ALARM_CHASSIS_MGMT_LINK_DOWN                                                   | SW_ALARM_CHASSIS_MGMT_LINK_DOWN_CLEAR                         |
| SW_ALARM_CHASSIS_PARTITION    | SW_ALARM_CHASSIS_PARTITION                                                        | SW_ALARM_CHASSIS_PARTITION_CLEAR                              |
| SW_ALARM_CHASSIS_PEM          | SW_ALARM_CHASSIS_PEM                                                              | SW_ALARM_CHASSIS_PEM_CLEAR                                    |
| SW_ALARM_CHASSIS_POE          | SW_ALARM_CHASSIS_POE                                                              | SW_ALARM_CHASSIS_POE_CLEAR                                    |
| SW_ALARM_CHASSIS_PSU          | SW_ALARM_CHASSIS_PSU                                                              | SW_ALARM_CHASSIS_PSU_CLEAR                                    |
| SW_ALARM_IOT                  | SW_ALARM_IOT_SET                                                                  | SW_ALARM_IOT_CLEAR                                            |
| SW_ALARM_VC_VERSION_MISMATCH  | SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH                                         | SW_ALARM_VIRTUAL_CHASSIS_VERSION_MISMATCH_CLEAR               |
| SW_BFD_SESSION                | SW_BFD_SESSION_DISCONNECTED                                                       | SW_BFD_SESSION_ESTABLISHED                                    |
| SW_BGP_NEIGHBOR               | SW_BGP_NEIGHBOR_DOWN                                                              | SW_BGP_NEIGHBOR_UP                                            |
| SW_CONFIG                     | SW_CONFIG_FAILED,SW_CONFIG_LOCK_FAILED,SW_CONFIG_ERROR_ADDTL_COMMAND              | SW_CONFIGURED,SW_RECONFIGURED                                 |
| SW_DDOS_PROTOCOL_VIOLATION    | SW_DDOS_PROTOCOL_VIOLATION_SET                                                    | SW_DDOS_PROTOCOL_VIOLATION_CLEAR                              |
| SW_DISCONNECTED               | SW_DISCONNECTED                                                                   | SW_CONNECTED                                                  |
| SW_EVPN_CORE_ISOLATION        | SW_EVPN_CORE_ISOLATED                                                             | SW_EVPN_CORE_ISOLATION_CLEARED                                |
| SW_FPC_POWER                  | SW_FPC_POWER_OFF                                                                  | SW_FPC_POWER_ON                                               |
| SW_LACPD_TIMEOUT              | SW_LACPD_TIMEOUT                                                                  | SW_LACPD_TIMEOUT_CLEARED                                      |
| SW_LOOP                       | SW_LOOP_DETECTED                                                                  | SW_LOOP_CLEARED                                               |
| SW_MAC_LEARNING               | SW_MAC_LEARNING_STOPPED                                                           | SW_MAC_LEARNING_RESUMED                                       |
| SW_MAC_LIMIT                  | SW_MAC_LIMIT_EXCEEDED                                                             | SW_MAC_LIMIT_RESET                                            |
| SW_OSPF_NEIGHBOR              | SW_OSPF_NEIGHBOR_DOWN                                                             | SW_OSPF_NEIGHBOR_UP                                           |
| SW_PORT                       | SW_PORT_DOWN                                                                      | SW_PORT_UP                                                    |
| SW_PORT_BPDU                  | SW_PORT_BPDU_BLOCKED                                                              | SW_PORT_BPDU_ERROR_CLEARED                                    |
| SW_RECOVERY_SNAPSHOT          | SW_RECOVERY_SNAPSHOT_FAILED                                                       | SW_RECOVERY_SNAPSHOT_SUCCEEDED,SW_RECOVERY_SNAPSHOT_NOTNEEDED |
| SW_UPGRADE                    | SW_UPGRADE_FAILED                                                                 | SW_UPGRADED                                                   |
| SW_VC_PORT                    | SW_VC_PORT_DOWN                                                                   | SW_VC_PORT_UP                                                 |
| SW_VC_TRANSITION              | SW_VC_IN_TRANSITION                                                               | SW_VC_STABLE                                                  |
| SW_ZTP                        | SW_ZTP_FAILED                                                                     | SW_ZTP_FINISHED                                               |
| TT_MONITORED_RESOURCE         | TT_MONITORED_RESOURCE_FAILED                                                      | TT_MONITORED_RESOURCE_RECOVERED                               |
| TT_PORT_BLOCKED               | TT_PORT_BLOCKED                                                                   | TT_PORT_RECOVERY                                              |
| TT_PORT_LACP                  | TT_PORT_DROPPED_FROM_LACP,TT_PORT_LAST_DROPPED_FROM_LACP                          | TT_PORT_JOINED_LACP,TT_PORT_FIRST_JOIN_LACP                   |
| TT_PORT_LINK                  | TT_PORT_LINK_DOWN                                                                 | TT_PORT_LINK_RECOVERY                                         |
| TT_TUNNELS                    | TT_TUNNELS_LOST                                                                   | TT_TUNNELS_UP                                                 |


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
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__,
        )


###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Display list of open events/alarms that are not cleared"
    )
    parser.add_argument(
        "-e", "--env_file", help="define the env file to use", default=None
    )
    parser.add_argument(
        "-o",
        "--org_id",
        help="Set the org_id where the webhook must be create/delete/retrieved",
        default="",
    )
    parser.add_argument(
        "-t", "--event_types", help="comma separated list of event types"
    )
    parser.add_argument(
        "-d", "--duration", help="duration of the events to look at", default="1d"
    )
    parser.add_argument(
        "-r",
        "--trigger_timeout",
        help="timeout (in minutes) before listing the event if it is not cleared",
        type=int,
        default=5,
    )
    parser.add_argument(
        "-l",
        "--log_file",
        help="define the filepath/filename where to write the logs",
        default=LOG_FILE,
    )
    parser.add_argument(
        "-v",
        "--view",
        help="Type of report to display",
        choices=["event", "device"],
        default="event",
    )
    parser.add_argument(
        "-c",
        "--csv_file",
        help="Path to the CSV file where to save the result",
        default=CSV_FILE,
    )
    parser.add_argument(
        "-n",
        "--no-resolve",
        help="disable the device (device name) resolution",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    ENV_FILE = args.env_file
    ORG_ID = args.org_id
    EVENT_TYPES = []
    DURATION = args.duration
    TIMEOUT = args.trigger_timeout
    VIEW = args.view
    CSV_FILE = args.csv_file
    LOG_FILE = args.log_file
    NO_RESOLVE = args.no_resolve

    # Validate duration format
    if not DURATION.endswith(("m", "h", "d", "w")):
        usage(
            f'Invalid -d / --duration parameter value, should be something like "10m", "2h", "7d", "1w"... Got "{DURATION}".'
        )

    # Process event types
    if args.event_types:
        for t in args.event_types.split(","):
            event_def = EVENT_TYPES_DEFINITIONS.get(t.strip().upper())
            if event_def and event_def in EVENT_TYPES_DEFINITIONS.values():
                EVENT_TYPES += event_def
            else:
                usage(f'Invalid -t / --event_type parameter value. Got "{t}".')

    if not EVENT_TYPES:
        for k, v in EVENT_TYPES_DEFINITIONS.items():
            EVENT_TYPES += v
    EVENT_TYPES = ",".join(EVENT_TYPES)
    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(
        APISESSION, ORG_ID, EVENT_TYPES, DURATION, TIMEOUT, VIEW, CSV_FILE, NO_RESOLVE
    )
