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
Example 1:
#mac,label
2E39D54797D9,Label1
636ddded62af,label2
AE2302F109F0,

Example 2:
#mac
2E39D54797D9
636ddded62af
AE2302F109F0

------
CSV Parameters
Required:
- mac               MAC Address of the Wi-Fi client

Optional:
- label             Name of the Label. If not provided, a default label value can be
                    passed in the script parameter with the -d option or will be asked
                    by the script


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
-d, --default=      default Label name to use if MAC addresses are not assigned to 
                    any label name in the CSV file 

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
        LOGGER.info(f"{message}")
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
    message = f"Retrieving Org Labels from Mist"
    try:
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.nactags.listOrgNacTags(apisession, org_id)
        nactags = mistapi.get_all(apisession, resp)
        if len(nactags) > 0:
            PB.log_success(message, display_pbar=False)
            return _process_org_nactags(nactags)
        else:
            PB.log_failure(message, display_pbar=False)
            CONSOLE.critical(f"No Org Auth Policy Labels found... Exiting...")
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

def _create_nactag(apisession:mistapi.APISession, org_id:str, nactag:dict):
    nactag_data = nactag["data"]
    nactag_newmacs = nactag["newmacs"]
    nactag_name = nactag_data["name"]
    message = f"Creating label {nactag_name} with {len(nactag_newmacs)} MAC(s)"
    try:
        PB.log_message(message)
        resp = mistapi.api.v1.orgs.nactags.createOrgNacTag(
            apisession,
            org_id,
            nactag_data
        )
        if resp.status_code == 200:
            LOGGER.info(f"_create_nac_label:new nactag created with values {resp.data}")
            PB.log_success(message, inc=True)
        else:
            LOGGER.error(
                f"_create_nac_label:unable to create the new "
                f"nactag with values {nactag_data}"
            )
            PB.log_failure(message, inc=True)
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("_create_nac_label:Exception occurred", exc_info=True)

def _update_nactag(apisession:mistapi.APISession, org_id:str, nactag:dict):
    nactag_data = nactag["data"]
    nactag_newmacs = nactag["newmacs"]
    nactag_id = nactag_data["id"]
    nactag_name = nactag_data["name"]
    message = f"Updating label {nactag_name} with {len(nactag_newmacs)} new MAC(s)"
    try:
        PB.log_message(message)
        resp = mistapi.api.v1.orgs.nactags.updateOrgNacTag(
            apisession,
            org_id,
            nactag_id,
            nactag_data
        )
        if resp.status_code == 200:
            LOGGER.info(f"_update_nactag:nactag updated with new values {resp.data}")
            PB.log_success(message, inc=True)
        else:
            LOGGER.error(f"_update_nactag:unable to updated nactag with new values {nactag_data}")
            PB.log_failure(message, inc=True)
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("_update_nactag:Exception occurred", exc_info=True)

def _update_nac_label(
        apisession:mistapi.APISession,
        org_id:str,
        nactags_to_process:dict,
        autocreate:bool
        ):

    PB.log_title("Updating Client List Label")
    for nactag_name in nactags_to_process:
        nactag = nactags_to_process[nactag_name.lower()]
        nactag_data = nactags_to_process[nactag_name.lower()]["data"]
        nactag_newmacs = nactags_to_process[nactag_name.lower()]["newmacs"]
        if len(nactag_newmacs) == 0:
            LOGGER.debug(
                f"_update_nac_label:nactag {nactag_name}. "
                f"Nothing to do"
            )
            message = f"No MAC Address to add to label {nactag_name}"
            PB.log_message(message)
            PB.log_warning(message, inc=True)
        elif nactag_data.get("id"):
            LOGGER.debug(
                f"_update_nac_label:nactag_id is {nactag_data['id']}. "
                f"Will create the label {nactag_name}"
            )
            _update_nactag(apisession, org_id, nactag)
        elif autocreate:
            LOGGER.info(
                f"_update_nac_label:autocreate is set to True. "
                f"Will create the label {nactag_name}"
            )
            _create_nactag(apisession, org_id, nactag)
        else:
            LOGGER.warning(
                f"_update_nac_label:autocreate is set to False. "
                f"Will NOT create the label {nactag_name}"
            )
            PB.log_failure(f"Label {nactag_name} does not exist", inc=True)

def _default_label_menu(nactags_from_mist:dict):
    label_names = []
    for label_name in nactags_from_mist:
        label_names.append(label_name)
    label_names.sort()
    while True:
        i = -1
        print()
        print("Available Labels:")
        for label in label_names:
            i+=1
            print(f"{i}) {label}")
        print()
        resp = input(f"Which default label do you want to apply (0-{i-1}, q to quit)? ")
        if resp == "q":
            sys.exit(0)
        try:
            resp_int = int(resp)
            if resp_int < 0 or resp_int > i:
                LOGGER.warning(f"_default_label_menu:invalid input {resp}. Not in 0-{i-1} range")
                print(f"Invalid input {resp}. Only numbers in 0-{i-1} range are allowed.")
            else:
                return label_names[resp_int]
        except:
            LOGGER.warning(f"_default_label_menu:invalid input {resp}")
            print(f"Invalid input {resp}. Only numbers and \"q\" are allowed.")

def _set_default_label(default_label:str, nactags_from_mist:dict, autocreate:bool):
    if default_label and nactags_from_mist.get(default_label):
        CONSOLE.info(
            f"default label {default_label} already exists "
            f"and will be used"
            )
        LOGGER.info(
            f"_set_default_label:default label {default_label} already exists "
            f"and will be used"
            )
        return default_label
    elif default_label and autocreate:
        CONSOLE.info(
            f"default label {default_label} does not exist "
            f"but autocreate is set to True. {default_label} will be created"
            )
        LOGGER.info(
            f"_set_default_label:default label {default_label} does not exist "
            f"but autocreate is set to True. {default_label} will be created"
            )
        return default_label
    elif default_label:
        CONSOLE.warning(
            f"default label {default_label} does not exist "
            f"and autocreate is set to False. New default value will be asked"
            )
        LOGGER.warning(
            f"_set_default_label:default label {default_label} does not exist "
            f"and autocreate is set to False. New default value will be asked"
            )
    else:
        CONSOLE.warning(
            f"No default label have been configured "
            "New default value will be asked"
            )
        LOGGER.warning(
            f"_set_default_label:No default label have been configured. "
            "New default value will be asked"
            )
    return _default_label_menu(nactags_from_mist)

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
            entries_without_label = 0
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
                        LOGGER.warning(f"_read_csv:label not in CSV file... Will use the default label")                        
                else:
                    entry = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        if field == "label" and column == "":
                            entry[field] = None
                        else:
                            entry[field] = column.lower().strip()
                        i += 1
                    entries.append(entry)
                    if not entry.get("label"):
                        entries_without_label += 1                    
                    LOGGER.debug(f"_read_csv:new entry processed: {entry['mac']} with label {entry.get('label')}")
        PB.log_success(message, display_pbar=False)
        return entries, entries_without_label
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

def _optimize_labels(entries:list, default_label:str, nactags_from_mist:dict):
    nactags_out = {}
    PB.log_title("Optimizing Labels", display_pbar=False)
    print()
    for entry in entries:
        mac = entry["mac"]
        label_name = entry.get("label")
        message = f"MAC Address {mac}"
        PB.log_message(message, display_pbar=False)
        LOGGER.debug(f"_optimize_labels:processing {entry}")

        # if not label set, use the default label
        if not label_name:
            LOGGER.debug(f"_optimize_labels:set label_name to default value {default_label}")
            label_name = default_label

        # if current label has not been added to the out list yet, do it
        if not nactags_out.get(label_name.lower()):
            LOGGER.debug(f"_optimize_labels:generating new out value for label_name {label_name}")
            nactag_mist = nactags_from_mist.get(label_name)
            # if label is already created in Mist
            if nactag_mist:
                LOGGER.debug(f"_optimize_labels:{label_name} already in Mist Cloud")
                if not nactag_mist.get("values"):
                    nactag_mist["values"] = []
            # if label is not yet created in Mist
            else:
                LOGGER.debug(f"_optimize_labels:{label_name} not yet in Mist Cloud")
                nactag_mist = {
                "values": [],
                "name": label_name,
                "type": "match",
                "match": "client_mac"
            }

            nactag_data = {
                "data": nactag_mist,
                "newmacs":[]
            }
            LOGGER.debug(f"_optimize_labels:adding new nactag {label_name.lower()} to out data: {nactag_data}")
            nactags_out[label_name.lower()] = nactag_data

        if not mac in nactags_out[label_name.lower()]["data"]["values"]:
            nactags_out[label_name.lower()]["data"]["values"].append(mac)
            nactags_out[label_name.lower()]["newmacs"].append(mac)
            LOGGER.debug(f"_optimize_labels:{mac} added to {label_name}")
            PB.log_success(message, display_pbar=False)
        else:
            LOGGER.warning(f"_optimize_labels:{mac} is already in {label_name}")
            PB.log_warning(message, display_pbar=False)
    return nactags_out

def start(apisession:mistapi.APISession, org_id:str=None, csv_file:str=None, autocreate:bool=False, default_label:str=None):
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
    default_label : str
        default Label name to use if MAC addresses are not assigned to any label name in the CSV
        file 

    """
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    if not csv_file:
        csv_file = CSV_FILE

    PB.log_title("Preparing data", display_pbar=False)
    print()
    entries, entries_without_label = _read_csv(csv_file)
    nactags_from_mist = _retrieve_org_nactags(apisession, org_id)

    if entries_without_label > 0:
        CONSOLE.info(f"{entries_without_label} mac(s) in the CSV file without label.")
        default_label = _set_default_label(default_label, nactags_from_mist, autocreate)
        print()

    nactags_to_process = _optimize_labels(entries, default_label, nactags_from_mist)

    PB.set_steps_total(len(nactags_to_process))

    _update_nac_label(apisession, org_id, nactags_to_process, autocreate)


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
Example 1:
#mac,label
2E39D54797D9,Label1
636ddded62af,label2
AE2302F109F0,

Example 2:
#mac
2E39D54797D9
636ddded62af
AE2302F109F0

------
CSV Parameters
Required:
- mac               MAC Address of the Wi-Fi client

Optional:
- label             Name of the Label. If not provided, a default label value can be
                    passed in the script parameter with the -d option or will be asked
                    by the script

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
-d, --default=      default Label name to use if MAC addresses are not assigned to 
                    any label name in the CSV file 

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
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:e:l:cd:", [
                                   "help", "org_id=", "file=", "env=", "log_file=", "create", "default="])
    except getopt.GetoptError as err:
        usage(err)

    ORG_ID = None
    AUTOCREATE = False
    DEFAULT_LABEL = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-f", "--file"]:
            CSV_FILE = a
        elif o in ["-c", "--create"]:
            AUTOCREATE = True
        elif o in ["-d", "--default"]:
            DEFAULT_LABEL = a
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
    start(APISESSION, ORG_ID, CSV_FILE, AUTOCREATE, DEFAULT_LABEL)

