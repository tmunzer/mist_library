"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to reconfigure switch interfaces based on a CSV file. The script
will create or replace device override at the switch level to reconfigure the 
interfaces.
The script will:
- regroup each interface under the corresponding switch
- locate the site where the switches are assigned from the Org Inventory
- for each switch validate the port profiles configured in the CSV are available 
  for the device (configured at the template level or the site level)
- for each interface of each switch, check if the configured port is already part 
  of an interface range in Mist. In this case, the script will split the current 
  range to remove this port and create a new entry for it in the device configuration
- update the configuration of each switch
- display the configuration before and after the changes

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
CSV Example:
Example:
#switch_mac,port,port_profile,description
2c:21:31:xx:xx:xx,ge-1/0/1,srv,"this is a test"
2c:21:31:xx:xx:xx,ge-2/0/1,sta,"this is a test"
2c:21:31:yy:yy:yy,ge-3/0/1,sta,"this is a test"
2c:21:31:zz:zz:zz,ge-1/0/1,sta,"this is a test"

------
CSV Parameters
Required:
- switch_mac                MAC Address of the Switch
- port                      port to configure (e.g. "ge-0/0/0")
- port_profile              port profile to assign (must be define at the template
                            level or the site level)

Optional:
- description               string to add in the port description field

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-f, --file          path the to csv file to load
                    default is ./update_port_config.csv

-d, --dry_run       Run the script in Dry Run mode. The full process will but the
                    new configuration will not be deployed on the switch
                    Default is False

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./update_port_config.py             
python3 ./update_port_config.py \
    -f ./update_port_config.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""
#### IMPORTS ####
import sys
import csv
import argparse
import logging
import re

MISTAPI_MIN_VERSION = "0.46.1"

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
CSV_FILE = "./update_port_config.csv"
LOG_FILE = "./script.log"

###############################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


###############################################################################
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
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}")
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()

###############################################################################
# FUNCTIONS


###############################################################################
# UPDATE SWITCH CONFIGS
def _retrieve_sites(apisession: mistapi.APISession, org_id: str):
    message = "Retrieving Org Sites from Mist"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(
            apisession, org_id, limit=1000
        )
        sites = mistapi.get_all(apisession, response)
        if sites:
            PB.log_success(message, inc=True)
            return sites
    except Exception:
        LOGGER.error("Exception occurred", exc_info=True)
    PB.log_failure(message, inc=True)
    sys.exit(0)


def _retrieve_switch_templates(apisession: mistapi.APISession, org_id: str) -> list:
    message = "Retrieving Org Switch Templates from Mist"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(
            apisession, org_id, limit=1000
        )
        templates = mistapi.get_all(apisession, response)
        if templates:
            PB.log_success(message, inc=True)
            return templates
    except Exception:
        LOGGER.error("Exception occurred", exc_info=True)
    PB.log_failure(message, inc=True)
    sys.exit(0)


def _retrieve_site_setting(apisession: mistapi.APISession, site_id: str) -> dict:
    message = f"Retrieving Site {site_id} Setting"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.sites.setting.getSiteSetting(
            apisession, site_id)
        if response.status_code == 200:
            PB.log_success(message, inc=True)
            return response.data
    except Exception:
        LOGGER.error("Exception occurred", exc_info=True)
    PB.log_failure(message, inc=True)
    return {}


def _extract_from_template(templates: list, template_id: str, site_id: str) -> list:
    port_usages = []
    if template_id:
        message = f"Extracting profiles from template {template_id}"
        PB.log_message(message)
        try:
            template_setting = next(
                item for item in templates if item["id"] == template_id
            )
            for profile_name in template_setting.get("port_usages", {}):
                if profile_name not in port_usages:
                    port_usages.append(profile_name)
            PB.log_success(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)
    else:
        message = f"No template assigned to site {site_id}"
        PB.log_message(message)
        PB.log_success(message, inc=True)
    return port_usages


def _extract_from_site(apisession: mistapi.APISession, site_id: str) -> list:
    port_usages = []
    site_setting = _retrieve_site_setting(apisession, site_id)
    message = f"Extracting profile from site {site_id}"
    PB.log_message(message)
    for profile_name in site_setting.get("port_usages", {}):
        if profile_name not in port_usages:
            port_usages.append(profile_name)
    return port_usages


def _extract_port_profiles(apisession: mistapi.APISession, org_id: str, site_ids: list) -> dict:
    sites = _retrieve_sites(apisession, org_id)
    site_port_profiles = {}
    templates = _retrieve_switch_templates(apisession, org_id)
    for site_id in site_ids:
        port_usages = []
        message = f"Finding site {site_id}"
        PB.log_message(message)
        try:
            site_info = next(item for item in sites if item["id"] == site_id)
            template_id = site_info.get("networktemplate_id")
            PB.log_success(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)

        port_usages += _extract_from_template(templates, template_id, site_id)
        port_usages += _extract_from_site(apisession, site_id)

        site_port_profiles[site_id] = port_usages
    return site_port_profiles


def _extract_from_device(apisession: mistapi.APISession, site_id: str, device_id: str) -> list:
    port_usages = []
    message = f"Extracting profiles from device {device_id}"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.sites.devices.getSiteDevice(
            apisession, site_id, device_id
        )
        if response.status_code == 200:
            device_setting = response.data
            for profile_name in device_setting.get("port_usages", {}):
                if profile_name not in port_usages:
                    port_usages.append(profile_name)
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except Exception:
        LOGGER.error("Exception occurred", exc_info=True)
        PB.log_failure(message, inc=True)
    return port_usages


def _checking_port_profiles(
    apisession: mistapi.APISession, org_id: str, site_ids: list, csv_switches: dict
) -> dict:
    site_port_profiles = _extract_port_profiles(apisession, org_id, site_ids)
    switches_to_process = {}
    for switch_mac in csv_switches:
        message = f"Checking port profiles for switch {switch_mac}"
        PB.log_message(message)
        csv_switch_data = csv_switches[switch_mac]
        mist_switch_site_id = csv_switch_data["site_id"]
        mist_device_port_profiles = []
        mist_template_port_profiles = site_port_profiles[mist_switch_site_id]
        missing_port_profile = []
        for port_profile in csv_switch_data["port_profiles"]:
            if port_profile in mist_template_port_profiles or port_profile in mist_device_port_profiles:
                LOGGER.debug(
                    "_checking_port_profiles:switch '%s': port profile "
                    "'%s' found in the site or template settings",
                    switch_mac,
                    port_profile
                )
            else:
                LOGGER.warning(
                    "_checking_port_profiles:switch '%s': port profile "
                    "'%s' not found in the site or template settings. "
                    "Checking at the device level...",
                    switch_mac,
                    port_profile
                )
                mist_device_port_profiles = _extract_from_device(
                    apisession, mist_switch_site_id, csv_switch_data["id"])
                if port_profile in mist_device_port_profiles:
                    LOGGER.debug(
                        "_checking_port_profiles:switch '%s': port profile "
                        "'%s' found at the device level",
                        switch_mac,
                        port_profile
                    )
                else:
                    LOGGER.error(
                        "_checking_port_profiles:switch '%s': port profile "
                        "'%s' not found at the device level",
                        switch_mac,
                        port_profile
                    )
                    missing_port_profile.append(port_profile)
        if not missing_port_profile:
            switches_to_process[switch_mac] = csv_switch_data
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)

    return switches_to_process


###############################################################################
# UPDATE SWITCH CONFIGS
def _retrieve_switch_config(
    apisession: mistapi.APISession, site_id: str, switch_mac: str, switch_id: str
) -> dict | None:
    message = f"Retrieving configuration for switch {switch_mac}"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.sites.devices.getSiteDevice(
            apisession, site_id, switch_id
        )
        if response.status_code == 200:
            PB.log_success(message, inc=True)
            return response.data
        else:
            PB.log_failure(message, inc=True)
            return None
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)


def _update_switch_config(
    apisession: mistapi.APISession,
    site_id: str,
    switch_mac: str,
    switch_id: str,
    config: dict,
) -> dict | None:
    message = f"Updating configuration for switch {switch_mac}"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.sites.devices.updateSiteDevice(
            apisession, site_id, switch_id, config
        )
        if response.status_code == 200:
            PB.log_success(message, inc=True)
            return response.data
        else:
            PB.log_failure(message, inc=True)
            return None
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)


def _decompose_interface(interface: str) -> tuple[str, str, str, str, str]:
    '''
    decompose interface range

    PARAMS
    -------
    interface : str
        interface name (e.g. ge-0/1/2) or interface range (e.g. ge-0/1/2-10)

    RETURNS:
    -------
    str
        interface type (e.g. "ge")
    str
        interface fpc id (e.g. "0")
    str
        interface pic number (e.g. "1")
    str 
        interface number or interface range starting index (e.g. "2")
    str
        interface number or interface range ending index (e.g. "10")
    '''
    out_phy = interface.split("-", 1)[0]
    out_fpc = interface.split("-", 1)[1].split("/")[0]
    out_pic = interface.split("-", 1)[1].split("/")[1]
    out_num = interface.split("-", 1)[1].split("/")[2]
    if "-" in out_num:
        out_num_min = out_num.split("-")[0]
        out_num_max = out_num.split("-")[1]
    else:
        out_num_min = out_num
        out_num_max = out_num
    return out_phy, out_fpc, out_pic, out_num_min, out_num_max


def _define_new_port_range(phy: str, fpc: str, pic: str, num_min: int, num_max: int) -> str:
    if str(num_min) == str(num_max):
        return f"{phy}-{fpc}/{pic}/{num_min}"
    else:
        return f"{phy}-{fpc}/{pic}/{num_min}-{num_max}"


def _process_port_range(mist_port_config_dict: dict, csv_port: str, csv_port_config: dict) -> tuple[dict, bool]:
    '''
    Function to check if a switch port (csv_port) we want to configure is part of a port 
    range in the port_config, and, if it's the case, split the port range to exclude the new port

    PARAMS
    -------
    mist_port_config_dict : dict
        port_config dict from the switch configuration

    csv_port : str
        interface to check/configure (e.g. "ge-0/0/0")

    csv_port_config : dict
        configuration to apply to the csv_port

    RETURNS:
    -------
    dict
        new port_config dict to apply to the switch
    bool
        True if the port_config configuration has been updated and must be pushed
        to Mist
    '''
    config_updated = False
    # create a copy of the mist port_config
    copy_port_config_dict = mist_port_config_dict.copy()
    csv_phy, csv_fpc, csv_pic, csv_num, _ = _decompose_interface(csv_port)
    # for each interface/range in the port_config
    for mist_range in mist_port_config_dict:
        LOGGER.debug(
            "_process_port_range:checking range '%s' from Mist", mist_range)
        mist_range_splitted = mist_range.replace(" ", "").split(",")
        mist_port_config = mist_port_config_dict[mist_range]
        # split the comma separated list (if any) and go over each item
        for mist_port in mist_range_splitted:
            # get the decomposed interface/interface range values (fpc, pic, nums)
            mist_phy, mist_fpc, mist_pic, mist_num_min, mist_num_max = _decompose_interface(
                mist_port)
            # check if the new interface (csv_port) is part if the interface range
            if (
                mist_phy == csv_phy
                and mist_fpc == csv_fpc
                and mist_pic == csv_pic
                and mist_num_min <= csv_num
                and mist_num_max >= csv_num
            ):
                LOGGER.info(
                    "_process_port_range:'%s' is part of '%s'", csv_port, mist_port)
                # CASE 1
                # if it is a single interface (mist configuration)
                # remove the current configuration (must be replaced by the new one)
                if mist_num_min == csv_num and mist_num_max == csv_num:
                    new_port = None
                # CASE 2
                # if the new interface is the low end of the interface range (mist configuration)
                # remove the low end interface of the range
                elif mist_num_min == csv_num:
                    new_port = [
                        _define_new_port_range(
                            mist_phy,
                            mist_fpc,
                            mist_pic,
                            int(mist_num_min)+1,
                            int(mist_num_max)
                        )
                    ]
                # CASE 3
                # if the new interface is the high end of the interface range (mist configuration)
                # remove the high end interface of the range
                elif mist_num_max == csv_num:
                    new_port = [
                        _define_new_port_range(
                            mist_phy,
                            mist_fpc,
                            mist_pic,
                            int(mist_num_min),
                            int(mist_num_max)-1
                        )
                    ]
                # CASE 4
                # else, means if the new interface is "inside" the interface range (mist configuration)
                # split the interface range in two parts, removing the new interface
                else:
                    new_port = [
                        _define_new_port_range(
                            mist_phy,
                            mist_fpc,
                            mist_pic,
                            int(mist_num_min),
                            int(csv_num)-1
                        ),
                        _define_new_port_range(
                            mist_phy,
                            mist_fpc,
                            mist_pic,
                            int(csv_num)+1,
                            int(mist_num_max)
                        )
                    ]

                LOGGER.debug("_process_port_range:new port is %s", new_port)
                # remove the interface/interface range which is including the new port from the port_config key
                new_mist_range_splitted = mist_range_splitted
                index = new_mist_range_splitted.index(mist_port)
                new_mist_range_splitted.pop(index)
                # if the interface range still exists (cases 2 to 4), add the newly generated port range(s)
                if new_port:
                    new_mist_range_splitted += new_port
                LOGGER.info(
                    "_process_port_range:new port range is %s", new_mist_range_splitted
                )
                # delete the port range from the copy of the port_config
                del copy_port_config_dict[mist_range]
                # add the new ranges
                if new_mist_range_splitted:
                    new_mist_range = ",".join(new_mist_range_splitted)
                    copy_port_config_dict[new_mist_range] = mist_port_config
                    LOGGER.debug(
                        "_process_port_range:new port config for '%s' is %s",
                        new_mist_range,
                        copy_port_config_dict[new_mist_range]
                    )
                # add the new port (port we want to configure)
                copy_port_config_dict[csv_port] = csv_port_config
                LOGGER.debug(
                    "_process_port_range:new port config for '%s' is %s",
                    csv_port,
                    copy_port_config_dict[csv_port]
                )
                config_updated = True
                break
    return copy_port_config_dict, config_updated


def _update_port_config(mist_port_config_dict: dict, csv_port_config_dict: dict) -> dict:
    for csv_port in csv_port_config_dict:
        config_updated = False
        copy_port_config_dict = mist_port_config_dict.copy()
        csv_port_config = csv_port_config_dict[csv_port]
        LOGGER.info(
            "_update_port_config:------------"
            "processing port '%s' with config %s",
            csv_port,
            csv_port_config
        )

        # if interface_name is alone in the mist_port_config, just replace it
        if mist_port_config_dict.get(csv_port):
            LOGGER.info(
                "_update_port_config:'%s' is alone at the device level. "
                "Replacing its configuration",
                csv_port
            )
            copy_port_config_dict[csv_port] = csv_port_config
            config_updated = True
        else:
            # if interface name is in a list of interface (ge-0/0/0,ge-0/0/1) or a range
            # of interfaces (ge-0/0/0-1) we need to loop over each current port_config
            copy_port_config_dict, config_updated = _process_port_range(
                mist_port_config_dict, csv_port, csv_port_config)
        if not config_updated:
            copy_port_config_dict[csv_port] = csv_port_config

        mist_port_config_dict = copy_port_config_dict.copy()

    return mist_port_config_dict


def _save_config(backup: list, site_id: str, switch_mac: str, switch_config: dict) -> None:
    for interface_range in switch_config:
        backup.append([
            site_id,
            switch_mac,
            interface_range,
            switch_config[interface_range].get("usage"),
            switch_config[interface_range].get("description"),
        ])


def _process_switch_config(apisession: mistapi.APISession, switches_to_process: dict, dry_run: bool) -> None:
    for switch_mac in switches_to_process:
        LOGGER.debug("_update_switch_config:starting switch %s", switch_mac)
        switch_data = switches_to_process[switch_mac]
        csv_port_config_dict = switch_data["port_config"]
        site_id = switch_data.get("site_id")
        switch_id = switch_data.get("id")
        config_before = []
        config_after = []
        if site_id and switch_id:
            switch_config_before = _retrieve_switch_config(
                apisession, site_id, switch_mac, switch_id
            )
            LOGGER.debug(switch_config_before)
            message = f"Preparing new configuration for switch {switch_mac}"
            PB.log_message(message)
            if isinstance(switch_config_before, dict):
                mist_port_config_dict = switch_config_before.get(
                    "port_config", {})
                _save_config(config_before, site_id,
                             switch_mac, mist_port_config_dict)
                LOGGER.debug(
                    "_update_switch_config:current port_config is %s", mist_port_config_dict
                )
                mist_port_config_dict = _update_port_config(
                    mist_port_config_dict, csv_port_config_dict
                )
                LOGGER.debug(
                    "_update_switch_config:new port_config is %s", mist_port_config_dict
                )
                PB.log_success(message, inc=True)
                if dry_run:
                    LOGGER.info(
                        "_update_switch_config:dry run mode. Not changes applied to the switch")
                    switch_config_after = {
                        "port_config": mist_port_config_dict}
                else:
                    switch_config_after = _update_switch_config(
                        apisession,
                        site_id,
                        switch_mac,
                        switch_id,
                        {"port_config": mist_port_config_dict},
                    )

                if switch_config_after:
                    _save_config(config_after, site_id, switch_mac,
                                 switch_config_after.get("port_config", {}))
        else:
            LOGGER.error(
                "_update_switch_config:unable to process device %s on site %s", switch_id, site_id
            )

    PB.log_title("BEFORE CHANGES", end=True)
    data = mistapi.cli.tabulate(config_before, [
                                "site_id", "switch_mac", "interface_range", "port_usage", "description"])
    LOGGER.info("\n%s", data)
    print(data)
    print()
    print()
    if dry_run:
        PB.log_title("AFTER CHANGES - DRY RUN", end=True)
    else:
        PB.log_title("AFTER CHANGES", end=True)
    data = mistapi.cli.tabulate(config_after, [
                                "site_id", "switch_mac", "interface_range", "port_usage", "description"])
    LOGGER.info("\n%s", data)
    print(data)


###############################################################################
# PROCESS CSV
def _retrieve_switch_inventory(apisession: mistapi.APISession, org_id: str) -> list:
    message = "Retrieving Org Switch inventory from Mist"
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.inventory.getOrgInventory(
            apisession, org_id, type="switch", vc=True, limit=1000
        )
        inventory = mistapi.get_all(apisession, response)
        if inventory:
            PB.log_success(message, display_pbar=False)
            return inventory
        else:
            PB.log_failure(message, display_pbar=False)
            sys.exit(0)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)


def _locate_vc_master(inventory: list, vc_mac: str) -> dict:
    message = f"Locating VC Primary switch {vc_mac}"
    PB.log_message(message, display_pbar=False)
    try:
        switch_data = next(
            item for item in inventory if item.get("mac") == vc_mac
        )
        PB.log_success(message, display_pbar=False, inc=False)
        return switch_data
    except Exception:
        PB.log_failure(message, display_pbar=False, inc=False)
        LOGGER.error(
            "_locate_vc_master:vc_mac %s not found", vc_mac
        )
        return {}


def _locate_switches(
    apisession: mistapi.APISession,
    org_id: str,
    switches_to_process: dict
) -> list[str]:
    site_ids = []
    switches = {}
    inventory: list = _retrieve_switch_inventory(apisession, org_id)
    for switch_mac in switches_to_process:
        if switches.get(switch_mac):
            site_ids.append(switches[switch_mac])
        else:
            message = f"Locating switch {switch_mac}"
            PB.log_message(message, display_pbar=False)
            try:
                switch_data: dict = next(
                    item for item in inventory if item.get("mac") == switch_mac
                )
                if switch_data.get("vc_mac"):
                    switch_data = _locate_vc_master(
                        inventory, switch_data["vc_mac"])

                switch_id = switch_data.get("id")
                site_id = switch_data.get("site_id")
                LOGGER.debug(
                    "_locate_switches:switch %s has the id %s and is assigned to %s",
                    switch_mac, switch_id, site_id
                )
                if not site_id:
                    PB.log_failure(message, display_pbar=False)
                    LOGGER.error(
                        "_locate_switches:switch %s is not assigned to any site", switch_mac
                    )
                else:
                    switches_to_process[switch_mac]["id"] = switch_id
                    switches_to_process[switch_mac]["site_id"] = site_id
                    if not site_id in site_ids:
                        LOGGER.debug(
                            "_locate_switches:site_id %s not seen yet. Will add it to the list", site_id
                        )
                        site_ids.append(site_id)
                    PB.log_success(message, display_pbar=False)
            except Exception:
                PB.log_failure(message, display_pbar=False)
                LOGGER.error(
                    "_locate_switches:unable to find switch %s in the org inventory", switch_mac
                )

    return site_ids


def _processing_switch_data(entries: list) -> dict:
    switches_config = {}
    PB.log_title("Processing Port Configurations", display_pbar=False)
    print()
    for entry in entries:
        switch_mac = entry["switch_mac"]
        port = entry["port"].lower()
        port_profile = entry["port_profile"]
        description = entry.get("description", "")
        message = f"Switch {switch_mac} - port {port}"
        PB.log_message(message, display_pbar=False)
        LOGGER.debug("_optimize_port_profiles:processing %s", entry)

        # if current switch has not been added to the out list yet, do it
        if not switches_config.get(switch_mac.lower()):
            LOGGER.debug(
                "_optimize_port_profiles:generating new out value for label_name %s", switch_mac
            )
            switches_config[switch_mac.lower()] = {
                "port_config": {},
                "port_profiles": [],
            }

        # if same switch/port is defined multiple times
        if switches_config[switch_mac.lower()].get(port):
            PB.log_failure(message, display_pbar=False)
            LOGGER.critical(
                "Switch %s and Port %s found multiple times in the CSV file. "
                "Please fix the CSV file and try again. Exiting...", switch_mac, port
            )
            sys.exit(0)

        # if everything is ok, generating the configuration and saving it
        port_data = {"usage": port_profile, "description": description}
        switches_config[switch_mac.lower()]["port_config"][port] = port_data

        # also add the port_profile name into the switch metadata
        if port_profile not in switches_config[switch_mac.lower()]["port_profiles"]:
            switches_config[switch_mac.lower()]["port_profiles"].append(
                port_profile)

        LOGGER.debug(
            "_optimize_port_profiles: adding port %s configuration for the switch %s: %s",
            port, switch_mac, port_data
        )
        PB.log_success(message, display_pbar=False)

    return switches_config


def _read_csv(csv_file: str) -> list:
    message = "Processing CSV File"
    try:
        PB.log_message(message, display_pbar=False)
        LOGGER.debug("_read_csv:opening CSV file %s", csv_file)
        with open(csv_file, "r", encoding="utf-8") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            data = [[c.replace("\ufeff", "") for c in row] for row in data]
            fields = []
            entries = []
            line_number = 0
            for line in data:
                line_number += 1
                LOGGER.debug("_read_csv:new csv line:%s", line)
                if not fields:
                    for column in line:
                        column = re.sub("[^a-zA-Z_]", "", column)
                        fields.append(column.replace("#", "").strip())
                    LOGGER.debug("_read_csv:detected CSV fields: %s", fields)
                    if "switch_mac" not in fields:
                        LOGGER.critical(
                            "_read_csv:switch_mac address not in CSV file... Exiting..."
                        )
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (Switch MAC Address not found). "
                            "Please double check it... Exiting..."
                        )
                        sys.exit(255)
                    if "port" not in fields:
                        LOGGER.critical(
                            "_read_csv:port not in CSV file... Exiting...")
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (Port Name not found). "
                            "Please double check it... Exiting..."
                        )
                        sys.exit(255)
                    if "port_profile" not in fields:
                        LOGGER.critical(
                            "_read_csv:port_profile not in CSV file... Exiting..."
                        )
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (Port Profile Name not found). "
                            "Please double check it... Exiting..."
                        )
                        sys.exit(255)
                else:
                    entry = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        if field == "switch_mac":
                            mac = re.sub("[^0-9a-f]", "", column.lower())
                            if len(mac) == 12:
                                entry[field] = mac
                            else:
                                PB.log_failure(message, display_pbar=False)
                                CONSOLE.error(
                                    f"MAC Address {column} in line {line_number} invalid... Exiting..."
                                )
                                sys.exit(0)
                        else:
                            entry[field] = column.lower().strip()
                        i += 1
                    entries.append(entry)
                    LOGGER.debug(
                        "_read_csv:new entry processed: %s port %s with port_profile %s", entry[
                            'switch_mac'], entry['port'], entry['port_profile']
                    )
        PB.log_success(message, display_pbar=False)
        return entries
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)


###############################################################################
# START
def start(
    apisession: mistapi.APISession,
    org_id: str = "",
    csv_file: str = "",
    dry_run: bool = False
) -> None:
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
    csv_file : str
        Path to the CSV file where the guests information are stored.
        default is "./import_guests.csv"
    dry_run : bool
        Run the script in Dry Run mode. The full process will but the  new configuration will
        not be deployed on the switch
        default is False
    """
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    if not csv_file:
        csv_file = CSV_FILE

    PB.log_title("Preparing data", display_pbar=False)
    print()
    entries = _read_csv(csv_file)
    if org_id and csv_file and entries:
        switches = _processing_switch_data(entries)
        site_ids = _locate_switches(apisession, org_id, switches)

        PB.set_steps_total(len(site_ids) * 3 + len(switches) + 2)
        PB.log_title("Validating switches configuration")
        switches_to_process = _checking_port_profiles(
            apisession, org_id, site_ids, switches
        )

        PB.log_title("Updating switches configuration")
        if len(switches_to_process) > 0:
            PB.set_steps_total(len(switches_to_process) * 3)
            _process_switch_config(apisession, switches_to_process, dry_run)
        else:
            PB.log_message("No switch to process")


###############################################################################
# USAGE
def usage(error_message: str | None = None) -> None:
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
Python script to reconfigure switch interfaces based on a CSV file. The script
will create or replace device override at the switch level to reconfigure the 
interfaces.
The script will:
- regroup each interface under the corresponding switch
- locate the site where the switches are assigned from the Org Inventory
- for each switch validate the port profiles configured in the CSV are available 
  for the device (configured at the template level or the site level)
- for each interface of each switch, check if the configured port is already part 
  of an interface range in Mist. In this case, the script will split the current 
  range to remove this port and create a new entry for it in the device configuration
- update the configuration of each switch
- display the configuration before and after the changes

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
CSV Example:
Example:
#switch_mac,port,port_profile,description
2c:21:31:xx:xx:xx,ge-1/0/1,srv,"this is a test"
2c:21:31:xx:xx:xx,ge-2/0/1,sta,"this is a test"
2c:21:31:yy:yy:yy,ge-3/0/1,sta,"this is a test"
2c:21:31:zz:zz:zz,ge-1/0/1,sta,"this is a test"

------
CSV Parameters
Required:
- switch_mac                MAC Address of the Switch
- port                      port to configure (e.g. "ge-0/0/0")
- port_profile              port profile to assign (must be define at the template
                            level or the site level)

Optional:
- description               string to add in the port description field

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-f, --file          path the to csv file to load
                    default is ./update_port_config.csv

-d, --dry_run       Run the script in Dry Run mode. The full process will but the
                    new configuration will not be deployed on the switch
                    Default is False

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./update_port_config.py             
python3 ./update_port_config.py \
    -f ./update_port_config.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 
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
            mistapi.__version__
        )


#####################################################################
#####  ENTRY POINT ####

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to update switch port configuration based on a CSV file")
    # parser.add_argument("-h", "--help", action="store_true",
    #                     help="display this help")
    parser.add_argument("-f", "--file", type=str,
                        help="path to the csv file to load. default is ./update_port_config.csv")
    parser.add_argument("-o", "--org_id", type=str, help="Set the org_id where the webhook must be create/delete/retrieved. This parameter cannot be used if -s/--site_id is used. If no org_id and not site_id are defined, the script will show a menu to select the org/the site.")
    parser.add_argument("-d", "--dry_run", action="store_true",
                        help="Run the script in Dry Run mode. The full process will but the new configuration will not be deployed on the switch. Default is False")
    parser.add_argument("-l", "--log_file", type=str,
                        help="define the filepath/filename where to write the logs. default is ./script.log")
    parser.add_argument("-e", "--env", type=str,
                        help="define the env file to use (see mistapi env file documentation here: https://pypi.org/project/mistapi/). default is ~/.mist_env")

    args = parser.parse_args()


    if args.help:
        usage()

    ORG_ID = args.org_id
    CSV_FILE = args.file if args.file else "./update_port_config.csv"
    ENV_FILE = args.env if args.env else "~/.mist_env"
    LOG_FILE = args.log_file if args.log_file else "./script.log"
    DRY_RUN = args.dry_run

    PARAMS = {
        "-f": CSV_FILE,
        "-o": ORG_ID,
        "-l": LOG_FILE,
        "-e": ENV_FILE,
        "-d": DRY_RUN
    }

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    #### LOG SCRIPT PARAMETERS ####
    for param, value in PARAMS.items():
        LOGGER.debug("opts: %s is %s", param, value)
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, CSV_FILE, DRY_RUN)
