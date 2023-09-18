'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generate a report of the application usage on a specific site

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
-s, --site_id=      required for Site reports. Set the site_id    
-d, --duration=     Hours to report
                    default is 96
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_app_usage.csv"            
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_app_usage.py                  
python3 ./report_app_usage.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --duration=48 

'''

#### IMPORTS ####
import logging
import csv
import datetime
import sys
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


#### PARAMETERS #####

log_file = "./script.log"
hours_to_report = 96
csv_delimiter = ","
csv_file = "report_app_usage.csv"
env_file = "~/.mist_env"

#### LOGS ####
logger = logging.getLogger(__name__)
out=sys.stdout

###############################################################################
### PROGRESS BAR
def _progress_bar_update(count:int, total:int, size:int):  
    if total == 0:
        return  
    elif count > total:
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
### FUNCTIONS

def _get_clients_list(mist_session, site_id):
    clients = mistapi.api.v1.sites.stats.listSiteWirelessClientsStats(mist_session, site_id).data
    return clients


def _get_site_name(mist_session, site_id):
    site_info = mistapi.api.v1.sites.sites.getSiteInfo(mist_session, site_id).data
    return site_info["name"]

def _convert_numbers(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    size = round(size, 2)
    return "%s %sB" %(size, power_labels[n])

def _generate_site_report(mist_session, site_name, site_id, start, stop, interval):
    app_usage = []
    clients = _get_clients_list(mist_session, site_id)
    console.info("%s clients to process... Please wait..." %(len(clients)))
    i=0
    _progress_bar_update(0, len(clients), 50)
    for client in clients:
        client_mac = client["mac"]
        if "username" in client: client_username = client["username"]
        else: client_username = ""
        if "hostname" in client: client_hostname = client["hostname"]
        else: client_hostname = ""        
        client_app = mistapi.api.v1.sites.insights.getSiteInsightMetricsForClient(mist_session, site_id, client_mac=client_mac, start=start, end=stop, interval=interval, metric="top-app-by-bytes").data
        tmp={"site name": site_name, "site id": site_id, "client mac": client_mac, "username": client_username, "hostname": client_hostname}
        for app in client_app.get("results", []):
                usage = _convert_numbers(app["total_bytes"])
                tmp[app["app"]] = usage
        i+=1
        _progress_bar_update(i, len(clients), 50)
        app_usage.append(tmp)
    _progress_bar_end(len(clients), 50)
    return app_usage

### SAVE REPORT
def _save_report(app_usage):
    console.info("Saving to file %s..." %(csv_file))
    fields = []
    for row in app_usage:
        for key in row:
            if not key in fields: fields.append(key)

    with open(csv_file, 'w') as output_file:
        dict_writer = csv.DictWriter(output_file, restval="-", fieldnames=fields, delimiter=csv_delimiter)
        dict_writer.writeheader()
        dict_writer.writerows(app_usage)
    console.info("File %s saved!" %(csv_file))

### GENERATE REPORT
def generate_report(mist_session, site_ids, time):
    app_usage = []
    if type(site_ids) == str:
        site_ids = [ site_ids]
    for site_id in site_ids:
        site_name = _get_site_name(mist_session, site_id)
        console.info("Processing site %s (id %s)" %(site_name, site_id))
        app_usage += _generate_site_report(mist_session, site_name, site_id, time["start"], time["stop"], time["interval"])
    mistapi.cli.pretty_print(app_usage)
    _save_report(app_usage)

def _ask_period(hours):
    now = datetime.datetime.now()
    start = round((datetime.datetime.now() - datetime.timedelta(hours=hours)).timestamp(), 0)
    stop = round(now.timestamp(), 0)
    interval =  3600
    return {"start": start, "stop": stop, "interval": interval}

###############################################################################
### USAGE
def usage():
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generate a report of the application usage on a specific site

Requirements:
mistapi: https://pypi.org/project/mistapi/

Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

Options:
-h, --help          display this help
-s, --site_id=      required for Site reports. Set the site_id    
-d, --duration=     Hours to report
                    default is 96
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_app_usage.csv"                
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

Examples:
python3 ./report_app_usage.py                  
python3 ./report_app_usage.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --duration=48 

""")
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
        opts, args = getopt.getopt(sys.argv[1:], "hs:d:f:e:l:", ["help", "site_id=", "duration=", "out_file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    site_id=None
    query_params={}
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-s", "--site_id"]:
            site_id = a
        elif o in ["-d", "--duration"]:
            try:
                hours_to_report = int(a)
            except:
                console.error(f"Duration value \"{a}\" is not valid")
                usage()
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
    mist_session = mistapi.APISession(env_file=env_file)
    mist_session.login()
    if not site_id:
        site_id = mistapi.cli.select_site(mist_session, allow_many=True)
    ### START ###
    time = _ask_period(hours_to_report)
    generate_report(mist_session, site_id, time)
