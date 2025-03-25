"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to update the IP addresses of the switches in an EVPN Topology.
The script will generate the IP addresses based on the networks defined in the
EVPN Topology and the number of switches to update, and only update the switches
that are part of the Routing layer.
It is possible to select the first or last IP addresses of the networks or to
define a specific starting IP address for each network.

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
-h, --help          display this help

-f, --file=         path to the CSV file
                    Default is ./provision_evpntoplogy_vlans.csv

-o, --org_id=       ID of the Mist Org (only for Org EVPN Topology)
-s, --site_id=      ID of the Mist Site (only for Site EVPN Topology)
-t, --evpn_id=      ID of the EVPN Topology

--ipv4_first        Use the first IP addresses of the networks to generate 
                    the IP addresses (EVPN Gateway excluded).
                    Cannot be used with --ipv4_last or --ipv4_from/--ipv4_to.
--ipv4_last         Use the last IP addresses of the networks to generate 
                    the IP addresses
                    Cannot be used with --ipv4_first or --ipv4_from/--ipv4_to.
--ipv4_from=        Define the first IP address of the range of IP addresses for each
                    network. Format is "network_name:ip_address". Multiple networks can be
                    defined separated by a comma.
                    Cannot be used with --ipv4_first or --ipv4_last, but can be used
                    (for different networks) with --ipv4_to
                    e.g. --ipv4_from="corp:10.31.12.100,voice:10.31.23.0"
                    e.g. --ipv4_from="corp:10.31.12.100"  --ipv4_from="voice:10.31.23.0"
--ipv4_to=          Define the last IP address of the range of IP addresses for each
                    network. Format is "network_name:ip_address". Multiple networks can be
                    defined separated by a comma.
                    Cannot be used with --ipv4_first or --ipv4_last, but can be used
                    (for different networks) with --ipv4_from
                    e.g. --ipv4_to="corp:10.31.12.100,voice:10.31.23.0"
                    e.g. --ipv4_to="corp:10.31.12.100"  --ipv4_to="voice:10.31.23.0"
                
-l, --log_file=     define the filepath/filename where to write the logs
                    Default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    Default is "~/.mist_env"

-------
Examples:
python3 ./update_evpn_switch_ip.py --ipv4_last
python3 ./update_evpn_switch_ip.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -t 95e1a820-xxxx-xxxx-xxxx-59fc972d0607 \
    --ipv4_from="corp:10.11.12.100"
    --ipv4_from="voice:10.12.12.150"

"""

#### IMPORTS #####
import sys
import csv
import getopt
import logging
import ipaddress

MISTAPI_MIN_VERSION = "0.55.5"

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

#####################################################################
#### PARAMETERS #####
VRF_FILE = "./provision_evpntoplogy_vlans.csv"
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print("\033[A")
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
        print()
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def inc(self, size: int = 80):
        self.steps_count += 1
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
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


###############################################################################
# RETRIEVE DATA
def _retrieve_switch(apisession: mistapi.APISession, site_id: str, switch_mac: str):
    device_id = f"00000000-0000-0000-1000-{switch_mac}"
    try:
        message = f"Retrieving Device {switch_mac} config"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.sites.devices.getSiteDevice(
            apisession, site_id, device_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        CONSOLE.error("Please check script logs")
        sys.exit(1)


def _update_switch(apisession: mistapi.APISession, device: dict):
    site_id = device.get("site_id")
    device_id = device.get("id")
    try:
        message = f"Update Device config for {device_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.sites.devices.updateSiteDevice(
            apisession, site_id, device_id, device
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        CONSOLE.error("Please check script logs")
        sys.exit(1)


def _generate_switch(device: dict, networks: dict, index: int):
    warning = False
    message = f"Generate Device config for {device.get('mac')}"
    PB.log_message(message, display_pbar=False)
    for network_name, network_conf in networks.items():
        try:
            device["other_ip_configs"][network_name] = {
                "type": "static",
                "ip": str(network_conf["ips"][index]),
                "netmask": str(network_conf["netmask"]),
                "evpn_anycast": True,
            }
        except:
            warning = True
            LOGGER.error("Exception occurred", exc_info=True)
            device["other_ip_configs"][network_name] = network_conf
    if warning:
        PB.log_warning(message, display_pbar=False)
    else:
        PB.log_success(message, display_pbar=False)
    return device


def _process_switch(
    apisession: mistapi.APISession, switch: dict, networks: dict, index: int
):
    site_id = switch.get("site_id")
    switch_mac = switch.get("mac")
    device = _retrieve_switch(apisession, site_id, switch_mac)
    device = _generate_switch(device, networks, index)
    _update_switch(apisession, device)


###############################################################################
# ORG SCOPE
def _retrieve_org_evpn_topo(
    apisession: mistapi.APISession, org_id: str, evpn_topo_id: str
):
    try:
        message = f"Retrieving Org EVPN Topology {evpn_topo_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.evpn_topologies.getOrgEvpnTopology(
            apisession, org_id, evpn_topo_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        CONSOLE.error("Please check script logs")
        sys.exit(1)


def _retrieve_org_networks(
    api_session: mistapi.APISession, org_id: str, switches: list
):
    networks = {}
    deviceprofile_ids = []
    for switch in switches:
        deviceprofile_id = switch.get("deviceprofile_id")
        if deviceprofile_id not in deviceprofile_ids:
            try:
                message = f"Retrieving Networks for Device Profile {deviceprofile_id}"
                PB.log_message(message, display_pbar=False)
                resp = mistapi.api.v1.orgs.deviceprofiles.getOrgDeviceProfile(
                    api_session, org_id, deviceprofile_id
                )
                if resp.status_code == 200:
                    deviceprofile_ids.append(deviceprofile_id)
                    PB.log_success(message, display_pbar=False)
                    for network_name, network_data in resp.data.get("networks", {}).items():
                        networks[network_name] = network_data
                else:
                    PB.log_failure(message, display_pbar=False)
                    CONSOLE.error("Please check script logs")
                    sys.exit(1)
            except:
                PB.log_failure(message, display_pbar=False)
                LOGGER.error("Exception occurred", exc_info=True)
                CONSOLE.error("Please check script logs")
                sys.exit(1)
    return networks


###############################################################################
# SITE SCOPE
def _retrieve_site_evpn_topo(
    apisession: mistapi.APISession, site_id: str, evpn_topo_id: str
):
    try:
        message = f"Retrieving Site EVPN Topology {evpn_topo_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.sites.evpn_topologies.getSiteEvpnTopology(
            apisession, site_id, evpn_topo_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        CONSOLE.error("Please check script logs")
        sys.exit(1)


def _retrieve_site_networks(api_session: mistapi.APISession, site_id: str):
    try:
        message = f"Retrieving Networks for Site {site_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.sites.setting.getSiteSetting(api_session, site_id)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data.get("networks", {})
        else:
            PB.log_failure(message, display_pbar=False)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)


###############################################################################
# EVPN TOPO PROCESSING
def _process_networks(
    networks: dict,
    ipv4_first: bool,
    ipv4_last: bool,
    ipv4_from: dict,
    ipv4_to: dict,
    switch_count: int,
):
    network_ips = {}
    for network_name, networks_data in networks.items():
        subnet = networks_data.get("subnet")
        gateway = networks_data.get("gateway")
        if subnet:
            addresses = list(ipaddress.ip_network(subnet).hosts())
            netmask = str(ipaddress.ip_network(subnet).netmask)
            if gateway:
                addresses.remove(ipaddress.IPv4Address(gateway))
            if ipv4_first:
                try:
                    network_ips[network_name] = {
                        "ips": addresses[:switch_count],
                        "netmask": netmask,
                    }
                except:
                    CONSOLE.error(
                        f"Not enough IP addresses available for the network {network_name}"
                    )
                    sys.exit(2)
            elif ipv4_last:
                try:
                    network_ips[network_name] = {
                        "ips": addresses[-switch_count:],
                        "netmask": netmask,
                    }
                except:
                    CONSOLE.error(
                        f"Not enough IP addresses available for the network {network_name}"
                    )
                    sys.exit(2)
            elif network_name in ipv4_from:
                LOGGER.debug(f"_process_networks: ipv4_from: {ipv4_from}")
                start = ipv4_from.get(network_name)
                index = addresses.index(ipaddress.IPv4Address(start))
                try:
                    network_ips[network_name] = {
                        "ips": addresses[index : index + switch_count],
                        "netmask": netmask,
                    }
                except:
                    CONSOLE.error(
                        f"Not enough IP addresses available for the network {network_name}"
                    )
                    sys.exit(2)
            elif network_name in ipv4_to:
                LOGGER.debug(f"_process_networks: ipv4_from: {ipv4_to}")
                start = ipv4_to.get(network_name)
                index = addresses.index(ipaddress.IPv4Address(start))
                try:
                    network_ips[network_name] = {
                        "ips": addresses[index - switch_count : index],
                        "netmask": netmask,
                    }
                except:
                    CONSOLE.error(
                        f"Not enough IP addresses available for the network {network_name}"
                    )
                    sys.exit(2)
            
            
    for network_name in network_ips:
        LOGGER.info(
            f"_process_networks: IPs for network {network_name} ({networks[network_name]['subnet']}): {network_ips[network_name]}"
        )
    return network_ips


def _process_evpn_topo(
    apisession: mistapi.APISession,
    org_id: str,
    site_id: str,
    evpn_topo_id: str,
    ipv4_first: bool,
    ipv4_last: bool,
    ipv4_from: dict,
    ipv4_to: dict,
):
    evpn_topo = None
    networks = None
    if org_id:
        evpn_topo = _retrieve_org_evpn_topo(apisession, org_id, evpn_topo_id)
        networks = _retrieve_org_networks(apisession, org_id, evpn_topo.get("switches"))
    else:
        evpn_topo = _retrieve_site_evpn_topo(apisession, site_id, evpn_topo_id)
        networks = _retrieve_site_networks(apisession, site_id)
    LOGGER.debug(f"_process_evpn_topo: EVPN Topology: {evpn_topo}")
    LOGGER.debug(f"_process_evpn_topo: Networks: {networks}")
    routed_at = evpn_topo.get("evpn_options", {}).get("routed_at")
    switches = []
    dedicated_ip = False
    shared_ip = False
    for switch in evpn_topo.get("switches"):
        switch_role = switch.get("role")
        switch_mac = switch.get("mac")
        if (
            (switch_role == "collapsed-core") 
            or (routed_at == "core" and switch_role == "core")
        ):
            LOGGER.debug(
                f"_process_evpn_topo: switch {switch_mac} is {switch_role}. EVPN routed at {routed_at}. Will be updated with dedicated IP"
            )
            switches.append(switch)
            dedicated_ip = True
        elif (
            (routed_at == "distribution" and switch_role == "distribution")
            or (routed_at == "edge" and switch_role == "access")
        ):
            LOGGER.debug(
                f"_process_evpn_topo: switch {switch_mac} is {switch_role}. EVPN routed at {routed_at}. Will be updated with shared IP"
            )
            switches.append(switch)
            shared_ip = True
        else:
            LOGGER.debug(
                f"_process_evpn_topo: switch {switch_mac} is {switch_role}. EVPN routed at {routed_at}. Will NOT be updated"
            )
    if dedicated_ip == shared_ip:
        CONSOLE.error("Unable to determine the type of EVPN Topology... Please report the issue and the script.log file...")
    elif dedicated_ip:
        network_ips = _process_networks(
            networks, ipv4_first, ipv4_last, ipv4_from, ipv4_to, len(switches)
        )
        for index, switch in enumerate(switches):
            _process_switch(apisession, switch, network_ips, index)
    else:
        network_ips = _process_networks(
            networks, ipv4_first, ipv4_last, ipv4_from, ipv4_to,1
        )
        for index, switch in enumerate(switches):
            _process_switch(apisession, switch, network_ips, 0)


###############################################################################
# MAIN


def _select_scope(apisession: mistapi.APISession):
    while True:
        print("EVPN Topology Scope to edit:")
        print("1. Organization")
        print("2. Site")
        print("3. Exit")
        choice = input("Select the scope: ")
        if choice == "1":
            org_id = mistapi.cli.select_org(apisession)[0]
            break
        elif choice == "2":
            site_id = mistapi.cli.select_site(apisession)[0]
            break
        elif choice == "3":
            sys.exit(0)
        else:
            print("Invalid choice")
    return org_id, site_id


def _retrieve_evpn_topologies(
    apisession: mistapi.APISession, org_id: str, site_id: str
):
    if org_id:
        message = f"Retrieving EVPN Topologies for Org {org_id}"
        PB.log_message(message)
        response = mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies(
            apisession, org_id
        )
        if response.status_code == 200:
            PB.log_success(message)
            return mistapi.get_all(apisession, response)
        else:
            PB.log_failure(message)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    elif site_id:
        message = f"Retrieving EVPN Topologies for Site {site_id}"
        PB.log_message(message)
        response = mistapi.api.v1.sites.evpn_topologies.listSiteEvpnTopologies(
            apisession, site_id
        )
        if response.status_code == 200:
            PB.log_success(message)
            return mistapi.get_all(apisession, response)
        else:
            PB.log_failure(message)
            CONSOLE.error("Please check script logs")
            sys.exit(1)
    else:
        CONSOLE.error("Invalid parameters")
        sys.exit(2)


def _select_evpn_topo(apisession: mistapi.APISession, org_id: str, site_id: str):
    evpn_topo_id = None
    evpntopologies = _retrieve_evpn_topologies(apisession, org_id, site_id)
    if evpntopologies:
        print("EVPN Topologies:")
        for index, evpntopo in enumerate(evpntopologies):
            print(f"{index+1}. {evpntopo.get('name')} ({evpntopo.get('id')})")
        choice = input("Select the EVPN Topology: ")
        evpn_topo_id = evpntopologies[int(choice) - 1].get("id")
    return evpn_topo_id


def start(
    apisession: mistapi.APISession,
    org_id: str = None,
    site_id: str = None,
    evpn_topo_id: str = None,
    ipv4_first: bool = False,
    ipv4_last: bool = False,
    ipv4_from: dict = {},
    ipv4_to: dict = {},
):
    """
    Start the process to create the EVPN VLANs and VRFs

    PARAMS
    -------
    :param  mistapi.APISession  apisession      mistapi session with `Super User` access the source
                                                Org, already logged in
    :param  str                 evpn_topo_id    ID of the Mist EVPN Topology
    :param  str                 vrf_file_path   path to the CSV file with all the VRFs to create
    :param  str                 subnet_base     Base network to use to generate the VLAN subnets.
                                                e.g. if 10.0.0.0/8, generated networks will belong
                                                to this subnet (10.0.1.0/24, 10.0.2.0/24, ...)
                                                Default is 10.0.0.0/8
    :param  int                 subnet_mask     Netmask of the generate VLAN subnets.
                                                e.g. if 24, the generated networks will be using a
                                                /24 mask
                                                Default is 24
    :param  int                 vlan_start      First VLAN to generate. All the other VLAN IDs will
                                                be incremental
                                                Default is 10
    :param  str                 org_id          Optional, org_id of the org where to process the
                                                sites
    :param  str                 org_name        Optional, name of the org where to process the sites
                                                (used for validation)
    :param  str                 site_id         ID of the Site (Required for Site EVPN Topology)
    :param  bool                replace         If True, replace the existing VRF and Networks from
                                                the EVPN topology. If False, the new VRF and
                                                Networks will be added to the existing ones.
                                                Default is False
    """

    if not ipv4_first and not ipv4_last and not ipv4_from:
        usage(
            "At least one of the following parameters must be defined: --ipv4_first, --ipv4_last, --ipv4_from"
        )
        sys.exit(2)

    if not org_id and not site_id:
        org_id, site_id = _select_scope(apisession)
    if not evpn_topo_id:
        evpn_topo_id = _select_evpn_topo(apisession, org_id, site_id)

    _process_evpn_topo(
        apisession,
        org_id,
        site_id,
        evpn_topo_id,
        ipv4_first,
        ipv4_last,
        ipv4_from,
        ipv4_to,
    )


###############################################################################
# USAGE
def usage(error: str = None):
    """
    display script usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to update the IP addresses of the switches in an EVPN Topology.
The script will generate the IP addresses based on the networks defined in the
EVPN Topology and the number of switches to update, and only update the switches
that are part of the Routing layer.
It is possible to select the first or last IP addresses of the networks or to
define a specific starting IP address for each network.

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
-h, --help          display this help

-f, --file=         path to the CSV file
                    Default is ./provision_evpntoplogy_vlans.csv

-o, --org_id=       ID of the Mist Org (only for Org EVPN Topology)
-s, --site_id=      ID of the Mist Site (only for Site EVPN Topology)
-t, --evpn_id=      ID of the EVPN Topology

--ipv4_first        Use the first IP addresses of the networks to generate 
                    the IP addresses (EVPN Gateway excluded).
                    Cannot be used with --ipv4_last or --ipv4_from.
--ipv4_last         Use the last IP addresses of the networks to generate 
                    the IP addresses
                    Cannot be used with --ipv4_first or --ipv4_from.
--ipv4_from=        Define the first IP address of the range of IP addresses for each
                    network. Format is "network_name:ip_address". Multiple networks can be
                    defined separated by a comma.
                    Cannot be used with --ipv4_first or --ipv4_last, but can be used
                    (for different networks) with --ipv4_to
                    e.g. --ipv4_from="corp:10.31.12.100,voice:10.31.23.0"
                    e.g. --ipv4_from="corp:10.31.12.100"  --ipv4_from="voice:10.31.23.0"
--ipv4_to=          Define the last IP address of the range of IP addresses for each
                    network. Format is "network_name:ip_address". Multiple networks can be
                    defined separated by a comma.
                    Cannot be used with --ipv4_first or --ipv4_last, but can be used
                    (for different networks) with --ipv4_from
                    e.g. --ipv4_to="corp:10.31.12.100,voice:10.31.23.0"
                    e.g. --ipv4_to="corp:10.31.12.100"  --ipv4_to="voice:10.31.23.0"
                
-l, --log_file=     define the filepath/filename where to write the logs
                    Default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    Default is "~/.mist_env"

-------
Examples:
python3 ./update_evpn_switch_ip.py --ipv4_last
python3 ./update_evpn_switch_ip.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -t 95e1a820-xxxx-xxxx-xxxx-59fc972d0607 \
    --ipv4_from="corp:10.11.12.100"
    --ipv4_from="voice:10.12.12.150"

"""
    )
    if error:
        CONSOLE.error(error)
    sys.exit(0)


def check_mistapi_version():
    """
    Function to check the mistapi package version
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
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:s:t:e:l:",
            [
                "help",
                "org_id=",
                "site_id=",
                "evpn_id=",
                "ipv4_first",
                "ipv4_last",
                "ipv4_from=",
                "ipv4_to="
                "env=",
                "log_file=",
            ],
        )
    except getopt.GetoptError as err:
        usage(err)

    PARAMS = {}
    ORG_ID = None
    ORG_NAME = None
    SITE_ID = None
    EVPN_TOPO_ID = None
    IPV4_FIRST = False
    IPV4_LAST = False
    IPV4_FROM = {}
    IPV4_TO = {}

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            PARAMS[o] = a
            ORG_ID = a
        elif o in ["-s", "--site_id"]:
            PARAMS[o] = a
            SITE_ID = a
        elif o in ["-t", "--evpn_id"]:
            PARAMS[o] = a
            EVPN_TOPO_ID = a
        elif o in ["--ipv4_first"]:
            if IPV4_LAST or IPV4_FROM:
                usage(
                    "Invalid parameters: --ipv4_first cannot be used with --ipv4_last or --ipv4_from/--ipv4_to"
                )
            PARAMS[o] = True
            IPV4_FIRST = True
        elif o in ["--ipv4_last"]:
            if IPV4_FIRST or IPV4_FROM:
                usage(
                    "Invalid parameters: --ipv4_last cannot be used with --ipv4_first or --ipv4_from/--ipv4_to"
                )
            PARAMS[o] = True
            IPV4_LAST = True
        elif o in ["--ipv4_from"]:
            if IPV4_FIRST or IPV4_LAST:
                usage(
                    "Invalid parameters: --ipv4_from cannot be used with --ipv4_first or --ipv4_last"
                )
            PARAMS[o] = a
            for b in a.split(","):
                IPV4_FROM[b.split(":")[0]] = b.split(":")[1]
        elif o in ["--ipv4_to"]:
            if IPV4_FIRST or IPV4_LAST:
                usage(
                    "Invalid parameters: --ipv4_to cannot be used with --ipv4_first or --ipv4_last"
                )
            PARAMS[o] = a
            for b in a.split(","):
                IPV4_TO[b.split(":")[0]] = b.split(":")[1]
        elif o in ["-e", "--env"]:
            PARAMS[o] = a
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            PARAMS[o] = a
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    #### LOG SCRIPT PARAMETERS ####
    for param, value in PARAMS.items():
        LOGGER.debug(f"opts: {param} is {value}")
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()

    ### START ###
    start(
        apisession,
        ORG_ID,
        SITE_ID,
        EVPN_TOPO_ID,
        IPV4_FIRST,
        IPV4_LAST,
        IPV4_FROM,
        IPV4_TO,
    )
