'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''


#### IMPORTS #####
import logging
import sys

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
PSK = {"name":'myUser', "passphrase":'myBadPassword', "ssid":'mySSID', "usage":'multi'}
LOG_FILE = "./sites_scripts.log"
ENV_FILE = "./.env"
#### LOGS ####
LOGGER = logging.getLogger(__name__)
#### FUNCTIONS #####

def start(apisession):
    site_id = mistapi.cli.select_site(apisession, allow_many=False)
    mistapi.api.v1.sites.psks.createSitePsk(apisession, site_id, PSK)
    response = mistapi.api.v1.sites.psks.listSitePsks(apisession, site_id)
    psks = mistapi.get_all(apisession, response)
    mistapi.cli.pretty_print(psks)

##### ENTRY POINT ####

if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION)
