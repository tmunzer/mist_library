'''
Github repository: https://github.com/tmunzer/Mist_library/
Written by Thomas Munzer (tmunzer@juniper.net)
'''

import mlib as mist_lib
from mlib import cli
import sys
#### PARAMETERS #####
csv_separator = ","

mist = mist_lib.Mist_Session()
site_ids = cli.select_site(mist, allow_many=True)

  
settings = mist_lib.models.sites.Settings()
settings.rogue.cli()

for site_id in site_ids:
    mist_lib.requests.sites.settings.update(mist, site_id, settings.toJSON())
    print(mist_lib.requests.sites.settings.get(mist, site_id)['result']["rogue"])
sys.exit(0)