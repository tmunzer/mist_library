'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### IMPORTS #####

import mlib.cli as _cli
import mlib.requests.const as const
import mlib.requests.orgs as orgs
import mlib.requests.sites as sites
import json

#### FUNCTIONS #####
def help():
    print('''
    Info:
    This Python3 module is built to help you to use and test Mist Library

    Help:
    When this module is imported, it will automatically authenticate you, create a Mist session, and 
    store is into the variable
            console.session

    You can use it afterward with Mist Library request. For example, you can do:
    The you will be able to use the script to generate and send request to the Mist Cloud. For example, 
    you can do:
            console.mlib.orgs.channels.country_codes_get(console.session)

    Some API request will ask for an "org_id" or a "site_id". The following commands are here to help
    you to retrieve (and store) this information:
            console.get_org_id()
            console.get_site_id()

    Udage:
    console.help()            Show this message
    console.get_org_id()      Help you to retrieve an Org ID
    console.get_site_id()     Help you to retrieve a Site ID
    console.show(data)        Nicely display API call response. Where "data" is is the API response
    ''')

def find_org_id():
    org_id = _cli.select_org(session)
    print("")
    print("Selected org id: %s" %org_id)
    return org_id[0]

def find_site_id(org_id=None):
    site_id = _cli.select_site(session, org_id=org_id)
    print("")
    print("Selected site id: %s" %site_id)
    return site_id[0]

def table(response):
    _cli.show(response)
    
def pretty(response):
    print(json.dumps(response, indent=2))
    
def __init():
    import mlib
    session = mlib.Mist_Session()
    return session

#### SCRIPT ENTRYPOINT #####
help()
session = __init()
