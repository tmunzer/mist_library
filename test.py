import mlib

session = mlib.Mist_Session()
site_id = "fa018c13-008b-46ae-aa18-1eeb894a96c4"

psk = mlib.models.sites.psks.Psk()
print(psk.toJSON())

