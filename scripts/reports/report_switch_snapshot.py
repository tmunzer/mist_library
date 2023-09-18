'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to gerenates a list of all the switches for a specified org/site
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

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_id=      Set the site_id  (only one of the org_id or site_id can be defined)
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"                
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_switch_snapshot.py                  
python3 ./report_switch_snapshot.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''

#### IMPORTS #####
import sys
import csv
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
logger = logging.getLogger(__name__)
out=sys.stdout

#### PARAMETERS #####
csv_file = "./report_switch_snapshot.csv"
log_file = "./script.log"
env_file = "~/.mist_env"


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

def _process_switches(switches:list) -> list:
    i=0
    data = []
    _progress_bar_update(i, len(switches), 55)
    for switch in switches:
        version = switch.get("version")
        name = switch.get("name")
        for fpc in switch.get("module_stat", []):
            fpc_serial = fpc.get("serial")
            fpc_mac = fpc.get("mac")
            fpc_version = fpc.get("version")
            fpc_snapshot = fpc.get("recovery_version")
            fpc_backup = fpc.get("backup_version")
            fpc_pending = fpc.get("pending_version")
            if version == fpc_snapshot or version == fpc_backup:
                fpc_compliance = True
            else:
                fpc_compliance = False
            data.append({
                "vc_name": name,
                "vc_version": version,            
                "fpc_serial": fpc_serial,
                "fpc_mac": fpc_mac,
                "fpc_version": fpc_version,
                "fpc_snapshot": fpc_snapshot,
                "fpc_backup": fpc_backup,
                "fpc_pending": fpc_pending,
                "fpc_compliance": fpc_compliance
            })
        i+=1
        _progress_bar_update(i, len(switches), 55)
    _progress_bar_end(len(switch), 55)
    return data

def _get_org_switches(apisession, org_id:str) -> list:
    print(" Retrieving Switches ".center(80, '-'))
    response = mistapi.api.v1.orgs.stats.listOrgDevicesStats(apisession, org_id, type="switch", limit=1000)
    switches = response.data
    while response.next:
        response = mistapi.get_next(apisession, response)
        switches = switches + response.data
    return switches

def _get_site_switches(apisession, site_id:str) -> list:
    print(" Retrieving Switches ".center(80, '-'))
    response = mistapi.api.v1.sites.stats.listSiteDevicesStats(apisession, site_id, type="switch", limit=1000)
    switches = response.data
    while response.next:
        response = mistapi.get_next(apisession, response)
        switches = switches + response.data
    return switches

### SAVE REPORT
def _save_as_csv( data:list, scope:str, scope_id:str):
    headers=[]    
    size = 50
    total = len(data)
    print(" Saving Data ".center(80, "-"))
    print()
    print("Generating CSV Headers ".ljust(80,"."))
    i = 0
    for entry in data:
        for key in entry:
            if not key in headers:
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
            except:
                console.error("Please enter a number\r\n ")

###############################################################################
### USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to gerenates a list of all the switches for a specified org/site
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

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_id=      Set the site_id  (only one of the org_id or site_id can be defined)
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"                
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_switch_snapshot.py                  
python3 ./report_switch_snapshot.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

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



###############################################################################
### ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:s:f:e:l:", ["help", "org_id=", "site_id", "out_file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    scope=None
    scope_id=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            if scope:
                console.error("Only one of org_id or site_id can be defined.")
                usage()
            scope = "org"
            scope_id = a
        elif o in ["-s", "--site_id"]:
            if scope:
                console.error("Only one of org_id or site_id can be defined.")
                usage()
            scope = "site"
            scope_id = a
        elif o in ["-f", "--out_file"]:
            csv_file=a    
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
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    ### SCOPE SELECTION ###
    if not scope:
        menu = ["org", "site"]
        scope = _show_menu("", menu)
        if scope == "org":
            scope_id = mistapi.cli.select_org(apisession)[0]
        elif scope == "site":
            scope_id = mistapi.cli.select_site(apisession)[0]
    ### START ###
    if scope == "org":
        switches = _get_org_switches(apisession, scope_id)
    elif scope == "site":
        switches = _get_site_switches(apisession, scope_id)
    print(" Processing Switcches ".center(80, '-'))
    data = _process_switches(switches)


    print(" Process Done ".center(80, '-'))
    _save_as_csv(data, scope, scope_id)
    mistapi.cli.pretty_print(data)