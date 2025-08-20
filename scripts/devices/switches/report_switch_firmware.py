'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generates a list of all the switches for a specified org/site
with, for each FPC:
        - VC name
        - VC reported Version
        - FPC Serial Number
        - FPC MAC Address
        - FPC Version
        - FPC Snapshot version
        - FPC Backup version
        - FPC Pending version
        - FPC Compliance (if the snapshot/backup is up to date)

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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_id=      Set the site_id  (only one of the org_id or site_id can be defined)

-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"
-d, --datetime      append the current date and time (ISO format) to the report name
-t, --timestamp     append the current timestamp to the report name

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_switch_firmware.py
python3 ./report_switch_firmware.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

'''

#### IMPORTS #####
import sys
import csv
import datetime
import getopt
import logging

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



#### LOGS ####
LOGGER = logging.getLogger(__name__)
out=sys.stdout

#### PARAMETERS #####
CSV_FILE = "./report_switch_firmware.csv"
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"


###############################################################################
### PROGRESS BAR
def _progress_bar_update(count:int, total:int, size:int):
    if total == 0:
        return
    if count > total:
        count = total
    x = int(size*count/total)
    out.write(f"Progress: ".ljust(10))
    out.write(f"[{'█'*x}{'.'*(size-x)}]")
    out.write(f"{count}/{total}\r".rjust(79 - size - 10))
    out.flush()

def _progress_bar_end(total:int, size:int):
    if total == 0:
        return
    _progress_bar_update(total, total, size)
    out.write("\n")
    out.flush()

###############################################################################
#### FUNCTIONS ####
def _process_fpc(
        vc_name:str,
        vc_version:str,
        vc_device_id:str,
        vc_site_id:str,
        fpc:dict,
        data:list
        ) -> None:
    
    data.append({
        "vc_name": vc_name,
        "vc_version": vc_version,
        "vc_device_id": vc_device_id,
        "vc_site_id": vc_site_id,
        "fpc_serial": fpc.get("serial"),
        "fpc_mac": fpc.get("mac"),
        "fpc_model": fpc.get("model"),
        "fpc_version": fpc.get("version"),
        "fpc_snapshot": fpc.get("recovery_version"),
        "fpc_backup": fpc.get("backup_version"),
        "fpc_need_snapshot": (fpc.get("backup_version") and fpc.get("version") != fpc.get("backup_version")) or (fpc.get("recovery_version") and fpc.get("version") != fpc.get("recovery_version")),
        "fpc_pending": fpc.get("pending_version"),
        "fpc_need_reboot": fpc.get("pending_version", "") != ""
    })
    
def _process_switches(switches:list) -> list:
    i=0
    data = []
    _progress_bar_update(i, len(switches), 55)
    for vc in switches:
        vc_version = vc.get("version")
        vc_name = vc.get("name")
        vc_device_id = vc.get("id")
        vc_site_id = vc.get("site_id")
        for fpc in vc.get("module_stat", []):
            _process_fpc(vc_name, vc_version, vc_device_id, vc_site_id, fpc, data)
        i+=1
        _progress_bar_update(i, len(switches), 55)
    _progress_bar_end(len(vc), 55)
    return data

def _get_org_switches(apisession, org_id:str) -> list:
    print(" Retrieving Switches ".center(80, '-'))
    response = mistapi.api.v1.orgs.stats.listOrgDevicesStats(apisession, org_id, type="switch", limit=1000)
    switches:list = response.data
    while response and response.next:
        response = mistapi.get_next(apisession, response)
        switches.extend(response.data)
    return switches

def _get_site_switches(apisession, site_id:str) -> list:
    print(" Retrieving Switches ".center(80, '-'))
    response = mistapi.api.v1.sites.stats.listSiteDevicesStats(apisession, site_id, type="switch", limit=1000)
    switches:list = response.data
    while response and response.next:
        response = mistapi.get_next(apisession, response)
        switches.extend(response.data)
    return switches

### SAVE REPORT
def _save_as_csv(
        data:list,
        scope:str,
        scope_id:str,
        csv_file:str,
        append_dt:bool,
        append_ts:bool
    ):
    print(" Saving Data ".center(80, "-"))
    print()
    print("Generating CSV Headers ".ljust(80,"."))

    headers=[]
    size = 50
    total = len(data)

    if append_dt:
        dt = datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')
        csv_file = f"{csv_file.replace('.csv', f'_{dt}')}.csv"
    elif append_ts:
        ts = round(datetime.datetime.timestamp(datetime.datetime.now()))
        csv_file = f"{csv_file.replace('.csv', f'_{ts}')}.csv"

    i = 0
    for entry in data:
        for key in entry:
            if key not in headers:
                headers.append(key)
        i += 1
        _progress_bar_update(i, total, size)
    _progress_bar_end(total, size)
    print()
    print("Saving to file ".ljust(80,"."))
    i = 0
    with open(csv_file, "w", encoding='UTF8', newline='') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([f"#Switches snapshot/backup for {scope} {scope_id}"])
        csv_writer.writerow(headers)
        for entry in data:
            tmp=[]
            for header in headers:
                tmp.append(entry.get(header, ""))
            csv_writer.writerow(tmp)
            i += 1
            _progress_bar_update(i, total, size)
        _progress_bar_end(total, size)
        print()
    return headers
####################
## MENU

def _show_menu(header:str, menu:list) -> str:
    print()
    print("".center(80, "-"))
    resp=None
    while True:
        print(f"{header}")
        i=0
        for entry in menu:
            print(f"{i}) {entry}")
            i+=1
        resp = input(f"Please select an option (0-{i-1}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp=int(resp)
                if resp < 0 or resp >= i:
                    console.error(f"Please enter a number between 0 and {i -1}.")
                else:
                    return menu[resp]
            except Exception:
                console.error("Please enter a number\r\n ")

###############################################################################
### START
def _start(
    apisession: mistapi.APISession,
    scope:str,
    scope_id: str,
    csv_file:str,
    append_dt:bool=False,
    append_ts:bool=False,
    ) -> None:

    """
    Start the backup process

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session 
    scope : str, enum: org, site
        At which level the devices must be retrieved
    scope_id : str
        ID of the scope (org_id or site_id) where the devices must be retrieved
    csv_file : str
        define the filepath/filename where to save the data
        default is "./report_switch_firmware.csv"
    append_dt : bool, default = False
        append the current date and time (ISO format) to the backup name 
    append_ts : bool, default = False
        append the timestamp at the end of the report and summary files

    """
    if not scope:
        menu = ["org", "site"]
        scope = _show_menu("", menu)
        if scope == "org":
            scope_id = mistapi.cli.select_org(apisession)[0]
        elif scope == "site":
            scope_id = mistapi.cli.select_site(apisession)[0]

    switches = None
    data = None
    if scope == "org":
        switches = _get_org_switches(apisession, scope_id)
    elif scope == "site":
        switches = _get_site_switches(apisession, scope_id)
    print(" Processing switches ".center(80, '-'))
    if switches:
        data = _process_switches(switches)

    if data:
        print(" Process Done ".center(80, '-'))
        headers = _save_as_csv(data, scope, scope_id, csv_file, append_dt, append_ts)
        mistapi.cli.display_list_of_json_as_table(data, headers)


###############################################################################
### USAGE
def usage(error_message:str=""):
    """
    display usage
    """
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generates a list of all the switches for a specified org/site
with, for each FPC:
        - VC name
        - VC reported Version
        - FPC Serial Number
        - FPC MAC Address
        - FPC Version
        - FPC Snapshot version
        - FPC Backup version
        - FPC Pending version
        - FPC Compliance (if the snapshot/backup is up to date)

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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_id=      Set the site_id  (only one of the org_id or site_id can be defined)

-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"
-d, --datetime      append the current date and time (ISO format) to the report name
-t, --timestamp     append the current timestamp to the report name

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_switch_firmware.py
python3 ./report_switch_firmware.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

''')
    if error_message:
        console.critical(error_message)
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



###############################################################################
### ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:s:f:e:l:td", ["help", "org_id=", "site_id", "out_file=", "env=", "log_file=", "datetime", "timestamp"])
    except getopt.GetoptError as err:
        usage(err.msg)

    SCOPE=""
    SCOPE_ID=""
    APPEND_DT = False
    APPEND_TS = False
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            if SCOPE:
                usage("Invalid Parameters: \"-o\"/\"--org_id\" and \"-s\"/\"--site_id\" are exclusive")
            SCOPE = "org"
            SCOPE_ID = a
        elif o in ["-s", "--site_id"]:
            if SCOPE:
                usage("Invalid Parameters: \"-o\"/\"--org_id\" and \"-s\"/\"--site_id\" are exclusive")
            SCOPE = "site"
            SCOPE_ID = a
        elif o in ["-d", "--datetime"]:
            if APPEND_TS:
                usage("Invalid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                APPEND_DT = True
        elif o in ["-t", "--timestamp"]:
            if APPEND_DT:
                usage("Invalid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                APPEND_TS = True
        elif o in ["-f", "--out_file"]:
            CSV_FILE=a
        elif o in ["-e", "--env"]:
            ENV_FILE=a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a

        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    ### START ###
    _start(APISESSION, SCOPE, SCOPE_ID, CSV_FILE, APPEND_DT, APPEND_TS)
