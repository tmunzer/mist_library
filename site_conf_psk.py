'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### PARAMETERS #####
psk = {"name":'myUser', "passphrase":'myBadPassword', "ssid":'mySSID', "usage":'multi'}

#### IMPORTS #####
import mlib as mist_lib
from mlib import cli
from tabulate import tabulate

#### FUNCTIONS #####

#### SCRIPT ENTRYPOINT #####
mist = mist_lib.Mist_Session()
site_id = cli.select_site(mist)
  
psk = mist_lib.models.sites.psks.Psk()
psk.define(psk)
print(psk.toJSON())

mist_lib.requests.sites.psks.create(mist, site_id, psk.toJSON())
psks = mist_lib.requests.sites.psks.get(mist, site_id)['result']
cli.show(psks)

exit(0)
"""
for psk in psks:
    mist_lib.requests.sites.psks.delete(mist, site_id, psk_id=psk['id'])
print(mist_lib.requests.sites.psks.get(mist, site_id)['result'])
"""