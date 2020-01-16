def get(mist_session, org_id):
    uri = "/api/v1/orgs/%s/stats" % org_id
    resp = mist_session.mist_get(uri, org_id)
    return resp

