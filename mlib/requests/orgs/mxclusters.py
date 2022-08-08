def create(mist_session, org_id, mxcluster_settings):
    uri = f"/api/v1/orgs/{org_id}/mxclusters" 
    body = mxcluster_settings
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, mxcluster_id, body={}):
    uri = f"/api/v1/orgs/{org_id}/mxclusters/{mxcluster_id}" 
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp
    
def delete(mist_session, org_id, mxcluster_id):
    uri = f"/api/v1/orgs/{org_id}/mxclusters/{mxcluster_id}" 
    resp = mist_session.mist_delete(uri)
    return resp

def get(mist_session, org_id, page=1, limit=100):
    uri = f"/api/v1/orgs/{org_id}/mxclusters" 
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp


