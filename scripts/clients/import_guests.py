'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script import or update a list of Guests from a CSV file into a Mist 
Org or Mist Site


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
#mac,ssid
2E39D54797D9,GuestWLAN
636ddded62af,GuestWLAN

Example 2:
#mac,ssid,authorized,email
2E39D54797D9,GuestWLAN,true, user1@test.com,20
636ddded62af,GuestWLAN,False, user2@test.com,60
------
CSV Parameters
Required:
- mac                       MAC Address of the Wi-Fi client
- ssid                      Name of the Guest SSID 

Optional:
- authorized	            boolean (default True), whether the guest is current authorized
- authorized_expiring_time	integer, when the authorization would expire
- name	                    string, optional, the info provided by user
- email	                    string <email>, optional, the info provided by user
- company	                string, optional, the info provided by user
- field1	                string, optional, the info provided by user
- field2	                string, optional, the info provided by user
- field3	                string, optional, the info provided by user
- field4	                string, optional, the info provided by user
- minutes	                integer, minutes, the maximum is 259200 (180 days)

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.
-s, --site_id=      Set the site_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -o/--org_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_guests.py             
python3 ./import_guests.py \
    -f ./import_guests.csv \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''
#### IMPORTS ####
import sys
import csv
import getopt
import logging
import datetime

MISTAPI_MIN_VERSION = "0.44.1"

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
CSV_FILE="./import_guests.csv"
LOG_FILE = "./script.log"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
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

def _create_site_guest(apisession:mistapi.APISession, site_id:str, guests:list):
    PB.log_title("Create Site Guests")
    for guest in guests:
        message = f"create guest {guest['mac']}"
        try:
            PB.log_message(message)
            mac = guest["mac"]
            del guest["mac"]

            # Tmp fix. seems that "authorized_expiring_time" is not usable anymore at the site level. Use the "minutes" field instead
            expire_time = guest.get("authorized_expiring_time")
            if expire_time and not guest.get("minutes"):
                now = datetime.datetime.now().timestamp()
                minutes = (expire_time - now)/60
                guest["minutes"] = minutes

            resp = mistapi.api.v1.sites.guests.updateSiteGuestAuthorization(apisession, site_id, mac, guest)
            if resp.status_code == 200:
                PB.log_success(message, inc=True)
            else:
                PB.log_failure(message, inc=True)
        except Exception as e:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)

def _process_org_wlans(wlans:list):
    data = {}
    for wlan in wlans:
        ssid = wlan["ssid"]
        id = wlan["id"]
        if ssid not in data:
            data[ssid] = [id]
        else:
            data[ssid].append(id)
    return data

def _retrieve_org_wlans(apisession:mistapi.APISession, org_id:str):
    message = f"retrieving Org WLANs"
    try:
        PB.log_message(message)
        resp = mistapi.api.v1.orgs.wlans.listOrgWlans(apisession, org_id)
        wlans = mistapi.get_all(apisession, resp)
        if len(wlans) > 0:
            PB.log_success(message, inc=True)
            return _process_org_wlans(wlans)
        else:
            PB.log_failure(message, inc=True)
            CONSOLE.critical(f"No Org WLANs found... Exiting...")
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)


def _create_org_guest(apisession:mistapi.APISession, org_id:str, guests:list, wlans:dict):
    PB.log_title("Create Org Guests")

    for guest in guests:
        message = f"create guest {guest['mac']}"
        try:
            PB.log_message(message)

            mac = guest["mac"].replace(":", "")
            del guest["mac"]
            
            # Tmp fix. seems that "authorized_expiring_time" is not usable anymore at the site level. Use the "minutes" field instead
            expire_time = guest.get("authorized_expiring_time")
            if expire_time and not guest.get("minutes"):
                now = datetime.datetime.now().timestamp()
                minutes = (expire_time - now)/60
                guest["minutes"] = minutes

            if "ssid" in guest:
                ssid = guest["ssid"]
                del guest["ssid"]
                LOGGER.debug(f"_create_org_guest:looking for the id for WLAN {ssid}")
                wlan_ids = wlans.get(ssid, [])
                if len(wlan_ids)==0:
                    LOGGER.error(f"_create_org_guest:unable to find WLAN {ssid} in the org")
                    PB.log_failure(message, inc=True)
                    break
                elif len(wlan_ids) > 1:
                    LOGGER.error(
                        f"_create_org_guest:too many WLANs with the name {ssid} in the org"
                        )
                    PB.log_failure(message, inc=True)
                    break
                else:
                    LOGGER.debug(f"_create_org_guest:found the id for WLAN {ssid}: {wlan_ids[0]}")
                    guest["wlan_id"] = wlan_ids[0]            
            resp = mistapi.api.v1.orgs.guests.updateOrgGuestAuthorization(apisession, org_id, mac, guest)
            if resp.status_code == 200:
                PB.log_success(message, inc=True)
            else:
                PB.log_failure(message, inc=True)
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
            data = [[c.replace("\ufeff", "") for c in row] for row in data]
            fields = []
            guests = []
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
                    if "ssid" not in fields:
                        LOGGER.critical(f"_read_csv:ssid not in CSV file... Exiting...")
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (SSID not found). "
                            "Please double check it... Exiting..."
                            )
                        sys.exit(255)
                else:
                    guest = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        if field == "mac":
                            guest[field] = column.lower().strip()
                        elif field == "authorized":
                            val = column.lower().strip()
                            if val in ('y', 'yes', 't', 'true', 'on', '1'):
                                guest[field] = True
                            elif val in ('n', 'no', 'f', 'false', 'off', '0'):
                                guest[field] = False
                            else:
                                LOGGER.error(
                                    f"_read_csv:Unable to convert {field} value "
                                    f"({column}) to bool"
                                    )
                                guest[field] = True
                        elif field in ["authorized_expiring_time", "authorized_time"]:
                            try:
                                data = int(column)
                                guest[field] = data
                            except:
                                LOGGER.error(
                                    f"_read_csv:Unable to convert {field} value "
                                    f"({column}) to int"
                                    )
                        else:
                            guest[field] = column.strip()
                        i += 1
                    if "authorized" not in guest:
                        guest["authorized"] = True
                    LOGGER.debug(f"_read_csv:new guest:{guest}")
                    guests.append(guest)
        PB.log_message(message, display_pbar=False)
        return guests
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


def _menu(apisession:mistapi.APISession):
    while True:
        actions = ["ORG level", "SITE level"]
        print("Where do you want to import the Guests:")
        i = 0
        for action in actions:
            print(f"{i}) {action}")
            i += 1
        print()
        resp = input(f"Choice (0-{i}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= len(actions):
                    if actions[resp_num] == "ORG level":
                        org_id = mistapi.cli.select_org(apisession)[0], None
                        LOGGER.debug(f"_menu:selected org_id: {org_id}")
                        return org_id, None
                    elif actions[resp_num] == "SITE level":
                        site_id = mistapi.cli.select_site(apisession)[0]
                        LOGGER.debug(f"_menu:selected site_id: {site_id}")
                        return None, site_id
                    else:
                        LOGGER.error(f"_menu:wrong selection:{resp_num}")
                        print(f"{resp_num} is not part of the possibilities.")
            except:
                LOGGER.error(f"_menu:not number:{resp}")
                print("Only numbers are allowed.")



def start(apisession:mistapi.APISession, org_id:str=None, site_id:str=None, csv_file:str=None):
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
    site_id : str
        site_id where the webhook guests be added. This parameter cannot be used if "org_id"
        is used. If no site_id and not org_id are defined, the script will show a menu to
        select the org/the site.
    csv_file : str
        Path to the CSV file where the guests information are stored. 
        default is "./import_guests.csv"

    """
    if org_id and site_id:
        CONSOLE.critical("Inavlid Parameters: \"org_id\" and site_id\" are exclusive")
    elif not org_id and not site_id:
        org_id, site_id = _menu(apisession)

    if not csv_file:
        csv_file = CSV_FILE

    guests = _read_csv(csv_file)

    PB.set_steps_total(len(guests))

    if org_id:
        wlans = _retrieve_org_wlans(apisession, org_id)
        _create_org_guest(apisession, org_id, guests, wlans)
    elif site_id:
        _create_site_guest(apisession, site_id, guests)



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
Python script import or update a list of Guests from a CSV file into a Mist 
Org or Mist Site


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
#mac,ssid
2E39D54797D9,GuestWLAN
636ddded62af,GuestWLAN

Example 2:
#mac,ssid,authorized,email
2E39D54797D9,GuestWLAN,true, user1@test.com,20
636ddded62af,GuestWLAN,False, user2@test.com,60
------
CSV Parameters
Required:
- mac                       MAC Address of the Wi-Fi client
- ssid                      Name of the Guest SSID 

Optional:
- authorized	            boolean (default True), whether the guest is current authorized
- authorized_expiring_time	integer, when the authorization would expire
- company	                string, optional, the info provided by user
- email	                    string <email>, optional, the info provided by user
- field1	                string, optional, the info provided by user
- field2	                string, optional, the info provided by user
- field3	                string, optional, the info provided by user
- field4	                string, optional, the info provided by user
- minutes	                integer, minutes, the maximum is 259200 (180 days)
- name	                    string, optional, the info provided by user

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.
-s, --site_id=      Set the site_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -o/--org_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_guests.py             
python3 ./import_guests.py \
    -f ./import_guests.csv \
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
        LOGGER.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")

#####################################################################
##### ENTRY POINT ####

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:s:f:e:l:", [
                                   "help", "org_id=", "site_id=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        CONSOLE.error(err)
        usage()

    ORG_ID = None
    SITE_ID = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            if not SITE_ID:
                ORG_ID = a
            else:
                usage(
                    "Inavlid Parameters: \"-o\"/\"--org_id\" "
                    "and \"-s\"/\"--site_id\" are exclusive"
                    )
        elif o in ["-s", "--site_id"]:
            if not ORG_ID:
                SITE_ID = a
            else:
                usage(
                    "Inavlid Parameters: \"-o\"/\"--org_id\" "
                    "and \"-s\"/\"--site_id\" are exclusive"
                    )
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
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    start(apisession, ORG_ID, SITE_ID, CSV_FILE)
    
