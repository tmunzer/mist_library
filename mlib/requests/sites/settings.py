def get(mist_session, site_id):
    uri = "/api/v1/sites/%s/setting" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp


def update(mist_session, site_id, settings):
    uri = "/api/v1/sites/%s/setting" % site_id
    resp = mist_session.mist_put(uri, site_id=site_id, body=settings)
    return resp
