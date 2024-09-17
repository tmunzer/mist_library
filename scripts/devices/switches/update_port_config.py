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

It is recomended to use an environment file to store the required information
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
import getopt
import logging
import re

MISTAPI_MIN_VERSION = "0.46.1"

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
        else:
            PB.log_failure(message, inc=True)
            sys.exit(0)
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)

def _retrieve_switch_templates(apisession: mistapi.APISession, org_id: str):
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
        else:
            PB.log_failure(message, inc=True)
            sys.exit(0)
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)


def _retrieve_site_setting(apisession: mistapi.APISession, site_id: str):
    message = f"Retrieving Site {site_id} Setting"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.sites.setting.getSiteSetting(apisession, site_id)
        if response.status_code == 200:
            PB.log_success(message, inc=True)
            return response.data
        else:
            PB.log_failure(message, inc=True)
            return None
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

def _extract_from_template(templates: list, template_id: str, site_id: str):
    port_usages = []
    if template_id:
        message = f"Extracting profiles from template {template_id}"
        PB.log_message(message)
        try:
            template_setting = next(
                item for item in templates if item["id"] == template_id
            )
            for profile_name in template_setting.get("port_usages", {}):
                if not profile_name in port_usages:
                    port_usages.append(profile_name)
            PB.log_success(message, inc=True)
        except:
            PB.log_failure(message, inc=True)
    else:
        message = f"No template assigned to site {site_id}"
        PB.log_message(message)
        PB.log_success(message, inc=True)
    return port_usages


def _extract_from_site(apisession: mistapi.APISession, site_id: str):
    port_usages = []
    site_setting = _retrieve_site_setting(apisession, site_id)
    message = f"Extracting profile from site {site_id}"
    PB.log_message(message)
    for profile_name in site_setting.get("port_usages", {}):
        if not profile_name in port_usages:
            port_usages.append(profile_name)
    return port_usages


def _extract_port_profiles(apisession: mistapi.APISession, org_id: str, site_ids: list):
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
        except:
            PB.log_failure(message, inc=True)

        port_usages += _extract_from_template(templates, template_id, site_id)
        port_usages += _extract_from_site(apisession, site_id)

        site_port_profiles[site_id] = port_usages
    return site_port_profiles


def _checking_port_profiles(
    apisession: mistapi.APISession, org_id: str, site_ids: list, switches: dict
):
    site_port_profiles = _extract_port_profiles(apisession, org_id, site_ids)
    switches_to_process = {}
    for switch_mac in switches:
        message = f"Checking port profiles for switch {switch_mac}"
        PB.log_message(message)
        switch_data = switches[switch_mac]
        switch_site_id = switch_data["site_id"]
        switch_port_profiles = switch_data["port_profiles"]
        available_port_profiles = site_port_profiles[switch_site_id]
        missing_port_profile = []
        for port_profile in switch_port_profiles:
            if port_profile in available_port_profiles:
                LOGGER.debug(
                    f"_checking_port_profiles:switch '{switch_mac}': port profile "
                    f"'{port_profile}' found in the site or template settings"
                )
            else:
                LOGGER.error(
                    f"_checking_port_profiles:switch '{switch_mac}': port profile "
                    f"'{port_profile}' not found in the site or template settings"
                )
                missing_port_profile.append(port_profile)
        if not missing_port_profile:
            switches_to_process[switch_mac] = switch_data
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)

    return switches_to_process


###############################################################################
# UPDATE SWITCH CONFIGS
def _retrieve_switch_config(
    apisession: mistapi.APISession, site_id: str, switch_mac: str, switch_id: str
):
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
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)


def _update_switch_config(
    apisession: mistapi.APISession,
    site_id: str,
    switch_mac: str,
    switch_id: str,
    config: dict,
):
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
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)


def _decompose_interface(interface: str):
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

def _define_new_port_range(phy:str, fpc:str, pic:str, num_min:int, num_max:int):
    if str(num_min)==str(num_max):
        return f"{phy}-{fpc}/{pic}/{num_min}"
    else:
        return f"{phy}-{fpc}/{pic}/{num_min}-{num_max}"

def _process_port_range(mist_port_config_dict:dict, csv_port:str, csv_port_config:dict):
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
    csv_phy, csv_fpc, csv_pic, csv_num, not_used = _decompose_interface(csv_port)
    # for each interface/range in the port_config
    for mist_range in mist_port_config_dict:
        LOGGER.debug(f"_process_port_range:checking range '{mist_range}' from Mist")
        mist_range_splitted = mist_range.replace(" ", "").split(",")
        mist_port_config = mist_port_config_dict[mist_range]
        # split the comma separated list (if any) and go over each item
        for mist_port in mist_range_splitted:
            # get the decomposed inteface/interface range values (fpc, pic, nums)
            mist_phy,mist_fpc,mist_pic,mist_num_min,mist_num_max = _decompose_interface(mist_port)
            # check if the new interace (csv_port) is part if the interface range
            if (
                mist_phy == csv_phy
                and mist_fpc == csv_fpc
                and mist_pic == csv_pic
                and mist_num_min <= csv_num
                and mist_num_max >= csv_num
            ):
                LOGGER.info(f"_process_port_range:'{csv_port}' is part of '{mist_port}'")
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
                            mist_num_max
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
                            mist_num_min,
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
                            mist_num_min,
                            int(csv_num)-1
                        ),
                        _define_new_port_range(
                            mist_phy,
                            mist_fpc,
                            mist_pic,
                            int(csv_num)+1,
                            mist_num_max
                        )
                    ]

                LOGGER.debug(f"_process_port_range:new port is {new_port}")
                # remove the interface/interface range which is including the new port from the port_config key
                new_mist_range_splitted = mist_range_splitted
                index = new_mist_range_splitted.index(mist_port)
                new_mist_range_splitted.pop(index)
                # if the interface range still exists (cases 2 to 4), add the newly generated port range(s) 
                if new_port:
                    new_mist_range_splitted += new_port
                LOGGER.info(
                    f"_process_port_range:new port range is {new_mist_range_splitted}"
                )
                # delete the port range from the copy of the port_config
                del copy_port_config_dict[mist_range]
                # add the new ranges
                if new_mist_range_splitted:
                    new_mist_range = ",".join(new_mist_range_splitted)
                    copy_port_config_dict[new_mist_range] = mist_port_config
                    LOGGER.debug(
                        f"_process_port_range:new port config for '{new_mist_range}' "
                        f"is {copy_port_config_dict[new_mist_range]}"
                    )
                # add the new port (port we want to configure)
                copy_port_config_dict[csv_port] = csv_port_config
                LOGGER.debug(
                        f"_process_port_range:new port config for '{csv_port}' "
                        f"is {copy_port_config_dict[csv_port]}"
                    )
                config_updated = True
                break
    return copy_port_config_dict, config_updated

def _update_port_config(mist_port_config_dict: dict, csv_port_config_dict: dict):
    if mist_port_config_dict:
        for csv_port in csv_port_config_dict:
            config_updated = False
            copy_port_config_dict = mist_port_config_dict.copy()
            csv_port_config = csv_port_config_dict[csv_port]
            LOGGER.info(
                f"_update_port_config:------------"
                f"processing port '{csv_port}' with config {csv_port_config}"
                )

            # if interface_name is alone in the mist_port_config, just replace it
            if mist_port_config_dict.get(csv_port):
                LOGGER.info(
                    f"_update_port_config:'{csv_port}' is alone at the device level. "
                    f"Replacing its configuration"
                )
                copy_port_config_dict[csv_port] = csv_port_config
                config_updated = True
            else:
                # if interface name is in a list of interface (ge-0/0/0,ge-0/0/1) or a range
                # of interfaces (ge-0/0/0-1) we need to loop over each current port_config
                copy_port_config_dict, config_updated = _process_port_range(mist_port_config_dict, csv_port, csv_port_config)
            if not config_updated:
                copy_port_config_dict[csv_port] = csv_port_config

            mist_port_config_dict = copy_port_config_dict.copy()

    return mist_port_config_dict

def _save_config(backup:list, site_id:str, switch_mac:str, switch_config:dict):
    for interface_range in switch_config:
        backup.append([
            site_id,
            switch_mac,
            interface_range,
            switch_config[interface_range].get("usage"),
            switch_config[interface_range].get("description"),
        ])


def _process_switch_config(apisession: mistapi.APISession, switches_to_process: dict, dry_run:bool):
    for switch_mac in switches_to_process:
        LOGGER.debug(f"_update_switch_config:starting switch {switch_mac}")
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
            mist_port_config_dict = switch_config_before.get("port_config")
            _save_config(config_before, site_id, switch_mac, mist_port_config_dict)
            LOGGER.debug(
                f"_update_switch_config:current port_config is {mist_port_config_dict}"
            )
            mist_port_config_dict = _update_port_config(
                mist_port_config_dict, csv_port_config_dict
            )
            LOGGER.debug(
                f"_update_switch_config:new port_config is {mist_port_config_dict}"
            )
            PB.log_success(message, inc=True)
            if dry_run:
                LOGGER.info("_update_switch_config:dry run mode. Not changes applied to the switch")
                switch_config_after = {"port_config": mist_port_config_dict}
            else:
                switch_config_after = _update_switch_config(
                    apisession,
                    site_id,
                    switch_mac,
                    switch_id,
                    {"port_config": mist_port_config_dict},
                )
                
            _save_config(config_after, site_id, switch_mac, switch_config_after.get("port_config"))
        else:
            LOGGER.error(
                f"_update_switch_config:unable to process device {switch_id} on site {site_id}"
            )

    PB.log_title("BEFORE CHANGES", end=True)
    data = mistapi.cli.tabulate(config_before, ["site_id", "switch_mac", "interface_range", "port_usage", "description"])
    LOGGER.info(f"\n{data}")
    print(data)
    print()
    print()
    if dry_run:
        PB.log_title("AFTER CHANGES - DRY RUN", end=True)
    else:
        PB.log_title("AFTER CHANGES", end=True)
    data = mistapi.cli.tabulate(config_after, ["site_id", "switch_mac", "interface_range", "port_usage", "description"])
    LOGGER.info(f"\n{data}")
    print(data)



###############################################################################
# PROCESS CSV
def _retrieve_switch_inventory(apisession: mistapi.APISession, org_id: str):
    message = "Retrieving Org Switch inventory from Mist"
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.inventory.getOrgInventory(
            apisession, org_id, limit=1000
        )
        inventory = mistapi.get_all(apisession, response)
        if inventory:
            PB.log_success(message, display_pbar=False)
            return inventory
        else:
            PB.log_failure(message, display_pbar=False)
            sys.exit(0)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)


def _locate_switches(
    apisession: mistapi.APISession, org_id: str, switches_to_process: dict
):
    site_ids = []
    inventory = _retrieve_switch_inventory(apisession, org_id)
    for switch_mac in switches_to_process:
        message = f"Locating switch {switch_mac}"
        PB.log_message(message, display_pbar=False)
        try:
            switch_data = next(
                item for item in inventory if item.get("mac") == switch_mac
            )
            site_id = switch_data.get("site_id")
            id = switch_data.get("id")
            LOGGER.debug(
                f"_locate_switches:switch {site_id} has the id {id} and is assigned to {site_id}"
            )
            if not site_id:
                PB.log_failure(message, display_pbar=False)
                LOGGER.error(
                    f"_locate_switches:switch {switch_mac} is not assigned to any site"
                )
            else:
                switches_to_process[switch_mac]["id"] = id
                switches_to_process[switch_mac]["site_id"] = site_id
                if not site_id in site_ids:
                    LOGGER.debug(
                        f"_locate_switches:site_id {site_id} not seen yet. Will add it to the list"
                    )
                    site_ids.append(site_id)
                PB.log_success(message, display_pbar=False)
        except:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error(
                f"_locate_switches:unable to find switch {switch_mac} in the org inventory"
            )

    return site_ids


def _processing_switch_data(entries: list):
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
        LOGGER.debug(f"_optimize_port_profiles:processing {entry}")

        # if current switch has not been added to the out list yet, do it
        if not switches_config.get(switch_mac.lower()):
            LOGGER.debug(
                f"_optimize_port_profiles:generating new out value for label_name {switch_mac}"
            )
            switches_config[switch_mac.lower()] = {
                "port_config": {},
                "port_profiles": [],
            }

        # if same switch/port is defined multiple times
        if switches_config[switch_mac.lower()].get(port):
            PB.log_failure(message, display_pbar=False)
            LOGGER.critical(
                f"Switch {switch_mac} and Port {port} found multiple times in the CSV file. "
                "Please fix the CSV file and try again. Exiting..."
            )
            sys.exit(0)

        # if everything is ok, generating the configuration and saving it
        port_data = {"usage": port_profile, "description": description}
        switches_config[switch_mac.lower()]["port_config"][port] = port_data

        # also add the port_profile name into the switch metadata
        if not port_profile in switches_config[switch_mac.lower()]["port_profiles"]:
            switches_config[switch_mac.lower()]["port_profiles"].append(port_profile)

        LOGGER.debug(
            f"_optimize_port_profiles: adding port {port} configuration "
            f"for the swith {switch_mac}: {port_data}"
        )
        PB.log_success(message, display_pbar=False)

    return switches_config


def _read_csv(csv_file: str):
    message = "Processing CSV File"
    try:
        PB.log_message(message, display_pbar=False)
        LOGGER.debug(f"_read_csv:opening CSV file {csv_file}")
        with open(csv_file, "r") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            data = [[c.replace("\ufeff", "") for c in row] for row in data]
            fields = []
            entries = []
            line_number = 0
            for line in data:
                line_number += 1
                LOGGER.debug(f"_read_csv:new csv line:{line}")
                if not fields:
                    for column in line:
                        column = re.sub("[^a-zA-Z_]", "", column)
                        fields.append(column.replace("#", "").strip())
                    LOGGER.debug(f"_read_csv:detected CSV fields: {fields}")
                    if "switch_mac" not in fields:
                        LOGGER.critical(
                            f"_read_csv:switch_mac address not in CSV file... Exiting..."
                        )
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (Switch MAC Address not found). "
                            "Please double check it... Exiting..."
                        )
                        sys.exit(255)
                    if "port" not in fields:
                        LOGGER.critical(f"_read_csv:port not in CSV file... Exiting...")
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (Port Name not found). "
                            "Please double check it... Exiting..."
                        )
                        sys.exit(255)
                    if "port_profile" not in fields:
                        LOGGER.critical(
                            f"_read_csv:port_profile not in CSV file... Exiting..."
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
                        f"_read_csv:new entry processed: {entry['switch_mac']} port {entry['port']} with port_profile {entry['port_profile']}"
                    )
        PB.log_success(message, display_pbar=False)
        return entries
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


###############################################################################
# START
def start(apisession: mistapi.APISession, org_id: str = None, csv_file: str = None, dry_run:bool=False):
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

It is recomended to use an environment file to store the required information
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
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, '
            f"you are currently using version {mistapi.__version__}."
        )


#####################################################################
##### ENTRY POINT ####

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "ho:f:e:ld", ["help", "org_id=", "file=", "env=", "log_file=", "dry_run"]
        )
    except getopt.GetoptError as err:
        CONSOLE.error(err)
        usage()

    ORG_ID = None
    DRY_RUN = False
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-f", "--file"]:
            CSV_FILE = a
        elif o in ["-d", "--dry_run"]:
            DRY_RUN = True
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"
    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    start(apisession, ORG_ID, CSV_FILE, DRY_RUN)
