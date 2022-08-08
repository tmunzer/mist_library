
def get_country_codes(mist_session):
    uri = "/api/v1/const/countries"
    resp = mist_session.mist_get(uri)
    return resp

def get_ap_channels(mist_session, country_code):
    uri = "/api/v1/const/ap_channels"
    query = {"country_code":country_code}
    resp = mist_session.mist_get(uri=uri, query=query)
    return resp


