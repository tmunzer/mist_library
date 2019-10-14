
def get(mist_session, site_id):
    uri = "/api/v1/sites/%s/zones" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp
