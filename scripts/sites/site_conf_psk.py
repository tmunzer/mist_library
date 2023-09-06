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
else:
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip upgrade mistapi

    # Windows
    py -m pip upgrade mistapi
        """)
        sys.exit(2)

#### PARAMETERS #####
psk = {"name":'myUser', "passphrase":'myBadPassword', "ssid":'mySSID', "usage":'multi'}
log_file = "./sites_scripts.log"
env_file = "./.env"
#### LOGS ####
logger = logging.getLogger(__name__)
#### FUNCTIONS #####

def start(apisession):
    site_id = mistapi.cli.select_site(apisession, allow_many=False)
    mistapi.api.v1.sites.psks.createSitePsk(apisession, site_id, psk)
    response = mistapi.api.v1.sites.psks.listSitePsks(apisession, site_id)
    psks = mistapi.get_all(apisession, response)
    mistapi.cli.pretty_print(psks)

##### ENTRY POINT ####

if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession)
