'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script import import a list of MAC Address as "NAC Endpoints" from a 
CSV File.

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
Example 1:
#mac,labels,vlan,notes,name,radius_group
921b638445cd,"bldg1,flor1",vlan-100
721b638445ef,"bldg2,flor2",vlan-101,Canon Printers
721b638445ee,"bldg3,flor3",vlan-102,Printer2,VIP
921b638445ce,"bldg4,flor4",vlan-103
921b638445cf,"bldg5,flor5",vlan-104


------
CSV Parameters
Required:
- mac               MAC Address of the Wi-Fi client

Optional:
- labels            Name of the Label. If not provided, a default label value can be
                    passed in the script parameter with the -d option or will be asked
                    by the script
- vlan              Name of the VLAN to assign to the endpoint
- name              Name to assign to the endpoint
- radius_group      

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-f, --file          path the to csv file to load
                    default is ./import_user_macs.csv

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_user_macs.py             
python3 ./import_user_macs.py \
    -f ./import_user_macs.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''
#### IMPORTS ####
import sys
import csv
import getopt
import logging

MISTAPI_MIN_VERSION = "0.52.4"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
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
ENV_FILE="~/.mist_env"
CSV_FILE="./import_user_macs.csv"
LOG_FILE = "./script.log"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
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
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)
        
    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}")
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()

#####################################################################
# FUNCTIONS


def import_usermacs(
        apisession:mistapi.APISession,
        org_id:str,
        usermacs:dict
        ):
    try:
        message = "Importing user macs"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.usermacs.importOrgUserMacs(apisession, org_id, usermacs)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return
        else:
            PB.log_failure(message, display_pbar=False)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


def _read_csv(csv_file:str):
    message = "Processing CSV File"
    try:
        PB.log_message(message, display_pbar=False)
        LOGGER.debug(f"_read_csv:opening CSV file {csv_file}")
        with open(csv_file, "r") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            data = [[c.replace("\ufeff", "") for c in row] for row in data]
            fields = []
            entries = []
            for line in data:
                LOGGER.debug(f"_read_csv:new csv line:{line}")
                if not fields:
                    for column in line:
                        fields.append(column.replace("#", "").strip())
                    LOGGER.debug(f"_read_csv:detected CSV fields: {fields}")
                    if "mac" not in fields:
                        LOGGER.critical(f"_read_csv:mac address not in CSV file... Exiting...")
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (MAC Address not found). "
                            "Please double check it... Exiting..."
                            )
                        sys.exit(255)                       
                else:
                    entry = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        if field == "labels":
                            entry[field] = []
                            for label in column.split(","):
                                entry[field].append(label.strip())
                        else:
                            entry[field] = column.strip()
                        i += 1
                    entries.append(entry)
                    LOGGER.debug(f"_read_csv:new entry processed: {entry['mac']} with label {entry.get('labels')}")
        PB.log_success(message, display_pbar=False)
        return entries
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

def start(apisession:mistapi.APISession, org_id:str=None, csv_file:str=CSV_FILE):
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
    """
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    PB.log_title("Reading data", display_pbar=False)
    print()
    entries = _read_csv(csv_file)

    import_usermacs(apisession, org_id, entries)


###############################################################################
# USAGE
def usage(error_message:str=None):
    """
    show script usage
    """
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script import import a list of MAC Address as "NAC Endpoints" from a 
CSV File.

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
Example 1:
mac,labels,vlan,notes,name,radius_group
921b638445cd,"bldg1,flor1",vlan-100
721b638445ef,"bldg2,flor2",vlan-101,Canon Printers
721b638445ee,"bldg3,flor3",vlan-102,Printer2,VIP
921b638445ce,"bldg4,flor4",vlan-103
921b638445cf,"bldg5,flor5",vlan-104


------
CSV Parameters
Required:
- mac               MAC Address of the Wi-Fi client

Optional:
- labels            Name of the Label. If not provided, a default label value can be
                    passed in the script parameter with the -d option or will be asked
                    by the script
- vlan              Name of the VLAN to assign to the endpoint
- name              Name to assign to the endpoint
- radius_group      

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-f, --file          path the to csv file to load
                    default is ./import_user_macs.csv

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_user_macs.py             
python3 ./import_user_macs.py \
    -f ./import_user_macs.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

""")
    if error_message:
        CONSOLE.critical(error_message)
    sys.exit(0)

def check_mistapi_version():
    """
    check the current version of the mistapi package
    """
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
        LOGGER.info(
            f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, "
            f"you are currently using version {mistapi.__version__}."
        )

#####################################################################
##### ENTRY POINT ####

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:e:l:", [
                                   "help", "org_id=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        CONSOLE.error(err)
        usage()

    ORG_ID = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-f", "--file"]:
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
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    start(apisession, ORG_ID, CSV_FILE)

