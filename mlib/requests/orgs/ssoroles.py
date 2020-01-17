########## SSO ROLES ############


def get(mist_session, org_id, page=1, limit=100):
    uri = "/api/v1/orgs/%s/ssoroles" % org_id
    resp = mist_session.mist_get(uri, org_id, page=page, limit=limit)
    return resp

def create(mist_session, org_id, ssorole):
    uri = "/api/v1/orgs/%s/ssoroles" % org_id
    body = ssorole
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, ssorole_id, ssorole):
    uri = "/api/v1/orgs/%s/ssoroles/%s" % (org_id, ssorole_id)   
    body = ssorole 
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def delete(mist_session, org_id, ssorole_id):
    uri = "/api/v1/orgs/%s/ssoroles/%s" % (org_id, ssorole_id)    
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def get__saml_metadata(mist_session, org_id, sso_id):
    uri = "/api/v1/orgs/%s/ssos/%s/metadata" %(org_id, sso_id)
    resp = mist_session.mist_get(uri, org_id)
    return resp

def download_saml_metadata(mist_session, org_id, sso_id):
    uri = "/api/v1/orgs/%s/ssos/%s/metadata.xml" %(org_id, sso_id)
    resp = mist_session.mist_get(uri, org_id)
    return resp

def get_sso_failures(mist_session, org_id, sso_id, page=1, limit=100):
    uri = "/api/v1/orgs/%s/ssos/%s/failures" %(org_id, sso_id)
    resp = mist_session.mist_get(uri, org_id, page=page, limit=limit)
    return resp