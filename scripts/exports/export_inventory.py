'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to export the inventory from an organization. The export will 
include all the information available from the org inventory, including the
claim codes.
The current version is not exporting Mist Edges inventory.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-o, --org_id=       required for Org reports. Set the org_id    
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./export.csv"
--out_format=       define the output format (csv or json)
                    default is csv
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./export_inventory.py                  
python3 ./export_inventory.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 
'''

#### IMPORTS ####

import sys
import json
import csv
import os
import logging
import datetime
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

#### PARAMETERS #####

log_file = "./script.log"
env_file = os.path.join(os.path.expanduser('~'), ".mist_env")
out_file_format="csv"
out_file_path="./export.csv"

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
        if self.steps_total > 0:
            percent = self.steps_count/self.steps_total
        else:
            percent = 0
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

    def inc_only(self, size:int=80):
        print("\033[F")
        self.steps_count += 1
        self._pb_update(size)
    
    def reinit(self):
        self.steps_count = 0


pb = ProgressBar()

####################
## REQUEST
def _process_export(apisession:mistapi.APISession, org_id:str):
    data = []
    
    print()
    pb.log_title("Retrieving Data from Mist", display_pbar=False)

    for device_type in ["ap", "switch", "gateway"]:
        try:
            message = f"Retrieving {device_type.title()} Inventory"
            pb.log_message(message, display_pbar=False)
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(apisession, org_id, type=device_type, vc=True)
            data += mistapi.get_all(apisession, response)
            pb.log_success(message, display_pbar=False)
        except:
            pb.log_failure(message, display_pbar=False)
            logger.error("Exception occurred", exc_info=True)
    return data
####################
## SAVE TO FILE
def _save_as_csv(data:list, org_name:str, org_id:str):
    headers=[]    
    total = len(data)
    pb.log_title("Saving Data", display_pbar=False)
    pb.set_steps_total(total)
    message = "Generating CSV Headers"
    pb.log_message(message)
    i = 0
    for entry in data:
        for key in entry:
            if not key in headers:
                headers.append(key)
        i += 1
        pb.inc_only()
    pb.log_success(message, inc=True)
    
    message="Saving to file"
    pb.set_steps_total(total)
    pb.reinit()
    pb.log_message(message)
    i = 0
    with open(out_file_path, "w", encoding='UTF8', newline='') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([f"#Report: Device Inventory Export", f"Date: {datetime.datetime.now()}", f"Org Name: {org_name}", f"Org ID: {org_id}"])
        csv_writer.writerow(headers)
        for entry in data:
            tmp=[]
            for header in headers:
                tmp.append(entry.get(header, ""))
            csv_writer.writerow(tmp)
            i += 1
            pb.inc_only()
        pb.log_success(message, inc=True)
    print("\033[FDone.".ljust(80))


def _save_as_json(data:list, org_name:str, org_id:str):
    print(" Saving Data ".center(80, "-"))
    print()
    json_data = {
        'report': "Device Inventory Export",
        'Date': f'{datetime.datetime.now()}',
        'Org Name': org_name,
        'Org ID': org_id,
        'data': data
    }
    with open(os.path.abspath(out_file_path), 'w') as f:
        json.dump(json_data, f)
    print("Done.")

####################
## MENU

def start(apisession, org_id:str=None):
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    data=_process_export(apisession, org_id)
    if out_file_format == "csv":
        _save_as_csv(data, org_name, org_id)
    elif out_file_format == "json":
        _save_as_json(data, org_name, org_id)
    else:
        console.error(f"file format {out_file_format} not supported")

def usage():
    print(f"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to export the inventory from an organization. The export will 
include all the information available from the org inventory, including the
claim codes.
The current version is not exporting Mist Edges inventory.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-o, --org_id=       required for Org reports. Set the org_id    
-l, --log_file=     define the filepath/filename where to write the logs
                    default is {log_file}
-f, --out_file=     define the filepath/filename where to save the data
                    default is {out_file_path}
--out_format=       define the output format (csv or json)
                    default is csv
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is {env_file}

-------
Examples:
python3 ./export_inventory.py                  
python3 ./export_inventory.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 
    """)
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

#### SCRIPT ENTRYPOINT ####

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:e:l:", ["help", "org_id=", "out_format=", "out_file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()        
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["--out_format"]:
            if a in ["csv", "json"]:
                out_file_format=a
            else:
                console.error(f"Out format {a} not supported")
                usage()
        elif o in ["-f", "--out_file"]:
            out_file_path=a
        elif o in ["-e", "--env"]:
            env_file=a
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
    start(apisession, org_id)
