"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!              This script if for testing purpose.                           !!
!!              DO NOT USE IT WITH A PRODUCTION ORGANIZATION                  !!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Python script generate VLANs and VRFs for EVPN Topologies

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the 
additional required settings.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.


-------
CSV Example:
#vrf_name,vrf_subnets
VRF-X1,3
VRF-X2,5
VRF-X3,2

-------
CSV Parameters:
Required:
- vrf_name                  Name of the VRF
- vrf_subnets               Number of VLANs/Subnet to generate for the VRF

-------
Script Parameters:
-h, --help          display this help

-f, --file=         path to the CSV file
                    Default is ./provision_evpntoplogy_vlans.csv

-o, --org_id=       ID of the Mist Org
-n, --org_name=     Name of the Mist Org. Used to validate the destination org
-s, --site_id=      ID of the Mist Site (only for Site EVPN Topology)
-t, --evpn_id=      ID of the EVPN Topology

-b, --subnet_base=  Base network to use to generate the VLAN subnets.
                    e.g. if 10.0.0.0/8, generated networks will belong to 
                    this subnet (10.0.1.0/24, 10.0.2.0/24, ...)
                    Default is 10.0.0.0/8
-m, --subnet_mask=  Netmask of the generate VLAN subnets.
                    e.g. if 24, the generated networks will be using a /24 mask
                    Default is 24
-v, --vlan_start=   First VLAN to generate. All the other VLAN IDs will be incremental
                    Default is 10
-r, --replace       If set, replace the existing VRF and Networks from the EVPN
                    topology. If not set, the new VRF and Networks will be added
                    to the existing ones.
                
-l, --log_file=     define the filepath/filename where to write the logs
                    Default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    Default is "~/.mist_env"

-------
Examples:
python3 ./provision_evpntoplogy_vlans.py -f ./my_new_sites.csv                 
python3 ./provision_evpntoplogy_vlans.py \
    -f ./my_new_sites.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -n "My Org" \
    -t 95e1a820-xxxx-xxxx-xxxx-59fc972d0607 \
    -b 10.0.0.0/8 \
    -m 24 \
    -r

"""

#### IMPORTS #####
import sys
import csv
import getopt
import logging
import ipaddress

MISTAPI_MIN_VERSION = "0.48.0"

try:
    import mistapi
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

#####################################################################
#### PARAMETERS #####
ORG_ID = None
ORG_NAME = None
SITE_ID = None
EVPN_TOPO_ID = None
SUBNET_BASE = "10.0.0.0"
SUBNET_MASK = 24
VLAN_START = 10
REPLACE = False
VRF_FILE = "./provision_evpntoplogy_vlans.csv"
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####


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
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
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
            console.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        console.error("Please check script logs")
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
            console.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        console.error("Please check script logs")
        sys.exit(1)


def _generate_switch(device: dict, networks: dict):
    warning = False
    message = f"Generate Device config for {device.get('mac')}"
    PB.log_message(message, display_pbar=False)
    device["other_ip_configs"] = {}
    for network_name, network_conf in networks.items():
        try:
            subnet = ipaddress.ip_network(network_conf.get("subnet"))
            ip_address = str(list(subnet.hosts())[0])
            netmask = str(subnet.netmask)
            device["other_ip_configs"][network_name] = {
                "type": "static",
                "ip": ip_address,
                "netmask": netmask,
                "evpn_anycast": True,
            }
        except:
            warning = True
            LOGGER.error("Exception occurred", exc_info=True)
    if warning:
        PB.log_warning(message, display_pbar=False)
    else:
        PB.log_success(message, display_pbar=False)
    return device


def _process_switch(apisession: mistapi.APISession, switch: dict, networks: dict):
    site_id = switch.get("site_id")
    switch_mac = switch.get("mac")
    device = _retrieve_switch(apisession, site_id, switch_mac)
    device = _generate_switch(device, networks)
    _update_switch(apisession, device)


###############################################################################
# DEVICEPROFILE


def _retrieve_deviceprofile(
    apisession: mistapi.APISession, org_id: str, deviceprofile_id: str
):
    try:
        message = f"Retrieving Device Profile {deviceprofile_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.deviceprofiles.getOrgDeviceProfile(
            apisession, org_id, deviceprofile_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            console.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        console.error("Please check script logs")
        sys.exit(1)


def _update_deviceprofile(apisession: mistapi.APISession, deviceprofile: dict):
    org_id = deviceprofile.get("org_id")
    deviceprofile_id = deviceprofile.get("id")
    try:
        message = f"Update Device Profile {deviceprofile_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile(
            apisession, org_id, deviceprofile_id, deviceprofile
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            console.error("Please check script logs")
            sys.exit(1)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        console.error("Please check script logs")
        sys.exit(1)


def _generate_deviceprofile(
    deviceprofile: dict,
    vrf_list: list,
    subnet_base: str,
    subnet_mask: int,
    vlan_start: int,
):
    try:
        subnets = list(
            ipaddress.ip_network(subnet_base).subnets(new_prefix=subnet_mask)
        )
    except:
        console.critical(
            "Error when processing the subnets. "
            "Please check the subnet_base and subnet_mask values"
        )
        console.critical(
            f"Current values are subnet_base = {subnet_base} "
            f"and subnet_mask = {subnet_mask}"
        )
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)

    j = vlan_start
    LOGGER.debug(f"VRF from CSV: {vrf_list}")
    for vrf in vrf_list:
        try:
            vrf_name = vrf.get("vrf_name")
            vrf_subnets = int(vrf.get("vrf_subnets"))
            for vlan_id in range(j, vrf_subnets + j):
                j += 1
                vlan_name = f"{vrf_name}-vlan-{vlan_id}"
                deviceprofile["networks"][vlan_name] = {
                    "vlan_id": vlan_id,
                    "subnet": str(subnets[j - 1]),
                }
                if not deviceprofile["vrf_instances"].get(vrf_name):
                    deviceprofile["vrf_instances"][vrf_name] = {
                        "networks": [],
                        "extra_routes": {},
                    }
                deviceprofile["vrf_instances"][vrf_name]["networks"].append(vlan_name)
        except:
            console.error(f"Unable to process {vrf}")
            LOGGER.error("Exception occurred", exc_info=True)
            return False
    return deviceprofile


def _process_deviceprofile(
    apisession: mistapi.APISession,
    org_id: str,
    deviceprofile_id: str,
    vrf_list: list,
    subnet_base: str,
    subnet_mask: int,
    vlan_start: int,
    replace: bool = False,
):
    deviceprofile = _retrieve_deviceprofile(apisession, org_id, deviceprofile_id)
    if replace:
        deviceprofile["vrf_instances"] = {}
        deviceprofile["networks"] = {}
    deviceprofile = _generate_deviceprofile(
        deviceprofile, vrf_list, subnet_base, subnet_mask, vlan_start
    )
    _update_deviceprofile(apisession, deviceprofile)
    return deviceprofile


###############################################################################
# EVPN TOPOLOGY
def _retrieve_evpn_topo(
    apisession: mistapi.APISession, org_id: str, site_id: str, evpn_topo_id: str
):
    if site_id:
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
                console.error("Please check script logs")
                sys.exit(1)
        except:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Exception occurred", exc_info=True)
            console.error("Please check script logs")
            sys.exit(1)
    elif org_id:
        try:
            message = f"Retrieving Org EVPN Topology {evpn_topo_id}"
            PB.log_message(message, display_pbar=False)
            resp = mistapi.api.v1.orgs.evpn_topologies.getOrgEvpnTolopogy(
                apisession, org_id, evpn_topo_id
            )
            if resp.status_code == 200:
                PB.log_success(message, display_pbar=False)
                return resp.data
            else:
                PB.log_failure(message, display_pbar=False)
                console.error("Please check script logs")
                sys.exit(1)
        except:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Exception occurred", exc_info=True)
            console.error("Please check script logs")
            sys.exit(1)


def _process_evpn_topo(
    apisession: mistapi.APISession,
    org_id: str,
    site_id: str,
    evpn_topo_id: str,
    vrf_list: list,
    subnet_base: str,
    subnet_mask: int,
    vlan_start: int,
    replace: bool = False,
):
    evpn_topo = _retrieve_evpn_topo(apisession, org_id, site_id, evpn_topo_id)
    LOGGER.debug(evpn_topo)
    processed_deviceprofiles = {}
    for switch in evpn_topo.get("switches"):
        deviceprofile_id = switch.get("deviceprofile_id")
        if deviceprofile_id and not processed_deviceprofiles.get(deviceprofile_id):
            deviceprofile = _process_deviceprofile(
                apisession,
                org_id,
                deviceprofile_id,
                vrf_list,
                subnet_base,
                subnet_mask,
                vlan_start,
                replace,
            )
            processed_deviceprofiles[deviceprofile_id] = deviceprofile
        routed_at = evpn_topo.get("evpn_options", {}).get("routed_at")
        switch_role = switch.get("role")
        switch_mac = switch.get("mac")
        LOGGER.debug(
            f"switch {switch_mac} is {switch_role}. EVPN routed at {routed_at}"
        )
        if routed_at == "edge" and switch_role == "access":
            _process_switch(
                apisession,
                switch,
                processed_deviceprofiles[deviceprofile_id].get("networks"),
            )


###############################################################################
# PARSE CSV


###############################################################################
# Optional site parameters (if id and name is defined, the name will
# be used):
# - vrf_name
# - vrf_subnets
#
def _read_csv_file(file_path: str):
    with open(file_path, "r") as f:
        data = csv.reader(f, skipinitialspace=True, quotechar='"')
        data = [[c.replace("\ufeff", "") for c in row] for row in data]
        fields = []
        vrf_list = []
        for line in data:
            if not fields:
                for column in line:
                    fields.append(column.strip().replace("#", ""))
            else:
                vrf = {}
                i = 0
                for column in line:
                    field = fields[i]
                    vrf[field] = column.strip()
                    i += 1
                vrf_list.append(vrf)
        return vrf_list


def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = None
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    if not org_name:
        response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
        if response.status_code != 200:
            console.critical(f"Unable to retrieve the org information: {response.data}")
            sys.exit(3)
        org_name = response.data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: "
        )
        if resp == org_name:
            return org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def start(
    apisession: mistapi.APISession,
    evpn_topo_id: str,
    vrf_file_path: str = VRF_FILE,
    subnet_base: str = SUBNET_BASE,
    subnet_mask: int = SUBNET_MASK,
    vlan_start: int = VLAN_START,
    org_id: str = None,
    org_name: str = None,
    site_id: str = None,
    replace: bool = False,
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
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
        org_id, org_name = _check_org_name(apisession, org_id)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)

    vrf_list = _read_csv_file(vrf_file_path)
    _process_evpn_topo(
        apisession,
        org_id,
        site_id,
        evpn_topo_id,
        vrf_list,
        subnet_base,
        subnet_mask,
        vlan_start,
        replace,
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!              This script if for testing purpose.                           !!
!!              DO NOT USE IT WITH A PRODUCTION ORGANIZATION                  !!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Python script generate VLANs and VRFs for EVPN Topologies

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the 
additional required settings.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.


-------
CSV Example:
#vrf_name,vrf_subnets
VRF-X1,3
VRF-X2,5
VRF-X3,2

-------
CSV Parameters:
Required:
- vrf_name                  Name of the VRF
- vrf_subnets               Number of VLANs/Subnet to generate for the VRF

-------
Script Parameters:
-h, --help          display this help

-f, --file=         path to the CSV file
                    Default is ./provision_evpntoplogy_vlans.csv

-o, --org_id=       ID of the Mist Org
-n, --org_name=     Name of the Mist Org. Used to validate the destination org
-s, --site_id=      ID of the Mist Site (only for Site EVPN Topology)
-t, --evpn_id=      ID of the EVPN Topology

-b, --subnet_base=  Base network to use to generate the VLAN subnets.
                    e.g. if 10.0.0.0/8, generated networks will belong to 
                    this subnet (10.0.1.0/24, 10.0.2.0/24, ...)
                    Default is 10.0.0.0/8
-m, --subnet_mask=  Netmask of the generate VLAN subnets.
                    e.g. if 24, the generated networks will be using a /24 mask
                    Default is 24
-v, --vlan_start=   First VLAN to generate. All the other VLAN IDs will be incremental
                    Default is 10
-r, --replace       If set, replace the existing VRF and Networks from the EVPN
                    topology. If not set, the new VRF and Networks will be added
                    to the existing ones.
                
-l, --log_file=     define the filepath/filename where to write the logs
                    Default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    Default is "~/.mist_env"

-------
Examples:
python3 ./provision_evpntoplogy_vlans.py -f ./my_new_sites.csv                 
python3 ./provision_evpntoplogy_vlans.py \
    -f ./my_new_sites.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -n "My Org" \
    -t 95e1a820-xxxx-xxxx-xxxx-59fc972d0607 \
    -b 10.0.0.0/8 \
    -m 24 \
    -r

"""
    )
    if error:
        console.error(error)
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
            "ho:n:s:t:b:m:v:rf:e:l:",
            [
                "help",
                "org_id=",
                "org_name=",
                "site_id=",
                "evpn_id=",
                "subnet_base=",
                "subnet_mask=",
                "vlan_start=",
                "replace" "file=",
                "env=",
                "log_file=",
            ],
        )
    except getopt.GetoptError as err:
        usage(err)

    PARAMS = {}

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            PARAMS[o] = a
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            PARAMS[o] = a
            ORG_NAME = a
        elif o in ["-s", "--site_id"]:
            PARAMS[o] = a
            SITE_ID = a
        elif o in ["-t", "--evpn_id"]:
            PARAMS[o] = a
            EVPN_TOPO_ID = a
        elif o in ["-b", "--subnet_base"]:
            PARAMS[o] = a
            SUBNET_BASE = a
        elif o in ["-m", "--subnet_mask"]:
            PARAMS[o] = a
            try:
                tmp = int(a)
                if tmp >= 0 and tmp <= 24:
                    SUBNET_MASK = tmp
                else:
                    usage(f"Invalid subnet mask: {a}")
            except:
                usage(f"Invalid subnet mask: {a}")
        elif o in ["-v", "--vlan_start"]:
            PARAMS[o] = a
            VLAN_START = a
        elif o in ["-r", "--replace"]:
            PARAMS[o] = True
            REPLACE = True
        elif o in ["-f", "--file"]:
            PARAMS[o] = a
            VRF_FILE = a
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
        EVPN_TOPO_ID,
        VRF_FILE,
        SUBNET_BASE,
        SUBNET_MASK,
        VLAN_START,
        ORG_ID,
        ORG_NAME,
        SITE_ID,
        REPLACE,
    )
