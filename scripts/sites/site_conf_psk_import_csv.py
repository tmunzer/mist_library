'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

This script will import PSKs from a CSV file to one or multiple sites.
Usage:
python3 site_conf_psk_import_csv.py path_to_the_csv_file.csv

CSV file format:

pskName1,pskValue1,Wlan1
pskName2,pskValue2,Wlan2

'''

#### IMPORTS #####
import sys
import csv
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
LOG_FILE = "./sites_scripts.log"
ENV_FILE = "./.env"
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#### FUNCTIONS #####

def import_psk(apisession, site_id, psks):
    print("")
    print("".center(80, "-"))
    print(f"Starting PSKs import for site {site_id}".center(80, "-"))
    print("")
    for psk in psks:     
        print(f'PSK {psk["username"]}')
        body = {
            "username":psk["username"],
            "passphrase":psk["passphrase"],
            "ssid":psk["ssid"]
        }        
        result = mistapi.api.v1.sites.psks.createSitePsk(apisession, site_id, body=body).data
        mistapi.cli.pretty_print(result)

def read_csv(csv_file):
    print("")
    print("".center(80, "-"))
    print(f"Opening CSV file {csv_file}".center(80, "-"))
    print("")
    psks = []
    try:
        with open(sys.argv[1], 'r') as my_file:
            ppsk_file = csv.reader(my_file, delimiter=',')
            ppsk_file = [[c.replace("\ufeff", "") for c in row] for row in ppsk_file]
            for row in ppsk_file:
                username = row[0]
                passphrase = row[1]
                ssid = row[2]
                psks.append({"username": username,"passphrase": passphrase,"ssid": ssid})
        return psks
    except:
        print("Error while opening the CSV file... Aborting")

def list_psks(apisession, site_id):
    print("")
    print("".center(80, "-"))
    print(f"List of current PSKs for site {site_id}".center(80, "-"))
    print("")
    response = mistapi.api.v1.sites.psks.listSitePsks(apisession, site_id)
    psks = mistapi.get_all(apisession, response)
    mistapi.cli.pretty_print(psks)


def start(apisession):
    site_ids = mistapi.cli.select_site(apisession, allow_many=True)
    print("")
    print("".center(80, "-"))
    print(site_ids)

    psks = read_csv(sys.argv[1])

    for site_id in site_ids:
        import_psk(apisession, site_id, psks)

    for site_id in site_ids:
        list_psks(apisession, site_id)

#### SCRIPT ENTRYPOINT #####
if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION)
