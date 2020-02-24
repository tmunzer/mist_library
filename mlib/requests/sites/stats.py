def clients(mist_session, site_id):
    uri = "/api/v1/sites/%s/stats/clients" %(site_id)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

