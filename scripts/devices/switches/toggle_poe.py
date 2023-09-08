'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to enable/disable/toggle PoE for a specified Port Profile in a 
Switch Template.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

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
-o, --org_id=       Set the org_id
-t, --tmpl_id=      Set the Switch template_id
-p, --profile=      Set the Port Profile name
-a, --action=       Set the action to execupte. It must be one of the following:
                    - status: Retrieve the PoE status
                    - on: Enable PoE on the port profile
                    - off: Disable PoE on the port profile
                    - toggle: toogle PoE on the port profile (i.e. turn it off if 
                        currently enable, turn it on if currently enabled)
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./toggle_poe.py     
python3 ./toggle_poe.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -t 2c57044e-xxxx-xxxx-xxxx-69374b32a070 -p ap -a toggle

'''

#### IMPORTS ####
import logging
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


#####################################################################
#### PARAMETERS #####
log_file = "./script.log"
env_file = "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
#### FUNCTIONS ####
def _get_port_usages(apisession:mistapi.APISession, org_id:str, tmpl_id:str):
    print("Retrieving data from Mist ".ljust(79, "."), end="", flush=True)
    try:
        res = mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplate(apisession, org_id, tmpl_id)
        disabled = res.data.get("port_usages", {})
        print("\033[92m\u2714\033[0m")
        return disabled
    except:
        print('\033[31m\u2716\033[0m') 
        sys.exit(4)

def _status(apisession:mistapi.APISession, org_id:str, tmpl_id:str, profile:str):
    port_usages = _get_port_usages(apisession, org_id, tmpl_id)
    print("Extracting profile data ".ljust(79, "."), end="", flush=True)
    profile = port_usages.get(profile, {})
    if not profile:
        print('\033[31m\u2716\033[0m') 
        print(f"Profile {profile} not found")
    else:
        print("\033[92m\u2714\033[0m")
        return profile.get("poe_disabled", False)

def _display_status(apisession:mistapi.APISession, org_id:str, tmpl_id:str, profile:str):
    disabled = _status(apisession, org_id, tmpl_id, profile)
    print()
    print(" Result ".center(80, "-"))
    print()
    if disabled == True:
        print(f"PoE Current status: DISABLED")
    else:
        print(f"PoE Current status: ENABLED")

def _update(apisession:mistapi.APISession, org_id:str, tmpl_id:str, port_usages:dict):
    try:
        print("Updating PoE Status ".ljust(79, "."), end="", flush=True)
        res = mistapi.api.v1.orgs.networktemplates.updateOrgNetworkTemplates(apisession, org_id, tmpl_id, {"port_usages": port_usages})
        if res.status_code == 200:
            print("\033[92m\u2714\033[0m")
        else:
            raise Exception
    except:
        print('\033[31m\u2716\033[0m') 
        sys.exit(5)

def _change(apisession:mistapi.APISession, org_id:str, tmpl_id:str, profile:str, disabled:bool):  
    port_usages = _get_port_usages(apisession, org_id, tmpl_id)
    print("Extracting profile data ".ljust(79, "."), end="", flush=True)
    if not profile in port_usages:
        print('\033[31m\u2716\033[0m') 
        print(f"Profile {profile} not found")
    else:
        print("\033[92m\u2714\033[0m")
        port_usages[profile]["poe_disabled"] = disabled
        _update(apisession, org_id, tmpl_id, port_usages)

def _toggle(apisession:mistapi.APISession, org_id:str, tmpl_id:str, profile:str):  
    port_usages = _get_port_usages(apisession, org_id, tmpl_id)
    print("Extracting profile data ".ljust(79, "."), end="", flush=True)
    if not profile in port_usages:
        print('\033[31m\u2716\033[0m') 
        print(f"Profile {profile} not found")
    else:
        print("\033[92m\u2714\033[0m")
        port_usages[profile]["poe_disabled"] = not port_usages[profile]["poe_disabled"]
        _update(apisession, org_id, tmpl_id, port_usages)


####################
## MENU
def _show_menu(header:str, menu:list) -> str:
    print()
    print("".center(80, "-"))
    resp=None
    menu = sorted(menu, key=str.casefold)
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
            except:
                console.error("Please enter a number\r\n ")
            if resp < 0 or resp >= i:
                console.error(f"Please enter a number between 0 and {i -1}.")
            else:
                return menu[resp]

def _check_parameters(apisession:mistapi.APISession, org_id:str, tmpl_id:str, profile:str, action:str):
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    if not tmpl_id:
        response = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(apisession, org_id)
        templates = mistapi.get_all(apisession, response)
        template_names = {}
        template_menu = []
        for template in templates:
            template_menu.append(template.get("name"))
            template_names[template.get("name")] = template["id"]
        tmpl_name = _show_menu("Please select a Switch Template", template_menu)
        tmpl_id = template_names[tmpl_name]
    
    if not profile:
        template_settings = mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplate(apisession, org_id, tmpl_id).data
        port_usages = template_settings.get("port_usages")
        if not port_usages:
            console.error("There is no profile to update in this switch template")
            sys.exit(2)
        else:
            profile_names = []
            for port_usage in port_usages:
                profile_names.append(port_usage)
            profile = _show_menu("Please select a Profile", profile_names)

    if not action:
        action = _show_menu("Please select an Action", ["status", "on", "off", "toggle"])
        if action != "status":
            action_str = action
            if action != "toggle":
                action_str = f"turn {action}"
            while True:
                print()
                confirm = input(f"Do you confirm you want to {action_str} PoE on port profile {profile} (y/n)?")
                if confirm.lower() == "y":
                    break
                elif confirm.lower() == "n":
                    sys.exit(0)
    return org_id, tmpl_id, profile, action

def start(apisession:mistapi.APISession, org_id:str, tmpl_id:str, profile:str, action:str):
    org_id, tmpl_id, profile, action = _check_parameters(apisession, org_id, tmpl_id, profile, action)
    print(" Processing ".center(80, "-"))
    print()
    if action == "status":
        _display_status(apisession, org_id, tmpl_id, profile)
    if action == "off": 
        _change(apisession, org_id, tmpl_id, profile, True)
        _display_status(apisession, org_id, tmpl_id, profile)
    if action == "on": 
        _change(apisession, org_id, tmpl_id, profile, False)
        _display_status(apisession, org_id, tmpl_id, profile)
    if action == "toggle":
        _toggle(apisession, org_id, tmpl_id, profile)
        _display_status(apisession, org_id, tmpl_id, profile)

#####################################################################
##### USAGE ####
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to enable/disable/toggle PoE for a specified Port Profile in a 
Switch Template.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

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
-o, --org_id=       Set the org_id
-t, --tmpl_id=      Set the Switch template_id
-p, --profile=      Set the Port Profile name
-a, --action=       Set the action to execupte. It must be one of the following:
                    - status: Retrieve the PoE status
                    - on: Enable PoE on the port profile
                    - off: Disable PoE on the port profile
                    - toggle: toogle PoE on the port profile (i.e. turn it off if 
                        currently enable, turn it on if currently enabled)
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./toggle_poe.py     
python3 ./toggle_poe.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -t 2c57044e-xxxx-xxxx-xxxx-69374b32a070 -p ap -a toggle
'''
)
    sys.exit(0)

#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "e:o:t:p:a:", ["env=", "org-id=", "tmpl_id=", "profile=", "action="])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    
    org_id=None
    tmpl_id=None
    profile=None
    action=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
            sys.exit()
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-o", "--org_id"]:
            org_id=a
        elif o in ["-t", "--tmpl_id"]:
            tmpl_id=a
        elif o in ["-p", "--profile"]:
            profile=a
        elif o in ["-a", "--action"]:
            if a not in ["status", "on", "off", "toggle"]:
                console.error(f"Unknown action \"{o}\"")
                usage()
                sys.exit(0)
            else:
                action=a    
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id, tmpl_id, profile, action)


