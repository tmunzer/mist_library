
def reset(mist_session, site_id, map_id):
    uri = "/api/v1/sites/%s/location/ml/reset/map/%s" % (site_id, map_id)
    resp = mist_session.mist_post(uri, site_id=site_id)
    return resp

