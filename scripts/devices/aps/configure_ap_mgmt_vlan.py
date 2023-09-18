'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script reconfigure Management VLAN on all the Mist APs from one or 
multiple sites.

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
-h, --help              display this help
-s, --site_ids=         list of sites to use, comma separated
-v, --vlan_id=          Set the mgmt VLAN ID, 0 for untagged
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./configure_ap_mgmt_vlan.py     
python3 ./configure_ap_mgmt_vlan.py -s 203d3d02-xxxx-xxxx-xxxx-76896a3330f4,203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -v 31

'''

#####################################################################
#### IMPORTS ####
import logging
import sys
import getopt

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except:
        print("""
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """)
        sys.exit(2)


#####################################################################
#### PARAMETERS #####
log_file = "./script.log"
env_file = "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar():
    def __init__(self):        
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size:int=80):   
        if self.steps_count > self.steps_total: 
            self.steps_count = self.steps_total

        percent = self.steps_count/self.steps_total
        delta = 17
        x = int((size-delta)*percent)
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(self, message:str, result:str, inc:bool=False, size:int=80, display_pbar:bool=True):
        if inc: self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar: self._pb_update(size)

    def _pb_title(self, text:str, size:int=80, end:bool=False, display_pbar:bool=True):
        print("\033[A")
        print(f" {text} ".center(size, "-"),"\n\n")
        if not end and display_pbar: 
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total:int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar:bool=True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc:bool=False, display_pbar:bool=True):
        logger.info(f"{message}: Success")
        self._pb_new_step(message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc:bool=False, display_pbar:bool=True):
        logger.error(f"{message}: Failure")    
        self._pb_new_step(message, '\033[31m\u2716\033[0m\n', inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end:bool=False, display_pbar:bool=True):
        logger.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

pb = ProgressBar()
#####################################################################
#### FUNCTIONS ####

def _get_device_ids(apisession:mistapi.APISession, site_name:str, site_id:str):
    logger.info(f"{site_id}: Retrieving devices list")
    devices = []
    try:
        response = mistapi.api.v1.sites.devices.listSiteDevices(apisession, site_id=site_id, type="ap")
        devices = mistapi.get_all(apisession, response)
    except:
        logger.error(f"{site_id}: Unable to retrieve devices list")
        print(f"Unable to retrieve devices list from site {site_name}")
    finally:
        logger.info(f"{site_id}: {len(devices)} devices will be updated")
        return devices

def _update_vlan_id(ip_config:dict, vlan_id:int):
    # set "vlan_id" in AP settings if vlan_id > 0
    if vlan_id > 0:
        ip_config["vlan_id"] = vlan_id
    # or delete the "vlan_id" key from the AP settings 
    elif ip_config.get("vlan_id", None) is not None:
        del ip_config["vlan_id"]
    return ip_config


def _update_devices(apisession:mistapi.APISession, site_name:str, site_id:str, vlan_id:int):
    try:
        message="Retrieving devices list"
        pb.log_message(message, display_pbar=False)
        devices = _get_device_ids(apisession, site_name, site_id)
        pb.log_success(message, display_pbar=False)
    except:
        pb.log_failure(message, display_pbar=False)

    if len(devices) == 0:
        pb.log_success("No APs assigned to this site")
        logger.info(f"{site_id}: no devices to process")
    else:
        count = len(devices)
        pb.set_steps_total(count)
        for device in devices:
            device_id = device["id"]
            device_name = device.get("name", "No Name")
            device_mac = device.get("mac")
            if not device_name: device_name = device_mac
            message=f"Updating device {device_name} ({device_mac})"
            pb.log_message(message)
            try:
                device_settings = mistapi.api.v1.sites.devices.getSiteDevice(apisession, site_id=site_id, device_id=device_id).data
                logger.debug(device_settings)
                ip_config = device_settings.get("ip_config", {})
                logger.debug(f"ip_config before change: {ip_config}")
                ip_config = _update_vlan_id(ip_config, vlan_id)
                logger.debug(f"ip_config after change: {ip_config}")
                device_settings["ip_config"] = ip_config
                mistapi.api.v1.sites.devices.updateSiteDevice(apisession, site_id, device_id, device_settings)
                pb.log_success(message, inc=True)
            except:
                pb.log_failure(message, inc=True)

#####################################################################
##### MENU ####
def _enter_vlan_id():
    vid = -1
    while vid < 0 or vid > 4095:
        print("")    
        resp = input("Management VLAN ID (0 for untagged): ")
        try:
            resp = int(resp)
            if resp < 0 or resp > 4095:
                print("Please enter a number between 0 and 4095")
            else: 
                vid = resp
        except:
            print("Please enter a number between 0 and 4095")
    return vid


def process_sites(apisession:mistapi.APISession, site_ids:list, vlan_id:int):
    print()
    for site_id in site_ids:
        logger.info(f"{site_id}: Processing site")
        site_info = mistapi.api.v1.sites.sites.getSiteInfo(apisession, site_id).data
        site_name = site_info["name"]
        logger.info(f"{site_id}: name is {site_name}")
        pb.log_title(f"Processing Site {site_name}", display_pbar=False)
        _update_devices(apisession, site_name, site_id, vlan_id)
    pb.log_title("VLAN configuration done", end=True)


def start(apisession:mistapi.APISession, site_ids:list=None, vlan_id:int=-1):
    if not site_ids:
        site_ids = mistapi.cli.select_site(apisession, allow_many=True)
    if not type(vlan_id) == int or vlan_id < 0:
        vlan_id = _enter_vlan_id()
    logger.info(f"Site IDs: {site_ids}")
    logger.info(f"VLAN ID : {vlan_id}")
    process_sites(apisession, site_ids, vlan_id)


#####################################################################
##### USAGE ####
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script reconfigure Mist APs with a tagged managed VLAN

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
-h, --help              display this help
-s, --site_ids=         list of sites to use, comma separated
-v, --vlan_id=          Set the mgmt VLAN ID, 0 for untagged
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./configure_ap_mgmt_vlan.py     
python3 ./configure_ap_mgmt_vlan.py -s 203d3d02-xxxx-xxxx-xxxx-76896a3330f4,203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -v 31

'''
)
    sys.exit(0)

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """)
        sys.exit(2)
    else: 
        logger.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")

#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:v:e:l:", [
                                   "help", "site_ids=", "vlan_id=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    site_ids = []
    vlan_id = -1
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-s", "--site_ids"]:
            try:
                for site_id in  a.split(","):
                    site_ids.append(site_id.strip())
            except:
                console.critical("Unable to parse the Site IDs from the parameters")
                sys.exit(1)
        elif o in ["-v", "--vlan_id"]:
            try:
                vlan_id = int(a)
            except:
                console.critical("Unable to parse the VLAN ID from the parameters")
                sys.exit(1)
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, site_ids, vlan_id)




