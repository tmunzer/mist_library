"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to display the list of events/alarms that are not cleared. The 
script is trying to correlate the different events to identidy the "opening"
and the "closing" events, and only display the event if it is not "closed" for
more than the `trigger_timeout`.

NOTE 1: 
This script is only working with the following alarm types:
* gw_bgp_neighbor_up / gw_bgp_neighbor_down
* vpn_peer_up / vpn_peer_down

NOTE 2:
It is possible to leverage the linux `watch` command to get the list refreshed
every X sec/min. 
When using the `watch` command, all the script parameters should be passed as
arguments:

exmample: 
watch -n 30 python3 ./list_open_events.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t vpn_peer_down,vpn_peer_up,gw_bgp_neighbor_down,gw_bgp_neighbor_up

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Set the org_id where the webhook must be create/delete/retrieved
                            This parameter cannot be used if -s/--site_id is used.
                            If no org_id and not site_id are defined, the script will show
                            a menu to select the org/the site.

-a, --alarm_types=          comma separated list of alarm types that should be retrieved from
                            the Mist Org and processed. See the list in "Note 1" above
-d, --duration              duration of the events to look at
                            default: 1d
-t, --trigger_timeout=      timeout (in minutes) before listing the event if it is not closed
                            default: 5

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
        -d 1w -t vpn_peer_down,vpn_peer_up,gw_bgp_neighbor_down,gw_bgp_neighbor_up

"""

#### IMPORTS ####
import sys
import getopt
import logging
import re
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

#### FUNCTIONS ####


def _retrieve_events(
    mist_session: mistapi.APISession,
    org_id: str,
    alarm_types: str = None,
    duration: str = "1d",
    retry=False,
):
    try:
        resp = mistapi.api.v1.orgs.alarms.searchOrgAlarms(
            mist_session, org_id, type=alarm_types, duration=duration, limit=1000
        )
        if resp.status_code == 200:
            events = mistapi.get_all(mist_session, resp)
            return True, events
        elif not retry:
            return _retrieve_events(mist_session, org_id, alarm_types, duration, True)
        else:
            return False, None
    except Exception as e:
        LOGGER.error("Exception occurred", exc_info=True)
        if not retry:
            return _retrieve_events(mist_session, org_id, alarm_types, duration, True)
        else:
            return False, None


###################################################################################################
################################# VPN
def _vpn_peer_down(events: list):
    vpn_downs = {}
    tmp = list(filter(lambda event: event["type"] == "vpn_peer_down", events))
    for e in tmp:
        gateway = e.get("gateways", ["unknown"])[0]
        hostname = e.get("hostnames", ["unknown"])[0]
        last_seen = e.get("last_seen", -1)
        for r in e.get("reasons", []):
            peer_ip = r.replace("Tunnel to peer ", "").replace(" disconnected", "")
            if not vpn_downs.get(gateway):
                vpn_downs[gateway] = {
                    "hostname": hostname,
                    "peers": {peer_ip: {"last_seen": last_seen, "cleared": -1}},
                }
            elif not vpn_downs[gateway]["peers"].get(peer_ip):
                vpn_downs[gateway]["peers"][peer_ip] = {
                    "last_seen": last_seen,
                    "cleared": -1,
                }
            elif vpn_downs[gateway]["peers"][peer_ip]["last_seen"] < last_seen:
                vpn_downs[gateway]["hostname"] = hostname
                vpn_downs[gateway]["peers"][peer_ip]["last_seen"] = last_seen
    return vpn_downs


def _vpn_peer_up(events: list, vpn_downs: dict):
    tmp = list(filter(lambda event: event["type"] == "vpn_peer_up", events))
    for e in tmp:
        gateway = e.get("gateways", ["unknown"])[0]
        hostname = e.get("hostnames", ["unknown"])[0]
        last_seen = e.get("last_seen", -1)
        for r in e.get("reasons", []):
            peer_ip = r.replace("Tunnel to peer ", "").replace(" established", "")
            if (
                vpn_downs.get(gateway)
                and vpn_downs[gateway]["peers"].get(peer_ip)
                and vpn_downs[gateway]["peers"][peer_ip]["last_seen"] < last_seen
            ):
                vpn_downs[gateway]["hostname"] = hostname
                vpn_downs[gateway]["peers"][peer_ip]["cleared"] = last_seen
    return vpn_downs


def _process_vpn_peer(events, raised_timeout):
    vpn_downs = _vpn_peer_down(events)
    vpn_downs = _vpn_peer_up(events, vpn_downs)
    now_ts = round(datetime.timestamp(datetime.now()))
    vpn_headers = ["GW Hostname", "GW MAC", "Peer IP", "VPN down for (sec)"]
    vpn_results = []
    for gateway_mac, gateway_data in vpn_downs.items():
        gateway_name = gateway_data["hostname"]
        for peer_ip, peer_data in gateway_data.get("peers", {}).items():
            down = peer_data.get("last_seen", -1)
            cleared = peer_data.get("cleared", -1)
            delta = now_ts - down
            if cleared < 0 and delta > raised_timeout * 60:
                # if delta > raised_timeout*60 :
                #     delta_str = f"\033[31m{delta}\033[0m"
                # else:
                #     delta_str = f"\033[92m{delta}\033[0m"
                delta_str = f"{delta}"
                vpn_results.append([gateway_name, gateway_mac, peer_ip, delta_str])
    res = sorted(vpn_results, key=lambda x: x[3], reverse=False)
    return vpn_headers, res


###################################################################################################
################################# BGP
def _gw_bgp_neighbor_down(events: list):
    bgp_downs = {}
    tmp = list(filter(lambda event: event["type"] == "gw_bgp_neighbor_down", events))
    for e in tmp:
        gateway = e.get("gateways", ["unknown"])[0]
        hostname = e.get("hostnames", ["unknown"])[0]
        last_seen = e.get("last_seen", -1)
        for r in e.get("reasons", []):
            bgp_re = r"(?P<ip>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}) .* \(instance (?P<vpn_instance>\S+)\)"
            res = re.findall(bgp_re, r)
            peer_ip = res[0][0]
            vpn_instance = res[0][1]
            if not bgp_downs.get(gateway):
                bgp_downs[gateway] = {
                    "hostname": hostname,
                    "peers": {
                        peer_ip: {
                            "last_seen": last_seen,
                            "vpn_instance": vpn_instance,
                            "cleared": -1,
                        }
                    },
                }
            elif not bgp_downs[gateway]["peers"].get(peer_ip):
                bgp_downs[gateway]["peers"][peer_ip] = {
                    "last_seen": last_seen,
                    "vpn_instance": vpn_instance,
                    "cleared": -1,
                }
            elif bgp_downs[gateway]["peers"][peer_ip]["last_seen"] < last_seen:
                bgp_downs[gateway]["hostname"] = hostname
                bgp_downs[gateway]["peers"][peer_ip]["last_seen"] = last_seen
    return bgp_downs


def _gw_bgp_neighbor_up(events: list, bgp_downs: dict):
    tmp = list(filter(lambda event: event["type"] == "gw_bgp_neighbor_up", events))
    for e in tmp:
        gateway = e.get("gateways", ["unknown"])[0]
        hostname = e.get("hostnames", ["unknown"])[0]
        last_seen = e.get("last_seen", -1)
        for r in e.get("reasons", []):
            bgp_re = r"(?P<ip>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}) .* \(instance (?P<vpn_instance>\S+)\)"
            res = re.findall(bgp_re, r)
            peer_ip = res[0][0]
            if (bgp_downs.get(gateway)
                and bgp_downs[gateway]["peers"].get(peer_ip)
                and bgp_downs[gateway]["peers"][peer_ip]["last_seen"] < last_seen
            ):
                bgp_downs[gateway]["hostname"] = hostname
                bgp_downs[gateway]["peers"][peer_ip]["cleared"] = last_seen
    return bgp_downs


def _process_bgp_peer(events, raised_timeout):
    bgp_downs = _gw_bgp_neighbor_down(events)
    bgp_downs = _gw_bgp_neighbor_up(events, bgp_downs)
    now_ts = round(datetime.timestamp(datetime.now()))
    bgp_headers = [
        "GW Hostname",
        "GW MAC",
        "BGP Peer IP",
        "VPN Instance",
        "VPN down for (sec)",
    ]
    bgp_results = []
    for gateway_mac, gateway_data in bgp_downs.items():
        gateway_name = gateway_data["hostname"]
        for peer_ip, peer_data in gateway_data.get("peers", {}).items():
            vpn_instance = peer_data.get("vpn_instance")
            down = peer_data.get("last_seen", -1)
            cleared = peer_data.get("cleared", -1)
            delta = now_ts - down
            if cleared < 0 and delta > raised_timeout * 60:
                # if delta > raised_timeout*60 :
                #     delta_str = f"\033[31m{delta}\033[0m"
                # else:
                #     delta_str = f"\033[92m{delta}\033[0m"
                delta_str = f"{delta}"
                bgp_results.append(
                    [gateway_name, gateway_mac, peer_ip, vpn_instance, delta_str]
                )
    res = sorted(bgp_results, key=lambda x: x[4], reverse=False)
    return bgp_headers, res


def start(
    mist_session: mistapi.APISession,
    org_id: str,
    alarm_types: str = None,
    duration: str = "1d",
    raised_timeout: int = 5,
):
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]

    success, events = _retrieve_events(mist_session, org_id, alarm_types, duration)
    vpn_headers, vpn_results = _process_vpn_peer(events, raised_timeout)
    bgp_headers, bgp_results = _process_bgp_peer(events, raised_timeout)
    print()
    print(" VPN Status ".center(80, "_"))
    print()
    if vpn_results:
        print(mistapi.cli.tabulate(vpn_results, headers=vpn_headers, tablefmt="github"))
    else:
        print("No disconnected VPN found".center(80))
    print()
    print()
    print(" BGP Status ".center(80, "_"))
    print()
    if bgp_results:
        print(mistapi.cli.tabulate(bgp_results, headers=bgp_headers, tablefmt="github"))
    else:
        print("No BGP Peer Down found".center(80))
    print()
    print()


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
script is trying to correlate the different events to identidy the "opening"
and the "closing" events, and only display the event if it is not "closed" for
more than the `trigger_timeout`.

NOTE 1: 
This script is only working with the following alarm types:
* gw_bgp_neighbor_up / gw_bgp_neighbor_down
* vpn_peer_up / vpn_peer_down

NOTE 2:
It is possible to leverage the linux `watch` command to get the list refreshed
every X sec/min. 
When using the `watch` command, all the script parameters should be passed as
arguments:

exmample: 
watch -n 30 python3 ./list_open_events.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t vpn_peer_down,vpn_peer_up,gw_bgp_neighbor_down,gw_bgp_neighbor_up

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Set the org_id where the webhook must be create/delete/retrieved
                            This parameter cannot be used if -s/--site_id is used.
                            If no org_id and not site_id are defined, the script will show
                            a menu to select the org/the site.

-a, --alarm_types=          comma separated list of alarm types that should be retrieved from
                            the Mist Org and processed. See the list in "Note 1" above
-d, --duration              duration of the events to look at
                            default: 1d
-t, --trigger_timeout=      timeout (in minutes) before listing the event if it is not closed
                            default: 5

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
        -d 1w -t vpn_peer_down,vpn_peer_up,gw_bgp_neighbor_down,gw_bgp_neighbor_up
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
            "he:o:a:d:t:l:",
            [
                "help",
                "env_file=",
                "org_id=",
                "alarm_types=",
                "duration=",
                "trigger_timeout=",
                "log_file=",
            ],
        )
    except getopt.GetoptError as err:
        usage(err)

    ENV_FILE = None
    ORG_ID = None
    ALARM_TYPES = None
    DURATION = None
    TIMEOUT = 5
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-e", "--env_file"]:
            ENV_FILE = a
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-t", "--alarm_types"]:
            ALARM_TYPES = a
        elif o in ["-d", "--duration"]:
            DURATION = a
        elif o in ["-r", "--trigger_timeout"]:
            TIMEOUT = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    apisession.login()
    start(apisession, ORG_ID, ALARM_TYPES, DURATION, TIMEOUT)
