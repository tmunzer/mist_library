'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''
#### IMPORTS ####
import sys
import mistapi
import logging

#### PARAMETERS #####
log_file = "./script.log"
env_file = "./../../.env"
org_id = ""

#### LOGS ####
logger = logging.getLogger(__name__)


def get_stats(apisession:mistapi.APISession, org_id:str, page:int=1, switches:list=[]) -> list:
    try:
        resp = mistapi.api.v1.orgs.stats.getOrgDevicesStats(apisession, org_id=org_id, type="switch", limit=1000, page=page)
        if (resp.status_code == 200):
            switches = switches + resp.data
            total = int(resp.headers.get("X-Page-Total", 0))
            limit = int(resp.headers.get("X-Page-Limit", 0))
            page = int(resp.headers.get("X-Page-Page", 0))
            if page * limit < total:
                switches = get_stats(apisession, org_id, page + 1, switches)
            return switches
        else:
            print(resp.data)
            sys.exit(0)
    except:
        print("Error when retrieving switches stats")
        sys.exit(0)

def start(apisession:mistapi.APISession, org_id:str) -> None:
    if org_id == "":
        org_id = mistapi.cli.select_org(apisession)[0]

    switches = get_stats(apisession, org_id)

    for switch in switches:
        if switch.get("status") == "connected":
            version = switch.get("version")
            name = switch.get("name")

            for fpc in switch.get("module_stat", []):
                if fpc.get("vc_state") == "present":
                    fpc_serial = fpc.get("serial")
                    fpc_version = fpc.get("version")
                    fpc_recovery_version = fpc.get("recovery_version", "MISSING")
                    if fpc_recovery_version == "": fpc_recovery_version = "MISSING"
                    fpc_model = fpc.get("model")
                    if version != fpc_recovery_version:
                        print(f"{fpc_model} | {name} | {fpc_serial} with version {fpc_version} and snap {fpc_recovery_version}")


#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id)
