########## ORG SETTINGS ############

def get(mist_session, org_id):
    uri = f"/api/v1/orgs/{org_id}/setting" 
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def update(mist_session, org_id, settings):
    uri = f"/api/v1/orgs/{org_id}/setting" 
    body = settings
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp


