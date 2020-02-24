
def stats(mist_session, site_id, start, end, metrics, page=1, limit=100):
    uri = "/api/v1/sites/%s/insights/stats" % site_id
    query = {"start": start, "end": end, "metrics": metrics}
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp


def client(mist_session, site_id, client_mac, start, end, interval, metrics, page=1, limit=100):
    uri = "/api/v1/sites/%s/insights/client/%s/stats" %(site_id, client_mac)
    query = {"start": start, "end": end, "interval": interval, "metrics": metrics}
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp
