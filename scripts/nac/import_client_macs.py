'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script import import a list of MAC Address into "Client List" Mist NAC 
Labels from a CSV File.
If a NAC LAbel doesn't exist, the script can optionally create it during the 
process

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
#mac,label
2E39D54797D9,Label1
636ddded62af,label2

------
CSV Parameters
Required:
- mac                       MAC Address of the Wi-Fi client
- label                     Name of the Label


-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-f, --file          path the to csv file to load
                    default is ./import_client_macs.csv

-c, --create        If True, the script will automatically create the tags if not 
                    already created in the org
                    default is False

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_client_macs.py             
python3 ./import_client_macs.py \
    -f ./import_client_macs.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''
#### IMPORTS ####
import sys
import csv
import getopt
import logging

MISTAPI_MIN_VERSION = "0.46.1"

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
CSV_FILE="./import_client_macs.csv"
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
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()

#####################################################################
# FUNCTIONS

def _process_org_nactags(nactags:list):
    data = {}
    for nactag in nactags:
        if nactag.get("match") == "client_mac":
            name = nactag["name"].lower()
            if name not in data:
                data[name] = nactag
            else:
                data[name].append(id)
    return data

def _retrieve_org_nactags(apisession:mistapi.APISession, org_id:str):
    message = f"retrieving Org Client List Labels"
    try:
        PB.log_message(message)
        resp = mistapi.api.v1.orgs.nactags.listOrgNacTags(apisession, org_id)
        nactags = mistapi.get_all(apisession, resp)
        if len(nactags) > 0:
            PB.log_success(message, inc=True)
            return _process_org_nactags(nactags)
        else:
            PB.log_failure(message, inc=True)
            CONSOLE.critical(f"No Org Auth Policy Labels found... Exiting...")
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

def _create_nactag(apisession:mistapi.APISession, org_id:str, mac: str, label:str, message:str):
    message_create = f"creat NAT TAG {label}"
    try:
        PB.log_message(message_create)
        nactag_body = {
                "values": [ mac ],
                "name": label,
                "type": "match",
                "match": "client_mac"
            }
        resp = mistapi.api.v1.orgs.nactags.createOrgNacTag(apisession, org_id, nactag_body)
        if resp.status_code == 200:
            LOGGER.info(f"_create_nac_label:new nactag created with values {resp.data}")
            PB.log_success(message_create, inc=True)
            PB.log_success(message, inc=True)
            return resp.data
        else:
            LOGGER.error(
                f"_create_nac_label:unable to create the new "
                f"nactag with values {nactag_body}"
            )
            PB.log_failure(message_create, inc=True)
            PB.log_failure(message, inc=True)
    except Exception as e:
        PB.log_failure(message_create, inc=True)
        PB.log_failure(message, inc=True)
        LOGGER.error("_create_nac_label:Exception occurred", exc_info=True)

def _update_nactag(apisession:mistapi.APISession, org_id:str, mac:str, nactag:dict, message:str):
    try:
        nactag_values = nactag.get("values", [])
        if mac in nactag_values:
            PB.log_warning(message, inc=True)
            LOGGER.warning(
                f"_update_nactag:mac address {mac} is already in the nactag "
                f"{nactag['id']} values. skipping it..."
            )
        else:
            nactag_values.append(mac)
            nactag["values"] = nactag_values
            resp = mistapi.api.v1.orgs.nactags.updateOrgNacTag(
                apisession,
                org_id,
                nactag["id"],
                nactag
            )
            if resp.status_code == 200:
                LOGGER.info(f"_update_nactag:nactag updated with new values {resp.data}")
                PB.log_success(message, inc=True)
            else:
                LOGGER.error(f"_update_nactag:unable to updated nactag with new values {nactag}")
                PB.log_failure(message, inc=True)
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("_update_nactag:Exception occurred", exc_info=True)


def _update_nac_label(apisession:mistapi.APISession, org_id:str, entries:list, nactags:dict, autocreate:bool):
    PB.log_title("Updating Client List Label")
    for entry in entries:
        message = f"create mac {entry['mac']}"
        try:
            PB.log_message(message)
            mac = entry["mac"]
            label = entry["label"]
            LOGGER.debug(f"_update_nac_label:looking for nactag_id for label {label}")
            nactag = nactags.get(label, {})
            if not nactag:
                LOGGER.warning(
                    f"_update_nac_label:unable to find the nactag_id "
                    f"for label {label} in the org"
                )
                if autocreate:
                    LOGGER.info(
                        f"_update_nac_label:autocreate is set to True. "
                        f"Will create the missing tag"
                    )
                    new_nactag = _create_nactag(apisession, org_id, mac, label, message)
                    if new_nactag:
                        nactags[label] = new_nactag
                else:
                    LOGGER.info(
                        f"_update_nac_label:autocreate is set to False. "
                        f"Marking as not created"
                    )
                    PB.log_failure(message, inc=True)
            else:
                LOGGER.debug(
                    f"_update_nac_label:nactag_id is {nactag['id']}. "
                    f"values are {nactag.get('values')}"
                )
                _update_nactag(apisession, org_id, mac, nactag, message)
        except Exception as e:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)

def _read_csv(csv_file:str):
    message = "Processing CSV File"
    try:
        PB.log_message(message, display_pbar=False)
        LOGGER.debug(f"_read_csv:opening CSV file {csv_file}")
        with open(csv_file, "r") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            fields = []
            macs = []
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
                    if "label" not in fields:
                        LOGGER.critical(f"_read_csv:label not in CSV file... Exiting...")
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (Client List Label Name not found). "
                            "Please double check it... Exiting..."
                            )
                        sys.exit(255)
                else:
                    mac = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        mac[field] = column.lower().strip()
                        i += 1
                    LOGGER.debug(f"_read_csv:new mac added: {mac}")
                    macs.append(mac)
        PB.log_message(message, display_pbar=False)
        return macs
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

def start(apisession:mistapi.APISession, org_id:str=None, csv_file:str=None, autocreate:bool=False):
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
    autocreate : bool
        If True, the script will automatically create the tags if not already created in the org

    """
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    if not csv_file:
        csv_file = CSV_FILE

    macs = _read_csv(csv_file)

    PB.set_steps_total(len(macs))

    if org_id:
        nactags = _retrieve_org_nactags(apisession, org_id)
        _update_nac_label(apisession, org_id, macs, nactags, autocreate)


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
Python script import import a list of MAC Address into "Client List" Mist NAC 
Labels from a CSV File.
If a NAC LAbel doesn't exist, the script can optionally create it during the 
process

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
#mac,label
2E39D54797D9,Label1
636ddded62af,label2

------
CSV Parameters
Required:
- mac                       MAC Address of the Wi-Fi client
- label                     Name of the Label


-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-f, --file          path the to csv file to load
                    default is ./import_client_macs.csv

-c, --create        If True, the script will automatically create the tags if not 
                    already created in the org
                    default is False

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_client_macs.py             
python3 ./import_client_macs.py \
    -f ./import_client_macs.csv \
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
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:e:l:c", [
                                   "help", "org_id=", "file=", "env=", "log_file=", "create"])
    except getopt.GetoptError as err:
        CONSOLE.error(err)
        usage()

    ORG_ID = None
    AUTOCREATE = False
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-f", "--file"]:
            CSV_FILE = a
        elif o in ["-c", "--create"]:
            AUTOCREATE = True
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
    start(apisession, ORG_ID, CSV_FILE, AUTOCREATE)

