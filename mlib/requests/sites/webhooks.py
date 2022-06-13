
def get(mist_session, site_id, page=1, limit=100):
    uri = "/api/v1/sites/%s/webhooks" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id, page=page, limit=limit)
    return resp

def get_details(mist_session, site_id, webhook_id):
    uri = "/api/v1/sites/%s/webhooks/%s" % (site_id, webhook_id)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

def create(mist_session, site_id, webhook):
    uri = "/api/v1/sites/%s/webhooks" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=webhook)
    return resp


def update(mist_session, site_id, webhook_id, webhook_settings):
    uri = "/api/v1/sites/%s/webhooks/%s" % (site_id, webhook_id)
    resp = mist_session.mist_put(uri, site_id=site_id, body=webhook_settings)
    return resp


def delete(mist_session, site_id, webhook_id):
    uri = "/api/v1/sites/%s/webhooks/%s" % (site_id, webhook_id)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp


def report(mist_session, site_id, fields):
    webhooks = get(mist_session, site_id)
    result = []
    for webhook in webhooks['result']:
        temp = []
        for field in fields:
            if field not in webhook:
                temp.append("")
            elif field == "topics":
                temp.append(", ".join(webhook['topics']))            
            else:
                temp.append("%s" % webhook[field])
        result.append(temp)
    return result
