'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list all Access Points from orgs/sites and their associated BSSIDs, 
and save it to a CSV file. You can configure which fields you want to retrieve/save,
and where the script will save the CSV file.

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
-s, --site_ids=     list of sites to use, comma separated
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_bssids.py                  
python3 ./report_bssids.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''

#### IMPORTS #####
import sys
import logging
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
csv_separator = ","
fields = ["map_id", "id", "name", "ip", "model", "radio_stat.band_24.mac", "radio_stat.band_5.mac" , "radio_stat.band_6.mac" ]
csv_file = "./report_bssids.csv"

org_ids = []
site_ids = []

log_file = "./script.log"
env_file = "~/.mist_env"

#### GLOBAL VARIABLES ####
bssid_list = []

#### LOGS ####
logger = logging.getLogger(__name__)
out=sys.stdout

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
def extract_field(json_data, field):   
    split_field = field.split(".")
    cur_field = split_field[0]
    next_fields = ".".join(split_field[1:])
    if cur_field in json_data:
        if len(split_field) > 1:
            return extract_field(json_data[cur_field], next_fields)
        else:
            return json_data[cur_field] 
    else:
        return "N/A"

def bssids_from_sites(mist_session, sites, site_ids):
    i = 0
    _progress_bar_update(i, len(sites), 55)
    for site in sites:
        if len(org_ids) > 1 or site["id"] in site_ids:     
            response = mistapi.api.v1.sites.stats.listSiteDevicesStats(mist_session, site["id"], limit=1000)
            devices = response.data
            while response.next:
                response = mistapi.get_next(mist_session, response)
                devices += response.data
            for site_device in devices:
                device_stat = []            
                device_stat.append(site["id"])           
                device_stat.append(site["name"])     
                for field in fields:
                    field_data = extract_field(site_device, field)   
                    if (field == "radio_stat.band_24.mac" or field == "radio_stat.band_5.mac" or field == "radio_stat.band_6.mac") and not field_data == "N/A":
                        mac_start = field_data
                        mac_end = field_data[:-1] + "f"
                        device_stat.append("%s to %s" %(mac_start, mac_end))
                    else:
                        device_stat.append(field_data)                      
                bssid_list.append(device_stat)
        i+=1
        _progress_bar_update(i, len(sites), 55)
    _progress_bar_end(len(sites), 55)

def bssids_from_orgs(mist_session, org_id, site_ids):    
    org_sites = [privilege for privilege in mist_session.privileges if privilege.get("org_id") == org_id]
    # the admin only has access to the org information if he/she has this privilege 
    if len(org_sites) >= 1 and org_sites[0]["scope"] == "org":
        org_sites = mistapi.api.v1.orgs.sites.listOrgSites(mist_session, org_id).data
        bssids_from_sites(mist_session, org_sites, site_ids)        
    # if the admin doesn't have access to the org level, but only the sites
    elif len(org_sites) >= 1:
        org_sites = []
        # get the sites information
        for site_id in site_ids:
            org_sites.append(mistapi.api.v1.sites.sites.getSiteInfo(mist_session, site_id).data)
        bssids_from_sites(mist_session, org_sites, site_ids)        


###############################################################################
### USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list all Access Points from orgs/sites and their associated BSSIDs, 
and save it to a CSV file. You can configure which fields you want to retrieve/save,
and where the script will save the CSV file.

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
-s, --site_ids=     list of sites to use, comma separated
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_bssids.py                  
python3 ./report_bssids.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 


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
        opts, args = getopt.getopt(sys.argv[1:], "ho:s:e:l:", ["help", "org_id=", "site_ids=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id=None
    site_ids=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-s", "--site_ids"]:
            site_ids = a.split(",")
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

    if not org_id:
        org_id = mistapi.cli.select_org(apisession)
        site_ids = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=True)
    if not site_ids:
        site_ids = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=True)

    bssids_from_orgs(apisession, org_id, site_ids)
 
    fields.insert(0, "site_id")
    fields.insert(1, "site_name")

    mistapi.cli.pretty_print(bssid_list, fields)
    mistapi.cli.save_to_csv(csv_file, bssid_list, fields, csv_separator)