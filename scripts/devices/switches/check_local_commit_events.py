"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
This script can be used to retrieve and save into a file the CLI Commit events
(commit done localy one the switches) for all the switches belonging to a Mist 
Organization.

The script is automatically retrieving the list of sites with managed switches,
then it is retrieving the commit events for each site, and saving the CLI 
commit events into a file. 
The script is createing a dedicated folder for each Mist Org (based on the 
org_id), one sub folder for each site with managed switches withing the org
(based on the site_id), and then one file for each switch with local commit
events (based on the switch MAC address).

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
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.
-d, --duration=     retrieve the CLI commits for the specified duration (e.g. 1h, 1d,
                    7d, 30d). 
                    WARNING: There is no validation on the value, please check the
                    MIST API documentation for more information. Wrong format may 
                    result in empty results.
                    default: 7d
                    maximum: 30d

-f, --folder=       folder where to save the files. The script will create a subfolder
                    with the org_id then one subfolder per site, and one file per
                    switch with CLI commit events in the subfolder.
                    If the folder doesn't exists, it will be created.
                    default: "./cli_commit_events"

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./check_local_commit_events.py             
python3 ./check_local_commit_events.py \
    -d 1w \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 
"""

#### IMPORTS ####
import os
import sys
import getopt
import logging

MISTAPI_MIN_VERSION = "0.52.2"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
except:
    print(
        """
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)

#### PARAMETERS #####
ENV_FILE = "~/.mist_env"
CSV_FILE = "./update_port_config.csv"
LOG_FILE = "./script.log"

###############################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


###############################################################################
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
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}")
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


###############################################################################
# FUNCTION
def _find_sites(apisession: mistapi.APISession, org_id: str) -> list:
    """
    Find all the sites from the org with Managed switches

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where the webhook guests be added. This parameter cannot be used if "site_id"
        is used. If no org_id and not site_id are defined, the script will show a menu to
        select the org/the site.

    RETURNS
    -------
    list:
        list of site_id where there is at list one managed switch
    """
    site_ids = []
    try:
        message = "Retrieving the Sites with managed switches"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.devices.countOrgDevices(
            apisession, org_id, distinct="site_id", managed="true", limit=1000
        )
        if resp.status_code == 200:
            results = mistapi.get_all(apisession, resp)
            for site in results:
                if site.get("site_id") != "00000000-0000-0000-0000-000000000000":
                    site_ids.append(site.get("site_id"))
            PB.log_success(message, display_pbar=False)
            return site_ids
        else:
            PB.log_failure(message, display_pbar=False)
            sys.exit(100)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(100)


def _find_events(apisession: mistapi.APISession, site_id: str, duration: str) -> list:
    """
    Find all the cli commit events from the org

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where the webhook guests be added. This parameter cannot be used if "site_id"
        is used. If no org_id and not site_id are defined, the script will show a menu to
        select the org/the site.

    RETURNS
    -------
    list:
        list of the cli commit events
    """
    try:
        message = f"Site {site_id}: retrieving CLI Commit Events"
        PB.log_message(message,  display_pbar=True)
        resp = mistapi.api.v1.sites.devices.searchSiteDeviceEvents(
            apisession, site_id, type="SW_CONFIGURED", limit=1000, duration=duration
        )
        if resp.status_code == 200:
            results = mistapi.get_all(apisession, resp)
            PB.log_success(message, inc=True, display_pbar=True)
            return results
        else:
            PB.log_failure(message, inc=True, display_pbar=True)
            sys.exit(100)
    except:
        PB.log_failure(message, inc=True, display_pbar=True)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(100)


def _process_events(events: list, site_id: str) -> dict:
    cli_events = {}
    message = f"Site {site_id}: processing CLI Commit Events"
    PB.log_message(message,  display_pbar=True)
    for event in events:
        if event.get("commit_method") == "cli":
            config_diff = event.get("config_diff", "unknown")
            text = event.get("text", "unknown")
            timestamp = event.get("timestamp")
            mac = event.get("mac")
            commit_user = event.get("commit_user")
            version = event.get("version")
            if not cli_events.get(mac):
                cli_events[mac] = []
            cli_events[mac].append(
                {
                    "config_diff": config_diff,
                    "result": text,
                    "timestamp": timestamp,
                    "commit_user": commit_user,
                    "version": version,
                }
            )
    PB.log_success(message, inc=True, display_pbar=True)
    return cli_events


def _save_events(events: dict, site_id: str) -> None:
    if len(events) > 0:
        message = f"Site {site_id}: saving CLI Commit Events"
        PB.log_message(message,  display_pbar=True)
        try:
            if not os.path.exists(site_id):
                os.makedirs(site_id)
            for mac, switch_events in events.items():
                file_path = f"./{site_id}/{mac}"
                sorted_switch_events = sorted(switch_events, key=lambda d: d["timestamp"], reverse=True)
                with open(file_path, 'w') as f:
                    for e in sorted_switch_events:
                        f.write(f"-------------- commit at {e.get('timestamp')} - user {e.get('commit_user')} --------------\n")
                        f.write(e.get("config_diff"))
                        f.write("\n-\n")
                        f.write(f"result: {e.get('result')}\n\n")
        except Exception as e:
            PB.log_failure(message, inc=True, display_pbar=True)
            LOGGER.error("Exception occurred", exc_info=True)
            return
    else:
        message = f"Site {site_id}: no CLI Commit Events to save"
        PB.log_message(message,  display_pbar=True)
    PB.log_success(message,  inc=True, display_pbar=True)


def _check_folder(folder: str, org_id: str) -> None:
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.chdir(folder)
        if not os.path.exists(org_id):
            os.makedirs(org_id)
        os.chdir(org_id)
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(200)


def _processing_sites(
    apisession: mistapi.APISession,
    org_id: str,
    site_ids: list,
    duration: str = "7d",
    folder: str = "./cli_commit_events",
) -> None:
    _check_folder(folder, org_id)
    for site_id in site_ids:
        events = _find_events(apisession, site_id, duration)
        cli_events = _process_events(events, site_id)
        _save_events(cli_events, site_id)

###############################################################################
# START
def start(
    apisession: mistapi.APISession,
    org_id: str = None,
    duration: str = "7d",
    folder: str = "./cli_commit_events",
):
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
    duration: str, default: 7d
        retrieve the CLI commits for the specified duration (e.g. 1h, 1d, 7d, 30d), max: 30d
        WARNING: There is no validation on the value, please check the MIST API documentation
        for more information. Wrong format may result in empty results.
    folder: str, default: "./cli_commit_events"
        folder where to save the files. The script will create a subfolder with the org_id then
        one subfolder per site, and one file per switch with CLI commit events in the subfolder.
        If the folder doesn't exists, it will be created.
    """
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    site_ids = _find_sites(apisession, org_id)
    PB.set_steps_total(len(site_ids) * 3)
    _processing_sites(apisession, org_id, site_ids, duration, folder)


###############################################################################
# USAGE
def usage(error_message: str = None):
    """
    show script usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
This script can be used to retrieve and save into a file the CLI Commit events
(commit done localy one the switches) for all the switches belonging to a Mist 
Organization.

The script is automatically retrieving the list of sites with managed switches,
then it is retrieving the commit events for each site, and saving the CLI 
commit events into a file. 
The script is createing a dedicated folder for each Mist Org (based on the 
org_id), one sub folder for each site with managed switches withing the org
(based on the site_id), and then one file for each switch with local commit
events (based on the switch MAC address).

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
-h, --help          display this help
-f, --file=         OPTIONAL: path to the CSV file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.
-d, --duration=     retrieve the CLI commits for the specified duration (e.g. 1h, 1d,
                    7d, 30d). 
                    WARNING: There is no validation on the value, please check the
                    MIST API documentation for more information. Wrong format may 
                    result in empty results.
                    default: 7d
                    maximum: 30d

-f, --folder=       folder where to save the files. The script will create a subfolder
                    with the org_id then one subfolder per site, and one file per
                    switch with CLI commit events in the subfolder.
                    If the folder doesn't exists, it will be created.
                    default: "./cli_commit_events"

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./check_local_commit_events.py             
python3 ./check_local_commit_events.py \
    -d 1w \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 
"""
    )
    if error_message:
        CONSOLE.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """
    check the current version of the mistapi package
    """
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        LOGGER.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, '
            f"you are currently using version {mistapi.__version__}."
        )


#####################################################################
##### ENTRY POINT ####

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:d:f:e:l",
            ["help", "org_id=", "duration=", "folder=", "env=", "log_file="],
        )
    except getopt.GetoptError as err:
        CONSOLE.error(err)
        usage()

    ORG_ID = None
    DURATION = "7d"
    FOLDER = "./cli_commit_events"
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-d", "--duration"]:
            DURATION = a
        elif o in ["-f", "--folder"]:
            FOLDER = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    start(apisession, ORG_ID, DURATION, FOLDER)
