
def get_traffic_types(mist_session):
    uri = "/api/v1/const/traffic_types"
    resp = mist_session.mist_get(uri)
    return resp

