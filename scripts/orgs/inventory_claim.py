'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to claim devices to an org from a CSV file. 

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
#claim_code
AAAAAAAAAAAAAAAA
BBBBBBBBBBBBBBBB
...

-------
CSV Parameters:
Required:
- claim_code

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-f, --file=             Path to the csv file 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./inventory_claim.py -f my_csv_file.csv
python3 ./inventory_claim.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -f my_csv_file.csv

'''

#### IMPORTS ####
import logging
import sys
import os
import csv
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
def _result(failed_messages:list, duplicated_codes:list):
    pb.log_title("Result", end=True, display_pbar=False)    
    if not failed_messages and not duplicated_codes:
        console.info("All devices assigned successfully")
    else:
        for message in failed_messages:
            console.error(message)
        for duplicated in duplicated_codes:
            console.warning(f"device {duplicated} duplicated")

def _generate_failed_messages(claim_codes:list, reasons:list):
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
    pb.log_message(message) 
    try:

        resp = mistapi.api.v1.orgs.inventory.addOrgInventory(apisession, org_id, claim_codes)
        if resp.status_code == 200:
            if not resp.data.get("error", []) and not resp.data.get("duplicated", []):
                pb.log_success(message, inc=False)
                return {"error": [],"duplicated": []}
            else:
                pb.log_warning(message, inc=False)
                return {"error": _generate_failed_messages(resp.data.get("error", []), resp.data.get("reason",[])), "duplicated": resp.data.get("duplicated", [])}
        else:
            pb.log_failure(message, inc=False)
            return {"error": _generate_failed_messages(resp.data.get("error", []),  resp.data.get("reason",[])), "duplicated":resp.data.get("duplicated", [])}
    except:
        pb.log_failure(message, inc=False)
        return {"error": resp.data.get("error", [f"Unknown error for devices {claim_codes}"]), "duplicated": resp.data.get("duplicated", [])}


def _process_devices(apisession:mistapi.APISession, org_id:str, claim_codes:list):
    '''
    Claim devices to org
    '''
    failed_messages = []
    duplicated_codes = []
    limit = 50
    i = 0
    while i * limit < len(claim_codes):
        claim_code_start = i * limit
        claim_code_end = (i+1)*limit
        if claim_code_end > len(claim_codes): mac_end = len(claim_codes)
        claim_codes_to_process = claim_codes[claim_code_start:mac_end]
        res = _claim_devices(apisession, org_id, claim_codes_to_process)
        if res["error"]: failed_messages+=res["error"]
        if res["duplicated"]: duplicated_codes+=res["duplicated"]
        i+=1
    pb.inc()
    return failed_messages, duplicated_codes


def _read_csv_file(file_path: str):
    fields = []
    claim_codes = []
    claim_code_row = -1
    pb.log_message("Processing CSV file", display_pbar=False)
    with open(file_path, "r") as f:
        data_from_csv = csv.reader(f, skipinitialspace=True, quotechar='"')
        data_from_csv = [[c.replace("\ufeff", "") for c in row] for row in data_from_csv]
        for line in data_from_csv:
            if not fields:
                i=0
                for column in line:
                    column = column.replace("#", "")
                    fields.append(column)
                    if  column == "claim_code":      
                        if claim_code_row < 0:
                            claim_code_row = i
                        else:
                            console.error("CSV format not valid.")
                    else:
                        console.error("CSV format not valid.")
                    i+=1                    

                if claim_code_row < 0: 
                    console.error("Unable to find `claim_code` in the CSV file. Please check the file format")
                    sys.exit(0)
                
            elif claim_code_row > -1:
                claim_codes.append(line[claim_code_row])    
        pb.log_success("Processing CSV file", display_pbar=False, inc=False)
        return claim_codes

def start(apisession:mistapi.APISession, file_path:str, org_id:str):
    '''
    Start the backup process

    PARAMS
    -------
    :param  mistapi.APISession  apisession          - mistapi session with `Super User` access the Org, already logged in
    :param  str                 org_id              - org_id of the org to backup
    :param  str                 file_path           - Path to the CSV file 
    '''   
    if not org_id: org_id = mistapi.cli.select_org(apisession)[0]
    claim_codes = _read_csv_file(file_path)
    if not claim_codes:
        console.error("Not able to get claim codes from the CSV file")
        sys.exit(0)
    else:
        pb.set_steps_total(len(claim_codes))
        failed_messages, duplicated_codes = _process_devices(apisession, org_id, claim_codes)
        _result(failed_messages, duplicated_codes)


#####################################################################
#### USAGE ####
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to claim devices to an org from a CSV file. 

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
#claim_code
AAAAAAAAAAAAAAAA
BBBBBBBBBBBBBBBB
...

-------
CSV Parameters:
Required:
- claim_code

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-f, --file=             Path to the csv file 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./inventory_claim.py -f my_csv_file.csv
python3 ./inventory_claim.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -f my_csv_file.csv

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
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:e:l:", [
                                   "help", "org_id=", "file=", "env=", "log_file="])
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
        start(apisession, csv_file, org_id)
