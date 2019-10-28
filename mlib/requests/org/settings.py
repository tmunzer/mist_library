########## ORG SETTINGS ############

def get(mist_session, org_id):
    uri = "/api/v1/orgs/%s/setting" % org_id
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def update(mist_session, org_id, settings):
    uri = "/api/v1/orgs/%s/setting" % org_id    
    body = settings
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp


