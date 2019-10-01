
class Channels:

    def country_codes_get(self, mist_session):
        uri = "/api/v1/const/countries"
        resp = mist_session.mist_get(uri)
        return resp

    def ap_channels_get(self, mist_session, country_code):
        uri = "/api/v1/const/ap_channels?country_code=%s" % country_code
        resp = mist_session.mist_get(uri)
        return resp

class Sites():
    ########## SITES ############

    def mcreate(self, mist_session, org_id, name, timezone="", country_code="", address="", lat="", lng="", sitegroup_ids="", rftemplate_id="", secpolicy_id="", alarmtemplate_id=""):
        uri = "/api/v1/orgs/%s/sites" % org_id
        body = {
            "name": name,
            "timezone": timezone,
            "country_code": country_code,
            "rftemplate_id": rftemplate_id,
            "secpolicy_id": secpolicy_id,
            "alarmtemplate_id": alarmtemplate_id,
            "latlng": {
                "lat": lat,
                "lng": lng},
            "sitegroup_ids": sitegroup_ids,
            "address": address
        }
        resp = mist_session.mist_post(uri, org_id=org_id, body=body)
        return resp

    def mupdate(self, mist_session, org_id, site_id, update={}):
        uri = "/api/v1/sites/%s" % site_id
        fields = ["name", "timezone", "country_code", "address", "lat", "lng", "sitegroup_ids", "rftemplate_id", "secpolicy_id", "alarmtemplate_id"]
        body = {}
        for field in fields:
            if hasattr(update, field):
                body[field] = update[field]
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp
        
    def mdelete(self, mist_session, org_id, site_id):
        uri = "/api/v1/sites/%s" % site_id
        resp = mist_session.mist_delete(uri)
        return resp

    def mget(self, mist_session, org_id):
        uri = "/api/v1/orgs/%s/sites" % org_id
        resp = mist_session.mist_get(uri, org_id=org_id)
        return resp

    def stats(self, mist_session, site_id):
        uri = "/api/v1/sites/%s/stats" % site_id
        resp = mist_session.mist_get(uri)
        return resp

    ########## SITE GROUPS ############

class Site_Groups:

    def mget(self, mist_session, org_id):
        uri = "/api/v1/orgs/%s/sitegroups" % org_id
        resp = mist_session.mist_get(uri, org_id)
        return resp

    ########## INVENTORY ############
class Inventory:

    def mget(self, mist_session, org_id):
        uri = "/api/v1/orgs/%s/inventory" % org_id
        resp = mist_session.mist_get(uri, org_id=org_id)
        return resp

    def madd(self, mist_session, org_id, serials):
        uri = "/api/v1/orgs/%s/inventory" % org_id
        body = serials
        resp = mist_session.mist_post(uri, org_id=org_id, body=body)
        return resp
    
    def mdelete(self, mist_session, org_id, serials=[], macs=[]):
        uri = "/api/v1/orgs/%s/inventory" % org_id
        body = {
            "op": "delete",
            "serials": serials,
            "macs": macs
        }
        resp = mist_session.mist_delete(uri, org_id=org_id, body=body)
        return resp

    def assign(self, mist_session, org_id, site_id, macs):
        uri = "/api/v1/orgs/%s/inventory" % org_id
        body = {
            "op": "assign",
            "site_id": site_id,
            "macs": macs,
            "no_reassign": False
        }
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp

    def unassign(self, mist_session, org_id, macs):
        uri = "/api/v1/orgs/%s/inventory" % org_id
        body = {
            "op": "unassign",
            "macs": macs,
        }
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp
    

    ########## ADMINS ############
class Admins:    
    def mget(self, mist_session, org_id):
        uri = "/api/v1/orgs/%s/admins" % org_id
        resp = mist_session.mist_get(uri, org_id=org_id)
        return resp

    def mupdate(self, mist_session, org_id, admin_id, privileges=""):
        uri = "/api/v1/orgs/%s/admins/%s" % (org_id, admin_id)
        body = {}
        if privileges != "":
            body["privileges"] = privileges
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp

    def revoke(self, mist_session, org_id, admin_id):
        uri = "/api/v1/orgs/%s/admins/%s" %(org_id, admin_id)
        resp = mist_session.mist_delete(uri, org_id=org_id)
        return resp

    def create_invite(self, mist_session, org_id, email, privileges, first_name = "", last_name = "", hours = 24):
        uri =   "/api/v1/orgs/%s/invites" % org_id
        body = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "hours": hours,
            "privileges": privileges
        }
        resp = mist_session.mist_post(uri, org_id=org_id, body=body)
        return resp

    def delete_invite(self, mist_session, org_id, invite_id):
        uri = "/api/v1/orgs/%s/invites/%s" % (org_id, invite_id)
        resp = mist_session.mist_delete(uri, org_id=org_id)
        return resp

    def update_invite(self, mist_session, org_id, invite_id, email = "", privileges = "", first_name = "", last_name = "", hours = ""):
        uri = "/api/v1/orgs/%s/invites/%s" % (org_id, invite_id)
        body = {}
        if email != "":
            body["email"] = email
        if first_name != "":
            body["first_name"] = first_name
        if last_name != "":
            body["last_name"] = last_name
        if hours != "":
            body["hours"] = hours
        if privileges != "":
            body["privileges"] = privileges
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp

    ########## LICENSES ############
class Licences:

    def summary(self, mist_session, org_id):
        uri = "/api/v1/orgs/%s/licenses" % org_id
        resp = mist_session.mist_get(uri, org_id=org_id)
        return resp

    def usage_by_site(self, mist_session, org_id):
        uri = "/api/v1/orgs/%s/licenses/usages" % org_id
        resp = mist_session.mist_get(uri, org_id=org_id)
        return resp

    def claim_order(self, mist_session, org_id, code, mtype="all"):
        uri = "/api/v1/orgs/%s/claim" % org_id
        body = {
            "code": code,
            "type": mtype
        }
        resp = mist_session.mist_post(uri, org_id=org_id, body=body)
        return resp

    def move_to_another_org(self, mist_session, org_id, subscription_id, dst_org_id, quantity=1):
        uri = "/api/v1/orgs/%s/licenses" % org_id
        body = {
            "op": "amend",
            "subscription_id": subscription_id,
            "dst_org_id": dst_org_id,
            "quantity": quantity
        }
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp

    def undo_licence_move(self, mist_session, org_id, amendment_id):
        uri = "/api/v1/orgs/%s/licenses" % org_id
        body = {
            "op": "unamend",
            "amendment_id": amendment_id
        }
        resp = mist_session.mist_put(uri, org_id=org_id, body=body)
        return resp
