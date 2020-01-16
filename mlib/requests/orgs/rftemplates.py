def get(mist_session, org_id):
    uri = "/api/v1/orgs/%s/rftemplates" % org_id
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def create(mist_session, org_id, settings):
    uri = "/api/v1/orgs/%s/rftemplates" % org_id    
    body = settings
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def get_template(mist_session, org_id, rftemplate_id):
    uri = "/api/v1/orgs/%s/rftemplates/%s" %(org_id, rftemplate_id)
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def update_template(mist_session, org_id, rftemplate_id, settings):
    uri = "/api/v1/orgs/%s/rftemprftemplateslate/%s" %(org_id, rftemplate_id)
    body = settings
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def delete_template(mist_session, org_id, rftemplate_id):
    uri = "/api/v1/orgs/%s/rftemplates/%s" %(org_id, rftemplate_id)    
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp



