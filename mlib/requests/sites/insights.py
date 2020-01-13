
def get(mist_session, site_id, start, end, metrics, page=1, limit=100):
    uri = "/api/v1/sites/%s/insights/stats" % site_id
    query = {"start": start, "end": end, "metrics": metrics}
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp

