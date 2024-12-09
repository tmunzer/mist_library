'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to report the firmware deployed on all the SRX for a specified 
org/site with, for each Module:
        - Cluster name
        - Cluster reported Version
        - Module Serial Number
        - Module MAC Address
        - Module Version
        - Module Backup version
        - Module Need Backup (if the Backup Version must be updated)
        - Module Pending version
        - Module Need Reboot (if pending version is present)

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
                    default is "./report_gateway_firmware.csv"                
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_gateway_firmware.py                  
python3 ./report_gateway_firmware.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

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
CSV_FILE = "./report_gateway_firmware.csv"
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
def _process_module(
        cluster_name:str,
        cluster_version:str,
        cluster_device_id:str,
        cluster_site_id:str,
        module:dict,
        data:dict
        ) -> None:
    data.append({
        "cluster_name": cluster_name,
        "cluster_version": cluster_version,            
        "cluster_device_id": cluster_device_id,            
        "cluster_site_id": cluster_site_id,            
        "module_serial": module.get("serial"),
        "module_mac": module.get("mac"),
        "module_version": module.get("version"),
        "module_backup_version": module.get("backup_version"),
        "module_compliance": module.get("version") == module.get("backup_version"),
        "module_pending_version": module.get("pending_version"),
        "module_need_reboot": module.get("pending_version", "") != ""
    })

def _process_gateways(gateways:list) -> list:
    i=0
    data = []
    _progress_bar_update(i, len(gateways), 55)
    for cluster in gateways:
        if True:#"SRX" in cluster.get("version", ""):
            cluster_name = cluster.get("name")
            cluster_version = cluster.get("version")
            cluster_device_id = cluster.get("id")
            cluster_site_id = cluster.get("site_id")
            _process_module(cluster_name, cluster_version, cluster_device_id, cluster_site_id, cluster.get("module_stat", [{}])[0], data)
            if cluster.get("module2_stat"):
                _process_module(cluster_name, cluster_version,  cluster_device_id, cluster_site_id, cluster.get("module2_stat", [{}])[0], data)
        i+=1
        _progress_bar_update(i, len(gateways), 55)
    _progress_bar_end(len(gateways), 55)
    return data

def _get_org_gateways(apisession, org_id:str) -> list:
    print(" Retrieving Gateways ".center(80, '-'))
    response = mistapi.api.v1.orgs.stats.listOrgDevicesStats(apisession, org_id, type="gateway", limit=1000)
    gateways = response.data
    while response.next:
        response = mistapi.get_next(apisession, response)
        gateways = gateways + response.data
    return gateways

def _get_site_gateways(apisession, site_id:str) -> list:
    print(" Retrieving Gateways ".center(80, '-'))
    response = mistapi.api.v1.sites.stats.listSiteDevicesStats(apisession, site_id, type="gateway", limit=1000)
    gateways = response.data
    while response.next:
        response = mistapi.get_next(apisession, response)
        gateways = gateways + response.data
    return gateways

### SAVE REPORT
def _save_as_csv( data:list, scope:str, scope_id:str, csv_file:str):
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
        csv_writer.writerow([f"#Gateways Firmware Backup for {scope} {scope_id}"])
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
### START
def _start(apisession: mistapi.APISession, scope:str, scope_id: str, csv_file:str) -> None:

    if not scope:
        menu = ["org", "site"]
        scope = _show_menu("", menu)
        if scope == "org":
            scope_id = mistapi.cli.select_org(apisession)[0]
        elif scope == "site":
            scope_id = mistapi.cli.select_site(apisession)[0]

    gateways = None
    data = None
    if scope == "org":
        gateways = _get_org_gateways(apisession, scope_id)
    elif scope == "site":
        gateways = _get_site_gateways(apisession, scope_id)
    print(" Processing gateways ".center(80, '-'))
    if gateways:
        data = _process_gateways(gateways)

    if data:
        print(" Process Done ".center(80, '-'))
        _save_as_csv(data, scope, scope_id, csv_file)
        mistapi.cli.pretty_print(data)


###############################################################################
### USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to report the firmware deployed on all the SRX for a specified 
org/site with, for each Module:
        - Cluster name
        - Cluster reported Version
        - Module Serial Number
        - Module MAC Address
        - Module Version
        - Module Backup version
        - Module Need Backup (if the Backup Version must be updated)
        - Module Pending version
        - Module Need Reboot (if pending version is present)

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
                    default is "./report_gateway_firmware.csv"                
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_gateway_firmware.py                  
python3 ./report_gateway_firmware.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

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

    SCOPE=None
    SCOPE_ID=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            if SCOPE:
                console.error("Only one of org_id or site_id can be defined.")
                usage()
            SCOPE = "org"
            SCOPE_ID = a
        elif o in ["-s", "--site_id"]:
            if SCOPE:
                console.error("Only one of org_id or site_id can be defined.")
                usage()
            SCOPE = "site"
            SCOPE_ID = a
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
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    ### START ###
    _start(APISESSION, SCOPE, SCOPE_ID, CSV_FILE)
