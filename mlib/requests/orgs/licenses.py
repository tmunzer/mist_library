########## LICENSES ############
def summary(mist_session, org_id, page=1, limit=100):
    uri = f"/api/v1/orgs/{org_id}/licenses" 
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp

def usage_by_site(mist_session, org_id, page=1, limit=100):
    uri = f"/api/v1/orgs/{org_id}/licenses/usages" 
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp

def claim_order(mist_session, org_id, code, mtype="all"):
    uri = f"/api/v1/orgs/{org_id}/claim" 
    body = {
        "code": code,
        "type": mtype
    }
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def move_to_another_org(mist_session, org_id, subscription_id, dst_org_id, quantity=1):
    uri = f"/api/v1/orgs/{org_id}/licenses" 
    body = {
        "op": "amend",
        "subscription_id": subscription_id,
        "dst_org_id": dst_org_id,
        "quantity": quantity
    }
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def undo_licence_move(mist_session, org_id, amendment_id):
    uri = f"/api/v1/orgs/{org_id}/licenses" 
    body = {
        "op": "unamend",
        "amendment_id": amendment_id
    }
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

