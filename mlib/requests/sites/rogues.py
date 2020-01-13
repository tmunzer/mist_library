

def set_rogue(mist_session, site_id, rogue_param):
    uri = "/api/v1/sites/%s/setting" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=rogue_param)
    return resp


def get(mist_session, site_id, duration="1d", r_type="others", page=1, limit=100):
    uri = "/api/v1/sites/%s/insights/rogues" %site_id
    query = {"duration": duration, "type": r_type}
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp


def report(mist_session, site_id, r_type, fields):
    rogues = get(mist_session, site_id)
    result = []
    for rogue in rogues['result']["results"]:
        temp= []
        for field in fields:
            if field not in rogue:
                temp.append("")            
            else:
                temp.append("%s" % rogue[field])
        result.append(temp)
    return result