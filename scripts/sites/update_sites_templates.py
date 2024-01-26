'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script update the templates assigned to Mist Sites based on a CSV file, 
and/or update the auto assignment rules based on IP Subnet.

WARNING: if a template type is set in the CSV file, but it's value is empty, it 
will push is as-is to the site (and potentially remove the configured template)
If you don't need a type of template, DO NOT add it in the CSV file.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the 
additional required settings.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates it is possible to use the object name OR the object id (this
must be defined in the first line, by appending "_name" or "_id"). In case both name and id
are defined, the name will be used.

-------
CSV Example:
#site_name,rftemplate_id,networktemplate_name,gatewaytemplate_name
Juniper France,39ce2...ab5ee,ex-lab,test

-------
CSV Parameters:
Required:
- site_name

Optional:
- alarmtemplate_id or alarmtemplate_name
- aptemplate_id or aptemplate_name
- gatewaytemplate_id or gatewaytemplate_name
- networktemplate_id or networktemplate_name
- rftemplate_id or rftemplate_name
- secpolicy_id or secpolicy_name
- sitetemplate_id or sitetemplate_name
- subnet                                    if set, will add this subnet in the
                                            auto assignment rules to automatically 
                                            assign the APs deployed on this subnet
                                            to this site

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file

-o, --org_id=       Set the org_id
-n, --org_name=     Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value   

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_sites.py -f ./my_new_sites.csv                 
python3 ./import_sites.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

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

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####
PARAMETER_TYPES = [
    "site",
    "alarmtemplate",
    "aptemplate",
    "gatewaytemplate",
    "networktemplate",
    "rftemplate",
    "secpolicy",
    "sitetemplate"
]
GEOLOCATOR = None
TZFINDER = None
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

pb = ProgressBar()

#####################################################################
# Auto Assignment Rules
#####################################################################
def _get_current_org_config(apisession:mistapi.APISession, org_id:str):
    message = "Retrieving current Org Rules"
    pb.log_message(message, display_pbar=False)
    try:
        res = mistapi.api.v1.orgs.setting.getOrgSettings(apisession, org_id)
        if res.status_code == 200:
            pb.log_success(message, inc=True)
            auto_site_assignment = res.data.get("auto_site_assignment", {"enable": True})
            return auto_site_assignment
        else:
            pb.log_failure(message, inc=True)
    except:
        pb.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

def _set_new_org_config(apisession:mistapi.APISession, org_id:str, auto_site_assignment:dict):
    message = "Updating Org Rules"
    pb.log_message(message, display_pbar=False)
    try:
        res = mistapi.api.v1.orgs.setting.updateOrgSettings(apisession, org_id, {"auto_site_assignment": auto_site_assignment})
        if res.status_code == 200:
            pb.log_success(message, inc=True)
        else:
            pb.log_failure(message, inc=True)
    except:
        pb.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

def _compare_rules(org_rules:list, new_rules:list):
    errors = []
    if not org_rules:
        org_rules = []
    for rule in new_rules:
        message = f"Checking subnet {rule.get('subnet')}"
        pb.log_message(message)
        try:
            subnet_exists = list(r for r in org_rules if r.get("subnet") == rule.get("subnet"))
            if subnet_exists:
                LOGGER.warning(
                    f"_compare_rules:subnet {rule.get('subnet')} configured for site {rule.get('value')} already exists: {subnet_exists}"
                    )
                errors.append(
                    f"subnet {rule.get('subnet')} configured for site {rule.get('value')} already exists: {subnet_exists}"
                    )
            else:
                org_rules.append(rule)
        except:
            LOGGER.error("Exception occurred", exc_info=True)
            errors.append(
                f"error when processing subnet {rule.get('subnet')} configured for site {rule.get('value')}"
                )
    if errors:
        pb.log_warning(message, inc=True)
    return org_rules


def _update_org_rules(apisession:mistapi.APISession, org_id:str, new_rules:list):
    pb.log_title("Updating Autoprovisioning Rules")
    auto_site_assignment = _get_current_org_config(apisession, org_id)
    auto_site_assignment["rules"] = _compare_rules(auto_site_assignment.get("rules", {}), new_rules)
    _set_new_org_config(apisession, org_id, auto_site_assignment)


#####################################################################
# Site  Management
#####################################################################
def _update_sites(apisession: mistapi.APISession, sites: list, parameters: dict):
    '''
    Function to create and update all the sites
    '''
    pb.log_title("Updating Sites", display_pbar=True)
    for site in sites:
        site_name = site["site_name"]
        message = f"Updating site {site_name}"
        pb.log_message(message)
        site_id = parameters["site"].get(site_name)
        site = _replace_object_names_by_ids(site, parameters)
        if not site_id:
            pb.log_failure(message, True)
            LOGGER.error(f"_update_sites:unable to find site with name {site_name} in the Org. Skipping...")
        else:
            try:
                res = mistapi.api.v1.sites.sites.updateSiteInfo(apisession, site_id, site)
                if res.status_code == 200:
                    pb.log_success(message, True)
                else:
                    pb.log_failure(message, True)
            except:
                LOGGER.error("Exception occurred", exc_info=True)
                pb.log_failure(message, True)

###############################################################################
# MATCHING OBJECT NAME / OBJECT ID
###############################################################################
def _replace_object_names_by_ids(site: dict, parameters: dict) -> dict:
    '''
    replace the template/policy/groups names by the corresponding ids
    '''
    warning = False
    message = f"Site {site['site_name']}: updating IDs"
    pb.log_message(message)

    for parameter in PARAMETER_TYPES:
        try:
            if f"{parameter}_name" in site:
                if site[f"{parameter}_name"] == "":
                    site[f"{parameter}_id"] = None
                else:
                    name = site[f"{parameter}_name"]
                    site[f"{parameter}_id"] = parameters[parameter][name]
                del site[f"{parameter}_name"]
        except:
            warning = True
            pb.log_warning(
                f"{parameter.capitalize()} Name {site[f'{parameter}_name']} not found in the org", inc=False)
    if not warning:
        pb.log_success(message, True)
    else:
        pb.log_warning(message, True)
    return site

# GET FROM MIST
def _retrieve_objects(apisession: mistapi.APISession, org_id: str, parameters_in_use:list) -> dict:
    '''
    Get the list of the current templates, policies and sitegoups
    '''
    parameters = {}
    for parameter_type in parameters_in_use:
        message = f"Retrieving {parameter_type} from Mist"
        pb.log_message(message, display_pbar=False)
        parameter_values = {}
        data = []
        response = None
        try:
            if parameter_type == "site":
                response = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id)
            if parameter_type == "alarmtemplate":
                response = mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates(
                    apisession, org_id)
            elif parameter_type == "aptemplate":
                response = mistapi.api.v1.orgs.aptemplates.listOrgAptemplates(
                    apisession, org_id)
            elif parameter_type == "gatewaytemplate":
                response = mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates(
                    apisession, org_id)
            elif parameter_type == "networktemplate":
                response = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(
                    apisession, org_id)
            elif parameter_type == "rftemplate":
                response = mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates(
                    apisession, org_id)
            elif parameter_type == "secpolicy":
                response = mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies(
                    apisession, org_id)
            elif parameter_type == "sitetemplate":
                response = mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates(
                    apisession, org_id)
            data = mistapi.get_all(apisession, response)
            for entry in data:
                parameter_values[entry["name"]] = entry["id"]
            parameters[parameter_type] = parameter_values
            pb.log_success(message, display_pbar=False)
        except:
            pb.log_failure(message, display_pbar=False)
            LOGGER.error("Exception occurred", exc_info=True)
    return parameters

###############################################################################
# Optional site parameters (if id and name is defined, the name will
# be used):
# - alarmtemplate_id or alarmtemplate_name
# - aptemplate_id or aptemplate_name
# - gatewaytemplate_id or gatewaytemplate_name
# - networktemplate_id or networktemplate_name
# - rftemplate_id or rftemplate_name
# - secpolicy_id or secpolicy_name
# - subnet                                    if set, will add this subnet in the
#                                             auto assignment rules to automatically
#                                             assign the APs deployed on this subnet
#                                             to this site
#


def _check_settings(sites: list):
    message = "Validating Sites data"
    pb.log_title(message, display_pbar=False)
    site_name = []
    parameters_in_use = []
    line = 1
    for site in sites:
        line +=1
        if "site_name" not in site:
            pb.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Missing site parameter \"site_name\"")
            sys.exit(0)
        elif site["site_name"] in site_name:
            pb.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Site Name \"{site['site_name']}\" duplicated")
            sys.exit(0)
        else:
            site_name.append(site["site_name"])

        for key in site:
            parameter_name = key.split("_")
            if parameter_name[0] in PARAMETER_TYPES and parameter_name[1] in ["name", "id"]:
                if not parameter_name[0] in parameters_in_use:
                    parameters_in_use.append(parameter_name[0])
                pass
            else:
                pb.log_failure(message, display_pbar=False)
                console.error(f"Line {line}: Invalid site parameter \"{key}\"")
                sys.exit(0)
    pb.log_success(message, display_pbar=False)
    return parameters_in_use


def _process_sites_data(apisession: mistapi.APISession, org_id: str, sites: list) -> dict:
    '''
    Function to validate sites data and retrieve the required object from Mist
    '''
    parameters = {}
    pb.log_title("Preparing Sites Import", display_pbar=False)
    parameters_in_use = _check_settings(sites)
    parameters = _retrieve_objects(apisession, org_id, parameters_in_use)
    return parameters

def _read_csv_file(file_path: str):
    with open(file_path, "r") as f:
        data = csv.reader(f, skipinitialspace=True, quotechar='"')
        data = [[c.replace('\ufeff', '') for c in row] for row in data]
        fields = []
        sites = []
        auto_assignment_rules = []
        for line in data:
            if not fields:
                for column in line:
                    fields.append(column.strip().replace("#", ""))
            else:
                site = {}
                i = 0
                subnet = None
                for column in line:
                    field = fields[i]
                    if field == "subnet":
                        subnet = column
                    else:
                        site[field] = column
                    i += 1
                if subnet:
                    auto_assignment_rules.append({
                        "src": "subnet",
                        "subnet": subnet,
                        "value": site["name"]
                    })
                sites.append(site)
        return sites, auto_assignment_rules


def _check_org_name_in_script_param(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(
            f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    if not org_name:
        response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
        if response.status_code != 200:
            console.critical(
                f"Unable to retrieve the org information: {response.data}")
            sys.exit(3)
        org_name = response.data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def _create_org(apisession: mistapi.APISession, custom_dest_org_name: str = None):
    while True:
        if not custom_dest_org_name:
            custom_dest_org_name = input("Organization name? ")
        if custom_dest_org_name:
            org = {
                "name": custom_dest_org_name
            }
            message = f"Creating the organisation \"{custom_dest_org_name}\" in {apisession.get_cloud()} "
            pb.log_message(message, display_pbar=False)
            try:
                pb.log_success(message, display_pbar=False)
            except Exception as e:
                pb.log_failure(message, display_pbar=False)
                LOGGER.error("Exception occurred", exc_info=True)
                sys.exit(10)
            org_id = mistapi.api.v1.orgs.orgs.createOrg(
                apisession, org).data["id"]
            return org_id, custom_dest_org_name


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        res = input(
            "Do you want to import into a (n)ew organisation or (e)xisting one, (q) to quit? ")
        if res.lower() == "q":
            sys.exit(0)
        elif res.lower() == "e":
            org_id = mistapi.cli.select_org(apisession)[0]
            org_name = mistapi.api.v1.orgs.orgs.getOrg(
                apisession, org_id).data["name"]
            if _check_org_name(apisession, org_id, org_name):
                return org_id, org_name
        elif res.lower() == "n":
            return _create_org(apisession)


def start(apisession: mistapi.APISession, file_path: str, org_id: str = None, org_name: str = None):
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(
                f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and org_name:
        org_id, org_name = _create_org(apisession, org_name)
    elif not org_id and not org_name:
        org_id, org_name = _select_dest_org(apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)

    sites, auto_assignment_rules = _read_csv_file(file_path)
    # 2 = IDs + site settings update
    addition_steps = 0
    if auto_assignment_rules:
        addition_steps += 3
    pb.set_steps_total(len(sites) * 2 + addition_steps)
    parameters = _process_sites_data(apisession, org_id, sites)

    _update_sites(apisession, sites, parameters)

    if auto_assignment_rules:
        _update_org_rules(apisession, org_id, auto_assignment_rules)

    print()
    pb.log_title("Site Update Done", end=True)


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
Python script update the templates assigned to Mist Sites based on a CSV file, 
and/or update the auto assignment rules based on IP Subnet.

WARNING: if a template type is set in the CSV file, but it's value is empty, it 
will push is as-is to the site (and potentially remove the configured template)
If you don't need a type of template, DO NOT add it in the CSV file.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the 
additional required settings.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates it is possible to use the object name OR the object id (this
must be defined in the first line, by appending "_name" or "_id"). In case both name and id
are defined, the name will be used.

-------
CSV Example:
#site_name,rftemplate_id,networktemplate_name,gatewaytemplate_name
Juniper France,39ce2...ab5ee,ex-lab,test

-------
CSV Parameters:
Required:
- site_name

Optional:
- alarmtemplate_id or alarmtemplate_name
- aptemplate_id or aptemplate_name
- gatewaytemplate_id or gatewaytemplate_name
- networktemplate_id or networktemplate_name
- rftemplate_id or rftemplate_name
- secpolicy_id or secpolicy_name
- sitetemplate_id
- subnet                                    if set, will add this subnet in the
                                            auto assignment rules to automatically 
                                            assign the APs deployed on this subnet
                                            to this site

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file

-o, --org_id=       Set the org_id
-n, --org_name=     Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value   

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_sites.py -f ./my_new_sites.csv                 
python3 ./import_sites.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

''')
    if error:
        console.error(error)
    sys.exit(0)

def check_mistapi_version():
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


###############################################################################
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:g:f:e:l:", [
                                   "help", "org_id=", "org_name=", "google_api_key=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        usage(err)

    CSV_FILE = None
    ORG_ID = None
    ORG_NAME = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            ORG_NAME = a
        elif o in ["-g", "--google_api_key"]:
            GOOGLE_API_KEY = a
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
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    ### START ###
    if not CSV_FILE:
        usage("CSV File is missing")
    else:
        start(APISESSION, CSV_FILE, ORG_ID, ORG_NAME)
