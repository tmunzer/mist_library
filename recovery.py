import requests
import sys

host = "api.eu.mist.com"   # api.mist.com, api.eu.mist.com, api.gc1.mist.com, ...
org_id = ""
api_token = ""


switches = []

url = f"https://{host}/api/v1/orgs/{org_id}/stats/devices?type=switch&limit=1000"
headers = {
    "Authorization": f"Token {api_token}"
}

def get_stats(page, switches):
    try:
        resp = requests.get(f"{url}&page={page}", headers=headers)
        if (resp.status_code == 200):
            switches = switches + resp.json()
            total = int(resp.headers.get("X-Page-Total", 0))
            limit = int(resp.headers.get("X-Page-Limit", 0))
            page = int(resp.headers.get("X-Page-Page", 0))
            if page * limit < total:
                switches = get_stats(page + 1, switches)
            return switches
        else:
            print(resp.json())
            sys.exit(0)
    except:
        print("Error when retrieving switches stats")
        sys.exit(0)

switches = get_stats(1, switches)

for switch in switches:
    if switch.get("status") == "connected":
        success = True
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
                    success = False
