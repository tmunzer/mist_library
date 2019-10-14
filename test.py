import mlib

session = mlib.Mist_Session()
site_id = "fa018c13-008b-46ae-aa18-1eeb894a96c4"

print(mlib.requests.sites.virtual_beacons.get(session, site_id=site_id))