
def get(mist_session, site_id, start, end, insights):
    uri = "/api/v1/sites/%s/insights/stats?start=%s&end=%s&metrics=%s" % (site_id, start, end, metrics)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

