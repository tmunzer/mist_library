import mlib as mist_lib
from mlib import cli
from tabulate import tabulate
import json

backup_file = "./org_backup.json"
session_file = ""

mist_session = mist_lib.Mist_Session(session_file)
org_id = "39ce2088-1dbe-4346-987a-1a5a88bab5ee"


data = mist_lib.requests.orgs.templates.get(mist_session, org_id)["result"]
for d in data:
    mist_lib.requests.orgs.templates.delete(mist_session, org_id, d["id"])


data = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
for d in data:
    mist_lib.requests.orgs.deviceprofiles.delete(mist_session, org_id, d["id"])


data = mist_lib.requests.orgs.mxtunnels.get(mist_session, org_id)["result"]
for d in data:
    mist_lib.requests.orgs.mxtunnels.delete(mist_session, org_id, d["id"])

data =  mist_lib.requests.orgs.mxclusters.get(mist_session, org_id)["result"]
for d in data:
    mist_lib.requests.orgs.mxclusters.delete(mist_session, org_id, d["id"])

data =  mist_lib.requests.orgs.site_groups.get(mist_session, org_id)["result"]
for d in data:
    mist_lib.requests.orgs.site_groups.delete(mist_session, org_id, d["id"])


data=mist_lib.requests.orgs.rftemplates.get(mist_session, org_id)["result"]
for d in data:
    mist_lib.requests.orgs.rftemplates.delete_template(mist_session, org_id, d["id"])

sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)['result']
for site in sites:
    maps = mist_lib.requests.sites.maps.get(mist_session, site["id"])["result"]
    for xmap in maps:
        mist_lib.requests.sites.maps.delete(mist_session, site["id"], xmap["id"])
    mist_lib.requests.orgs.sites.delete(mist_session, org_id, site["id"])
    