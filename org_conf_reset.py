import mlib as mist_lib
from mlib import cli
from tabulate import tabulate
import json

backup_file = "./org_backup.json"
session_file = ""

mist_session = mist_lib.Mist_Session(session_file)
org_id = "00d3abaa-5601-430c-8137-3a66b8591173"


def delete_object(org_id, object_name, ids_to_not_delete):
    print(object_name)
    req = mist_lib.requests.route("orgs", object_name)
    data = req.get(mist_session, org_id)["result"]
    for d in data:
        if not d["id"] in ids_to_not_delete:
            req.delete(mist_session, org_id, d["id"])

ids_to_not_delete = []
object_names = [
                "webhooks",
                "assetfilters",
                "alarmtemplates",
                "deviceprofiles",
                "mxclusters",
                "mxtunnels",
                "psks",
                "rftemplates",
                "secpolicies",
                "sitegroups",
                "templates",
                "wlans",
                "wxrules",
                "wxtags",
                "wxtunnels", 
                "sites"]


primary_site = {
    "name": "Primary Site",
}
primary_site = mist_lib.orgs.sites.create(
    mist_session, org_id, primary_site)["result"]
ids_to_not_delete.append(primary_site["id"])

for object_name in object_names:
    delete_object(org_id, object_name, ids_to_not_delete)