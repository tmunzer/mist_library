import mlib as mist_lib
from mlib import cli
from geopy import Nominatim
from tzwhere import tzwhere

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.__debug import Console
    console = Console(log_level)

#### PARAMETERS #####

geolocator = Nominatim(user_agent="import_app")
tzwhere = tzwhere.tzwhere()


mist = mist_lib.Mist_Session("./session.py")
#mist.save()
org_id = "203d3d02-dbc0-4c1b-9f41-76896a3330f4"#cli.select_org(mist)

def get_site_groups_list():
    response = mist_lib.org.site_groups.get(mist, org_id)
    tmp = {}
    for group in response["result"]:
        if "site_ids" in group:
            site_ids = group["site_ids"]
        else:
            site_ids = []
        tmp[group["name"]] = {"id": group["id"], "site_ids": site_ids}
    return tmp

def create_site_group(group_name):
    response = mist_lib.org.site_groups.create(mist, org_id, group_name)
    if response['status_code'] == 200:
        name = response["result"]["name"]
        sitegroups_id = response["result"]["id"]
        console.notice("Site Group %s created with ID %s" % (name, sitegroups_id))
        return sitegroups_id

def assign_site_to_group(site_id, group_name):
    site_groups = get_site_groups_list()
    if site_groups == {} or not group_name in site_groups:
        group_id = create_site_group(group_name)
        site_ids = [site_id]
    else:
        group_id = site_groups[group_name]["id"]
        site_ids = site_groups[group_name]["site_ids"]        
        site_ids.append(site_id)
    response = mist_lib.org.site_groups.update(mist, org_id, group_id, {"site_ids": site_ids})
    if response["status_code"] == 200:
        console.notice("Site succesfully added to group %s (id %s)" % (group_name, group_id))
        return group_id
    
def assign_groups_to_site(site_id, site_name, group_ids):
    response = mist_lib.org.sites.update(mist, org_id, site_id, {"sitegroup_ids": group_ids})
    if response["status_code"] == 200:
        console.notice("Groups succesfully added to site %s (id %s)" % (site_name, site_id))
        return response

def create_site(name, address):
    location = geolocator.geocode(address, addressdetails=True)
    if type(location) == "NoneType":
        console.error("Unable to find the address %s" % address)
    else:
        console.info("Address found: %s" %location)        
        tz = tzwhere.tzNameAt(location.latitude, location.longitude)
        country_code=str(location.raw["address"]["country_code"]).upper()
        response = mist_lib.org.sites.create(mist, org_id, name=name, address=location.address, lat=location.latitude, lng=location.longitude, timezone=tz, country_code=country_code)
        if response["status_code"]==200:
            console.notice("Site %s created succesfully with ID %s" % (name, response["result"]["id"]))
            return response["result"]

def new_site(name, address, groups):
    site = create_site(name, address)
    group_ids = []
    for group in groups:
        group_ids.append(assign_site_to_group(site["id"], group))
    assign_groups_to_site(site["id"], name, group_ids)



new_site("test", '41 rue de Villiers, Neuilly sur Seine', groups=["test1"])
new_site("test2", '121 rue d\'aguesseau, Boulogne Billancourt', groups=["test1", "test2"])