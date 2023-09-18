'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to gerenate a Rogue AP report.

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
-s, --site_id=      Set the site_id    
-d, --duration=     Duration (10m, 1h, 1d, 1w)
                    default is 1d
-r, --rogue_types=  Types of rogues to include in the report, comma separated
                    possible values: spoof, lan, honeypot, others    
                    default is spoof,lan,honeypot,others
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"                
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_rogues.py                  
python3 ./report_rogues.py --site_ids=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --duration=4d -r lan,spoof

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

rogue_types = [ "honeypot", "lan", "others", "spoof"]
duration = "1d"
log_file = "./script.log"
csv_delimiter = ","
csv_file = "./report_rogues.csv"
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

def _process_rogues(rogues:list, rogue__type:str, site_name:str, site_id:str):
    for rogue in rogues:
        rogue["type"] = rogue__type
        rogue["site_id"] = site_id
        rogue["site_name"] = site_name
    return rogues

def _get_rogues(mist_session, site_id:str, site_name:str, rogue__type:str, site_rogues:list=[]):
    response = mistapi.api.v1.sites.insights.listSiteRogueAPs(mist_session, site_id, type=rogue__type, limit=1000, duration=duration)
    site_rogues = site_rogues + _process_rogues(response.data["results"], rogue__type, site_name, site_id)
    while response.next:
        response = mistapi.get_next(mist_session, response)
        site_rogues = site_rogues + _process_rogues(response.data["results"], rogue__type, site_name, site_id)
    return site_rogues

def _process_sites(mist_session, site_ids):
    i = 0
    total = len(site_ids) * len(rogue_types)
    rogues = []
    _progress_bar_update(i, total, 50)
    for site_id in site_ids:
        site_name = mistapi.api.v1.sites.sites.getSiteInfo(mist_session, site_id).data["name"]
        for rogue__type in rogue_types:
            rogues = rogues + _get_rogues(mist_session, site_id, site_name, rogue__type)
            i+=1
            _progress_bar_update(i, total, 50)        
    _progress_bar_end(total, 50)
    return rogues

### SAVE REPORT
def _save_as_csv( data:list, duration:int):
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
        csv_writer.writerow([f"#Rogue Report for the last {duration}"])
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

###############################################################################
### USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script gerenates a Rogue AP report.

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
-s, --site_id=      Set the site_id    
-d, --duration=     Duration (10m, 1h, 1d, 1w)
                    default is 1d
-r, --rogue_types=  Types of rogues to include in the report, comma separated
                    possible values: spoof, lan, honeypot, others    
                    default is spoof,lan,honeypot,others
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"                
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_rogues.py                  
python3 ./report_rogues.py --site_ids=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --duration=4d -r lan,spoof

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
        opts, args = getopt.getopt(sys.argv[1:], "hs:d:l:f:c:e:t:r:", ["help", "site_ids=", "duration=", "out_file=", "env=", "log_file=", "rogue_types="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    site_ids=None
    query_params={}
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-s", "--site_ids"]:
            site_ids = a.split(",")
        elif o in ["-d", "--duration"]:
            duration = a
        elif o in ["-r", "--rogue_types"]:
            rogue_types = a.split(",")
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
    if not site_ids:
        site_ids = mistapi.cli.select_site(mist_session, allow_many=True)
    ### START ###
    print(" Process Started ".center(80, '-'))
    data = _process_sites(mist_session, site_ids)


    print(" Process Done ".center(80, '-'))
    mistapi.cli.pretty_print(data)
    _save_as_csv(data, duration)


