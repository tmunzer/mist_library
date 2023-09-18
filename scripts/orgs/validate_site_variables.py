"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to validate that all the variables used in the templates used by
each site are configured at the site level.
The result is displayed on the console and saved in a CSV file.

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
-h, --help              display this help
-o, --org_id=           Set the org_id
-c, --csv_file=         Path to the CSV file where to save the output
                        default is "./validate_site_variables.csv"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./validate_site_variables.py     
python3 ./validate_site_variables.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""

#### IMPORTS ####
import logging
import sys
import csv
import json
import getopt
import re


MISTAPI_MIN_VERSION = "0.44.3"

try:
    import mistapi
    from mistapi.__logger import console
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

#####################################################################
#### PARAMETERS #####
CSV_FILE = "./validate_site_variables.csv"
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

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

    def log_warning(self, message, inc:bool=False, display_pbar:bool=True):
        LOGGER.warning(f"{message}")
        self._pb_new_step(message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


pb = ProgressBar()


#####################################################################
#### SITE FUNCTIONS ####
def _site_included(site: dict, included: dict = {}):
    '''
    Check if the WLAN template is used by the scpecified site 
    
    PARAMS
    -----------
    site : dict
        site info retrieved from /api/v1/orgs/{org_id}/site

    included : dict
        "applies" or "exceptions" info from the template

    RETURN
    -----------
    boolean
        True if the WLAN template is assigned to the site
    '''
    site_id = site["id"]
    sitegroup_ids = site.get("sitegroup_ids", [])
    if included:
        if (included.get("org_id") or site_id in included.get("site_ids", [])):
            return True
        if included.get("sitegroup_ids"):
            for sitegroup_id in sitegroup_ids:
                if sitegroup_id in included["sitegroup_ids"]:
                    return True
    return False


def _find_site_vars_in_wlans(
    site: dict, wlan_templates_vars: dict, required_vars: dict = {}
):
    '''
    Retrieve the WLAN site variables for the site
    
    PARAMS
    -----------
    site : dict
        site info retrieved from /api/v1/orgs/{org_id}/site

    wlan_templates_vars : dict
        dict of WLAN templates with their WLANs and the variables for each
    
    required_vars : dict
        site variables already identified for the site

    RETURN
    -----------
    dict
        updated site variables identified for the site
    '''
    for wlan_template_id in wlan_templates_vars:
        wlan_template = wlan_templates_vars[wlan_template_id]
        applies = wlan_template["applies"]
        exceptions = wlan_template["exceptions"]
        site_is_assigned = _site_included(site, applies)
        site_is_excluded = _site_included(site, exceptions)
        if site_is_assigned and not site_is_excluded:
            LOGGER.debug(f"WLAN: {wlan_template_id}, {wlan_template}")
            for wlan_id in wlan_template.get("wlans", []):
                wlan = wlan_template["wlans"][wlan_id]
                LOGGER.debug(f"WLAN: {wlan['name']}, {wlan['vars']}")
                for var in wlan["vars"]:
                    if not var in required_vars:
                        required_vars[var] = []
                    required_vars[var].append(
                        {
                            "template_type": "wlan",
                            "template_name": wlan_template["name"],
                            "template_id": wlan_template_id,
                            "wlan_name": wlan["name"],
                            "wlan_id": wlan_id,
                        }
                    )
                    LOGGER.debug(f"WLAN: var {var} added (wlan {wlan['name']})")
    return required_vars


def _find_site_vars_in_template(site: str,gateway_templates_vars: dict,switch_templates_vars: dict,required_vars: dict = {}):
    '''
    Retrieve the GW and SW site variables for the site
    
    PARAMS
    -----------
    site : dict
        site info retrieved from /api/v1/orgs/{org_id}/site

    gateway_templates_vars : dict
        dict of GW templates with their variables 

    switch_templates_vars : dict
        dict of SW templates with their variables 
    
    required_vars : dict
        site variables already identified for the site

    RETURN
    -----------
    dict
        updated site variables identified for the site
    '''
    gateway_template_id = site.get("gatewaytemplate_id")
    switch_template_id = site.get("networktemplate_id")
    if gateway_template_id and gateway_template_id in gateway_templates_vars:
        template = gateway_templates_vars[gateway_template_id]
        LOGGER.debug(f"GWTP: {gateway_template_id}, {template}")
        for var in template["vars"]:
            if not var in required_vars:
                required_vars[var] = []
            required_vars[var].append(
                {
                    "template_type": "gateway",
                    "template_name": template["name"],
                    "template_id": gateway_template_id,
                }
            )
            LOGGER.debug(f"GWTP: var {var} added (tempalte {template['name']})")

    if switch_template_id and switch_template_id in switch_templates_vars:
        template = switch_templates_vars[switch_template_id]
        LOGGER.debug(f"SWTP: {switch_template_id}, {template}")
        for var in template["vars"]:
            if not var in required_vars:
                required_vars[var] = []
            required_vars[var].append(
                {
                    "template_type": "switch",
                    "template_name": template["name"],
                    "template_id": switch_template_id,
                }
            )
            LOGGER.debug(f"SWTP: var {var} added (tempalte {template['name']})")

    return required_vars


def _check_sites(
    mist_session: mistapi.APISession,
    sites: list,
    gateway_template_vars: dict,
    switch_templates_vars: dict,
    wlan_templates_vars: dict,
):
    '''
    Compare the site vars with the required vars for each site
    
    PARAMS
    -----------
    mistapi.APISession : mist_session
        mistapi session including authentication and Mist host information

    sites : list
        list of sites retrieved from /api/v1/orgs/{org_id}/site

    gateway_templates_vars : dict
        dict of GW templates with their variables 

    switch_templates_vars : dict
        dict of SW templates with their variables 
    
    required_vars : dict
        site variables already identified for the site

    RETURN
    -----------
    dict
        dict of sites with the requireds and configured vars
    '''
    sites_vars = {}
    for site in sites:
        configured_vars = {}
        required_vars = {}
        try:
            message = f"{site['name']}: Retrieving site_vars"
            pb.log_message(message)
            LOGGER.debug(site)
            site_id = site["id"]
            site_setting = mistapi.api.v1.sites.setting.getSiteSetting(
                mist_session, site_id
            ).data
            pb.log_success(message, inc=True)
        except Exception as error:
            pb.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)
        else:
            try:
                message = f"{site['name']}: Processing site_vars"
                pb.log_message(message)
                tmp_vars = site_setting.get("vars", {})
                for var in tmp_vars:
                    configured_vars["{{" + var + "}}"] = tmp_vars[var]
                LOGGER.debug(f"site: {site_id} vars: {configured_vars}")
                _find_site_vars_in_wlans(site, wlan_templates_vars, required_vars)
                _find_site_vars_in_template(site, gateway_template_vars, switch_templates_vars, required_vars)
                sites_vars[site_id] = {
                    "name": site["name"],
                    "required_vars": required_vars,
                    "configured_vars": configured_vars
                }
                LOGGER.debug(f"{site_id}, {sites_vars[site_id]}")
                pb.log_success(message, inc=True)
            except Exception as error:
                pb.log_failure(message, inc=True)
                LOGGER.error("Exception occurred", exc_info=True)
    return sites_vars


#####################################################################
#### TEMPLATES FUNCTIONS ####
def _find_site_variables(data: dict):
    '''
    Find the required var in a template/wlan
    
    PARAMS
    -----------
    data : dict
        temaplate/wlan

    RETURN
    -----------
    list
        list of vars used in the template/wlan
    '''
    regex = r"({{[^}]*}})"
    result = []
    LOGGER.debug(f"regex: template id: {data['id']}")
    data_str = json.dumps(data)
    data_str = data_str.replace("Code {{code}} expires in {{duration}} minutes.", "")
    site_vars = re.findall(regex, data_str)
    LOGGER.debug(f"regex: vars: {site_vars}")
    for var in site_vars:
        if not var in result:
            result.append(var)
    LOGGER.debug(f"regex: out: {result}")
    return result


def _gateway_templates(mist_session: mistapi.APISession, org_id: str):
    '''
    Retrieve anf process the GW templates to identify the required vars
    
    PARAMS
    -----------
    mistapi.APISession : mist_session
        mistapi session including authentication and Mist host information

    org_id : str
        Mist org_id

    RETURN
    -----------
    dict
        dict of GW templates with the required vars
    '''
    gateway_template_vars = {}
    message = "Retrieving Gateway Templates"
    pb.log_message(message)
    try:
        response = mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates(
            mist_session, org_id, limit=1000
        )
        data = mistapi.get_all(mist_session, response)
        for template in data:
            template_id = template["id"]
            template_name = template["name"]
            template_vars = _find_site_variables(template)
            gateway_template_vars[template_id] = {
                "name": template_name,
                "vars": template_vars,
            }
        LOGGER.debug(f"gwtp: vars for Gateway Template {template_name} {template_name}: {template_vars}")
        pb.log_success(message, inc=True)
    except Exception as error:
        pb.log_failure(message, inc=True)
        LOGGER.error("gwtp: Unable to retrieve the list of Gateway Templates")
        LOGGER.error("Exception occurred", exc_info=True)
    return gateway_template_vars


def _switch_templates(mist_session: mistapi.APISession, org_id: str):
    '''
    Retrieve anf process the SW templates to identify the required vars
    
    PARAMS
    -----------
    mistapi.APISession : mist_session
        mistapi session including authentication and Mist host information

    org_id : str
        Mist org_id

    RETURN
    -----------
    dict
        dict of SW templates with the required vars
    '''
    switch_template_vars = {}
    message = "Retrieving Switch Templates"
    pb.log_message(message)
    try:
        response = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(
            mist_session, org_id, limit=1000
        )
        data = mistapi.get_all(mist_session, response)
        for template in data:
            template_id = template["id"]
            template_name = template["name"]
            template_vars = _find_site_variables(template)
            switch_template_vars[template_id] = {
                "name": template_name,
                "vars": template_vars,
            }
        LOGGER.debug(f"swtp: vars for Switch Template {template_name} {template_name}: {template_vars}")
        pb.log_success(message, inc=True)
    except Exception as error:
        pb.log_failure(message, inc=True)
        LOGGER.error("swtp: Unable to retrieve the list of Switch Templates")
        LOGGER.error("Exception occurred", exc_info=True)
    return switch_template_vars


def _wlan_templates(mist_session: mistapi.APISession, org_id: str):
    '''
    Retrieve anf process the WLAN templates to identify the required vars.
    This function also retrieving the list of Org WLANs and attach them to 
    the corresponding WLAN template
    
    PARAMS
    -----------
    mistapi.APISession : mist_session
        mistapi session including authentication and Mist host information

    org_id : str
        Mist org_id

    RETURN
    -----------
    dict
        dict of WLAN templates with the attached WLANs and the required vars
    '''
    wlan_template_vars = {}
    # retrieve the list of wlan templates
    try:
        message = "Retrieving WLAN Templates"
        pb.log_message(message)
        response = mistapi.api.v1.orgs.templates.listOrgTemplates(
            mist_session, org_id, limit=1000
        )
        data = mistapi.get_all(mist_session, response)
    except Exception as error:
        pb.log_failure(message, inc=True)
        LOGGER.error("Unable to retrieve the list of WLAN Templates")
        LOGGER.error("Exception occurred", exc_info=True)
        return wlan_template_vars
    
    # process the list of wlan templates
    warning = False
    for template in data:
        try:
            template_id = template["id"]
            template_name = template["name"]
            template_applies = template.get("applies")
            template_exceptions = template.get("exceptions")
            wlan_template_vars[template_id] = {
                "name": template_name,
                "applies": template_applies,
                "exceptions": template_exceptions,
                "wlans": {}
            }
        except Exception as error:
            warning = True
            LOGGER.error(f"wlan: Unable to process the WLAN Templates {template['id']}")
            LOGGER.error("Exception occurred", exc_info=True)
    if warning:
        pb.log_warning(message, inc=True)
    else:
        pb.log_success(message, inc=True)

    # retrieve the list of wlans
    warning = False
    try:
        message = "Retrieving Org WLANs"
        pb.log_message(message)
        response = mistapi.api.v1.orgs.wlans.listOrgWlans(
            mist_session, org_id, limit=1000
        )
        data = mistapi.get_all(mist_session, response)
    except Exception as error:
        warning = True        
        LOGGER.error("wlan: Unable to retrieve the list of Org WLANs")
        LOGGER.error("Exception occurred", exc_info=True)
    
    # process the list of wlans
    for wlan in data:
        try:
            wlan_id = wlan["id"]
            wlan_template_id = wlan["template_id"]
            wlan_name = wlan["ssid"]
            wlan_vars = _find_site_variables(wlan)
            wlan_template_vars[wlan_template_id]["wlans"][wlan_id] = {
                "name": wlan_name,
                "vars": wlan_vars,
            }
            LOGGER.debug(f"wlan: vars for wlan {wlan_name} {wlan_id}: {wlan_vars}")
        except Exception as error:
            LOGGER.error(f"wlan: Unable to process the WLANs {wlan_id}")
            LOGGER.error("Exception occurred", exc_info=True)
    if warning:
        pb.log_warning(message, inc=True)
    else:
        pb.log_success(message, inc=True)

    return wlan_template_vars


def _retrieve_templates_variables(mist_session: mistapi.APISession, org_id: str):
    '''
    Retrieve anf process Mist templates
    
    PARAMS
    -----------
    mistapi.APISession : mist_session
        mistapi session including authentication and Mist host information

    org_id : str
        Mist org_id

    RETURN
    -----------
    tuple
        dict of GW templates with the required vars
        dict of SW templates with the required vars
        dict of WLAN templates with the attached WLANs and the required vars
    '''
    gateway_template_vars = _gateway_templates(mist_session, org_id)
    switch_templates_vars = _switch_templates(mist_session, org_id)
    wlan_templates_vars = _wlan_templates(mist_session, org_id)
    return (gateway_template_vars, switch_templates_vars, wlan_templates_vars)


def _retrieve_sites(mist_session: mistapi.APISession, org_id: str):
    '''
    Retrieve sites info from the Mist Org
    
    PARAMS
    -----------
    mistapi.APISession : mist_session
        mistapi session including authentication and Mist host information

    org_id : str
        Mist org_id

    RETURN
    -----------
    list
        List of Mist Sites
    '''
    message = "Retrieving Sites from the org"
    pb.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(
            mist_session, org_id, limit=1000
        )
        sites = mistapi.get_all(mist_session, response)
        pb.log_success(message, display_pbar=False)
        return sites
    except Exception as error:
        pb.log_failure(message, display_pbar=False)
        LOGGER.critical(
            "Unable to retrieve the list of sites from the Mist Organization. Exiting..."
        )
        LOGGER.critical("Exception occurred", exc_info=True)
        sys.exit(255)


#####################################################################
#### END ####
def _process_data(sites_vars:dict, csv_file:str):
    '''
    Process the result, then display it on the console and save it in a CSV file
    
    PARAMS
    -----------
    sites_vars : dict
        dict of sites with the required vars, the configured vars, and all the
        required info

    csv_file : str
        file path where to save the result
    '''
    pb.log_title("RESULTS", end=True)
    result = []
    header = ["#site_name","site_id","template_type","template_name","template_id","wlan_name","wlan_id","var_name","value","configured"]
    for site_id in sites_vars:
        site_data = sites_vars[site_id]
        LOGGER.debug("".center(80, "-"))
        LOGGER.debug(site_data)
        site_name = site_data["name"]
        required_vars = site_data["required_vars"]
        if required_vars:
            LOGGER.debug(required_vars)
            for var_name in required_vars:
                var_data = required_vars[var_name]
                LOGGER.debug(var_data)
                var_value = None
                var_configured = False
                if var_name in site_data["configured_vars"]:
                    var_value = site_data["configured_vars"][var_name]
                    var_configured = True
                for entry in var_data:
                    data=[
                        site_name,
                        site_id,
                        entry["template_type"],
                        entry["template_name"],
                        entry["template_id"],
                        entry.get("wlan_name", ""),
                        entry.get("wlan_is", ""),
                        var_name,
                        var_value,
                        var_configured
                    ]
                    LOGGER.debug(data)
                    result.append(data)
    mistapi.cli.pretty_print(result, header)
    result.insert(0, header)
    with open(csv_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(result)



#####################################################################
#### START ####
def start(mist_session: mistapi.APISession, org_id: str, csv_file: str = None):
    """
    Start the backup process

    PARAMS
    -------
    :param  mistapi.APISession  dst_apisession      - mistapi session with `Super User` access the destination Org, already logged in
    :param  str                 org_id              - org_id of the org to backup
    :param  str                 csv_file            - Path to the CSV file where to save the output. default is "./validate_site_variables.csv"

    """
    if not csv_file:
        csv_file = CSV_FILE
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]
    sites = _retrieve_sites(mist_session, org_id)
    pb.set_steps_total(4 + len(sites) * 2)
    pb.log_title("Retrieving templates")
    (
        gateway_template_vars,
        switch_templates_vars,
        wlan_templates_vars,
    ) = _retrieve_templates_variables(mist_session, org_id)
    LOGGER.debug(f"gwtp: {gateway_template_vars}")
    LOGGER.debug(f"swtp: {switch_templates_vars}")
    LOGGER.debug(f"wlan: {wlan_templates_vars}")
    pb.log_title("Checking Sites")
    sites_vars = _check_sites(mist_session, sites, gateway_template_vars, switch_templates_vars, wlan_templates_vars)
    #print(json.dumps(sites_vars, indent=4))
    _process_data(sites_vars, csv_file)


#####################################################################
#### USAGE ####
def usage():
    '''
    Display Usage
    '''
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to validate that all the variables used in the templates used by
each site are configured at the site level.
The result is displayed on the console and saved in a CSV file.

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
-h, --help              display this help
-o, --org_id=           Set the org_id
-c, --csv_file=         Path to the CSV file where to save the output
                        default is "./validate_site_variables.csv"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./validate_site_variables.py     
python3 ./validate_site_variables.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""
    )
    sys.exit(0)


def check_mistapi_version():
    '''
    Check the mistapi package version in use, and compare it to MISTAPI_MIN_VERSION
    '''
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
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:c:l:e:",
            ["help", "org_id=", "env=", "log_file=", "csv_file="],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    csv_file = CSV_FILE
    log_file = LOG_FILE
    env_file = ENV_FILE
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["-e", "--csv_file"]:
            csv_file = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id, csv_file)
