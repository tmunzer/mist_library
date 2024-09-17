'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to rename devices (AP, Switch, Router) from a CSV file. The 
script will automatically locate the site where the device is assigned, and 
update its name.
The devices can be identified by their MAC Address or Serial Number in the CSV
file.

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
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file.
The allowed values are listed below.

-------
CSV Parameters:
Required:
- name
- mac (MAC Address format does not matter) or serial 

-------
CSV Example:
Example 1:
#mac,name
5c:5b:35:c0:ff:ee,AP1
2c:6b:f5:c0:ff:ee,SW02


Example 2:
#serial,name
A012345678901,AP1
HV0123456789,SW02

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           Mist Org ID where the devices are claimed to
-c, --csv_file=         CSV File to use.
                        default is "./rename_devices.csv"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./rename_devices.py     
python3 ./rename_devices.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4

'''

#####################################################################
#### IMPORTS ####
import logging
import sys
import csv
import re
import getopt

MISTAPI_MIN_VERSION = "0.46.1"

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
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
CSV_FILE = "./rename_devices.csv"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

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
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc:bool=False, display_pbar:bool=True):
        LOGGER.error(f"{message}: Failure")    
        self._pb_new_step(message, '\033[31m\u2716\033[0m\n', inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end:bool=False, display_pbar:bool=True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()
#####################################################################
#### FUNCTIONS ####

def _update_devices(apisession:mistapi.APISession, devices:dict):
    LOGGER.debug("_update_devices")
    for device_info in devices:
        device_id = devices[device_info].get("id")
        device_name = devices[device_info].get("name")
        device_site_id = devices[device_info].get("site_id")
        message=f"Updating device {device_info} name to {device_name}"
        PB.log_message(message)
        if not device_id:
            PB.log_failure(message)
            LOGGER.error(f"_update_devices:unable to find the device_id for device {device_info}")
        elif not device_site_id:
            PB.log_failure(message)
            LOGGER.error(f"_update_devices:unable to find the site_id for device {device_info}. "
                        f"It is possible this device is still in the Org inventory")
        else:
            try:
                resp = mistapi.api.v1.sites.devices.updateSiteDevice(apisession, site_id=device_site_id, device_id=device_id, body={"name": device_name})
                if resp.status_code == 200:
                    new_device_name = resp.data.get("name")
                    if new_device_name == device_name:
                        LOGGER.info(f"_update_devices:new device name is "
                                    f"\"{new_device_name}\"")
                        PB.log_success(message, inc=True)
                    else:
                        LOGGER.warning(f"_update_devices:seems device {device_info}"
                                    f" has not been renamed. New name is {new_device_name}")
                        PB.log_warning(message, inc=True)
                else:
                    LOGGER.error(f"_update_devices:unable to rename"
                                f" device {device_info}. Got HTTP{resp.status_code} from Mist")
                    PB.log_failure(message, inc=True)
            except:
                PB.log_failure(message, inc=True)


def _retrieve_org_inventory(apisession:mistapi.APISession, org_id:str):
    LOGGER.debug("_retrieve_org_inventory")
    LOGGER.debug(f"_retrieve_org_inventory:parameter:org_id:{org_id}")
    message = "Retrieve Org Inventory"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.inventory.getOrgInventory(apisession, org_id, limit=1000)
        inventory = mistapi.get_all(apisession, resp)
        PB.log_success(message, display_pbar=False)
        LOGGER.debug(f"_retrieve_org_inventory:got {len(inventory)} devices from the org inventory")
        return inventory
    except:
        PB.log_failure(message, display_pbar=False)
        return None

def _read_csv_file(csv_file:str):
    LOGGER.debug("_read_csv_file")
    LOGGER.debug(f"_read_csv_file:parameter:csv_file:{csv_file}")
    fields = []
    devices = {}
    info_field = None # will be eith "mac" or "serial"
    column_info_field = -1
    column_name = -1
    PB.log_message("Processing CSV file", display_pbar=False)
    with open(csv_file, "r") as f:
        data_from_csv = csv.reader(f, skipinitialspace=True, quotechar='"')
        data_from_csv = [[c.replace("\ufeff", "") for c in row] for row in data_from_csv]
        for line in data_from_csv:
            LOGGER.debug(f"_read_csv_file:{line}")
            # this is for the first line of the CSV file
            if not fields:
                i=0
                for column in line:
                    column = re.sub("[^a-zA-Z_]", "", column)
                    LOGGER.debug(f"_read_csv_file:{column}")
                    fields.append(column)
                    if column == "serial":
                        info_field = "serial"
                        if column_info_field < 0:
                            column_info_field = i
                        else:
                            console.error("Either \"serial\" or \"mac\" can be used, not both.")
                            sys.exit(0)
                    elif column == "mac":
                        info_field = "mac"
                        if column_info_field < 0:
                            column_info_field = i
                        else:
                            console.error("Either \"serial\" or \"mac\" can be used, not both.")
                            sys.exit(0)

                    elif column == "name":
                        column_name = i
                    i+=1

                if column_info_field < 0:
                    console.error("Unable to find `serial` or `mac` field in the CSV file. "
                                "Please check the file format")
                    sys.exit(0)
                if column_name < 0:
                    console.error("Unable to find `name` field in the CSV file. "
                                "Please check the file format")
                    sys.exit(0)

            # this is for the other lines, containing the data
            else:
                name = line[column_name]
                info = line[column_info_field]
                if info_field == "mac":
                    info = re.sub("[^a-f0-9]", "", info.lower())
                    if len(info) != 12:
                        console.error(f"MAC Address format if wrong at line {line}")
                        sys.exit(0)
                else:
                    info = info.upper()
                if not name:
                    console.error(f"Unable to get \"name\" at line {line}")
                    sys.exit(0)
                elif not info:
                    console.error(f"Unable to get \"{info_field}\" at line {line}")
                    sys.exit(0)
                else:
                    devices[info]={"name": name}
                    LOGGER.debug(f"_read_csv_file:new device:{info}:{devices[info]}")

    LOGGER.debug(f"_read_csv_file:got {len(devices)} devices to rename from {csv_file}")
    PB.log_success("Processing CSV file", display_pbar=False, inc=False)
    return info_field, devices

def _processing_data(info_field:str, devices_from_csv:dict, inventory:list):
    LOGGER.debug("_processing_data")
    message = "Processing inventory"
    PB.log_message(message, display_pbar=False)
    try:
        for device in inventory:
            device_info = device[info_field]
            if devices_from_csv.get(device_info):
                LOGGER.debug(f"_processing_data:device {device_info} will be renamed")
                devices_from_csv[device_info]["site_id"] = device.get("site_id")
                devices_from_csv[device_info]["id"] = device.get("id")
                LOGGER.debug(f"_processing_data:{devices_from_csv[device_info]}")
        PB.log_success(message, display_pbar=False)
        return devices_from_csv
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        console.critical("Unable to process data. Please check the logs. Exiting...")
        sys.exit(255)


def _prepare_data(apisession:mistapi.APISession, org_id:str, csv_file:str):
    LOGGER.debug("_prepare_data")
    LOGGER.debug(f"_prepare_data:parameter:org_id:{org_id}")
    LOGGER.debug(f"_prepare_data:parameter:csv_file:{csv_file}")
    PB.log_title("Processing data", display_pbar=False)
    info_field, devices_from_csv = _read_csv_file(csv_file)
    inventory = _retrieve_org_inventory(apisession, org_id)
    LOGGER.debug(inventory)
    data = _processing_data(info_field, devices_from_csv, inventory)
    LOGGER.debug(data)
    return data



def start(apisession:mistapi.APISession, org_id:str, csv_file:str):
    """
    Start the process to rename the devices

    PARAMS
    -------
    apisession : mistapi.APISession 
        mistapi session, already logged in
    org_id : str 
        only if the destination org already exists. org_id where to deploy the
        configuration
    csv_file : str 
        Path to the csv_file where the information are stored.
        default: "./rename_device.py"
    """
    LOGGER.debug("start")
    LOGGER.debug(f"start:parameter:org_id:{org_id}")
    LOGGER.debug(f"start:parameter:csv_file:{csv_file}")
    if not org_id:
        org_id = mistapi.cli.select_org(apisession, allow_many=True)[0]
    if not csv_file:
        csv_file = CSV_FILE

    devices = _prepare_data(apisession, org_id, csv_file)
    PB.set_steps_total(len(devices))
    _update_devices(apisession, devices)


#####################################################################
##### USAGE ####
def usage(error_message:str=None):
    """
    display usage

    PARAMS
    -------
    error_message : str
        if error_message is set, display it after the usage
    """
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to rename devices (AP, Switch, Router) from a CSV file. The 
script will automatically locate the site where the device is assigned, and 
update its name.
The devices can be identified by their MAC Address or Serial Number in the CSV
file.

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
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file.
The allowed values are listed below.

-------
CSV Parameters:
Required:
- name
- mac (MAC Address format does not matter) or serial 

-------
CSV Example:
Example 1:
#mac,name
5c:5b:35:c0:ff:ee,AP1
2c:6b:f5:c0:ff:ee,SW02


Example 2:
#serial,name
A012345678901,AP1
HV0123456789,SW02

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           Mist Org ID where the devices are claimed to
-c, --csv_file=         CSV File to use.
                        default is "./rename_devices.csv"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./rename_devices.py     
python3 ./rename_devices.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4

'''
)
    if error_message:
        console.critical(error_message)
    sys.exit(0)

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
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
        LOGGER.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, "
                    f"you are currently using version {mistapi.__version__}.")

#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:c:e:l:", [
                                   "help", "org_id=", "csv_file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()
    ORG_ID = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
                ORG_ID = a
        elif o in ["-c", "--csv_file"]:
                CSV_FILE = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, CSV_FILE)
