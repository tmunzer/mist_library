def get(mist_session, org_id):
    uri = f"/api/v1/orgs/{org_id}/stats" 
    resp = mist_session.mist_get(uri, org_id)
    return resp

