
def country_codes_get(mist_session):
    uri = "/api/v1/const/countries"
    resp = mist_session.mist_get(uri)
    return resp

def ap_channels_get(mist_session, country_code):
    uri = "/api/v1/const/ap_channels"
    query = {"country_code":country_code}
    resp = mist_session.mist_get(uri=uri, query=query)
    return resp


