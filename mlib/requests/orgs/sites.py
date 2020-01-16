########## SITES ############

def create(mist_session, org_id, site_settings):
    uri = "/api/v1/orgs/%s/sites" % org_id
    body = site_settings
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, site_id, body={}):
    uri = "/api/v1/sites/%s" % site_id
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp
    
def delete(mist_session, org_id, site_id):
    uri = "/api/v1/sites/%s" % site_id
    resp = mist_session.mist_delete(uri)
    return resp

def get(mist_session, org_id, page=1, limit=100):
    uri = "/api/v1/orgs/%s/sites" % org_id
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp

def stats(mist_session, site_id, page=1, limit=100):
    uri = "/api/v1/sites/%s/stats" % site_id
    resp = mist_session.mist_get(uri, page=page, limit=limit)
    return resp

