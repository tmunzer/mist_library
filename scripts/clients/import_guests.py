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

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Example:
Example 1:
#mac,wlan_id
2E39D54797D9,46b52093-17fe-408a-98df-51af64f1ce97
636ddded62af,46b52093-17fe-408a-98df-51af64f1ce97

Example 2:
#mac,authorized,email,minutes
2E39D54797D9,true,user1@test.com,20
636ddded62af,False,user2@test.com,60
------
CSV Parameters
Required:
- mac                       MAC Address of the Wi-Fi client

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
- ssid                      string, optional,Name of the Guest SSID 
- wlan_id                   string, optional, the id of the WLAN where the guest is authorized

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file, default is ./import_guests.csv

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
except ImportError:
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
ENV_FILE = "~/.mist_env"
CSV_FILE = "./import_guests.csv"
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
        print("Progress: ", end="")
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
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info("%s", message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()

#####################################################################
# FUNCTIONS


def _process_wlans(wlans: list) -> dict:
    data = {}
    for wlan in wlans:
        ssid = wlan["ssid"]
        wlan_id = wlan["id"]
        if ssid not in data:
            data[ssid] = [wlan_id]
        else:
            data[ssid].append(wlan_id)
    return data


def _update_guest_payload(message: str, guest: dict, wlans: dict) -> dict:

    # Tmp fix. seems that "authorized_expiring_time" is not usable anymore at the site level. Use the "minutes" field instead
    expire_time = guest.get("authorized_expiring_time")
    if expire_time and not guest.get("minutes"):
        now = datetime.datetime.now().timestamp()
        minutes = (expire_time - now)/60
        guest["minutes"] = minutes

    if "ssid" in guest:
        ssid = guest["ssid"]
        del guest["ssid"]
        LOGGER.debug("_replace_guest_wlan:looking for the id for WLAN %s", ssid)
        wlan_ids = wlans.get(ssid, [])
        if len(wlan_ids) == 0:
            LOGGER.error(
                "_replace_guest_wlan:unable to find WLAN %s in the org", ssid)
            PB.log_failure(message, inc=True)
            return {}
        elif len(wlan_ids) > 1:
            LOGGER.error(
                "_replace_guest_wlan:too many WLANs with the name %s in the org", ssid) 
            PB.log_failure(message, inc=True)
            return {}
        else:
            LOGGER.debug(
                "_replace_guest_wlan:found the id for WLAN %s: %s", ssid, wlan_ids[0])
            guest["wlan_id"] = wlan_ids[0]
    return guest


def _retrieve_site_wlans(apisession: mistapi.APISession, site_id: str) -> dict:
    message = "retrieving Site WLANs"
    try:
        PB.log_message(message)
        resp = mistapi.api.v1.sites.wlans.listSiteWlansDerived(
            apisession, site_id)
        wlans = mistapi.get_all(apisession, resp)
        if len(wlans) > 0:
            PB.log_success(message, inc=True)
            return _process_wlans(wlans)
        else:
            PB.log_failure(message, inc=True)
            CONSOLE.critical("No Site WLANs found... Exiting...")
            sys.exit(255)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(255)


def _create_site_guest(apisession: mistapi.APISession, site_id: str, guests: list, wlans: dict) -> None:
    PB.log_title("Create Site Guests")
    for guest in guests:
        message = f"create guest {guest['mac']}"
        try:
            PB.log_message(message)
            mac = guest["mac"]
            del guest["mac"]

            guest_payload = _update_guest_payload(message, guest, wlans)

            if guest_payload:
                resp = mistapi.api.v1.sites.guests.updateSiteGuestAuthorization(
                    apisession, site_id, mac, guest_payload)
                if resp.status_code == 200:
                    PB.log_success(message, inc=True)
                else:
                    PB.log_failure(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)


def _retrieve_org_wlans(apisession: mistapi.APISession, org_id: str) -> dict:
    message = "retrieving Org WLANs"
    try:
        PB.log_message(message)
        resp = mistapi.api.v1.orgs.wlans.listOrgWlans(apisession, org_id)
        wlans = mistapi.get_all(apisession, resp)
        if len(wlans) > 0:
            PB.log_success(message, inc=True)
            return _process_wlans(wlans)
        else:
            PB.log_failure(message, inc=True)
            CONSOLE.critical("No Org WLANs found... Exiting...")
            sys.exit(255)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(255)


def _create_org_guest(apisession: mistapi.APISession, org_id: str, guests: list, wlans: dict) -> None:
    PB.log_title("Create Org Guests")

    for guest in guests:
        message = f"create guest {guest['mac']}"
        try:
            PB.log_message(message)

            mac = guest["mac"].replace(":", "")
            del guest["mac"]

            guest_payload = _update_guest_payload(message, guest, wlans)

            if guest_payload:
                resp = mistapi.api.v1.orgs.guests.updateOrgGuestAuthorization(
                    apisession, org_id, mac, guest_payload)
                if resp.status_code == 200:
                    PB.log_success(message, inc=True)
                else:
                    PB.log_failure(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)


def _read_csv(csv_file: str) -> list:
    message = "Processing CSV File"
    try:
        PB.log_message(message, display_pbar=False)
        LOGGER.debug("_read_csv:opening CSV file %s", csv_file)
        with open(csv_file, "r", encoding="utf-8") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            data = [[c.replace("\ufeff", "") for c in row] for row in data]
            fields = []
            guests = []
            for line in data:
                LOGGER.debug("_read_csv:new csv line:%s", line)
                if not fields:
                    for column in line:
                        fields.append(column.replace("#", "").strip())
                    LOGGER.debug("_read_csv:detected CSV fields: %s", fields)
                    if "mac" not in fields:
                        LOGGER.critical(
                            "_read_csv:mac address not in CSV file... Exiting...")
                        PB.log_failure(message, display_pbar=False)
                        CONSOLE.critical(
                            "CSV format invalid (MAC Address not found). "
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
                                    "_read_csv:Unable to convert %s value (%s) to bool", field, column
                                )
                                guest[field] = True
                        elif field in ["authorized_expiring_time", "authorized_time"]:
                            try:
                                data = int(column)
                                guest[field] = data
                            except Exception:
                                LOGGER.error(
                                    "_read_csv:Unable to convert %s value (%s) to int", field, column
                                )
                        else:
                            guest[field] = column.strip()
                        i += 1
                    if "authorized" not in guest:
                        guest["authorized"] = True
                    LOGGER.debug("_read_csv:new guest:%s", guest)
                    guests.append(guest)
        PB.log_message(message, display_pbar=False)
        return guests
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(255)


def _menu(apisession: mistapi.APISession) -> tuple[str, str]:
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
                        org_id = mistapi.cli.select_org(apisession)[0]
                        LOGGER.debug("_menu:selected org_id: %s", org_id)
                        return org_id, ""
                    elif actions[resp_num] == "SITE level":
                        site_id = mistapi.cli.select_site(apisession)[0]
                        LOGGER.debug("_menu:selected site_id: %s", site_id)
                        return "", site_id
                    else:
                        LOGGER.error("_menu:wrong selection:%s", resp_num)
                        print(f"{resp_num} is not part of the possibilities.")
            except Exception:
                LOGGER.error("_menu:not number:%s", resp)
                print("Only numbers are allowed.")


def start(apisession: mistapi.APISession, org_id: str = "", site_id: str = "", csv_file: str = ""):
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
        CONSOLE.critical(
            "Invalid Parameters: \"org_id\" and site_id\" are exclusive")
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
        wlans = _retrieve_site_wlans(apisession, site_id)
        _create_site_guest(apisession, site_id, guests, wlans)


###############################################################################
# USAGE
def usage(error_message: str | None = None):
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

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Example:
Example 1:
#mac,wlan_id
2E39D54797D9,46b52093-17fe-408a-98df-51af64f1ce97
636ddded62af,46b52093-17fe-408a-98df-51af64f1ce97

Example 2:
#mac,authorized,email,minutes
2E39D54797D9,true,user1@test.com,20
636ddded62af,False,user2@test.com,60
------
CSV Parameters
Required:
- mac                       MAC Address of the Wi-Fi client

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
- ssid                      string, optional,Name of the Guest SSID 
- wlan_id                   string, optional, the id of the WLAN where the guest is authorized

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file, default is ./import_guests.csv

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
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__
        )

#####################################################################
#####  ENTRY POINT ####


if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:s:f:e:l:", [
                                   "help", "org_id=", "site_id=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        CONSOLE.error(err)
        usage()

    ORG_ID = ""
    SITE_ID = ""
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
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, SITE_ID, CSV_FILE)
