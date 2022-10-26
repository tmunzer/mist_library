########## INVENTORY ############

def get(mist_session, org_id, page=1, limit=100, device_type=None):
    uri = f"/api/v1/orgs/{org_id}/inventory" 
    query = {}
    if type in  ["ap", "switch", "gateway"]:
        query["type"] = device_type
    resp = mist_session.mist_get(uri, org_id=org_id, query=query, page=page, limit=limit)
    return resp

def add(mist_session, org_id, serials):
    uri = f"/api/v1/orgs/{org_id}/inventory" 
    body = serials
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def delete_multiple(mist_session, org_id, serials=[], macs=[]):
    uri = f"/api/v1/orgs/{org_id}/inventory" 
    body = {
        "op": "delete",
        "serials": serials,
        "macs": macs
    }
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def unassign(mist_session, org_id, macs):
    uri = f"/api/v1/orgs/{org_id}/inventory" 
    body = {
        "op": "unassign",
        "macs": macs,
    }
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def assign_macs_to_site(mist_session, org_id, site_id, macs):
    uri = f"/api/v1/orgs/{org_id}/inventory" 
    if type(macs) == str:
        macs = [macs]
    body = {
        "op": "assign",
        "site_id": site_id,
        "macs": macs,
        "no_reassign": False
    }
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp
