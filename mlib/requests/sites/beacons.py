def create(mist_session, site_id, beacon_settings):
    uri = "/api/v1/sites/%s/beacons" % site_id
    body = beacon_settings
    resp = mist_session.mist_post(uri, site_id=site_id, body=body)
    return resp

def update(mist_session, site_id, beacon_id, body={}):
    uri = "/api/v1/sites/%s/beacons/%s" % (site_id, beacon_id)
    resp = mist_session.mist_put(uri, site_id=site_id, body=body)
    return resp
    
def delete(mist_session, site_id, beacon_id):
    uri = "/api/v1/sites/%s/beacons/%s" % (site_id, beacon_id)
    resp = mist_session.mist_delete(uri)
    return resp

def get(mist_session, site_id, page=1, limit=100):
    uri = "/api/v1/sites/%s/beacons" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id, page=page, limit=limit)
    return resp


