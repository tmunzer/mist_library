'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script update the sitegroups assigned to sites based on a CSV file. The
script can append the new sitegroups (default) or replace the sitegroups
currently assigned with the new list.


-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the
additional required settings.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Example:
- Example with IDs
#site_id,sitegroup_ids
bd7e048b-a157-4541-81a8-25c06503d13b,"03f5c2fc-aa82-4c74-9d19-31a4e570f395,784f6803-e4b2-46d4-bf1f-23242d6c4e95"
7f99ae5f-2941-4f83-a48a-f5257bb78c42,"114be63a-04a8-4f67-86a4-15074bedef89"

- Example with Names
#site_name,sitegroup_names
"My First Site","Site Group 1, Site Group 2"
"My Second Site","Site Group 3"

-------
CSV Parameters:
Required:
- site_id or site_name
- sitegroup_ids or sitegroup_names

-------
Script Parameters:
-h, --help          display this help
-f, --file=         path to the CSV file
                    default: update_sitegroups.csv

-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)

-a, --auto_creaate  Only works with "sitegroup_names". If set, automaically the site
                    group if the site group name specified in the CSV file doesn't 
                    exist. Otherwise (default), this will trigger a warning message
-r, --replace       If set, the existing site groups will be replaced by the site groups
                    in the CSV file. Otherwise (default), the new site groups will be
                    added to the existing ones

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./update_sitegroups.py
python3 ./update_sitegroups.py -f ./update_sitegroups.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

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

#####################################################################
#### PARAMETERS #####
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
CSV_FILE = "./update_sitegroups.csv"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
# PROGRESS BAR
#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar():
    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count/self.steps_total
        delta = 17
        x = int((size-delta)*percent)
        print("\033[A")
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(self, message: str, result: str, inc: bool = False, size: int = 80, display_pbar: bool = True):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True):
        print()
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def inc(self, size: int = 80):
        self.steps_count += 1
        self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)
        print()

PB = ProgressBar()


#####################################################################
# Site  Management
#####################################################################
def _update_site(apisession: mistapi.APISession, site_info:str, site_id: str, sitegroup_ids:list):
    message = f"Site {site_info}: Updating Site Groups"
    PB.log_message(message)
    try:
        mistapi.api.v1.sites.sites.updateSiteInfo(
            apisession, site_id,
            {"sitegroup_ids": sitegroup_ids}
            )
        PB.log_success(message, True)
    except:
        PB.log_failure(message, True)
        LOGGER.error("_update_site: Exception occurred", exc_info=True)

def _find_mist_site(site_from_csv:dict, sites_from_mist:list, csv_attr:str, mist_attr:str) -> dict:
    mist_site = next((s for s in sites_from_mist if s[mist_attr] == site_from_csv[csv_attr]), None)
    if not mist_site:
        LOGGER.error(f"_find_mist_site: Unable to find the Site {site_from_csv[csv_attr]} in the Mist Org")
    return mist_site

def _process_sites(
        apisession:mistapi.APISession,
        data_from_csv:dict,
        sites_from_mist:list,
        fields:list,
        replace:bool
    ) -> None:
    errors = []
    for site in data_from_csv:
        mist_site = None
        site_info = None
        site_csv_attr = None
        site_mist_attr = None
        message = None

        if "site_name" in fields:
            site_info = site['site_name']
            site_csv_attr = "site_name"
            site_mist_attr = "name"
        else:
            site_info = site['site_id']
            site_csv_attr = "site_id"
            site_mist_attr = "id"
        message = f"Site {site_info}: Processing"
        PB.log_message(message, display_pbar=True)
        mist_site = _find_mist_site(site, sites_from_mist, site_csv_attr, site_mist_attr)
        if not mist_site:
            PB.log_failure(message, inc=True, display_pbar=True)
            continue

        PB.log_success(message, inc=True, display_pbar=True)
        need_update = False
        if replace:
            sitegroup_ids = site["sitegroup_ids"]
            need_update = True
        else:
            sitegroup_ids = mist_site.get("sitegroup_ids", [])
            for sitegroup_id in site["sitegroup_ids"]:
                if not sitegroup_id in sitegroup_ids:
                    LOGGER.debug(f"_process_sites: adding sitegroup_id \"{sitegroup_id}\" to site \"{site_info}\"")
                    sitegroup_ids.append(sitegroup_id)
                    need_update = True
        if need_update:
            _update_site(apisession, site_info, mist_site["id"], sitegroup_ids)
        else:
            PB.log_success(f"Site {site_info}: No update required")




###############################################################################
# SPECIFIC TO SITE GROUPS
def _check_sitegroup_ids(
        sites_from_csv: dict,
        sitegroups_from_mist: dict,
) -> list:
    missing_site_groups = []
    sitegroup_ids_from_mist = []
    for sitegroup_name, sitegroup_id in sitegroups_from_mist.items():
        sitegroup_ids_from_mist.append(sitegroup_id)
    for site in sites_from_csv:
        sitegroup_ids = []
        for sitegroup_id in site.get("sitegroup_ids", []):
            if sitegroup_id in sitegroup_ids_from_mist:
                sitegroup_ids.append(sitegroup_id)
            else:
                missing_site_groups.append(sitegroup_id)
                LOGGER.warning(f"_replace_sitegroup_names: Unable to find sitegroup {sitegroup_id} in Mist and \"autocreate\" is set to False")
        site["sitegroup_ids"] = sitegroup_ids
    return missing_site_groups

def _replace_sitegroup_names(
        apisession: mistapi.APISession,
        org_id: str,
        sites_from_csv: dict,
        sitegroups_from_mist: dict,
        autocreate: bool
    ) -> list:
    missing_site_groups = []
    LOGGER.debug(f"_replace_sitegroup_names: current list of site groups: {sitegroups_from_mist}")
    for site in sites_from_csv:
        sitegroup_ids = []
        for sitegroup_name in site.get("sitegroup_names", []):
            LOGGER.debug(f"_replace_sitegroup_names: searching id for sitegroup \"{sitegroup_name}\"")
            sitegroup_id = sitegroups_from_mist.get(sitegroup_name, None)
            if sitegroup_id:
                LOGGER.debug(f"_replace_sitegroup_names: searching id for sitegroup \"{sitegroup_name}\" is {sitegroup_id}")
                sitegroup_ids.append(sitegroup_id)
            elif autocreate:
                LOGGER.warning(f"_replace_sitegroup_names: sitegroup \"{sitegroup_name}\" not found and autocreate set to True. Will create it")
                new_sitegroup_id = _create_sitegroup(apisession, org_id, sitegroup_name)
                if new_sitegroup_id:
                    LOGGER.debug(f"_replace_sitegroup_names: sitegroup \"{sitegroup_name}\" created. ID is {new_sitegroup_id}")
                    sitegroup_ids.append(new_sitegroup_id)
                    sitegroups_from_mist[sitegroup_name] = new_sitegroup_id
                else:
                    missing_site_groups.append(sitegroup_name)
            else:
                LOGGER.warning(f"_replace_sitegroup_names: sitegroup \"{sitegroup_name}\" not found and autocreate set to False. Will not create it")
                missing_site_groups.append(sitegroup_name)
        site["sitegroup_ids"] = sitegroup_ids
    return missing_site_groups

def _create_sitegroup(
        apisession: mistapi.APISession,
        org_id: str,
        sitegroup_name: str
    ) -> str:
    message = f"Creating sitegroup {sitegroup_name}"
    PB.log_message(message)
    try:
        resp = mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup(apisession, org_id, {"name": sitegroup_name})
        if resp.status_code == 200:
            PB.log_success(message)
            return resp.data.get("id")
        else:
            PB.log_failure(message)
            return None
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("_create_sitegroup:Exception occurred", exc_info=True)
        return None


###############################################################################
# GET FROM MIST

def _retrieve_sitegroups(apisession: mistapi.APISession, org_id: str) -> dict:
    '''
    Get the list of sitegoups
    '''
    sitegroups = {}
    message = f"Retrieving Site Groups from Mist"
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups(
                apisession, org_id)
        if response.status_code == 200:
            data = mistapi.get_all(apisession, response)
            for entry in data:
                sitegroups[entry["name"]] = entry["id"]
            PB.log_success(message, display_pbar=False)
            return sitegroups
        else:
            PB.log_failure(message, display_pbar=False)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)

def _retrieve_sites(apisession: mistapi.APISession, org_id: str) -> dict:
    '''
    Get the list of sites
    '''
    message = f"Retrieving Sites from Mist"
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(
                apisession, org_id)
        if response.status_code == 200:
            data = mistapi.get_all(apisession, response)
            PB.log_success(message, display_pbar=False)
            return data
        else:
            PB.log_failure(message, display_pbar=False)
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)


###############################################################################
# PARSE CSV

###############################################################################
# Required  parameters
# - site_id or site_name
# - sitegroup_ids or sitegroup_names
#

def _extract_groups(data: str) -> list:
    entries = data.split(",")
    result = []
    for entry in entries:
        result.append(entry.strip())
    return result

def _read_csv_file(file_path: str):
    with open(file_path, "r") as f:
        data = csv.reader(f, skipinitialspace=True, quotechar='"')
        data = [[c.replace('\ufeff', '') for c in row] for row in data]
        fields = []
        sites = []
        for line in data:
            if not fields:
                for column in line:
                    fields.append(column.strip().replace("#", ""))
            else:
                site = {}
                i = 0
                for column in line:

                    field = fields[i]
                    if field.startswith("sitegroup_"):
                        column = _extract_groups(column)
                    site[field] = column
                    i += 1
                sites.append(site)

        if "site_name" in fields and "site_id" in fields:
            usage("Only one of \"site_name\" and \"site_id\" can be defined in the CSV file")
        if "sitegroup_names" in fields and "sitegroup_ids" in fields:
            usage("Only sitegroup_names of \"site_name\" and \"sitegroup_ids\" can be defined in the CSV file")

        return sites, fields

###############################################################################
# START
def start(
        apisession: mistapi.APISession,
        file_path: str ="./update_sitegroups.csv",
        org_id: str = None,
        autocreate:bool = False,
        replace: bool = False
    ):
    '''
    Start the process to create the sites

    PARAMS
    -------
    apisession : mistapi.APISession        
        mistapi session with `Super User` access the source Org, already logged in
    file_path : str
        path to the CSV file with all the sites and sitegroups
    org_id : str
        Optional, org_id of the org where to process the sites
    autocreate : bool
        Only works with "sitegroup_names". If set, automaically the site group if
        the site group name specified in the CSV file doesn't exist. Otherwise
        (default), this will trigger a warning message
    replace : bool
        If True, the existing site groups will be replaced by the site groups in
        the CSV file. Otherwise (default is False), the new site groups will be
        added to the existing ones
    '''
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    PB.log_title("Peparing the data", display_pbar=False)
    sites_from_csv, fields = _read_csv_file(file_path)
    PB.set_steps_total(len(sites_from_csv) * 2)

    sites_from_mist = _retrieve_sites(apisession, org_id)
    sitegroups_from_mist = _retrieve_sitegroups(apisession, org_id)
    missing_site_groups = []
    if "sitegroup_names" in fields:
        missing_site_groups = _replace_sitegroup_names(apisession, org_id, sites_from_csv, sitegroups_from_mist, autocreate)
    else:
        missing_site_groups = _check_sitegroup_ids(sites_from_csv, sitegroups_from_mist)
    if missing_site_groups:
        PB.log_title("Missing Site Groups", display_pbar=False)
        print("The following Site Groups were not find in your Mist Organization:")
        for s in missing_site_groups:
            print(f"- {s}")
        resp = input("Do you want to continue? The missing site groups won't be added. (y/N)")
        if resp.lower() != "y":
            sys.exit(0)

    PB.log_title("Processing the sites", display_pbar=False)
    _process_sites(apisession, sites_from_csv, sites_from_mist, fields, replace)

    PB.log_title("Site Import Done", end=True)


###############################################################################
# USAGE
def usage(error:str=None):
    """
    display script usage
    """
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script update the sitegroups assigned to sites based on a CSV file. The
script can append the new sitegroups (default) or replace the sitegroups
currently assigned with the new list.


-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the
additional required settings.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Example:
- Example with IDs
#site_id,sitegroup_ids
bd7e048b-a157-4541-81a8-25c06503d13b,"03f5c2fc-aa82-4c74-9d19-31a4e570f395,784f6803-e4b2-46d4-bf1f-23242d6c4e95"
7f99ae5f-2941-4f83-a48a-f5257bb78c42,"114be63a-04a8-4f67-86a4-15074bedef89"

- Example with Names
#site_name,sitegroup_names
"My First Site","Site Group 1, Site Group 2"
"My Second Site","Site Group 3"

-------
CSV Parameters:
Required:
- site_id or site_name
- sitegroup_ids or sitegroup_names

-------
Script Parameters:
-h, --help          display this help
-f, --file=         path to the CSV file
                    default: update_sitegroups.csv

-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)

-a, --auto_creaate  Only works with "sitegroup_names". If set, automaically the site
                    group if the site group name specified in the CSV file doesn't 
                    exist. Otherwise (default), this will trigger a warning message
-r, --replace       If set, the existing site groups will be replaced by the site groups
                    in the CSV file. Otherwise (default), the new site groups will be
                    added to the existing ones

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./update_sitegroups.py
python3 ./update_sitegroups.py -f ./update_sitegroups.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

''')
    if error:
        console.error(error)
    sys.exit(0)

def check_mistapi_version():
    """
    Function to check the mistapi package version
    """
    mistapi_version = mistapi.__version__.split(".")
    min_version = MISTAPI_MIN_VERSION.split(".")
    if (
        int(mistapi_version[0]) < int(min_version[0])
        or int(mistapi_version[1]) < int(min_version[1])
        or int(mistapi_version[2]) < int(min_version[2])
        ):
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


###############################################################################
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                    "ho:f:e:l:ra",
                                    [
                                        "help",
                                        "org_id=",
                                        "file=",
                                        "env=",
                                        "log_file=",
                                        "replace",
                                        "auto_create"
                                    ]
                                )
    except getopt.GetoptError as err:
        usage(err)

    ORG_ID = None
    REPLACE = False
    AUTOCREATE = False
    PARAMS = {}

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            PARAMS[o]=a
            ORG_ID = a
        elif o in ["-f", "--file"]:
            PARAMS[o]=a
            CSV_FILE = a
        elif o in ["-a", "--auto_create"]:
            PARAMS[o]=True
            AUTOCREATE = True
        elif o in ["-r", "--replace"]:
            PARAMS[o]=True
            REPLACE = True
        elif o in ["-e", "--env"]:
            PARAMS[o]=a
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            PARAMS[o]=a
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    #### LOG SCRIPT PARAMETERS ####
    for param, value in PARAMS.items():
        LOGGER.debug(f"opts: {param} is {value}")
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()

    ### START ###
    start(APISESSION, CSV_FILE, ORG_ID, AUTOCREATE, REPLACE)
