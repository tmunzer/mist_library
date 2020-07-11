from . import sites
from . import orgs

def route(level, object_name):
    if level == "orgs":
        if object_name == "":
            return orgs
        elif object_name == "admins":
            return orgs.admins
        elif object_name == "alarmtemplates":
            return orgs.alarmtemplates
        elif object_name == "assetfilters":
            return orgs.assetfilters
        elif object_name == "channels":
            return orgs.channels
        elif object_name == "deviceprofiles":
            return orgs.deviceprofiles
        elif object_name == "info":
            return orgs.info
        elif object_name == "inventory":
            return orgs.inventory
        elif object_name == "licenses":
            return orgs.licenses
        elif object_name == "mxclusters":
            return orgs.mxclusters
        elif object_name == "mxedges":
            return orgs.mxedges
        elif object_name == "mxtunnels":
            return orgs.mxtunnels
        elif object_name == "networktemplates":
            return orgs.networktemplates
        elif object_name == "psks":
            return orgs.psks
        elif object_name == "rftemplates":
            return orgs.rftemplates
        elif object_name == "secpolicies":
            return orgs.secpolicies
        elif object_name == "settings":
            return orgs.settings
        elif object_name == "sitegroups":
            return orgs.sitegroups
        elif object_name == "sites":
            return orgs.sites
        elif object_name == "ssoroles":
            return orgs.ssoroles
        elif object_name == "ssos":
            return orgs.ssos
        elif object_name == "stats":
            return orgs.stats
        elif object_name == "subscriptions":
            return orgs.subscriptions
        elif object_name == "templates":
            return orgs.templates
        elif object_name == "webhooks":
            return orgs.webhooks
        elif object_name == "wlans":
            return orgs.wlans
        elif object_name == "wxrules":
            return orgs.wxrules
        elif object_name == "wxtags":
            return orgs.wxtags
        elif object_name == "wxtunnels":
            return orgs.wxtunnels

    elif level == "sites":
        if object_name == "":
            return sites
        elif object_name == "assetfilters":
            return sites.assetfilters
        elif object_name == "assets":
            return sites.assets
        elif object_name == "beacons":
            return sites.beacons
        elif object_name == "client_events":
            return sites.client_events
        elif object_name == "const":
            return sites.const
        elif object_name == "devices":
            return sites.devices
        elif object_name == "info":
            return sites.info
        elif object_name == "insights":
            return sites.insights
        elif object_name == "iot":
            return sites.iot
        elif object_name == "location":
            return sites.location
        elif object_name == "maps":
            return sites.maps
        elif object_name == "psks":
            return sites.psks
        elif object_name == "rogues":
            return sites.rogues
        elif object_name == "rrm":
            return sites.rrm
        elif object_name == "rssizones":
            return sites.rssizones
        elif object_name == "settings":
            return sites.settings
        elif object_name == "system_events":
            return sites.system_events
        elif object_name == "vbeacons":
            return sites.vbeacons
        elif object_name == "webhooks":
            return sites.webhooks
        elif object_name == "wlans":
            return sites.wlans
        elif object_name == "wxrules":
            return sites.wxrules
        elif object_name == "wxtags":
            return sites.wxtags
        elif object_name == "wxtunnels":
            return sites.wxtunnels
        elif object_name == "zones":
            return sites.zones