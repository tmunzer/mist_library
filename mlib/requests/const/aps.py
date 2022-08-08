
def get_ap_led_definition(mist_session):
    uri = "/api/v1/const/ap_led_status"
    resp = mist_session.mist_get(uri)
    return resp

def get_ap_models(mist_session):
    uri = "/api/v1/const/ap_models"
    resp = mist_session.mist_get(uri)
    return resp


