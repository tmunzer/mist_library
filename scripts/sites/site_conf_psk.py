'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''


#### IMPORTS #####
import mistapi
import logging
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
    psks = mistapi.api.v1.sites.psks.getSitePsks(apisession, site_id).data
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
