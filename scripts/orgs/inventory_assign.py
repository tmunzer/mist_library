'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to assign devices to sites from a CSV file. 
If the devices are already in the Org Inventory, the device MAC Address, Serial
Number or Claim Code can be provided.
If devices are not yet in the Org Inventory, only Claim Codes can be used. The
script will first claim the devices and then assign them to the sites.

To allow the script to reassign a device from a previous site, please use the 
`-r` flag.
To set the switches/gateways as managed (not read only mode), please use the 
`-m` flag.

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
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

-------
CSV Examples:
Example 1:
#site_id, mac
0f661715-xxxx-xxxx-xxxx-cea446308f64,a4:e1:1a:00:00:00
de45d851-xxxx-xxxx-xxxx-93b0cc52b435,d4:20:b0:11:11:11
...

Example 2:
#site_name, mac
"Site 2",a4:e1:1a:00:00:00
...

Example 3:
#site_name, serial
"Site 2",A113454322345
...

Example 4:
#site_id, serial
de45d851-xxxx-xxxx-xxxx-93b0cc52b435,A113454322345
...
-------
CSV Parameters:
Required:
- site_id or site_name
- mac, serial or claimcode

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-f, --file=             Path to the csv file 

-m, --managed           Enable the "managed" mode for the switches/gateways.
                        By default the assigned switches/gateways will be in
                        monitor mode only
-r, --reassign          Allow the script to reassign devices from a previous
                        site.
                        By default, if a device is already assigned the script
                        will report an error for this device.

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./inventory_assign.py -f my_csv_file.csv
python3 ./inventory_assign.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -f my_csv_file.csv

'''

#### IMPORTS ####
import logging
import sys
import os
import csv
import getopt
import re

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
csv_separator = ","
env_file="~/.mist_env"
log_file = "./script.log"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
# BACKUP OBJECTS REFS
device_types = ["ap","switch","gateway","mxedge"]

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
        print(f" {text} ".center(size, "-"),"\n")
        if not end and display_pbar: 
            print("".ljust(80))
            self._pb_update(size)

    def inc(self, size: int = 80):
        print("\033[A")
        self.steps_count += 1
        self._pb_update(size)

    def set_steps_total(self, steps_total:int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar:bool=True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc:bool=False, display_pbar:bool=True):
        logger.info(f"{message}: Success")
        self._pb_new_step(message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        logger.warning(f"{message}")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc:bool=False, display_pbar:bool=True):
        logger.error(f"{message}: Failure")
        self._pb_new_step(message, '\033[31m\u2716\033[0m\n', inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end:bool=False, display_pbar:bool=True):
        logger.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

pb = ProgressBar()

#####################################################################
def _result(failed_messages:list):
    pb.log_title("Result", end=True, display_pbar=False)    
    if not failed_messages:
        console.info("All devices assigned successfully")
    else:
        for message in failed_messages:
            console.error(message)

    

#####################################################################
## CLAIM
def _generate_failed_claim_messages(claim_codes:list, reasons:list):
    failed_messages = []
    i = 0
    while i < len(claim_codes):
        claim_code = claim_codes[i]
        if not claim_code: claim_code = "unknown"
        mess = reasons[i]
        if not mess: mess = "Unknown reason"
        failed_messages.append(f"device {claim_code}: {mess}")
        i+=1
    return failed_messages

def _claim_devices(apisession:mistapi.APISession, org_id:str,claim_codes:list):
    message = f"Claiming {len(claim_codes)} device(s)"
    pb.log_message(message, display_pbar=False) 
    try:

        resp = mistapi.api.v1.orgs.inventory.addOrgInventory(apisession, org_id, claim_codes)
        if resp.status_code == 200:
            device_macs = {}
            added = resp.data.get("added", [])
            duplicated = resp.data.get("duplicated", [])
            error = resp.data.get("error", [])
            if duplicated or error:
                pb.log_warning(message, display_pbar=False)
            else:
                pb.log_success(message, display_pbar=False)
            if added:
                for device in resp.data.get("inventory_added", []):
                    device_macs[device["magic"]] = device["mac"]
            return {"added": device_macs, "error": _generate_failed_claim_messages(resp.data.get("error", []), resp.data.get("reason",[])), "duplicated": resp.data.get("duplicated", [])}
        else:
            pb.log_failure(message, display_pbar=False)
            return {"error": _generate_failed_claim_messages(resp.data.get("error", []),  resp.data.get("reason",[])), "duplicated":resp.data.get("duplicated", [])}
    except:
        pb.log_failure(message, display_pbar=False)
        return {"error": resp.data.get("error", [f"Unknown error for devices {claim_codes}"]), "duplicated": resp.data.get("duplicated", [])}

#####################################################################
## ASSIGN


def _generate_failed_assign_messages(macs:list, reasons:list):
    failed_messages = []
    i = 0
    while i < len(macs):
        mac = macs[i]
        if not mac: mac = "unknown"
        mess = reasons[i]
        if not mess: mess = "Unknown reason"
        failed_messages.append(f"device {mac}: {mess}")
        i+=1
    return failed_messages

def _assign_devices(apisession:mistapi.APISession, org_id:str, site_id:str, macs:list, managed:bool=False, no_reassign:bool=True):
    message = f"Assigning {len(macs)} device(s)"
    pb.log_message(message) 
    try:
        body =  {
            "op": "assign",
            "site_id": site_id,
            "macs": macs,
            "managed": managed,
            "disable_auto_config": not managed,
            "no_reassign": no_reassign
        }
        resp = mistapi.api.v1.orgs.inventory.updateOrgInventoryAssignment(apisession, org_id, body)
        if resp.status_code == 200:
            if not resp.data.get("error", []):
                pb.log_success(message, inc=False)
                return []
            else:
                pb.log_warning(message, inc=False)
                return _generate_failed_assign_messages(resp.data.get("error", []), resp.data.get("reason",[]))
        else:
            pb.log_failure(message, inc=False)
            return _generate_failed_assign_messages(resp.data.get("error", []), resp.data.get("reason",[]))
    except:
        pb.log_failure(message, inc=False)
        return resp.data.get("reason", [f"Unknown error for devices {macs}"])


def _process_devices(apisession:mistapi.APISession, org_id:str, data:object, managed:bool=False, no_reassign:bool=True):
    '''
    create all the administrators from the "file_path" file.
    '''
    failed_messages = []
    limit = 100
    for site_id in data:
        pb.log_title(f"Site {site_id}")
        device_macs = data[site_id]          
        i = 0
        while i * limit < len(device_macs):
            mac_start = i * limit
            mac_end = (i+1)*limit
            if mac_end > len(device_macs): mac_end = len(device_macs)
            macs = device_macs[mac_start:mac_end]
            failed = _assign_devices(apisession, org_id, site_id, macs, managed, no_reassign)
            if failed:
                failed_messages+=failed                
            i+=1
        pb.inc()
    return failed_messages


def _read_csv_file(apisession: mistapi.APISession, file_path: str, org_id:str):
    fields = []
    data = {}
    data_cc = {}
    sites = {}
    inventory = {}
    use_site_name = False
    use_serial = False
    use_claimcode = False
    use_name = False
    claimcodes = []
    row_site = -1
    row_device = -1
    pb.log_message("Processing CSV file", display_pbar=False)
    with open(file_path, "r") as f:
        data_from_csv = csv.reader(f, skipinitialspace=True, quotechar='"')
        for line in data_from_csv:
            if not fields:
                i=0
                for column in line:
                    column = re.sub("[^a-zA-Z_]", "", column)
                    fields.append(column)
                    if "site" in column:
                        if row_site < 0:
                            row_site = i
                        else:
                            console.error("Either \"site_name\" or \"site_id\" can be used, not both.")
                    elif column in ["serial", "mac", "claimcode", "name"]:
                        if row_device < 0:
                            row_device = i
                        else:
                            console.error("Either \"serial\" or \"mac\" can be used, not both.")
                    i+=1
                    
                if "site_name" in fields:
                    use_site_name = True
                    message = "Retrieving site list from Mist"
                    pb.log_message(message, display_pbar=False)
                    try:
                        response = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
                        sites_from_mist = mistapi.get_all(apisession, response)
                        for site in sites_from_mist:                        
                            sites[site["name"]] = site["id"]
                        pb.log_success(message, inc=False, display_pbar=False)
                        pb.log_message("Processing CSV file", display_pbar=False)
                    except:
                        pb.log_failure(message, inc=False, display_pbar=False)
                        sys.exit(0)

                if "claimcode" in fields:
                    use_claimcode = True
                elif "serial" or "name" in fields:  
                    if "serial" in fields:
                        use_serial = True
                    elif "name" in fields:
                        use_name = True

                    message = "Retrieving device list from Mist"
                    pb.log_message(message, display_pbar=False)
                    try:
                        response  = mistapi.api.v1.orgs.inventory.getOrgInventory(apisession, org_id, limit=1000)
                        devices_from_mist = mistapi.get_all(apisession, response)
                        for device in devices_from_mist:
                            if "serial" in fields:                        
                                inventory[device["serial"]] = device["mac"]
                            elif "name" in fields:
                                inventory[device["name"]] = device["mac"] 
                        pb.log_success(message, inc=False, display_pbar=False)
                        pb.log_message("Processing CSV file", display_pbar=False)
                    except:
                        pb.log_failure(message, inc=False, display_pbar=False)
                        sys.exit(0)

                if row_site < 0: 
                    console.error("Unable to find `site_id` or `site_name` in the CSV file. Please check the file format")
                    sys.exit(0)
                if row_device < 0: 
                    console.error("Unable to find `mac` or `serial` or `name` in the CSV file. Please check the file format")
                    sys.exit(0)
            else:
                device_mac = None
                if use_site_name:
                    site_id = sites.get(line[row_site])
                else:
                    site_id = line[row_site]

                if use_serial or use_name:
                    device_mac = inventory.get(line[row_device])
                elif use_claimcode:
                    claimcodes.append(line[row_device])
                else:
                    device_mac = line[row_device]

                if (site_id and device_mac):
                    if not site_id in data:
                        data[site_id] = [device_mac.replace(":", "").replace("-", "")]
                    else:
                        data[site_id].append(device_mac.replace(":", "").replace("-", ""))
                elif (site_id and use_claimcode):
                    if not site_id in data_cc:
                        data_cc[site_id] = [line[row_device]]
                    else:
                        data_cc[site_id].append(line[row_device])
                elif (not site_id):
                    console.error(f"Unable to get site_id for line {line}")
                    sys.exit(0)
                elif (not device_mac):
                    console.error(f"Unable to get device mac for line {line}")
                    sys.exit(0)

    
        pb.log_success("Processing CSV file", display_pbar=False, inc=False)

        if use_claimcode:
            _claim_devices(apisession, org_id, claimcodes)
            response  = mistapi.api.v1.orgs.inventory.getOrgInventory(apisession, org_id, limit=1000)
            devices_from_mist = mistapi.get_all(apisession, response)
            for device in devices_from_mist:                        
                inventory[device["magic"]] = device["mac"]
            for site_id in data_cc:
                data[site_id] = []
                for claimcode in data_cc[site_id]:
                    device_mac = inventory.get(claimcode)
                    data[site_id].append(device_mac)


        return data

def start(apisession:mistapi.APISession, file_path:str, org_id:str, managed:bool=False, no_reassign:bool=True):
    '''
    Start the backup process

    PARAMS
    -------
    :param  mistapi.APISession  apisession          - mistapi session with `Super User` access the Org, already logged in
    :param  str                 org_id              - org_id of the org to backup
    :param  str                 file_path           - Path to the CSV file 
    :param  bool                managed             - If `False`, an adopted switch/gateway will not be managed/configured by Mist
    :param  bool                no_reassign         - If `True`,  treat site assignment against an already assigned AP as error
    '''   
    if not org_id: 
        org_id = mistapi.cli.select_org(apisession)[0]
        print("\n\n")
    data = _read_csv_file(apisession, file_path, org_id)
    pb.set_steps_total(len(data))
    failed_messages = _process_devices(apisession, org_id, data, managed, no_reassign)
    _result(failed_messages)


#####################################################################
#### USAGE ####
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to assign devices to sites from a CSV file. 
If the devices are already in the Org Inventory, the device MAC Address, Serial
Number or Claim Code can be provided.
If devices are not yet in the Org Inventory, only Claim Codes can be used. The
script will first claim the devices and then assign them to the sites.

To allow the script to reassign a device from a previous site, please use the 
`-r` flag.
To set the switches/gateways as managed (not read only mode), please use the 
`-m` flag.

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
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or 
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Examples:
Example 1:
#site_id, mac
0f661715-xxxx-xxxx-xxxx-cea446308f64,a4:e1:1a:00:00:00
de45d851-xxxx-xxxx-xxxx-93b0cc52b435,d4:20:b0:11:11:11
...

Example 2:
#site_name, mac
"Site 2",a4:e1:1a:00:00:00
...

Example 3:
#site_name, serial
"Site 2",A113454322345
...

Example 4:
#site_id, serial
de45d851-xxxx-xxxx-xxxx-93b0cc52b435,A113454322345
...

       
Example 5 (only possible if the names in inventory are unique):
#site_name, name
"Site 2", device01
          
""
-------
CSV Parameters:
Required:
- site_id or site_name
- mac, serial, name or claimcode

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-f, --file=             Path to the csv file 

-m, --managed           Enable the "managed" mode for the switches/gateways.
                        By default the assigned switches/gateways will be in
                        monitor mode only
-r, --reassign          Allow the script to reassign devices from a previous
                        site.
                        By default, if a device is already assigned the script
                        will report an error for this device.

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./inventory_assign.py -f my_csv_file.csv
python3 ./inventory_assign.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -f my_csv_file.csv

''')
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
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:mre:l:", [
                                   "help", "org_id=", "file=", "managed", "reassign", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    csv_file = None
    managed= False
    no_reassign = True
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a      
        elif o in ["-f", "--file"]:
            csv_file = a      
        elif o in ["-m", "--managed"]:
            managed = True
        elif o in ["-r", "--reassign"]:
            no_reassign = False
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["-e", "--env"]:
            env_file = a
        else:
            assert False, "unhandled option"
    
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    ### START ###
    if not csv_file:
        console.error("CSV File is missing")
        usage()
    else:
        start(apisession, csv_file, org_id, managed, no_reassign)
