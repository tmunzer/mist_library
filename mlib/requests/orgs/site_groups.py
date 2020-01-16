########## SITE GROUPS ############


def get(mist_session, org_id, page=1, limit=100):
    uri = "/api/v1/orgs/%s/sitegroups" % org_id
    resp = mist_session.mist_get(uri, org_id, page=page, limit=limit)
    return resp

def create(mist_session, org_id, group_name):
    uri = "/api/v1/orgs/%s/sitegroups" % org_id
    body = {"name": group_name}
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, sitegroup_id, body):
    uri = "/api/v1/orgs/%s/sitegroups/%s" % (org_id, sitegroup_id)    
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def delete(mist_session, org_id, sitegroup_id):
    uri = "/api/v1/orgs/%s/sitegroups/%s" % (org_id, sitegroup_id)    
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp
