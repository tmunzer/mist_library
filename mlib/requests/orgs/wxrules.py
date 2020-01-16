def create(mist_session, org_id, wxrule_settings):
    uri = "/api/v1/orgs/%s/wxrules" % org_id
    body = wxrule_settings
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, wxrule_id, body={}):
    uri = "/api/v1/orgs/%s/wxrules/%s" % (org_id, wxrule_id)
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp
    
def delete(mist_session, org_id, wxrule_id):
    uri = "/api/v1/orgs/%s/wxrules/%s" % (org_id, wxrule_id)
    resp = mist_session.mist_delete(uri)
    return resp

def get(mist_session, org_id, page=1, limit=100):
    uri = "/api/v1/orgs/%s/wxrules" % org_id
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp


