'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script to list all WLANs from orgs/sites and their parameters, and save it to a CSV file.
You can configure which fields you want to retrieve/save, and where the script will save the CSV file.

You can run the script with the command "python3 org_report_wlans.py"

The script has 2 different steps:
1) admin login
2) select the organisation/site from where you want to retrieve the information


available fields:
ssid, enabled, auth, roam_mode, auth_servers_nas_id, auth_servers_nas_ip, auth_servers_timeout, auth_servers_retries, auth_servers, acct_servers,
acct_interim_interval, dynamic_vlan, band, band_steer, band_steer_force_band5, disable_11ax, interface, vlan_enabled, vlan_id, vlan_pooling, vlan_ids,
wxtunnel_id, wxtunnel_remote_id, mxtunneL_id, hide_ssid, dtim, disable_wmm, disable_uapsd, use_eapol_v1, legacy_overds, hostname_id, isolation, arp_filter,
limit_bcast, allow_mdns, allow_ipv6_ndp, no_static_ip, no_static_dns, enable_wireless_bridging, apply_to, wxtag_ids, ap_ids, wlan_limit_up_enabled, 
wlan_limit_up, wlan_limit_down_enabled, wlan_limit_down, client_limit_up_enabled, client_limit_up, client_limit_down_enabled, client_limit_down, 
max_idletime, sle_excluded, portal_template_url, portal_image, thumbnail, portal_api_secret, portal_sso_url, portal_allowed_subnets, portal_allowed_hostnames, 
portal_denied_hostnames

not yet available fields:
dns_server_rewrite, coa_server, radsec, airwatch, cisco_cwa, rateset, schedule, qos, app_limit, app_qos, portal
'''
#### IMPORTS ####
import sys
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


#### PARAMETERS #####
csv_separator = ","
fields = ["id", "ssid", "enabled", "auth", "auth_servers", "acct_servers",
          "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid"]
csv_file = "./report.csv"
log_file = "./script.log"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#### GLOBAL VARIABLES ####
wlans_summarized = []

#### FUNCTIONS ####


def country_code(site):
    if "country_code" in site:
        return site["country_code"]
    else:
        return "N/A"


def wlans_from_sites(mist_session, sites, org_info, site_ids):
    for site in sites:
        if site["id"] in site_ids:
            site_wlans = mistapi.api.v1.sites.wlans.listSiteWlanDerived(
                mist_session, site["id"]).data
            for site_wlan in site_wlans:
                tmp= []
                tmp.append("site")
                tmp.append(org_info["name"])
                tmp.append(org_info["id"])
                tmp.append(site["name"])
                tmp.append(site["id"])
                tmp.append(country_code(site))
                for field in fields:
                    tmp.append(site_wlan.get(field, ""))
                wlans_summarized.append(tmp)


def start(mist_session, org_id, site_ids):
    # org_sites = list(filter(lambda privilege: "org_id" in privilege and privilege["org_id"] == org_id, mist_session.privileges))
    org_info = mistapi.api.v1.orgs.orgs.getOrg(
        mist_session, org_id).data
    org_info = {
        "name": org_info["name"],
        "id": org_id
    }
    org_sites = []
    for site_id in site_ids:
        org_sites.append(mistapi.api.v1.sites.sites.getSiteInfo(
            mist_session, site_id).data)
    wlans_from_sites(mist_session, org_sites, org_info, site_ids)

def usage():
    print('''''')

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
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "he:o:", [
                                   "help", "env_file=", "org_id="])
    except getopt.GetoptError as err:
        usage()

    env_file=None
    org_id=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-e", "--env_file"]:
            env_file = a
        elif o in ["-o", "--org_id"]:
            org_id = a
        else:
            assert False, "unhandled option"

    mist = mistapi.APISession(env_file=env_file)
    mist.login()

    if not org_id:
        org_id = mistapi.cli.select_org(mist, allow_many=False)[0]
    site_ids = mistapi.cli.select_site(mist, org_id=org_id, allow_many=True)

    start(mist, org_id, site_ids)


    fields.insert(0, "origin")
    fields.insert(1, "org_name")
    fields.insert(2, "org_id")
    fields.insert(3, "site_name")
    fields.insert(4, "site_id")
    fields.insert(5, "country_code")

    mistapi.cli.pretty_print(wlans_summarized, fields)

    print("saving to file...")
    with open(csv_file, "w") as f:
        for column in fields:
            f.write(f"{column},")
        f.write('\r\n')
        for row in wlans_summarized:
            for field in row:
                f.write(field)
                f.write(csv_separator)
            f.write('\r\n')
