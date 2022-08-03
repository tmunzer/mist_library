'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#######################################################################################################################################
#######################################################################################################################################
############################################# IMPORTS
#######################################################################################################################################

import os
from dotenv import load_dotenv
import getopt
import sys
from mlib import cli, mist, orgs

def _load_conf(cloud, org_id, tmpl_id, profile):    
    print("Loading config ".ljust(79, "."), end="", flush=True)
    mist_config = {}
    mist_config["api_token"]= os.environ.get("MIST_API_TOKEN", default=None)
    
    if cloud:
        mist_config["host"]=cloud
    else:
        mist_config["host"]= os.environ.get("MIST_HOST", default=None)
    
    if org_id:
        mist_config["org_id"]=org_id
    else:
        mist_config["org_id"]= os.environ.get("MIST_ORG_ID", default=None)
    
    if tmpl_id:
        mist_config["tmpl_id"]=tmpl_id
    else:
        mist_config["tmpl_id"]= os.environ.get("MIST_TEMPLATE_ID", default=None)
    
    if profile:
        mist_config["profile"]=profile
    else:
        mist_config["profile"]= os.environ.get("MIST_PORT_PROFILE", default=None)
    
    if not mist_config["tmpl_id"]: 
        print('\033[31m\u2716\033[0m')
        print("ERROR: Missing the tmpl_id")
        sys.exit(1)
    if not mist_config["profile"]:
        print('\033[31m\u2716\033[0m') 
        print("ERROR: Missing the profile")
        sys.exit(1)

    print("\033[92m\u2714\033[0m")

    return mist_config

def _get_port_usages(session, org_id, tmpl_id):
    print("Retrieving data from Mist ".ljust(79, "."), end="", flush=True)
    try:
        res = orgs.networktemplates.get_by_id(session, org_id, tmpl_id)
        disabled = res.get("result", {}).get("port_usages", {})
        print("\033[92m\u2714\033[0m")
        return disabled
    except:
        print('\033[31m\u2716\033[0m') 
        sys.exit(4)

def _status(session, org_id, tmpl_id, profile):
    port_usages = _get_port_usages(session, org_id, tmpl_id)
    print("Extracting profile data ".ljust(79, "."), end="", flush=True)
    profile = port_usages.get(profile)
    if not profile:
        print('\033[31m\u2716\033[0m') 
        print(f"Profile {profile} not found")
    else:
        print("\033[92m\u2714\033[0m")
        return profile.get("poe_disabled", False)

def _display_status(session, org_id, tmpl_id, profile):
    disabled = _status(session, org_id, tmpl_id, profile)
    print()
    print(" Result ".center(80, "-"))
    print()
    if disabled == True:
        print(f"PoE Current status: DISABLED")
    else:
        print(f"PoE Current status: ENABLED")

def _update(session, org_id, tmpl_id,port_usages):
    try:
        print("Updating PoE Status ".ljust(79, "."), end="", flush=True)
        res = orgs.networktemplates.update(session, org_id, tmpl_id, {"port_usages": port_usages})
        if res.get("status_code") == 200:
            print("\033[92m\u2714\033[0m")
        else:
            raise
    except:
        print('\033[31m\u2716\033[0m') 
        sys.exit(5)


def _change(session, org_id, tmpl_id, profile, disabled):  
    port_usages = _get_port_usages(session, org_id, tmpl_id)
    print("Extracting profile data ".ljust(79, "."), end="", flush=True)
    if not profile in port_usages:
        print('\033[31m\u2716\033[0m') 
        print(f"Profile {profile} not found")
    else:
        print("\033[92m\u2714\033[0m")
        port_usages[profile]["poe_disabled"] = disabled
        _update(session, org_id, tmpl_id, port_usages)

def _toggle(session, org_id, tmpl_id, profile):  
    port_usages = _get_port_usages(session, org_id, tmpl_id)
    print("Extracting profile data ".ljust(79, "."), end="", flush=True)
    if not profile in port_usages:
        print('\033[31m\u2716\033[0m') 
        print(f"Profile {profile} not found")
    else:
        print("\033[92m\u2714\033[0m")
        port_usages[profile]["poe_disabled"] = not port_usages[profile]["poe_disabled"]
        _update(session, org_id, tmpl_id, port_usages)

def usage():
    print("""
---
Usage:
-e, --env=file          Configuration file location. By default the script
                        is looking for a ".env" file in the script root folder

-c, --cloud             Mist API Cloud (e.g. api.mist.com)

-o, --org_id=oid        Mist ORG ID

-t, --tmpl_id=tid       Mist Switch template_id

-p, --profile=name      Mist Port Profile name

-s, --status            Get the PoE Status

--toggle                Toggle PoE

--on                    Turn ON PoE

--off                   Turn OFF PoE

---
Configuration file example:
MIST_HOST = "api.mist.com"              # Optional
MIST_API_TOKEN = "xxxxxxxxxxxxxxxxx"    # Optional
MIST_ORG_ID = "xxxxxxxxxxxxxx"          # Optional
MIST_TEMPLATE_ID = "xxxxxxxxxxxxxx"     # Required in .env file or parameter
MIST_PORT_PROFILE = "xxxx"              # Required in .env file or parameter

    """)

def main():    
    print("""

Python Script to toggle PoE on switch Port Profile.
Written by Thomas Munzer (tmunzer@juniper.net)
Github: https://github.com/tmunzer/mist_library

""")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "e:c:o:t:p:s", ["env=", "cloud=", "org-id=", "tmpl_id=", "profile=", "status", "toggle", "on", "off"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    env_file = None
    cloud=None
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
        elif o in ["-c", "--cloud"]:
            cloud=a
        elif o in ["-o", "--org_id"]:
            org_id=a
        elif o in ["-t", "--tmpl_id"]:
            tmpl_id=a
        elif o in ["-p", "--profile"]:
            profile=a
        elif o in ["--status"]:
            action="status"
        elif o in ["--toggle"]:
            if action:
                usage()
                sys.exit(3)
            action="toggle"
        elif o in ["--on"]:
            if action:
                usage()
                sys.exit(3)
            action="on"
        elif o in ["--off"]:
            if action:
                usage()
                sys.exit(3)
            action="off"
        
        else:
            assert False, "unhandled option"
  
    if env_file:
        load_dotenv(dotend_path=env_file)
    else:
        load_dotenv()

    mist_config = _load_conf(cloud, org_id, tmpl_id, profile)

    session = mist.Mist_Session(load_settings=False, apitoken=mist_config["api_token"], host=mist_config["host"])
    if not mist_config["org_id"]:
        mist_config["org_id"] = cli.select_org(session)[0]
    if action == "status":
        _display_status(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"])
    if action == "off": 
        _change(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"], True)
        _display_status(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"])
    if action == "on": 
        _change(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"], False)
        _display_status(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"])
    if action == "toggle":
        _toggle(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"])
        _display_status(session, mist_config["org_id"], mist_config["tmpl_id"], mist_config["profile"])


#######################################################################################################################################
#######################################################################################################################################
############################################# ENTRYPOINT
#######################################################################################################################################
if __name__=="__main__":
        main()

