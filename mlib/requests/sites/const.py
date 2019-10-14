
def get_applications(mist_session):
    uri = "/api/v1/const/applications"
    resp = mist_session.mist_get(uri)
    return resp

def get_ap_led_status(mist_session):
    uri = "/api/v1/const/ap_led_status"
    resp = mist_session.mist_get(uri)
    return resp

