class Auth:
    def __init__(self):
        self.m_type = ""  # psk, wep or eap
        # PSK
        self.psk = ""
        self.enable_mac_auth = False
        self.multi_psk_only = False
        self.pairwise = []
        self.wep_as_secondary_auth = False
        self.private_vlan = False
        # WEP
        self.keys = []
        self.key_idx = 1
        # EAP
        self.eap_reauth = False

    def psk_auth(self, psk, enable_mac_auth=False, multi_psk_only=False, wpa1_ccmp=False, wpa2_tkip=False, wpa1_tkip=False, wpa2_ccmp=True, wep_as_secondary_auth=False, private_vlan=False):
        self.m_type = "psk"
        self.psk = psk
        self.enable_mac_auth = enable_mac_auth
        self.multi_psk_only = multi_psk_only
        self.pairwise = []
        if wpa1_ccmp == True:
            self.pairwise.append("wpa1-ccmp")
        if wpa2_ccmp == True:
            self.pairwise.append("wpa2-ccmp")
        if wpa1_tkip == True:
            self.pairwise.append("wpa1_tkip")
        if wpa1_tkip == True:
            self.pairwise.append("wpa1-tkip")
        self.wep_as_secondary_auth = wep_as_secondary_auth
        if self.multi_psk_only == True:
            self.private_vlan = private_vlan
        else:
            self.private_vlan = False

    def wep_auth(self, keys=[], key_idx=1):
        self.m_type = "wep"
        self.keys = keys
        self.key_idx = key_idx

    def eap_auth(self, eap_reauth=False, wpa1_ccmp=False, wpa2_tkip=False, wpa1_tkip=False, wpa2_ccmp=True,):
        self.m_type = "eap"
        self.pairwise = []
        if wpa1_ccmp == True:
            self.pairwise.append("wpa1-ccmp")
        if wpa2_ccmp == True:
            self.pairwise.append("wpa2-ccmp")
        if wpa1_tkip == True:
            self.pairwise.append("wpa1_tkip")
        if wpa1_tkip == True:
            self.pairwise.append("wpa1-tkip")
        self.eap_reauth = eap_reauth

    def open_auth(self):
        self.m_type = "open"


class CoA_Server:
    def __init__(self, enabled=False, ip="0.0.0.0", port=3799, secret="", disable_event_timestamp_check=False):
        self.enabled = enabled
        self.ip = ip
        self.port = port
        self.secret = secret
        self.disable_event_timestamp_check = disable_event_timestamp_check


class Auth_Server:
    def __init__(self, host="0.0.0.0", port=1812, secret=""):
        self.host = host
        self.port = port
        self.secret = secret

    def add_auth_server(self, host="0.0.0.0", port=1812, secret=""):
        self.host = host
        self.port = port
        self.secret = secret


class Acct_Server:
    def __init__(self, host="0.0.0.0", port=1812, secret=""):
        self.host = host
        self.port = port
        self.secret = secret

    def add_acct_server(self, host="0.0.0.0", port=1812, secret=""):
        self.host = host
        self.port = port
        self.secret = secret


class Vlan:
    def __init__(self, id=0, name=""):
        self.id = id
        self.name = name
    
    def add_vlan(self, id, name):
        self.id = id
        self.name = name


class Dynamic_Vlan:
    def __init__(self, enabled=False, dynamic_vlan_type="standard", vlans=[], default_vlan_id=999, local_vlan_ids=[]):
        self.enabled = enabled
        self.dynamic_vlan_type = dynamic_vlan_type
        self.vlans = vlans
        self.default_vlan_id = default_vlan_id
        self.local_vlan_ids = local_vlan_ids


class Dns_Server_Rewrite:
    def __init__(self, enabled=False, radius_groups={}):
        self.enabled = enabled
        self.radius_groups = radius_groups

    def add_group(self, name, server):
        self.radius_groups[name] = server


class Portal:
    
    def __init__(self):
        self.enabled = False
        self.bypass_when_cloud_down = True
        self.facebook_client_id = ""
        self.forward_url = ""
        self.sms_enabled = False
        self.facebook_client_secret = ""
        self.passphrase_enabled = False
        self.amazon_email_domains = []
        self.google_enabled = False
        self.email_enabled = False
        self.external_portal_url = ""
        self.google_email_domains = []
        self.privacy = False
        self.microsoft_email_domains = []
        self.azure_enabled = False
        self.microsoft_enabled = False
        self.forward = False
        self.azure_client_secret = ""
        self.amazon_enabled = False
        self.auth =  "none"
        self.google_client_secret = ""
        self.amazon_client_secret = ""
        self.expire = 480
        self.facebook_enabled = False
        self.azure_tenant_id = ""
        self.password = ""
        self.amazon_client_id = ""
        self.google_client_id = ""
        self.facebook_email_domains = []
        self.azure_client_id = ""
        self.sms_provider = "manual"
        self.microsoft_client_secret = ""
        self.microsoft_client_id = ""
        self.smsMessageFormat = "Code {{code}} expires in {{duration}} minutes."
        

class Radius:

    def __init__(self, enabled=False, host="0.0.0.0", port=1812, secret=""):
        self.m_enabled = enabled
        self.host = host
        self.port = port
        self.secret = secret
        self.auth_server_nas_id = ""
        self.auth_server_nas_ip = ""
        self.auth_servers_timout = 5
        self.auth_servers_retry = 3
        self.auth_servers = []
        self.acct_servers = []
        self.acct_interim_interval = 0
        self.coa_server = CoA_Server()
        self.disable_event_timestamp_check = False
        self.dynamic_vlan = Dynamic_Vlan()
        self.m_type = "standard"
        self.vlans = ""
        self.default_vlan_id = 999
        self.local_vlan_ids = []
        self.radsec = ""
        self.server_name = ""
        self.dns_server_rewrite = Dns_Server_Rewrite()
        self.radius_groups = ""

    def set_auth_server_nas_id(self, auth_server_nas_id):
        self.auth_server_nas_id = auth_server_nas_id

    def set_auth_server_nas_ip(self, auth_server_nas_ip):
        self.auth_server_nas_ip = auth_server_nas_ip

    def set_auth_servers_timout(self, auth_servers_timout):
        if auth_servers_timout >= 0:
            self.auth_servers_timout = auth_servers_timout

    def set_auth_servers_retry(self, auth_servers_retry):
        if auth_servers_retry >= 0:
            self.auth_servers_retry = auth_servers_retry

    def set_auth_servers(self, auth_servers):
        self.auth_servers = auth_servers

    def set_host(self, host):
        self.host = host

    def set_port(self, port):
        if port > 0 and port < 65535:
            self.port = port

    def set_secret(self, secret):
        self.secret = secret

    def set_acct_servers(self, acct_servers):
        self.acct_servers = acct_servers

    def set_acct_interim_interval(self, acct_interim_interval):
        if acct_interim_interval >= 0:
            self.acct_interim_interval = acct_interim_interval

    def set_coa_server(self, enabled=False, ip="0.0.0.0", port=3799, secret="", disable_event_timestamp_check=False):
        self.coa_server = CoA_Server(enabled=enabled, ip=ip, port=port, secret=secret,
                                     disable_event_timestamp_check=disable_event_timestamp_check)

    def set_disable_event_timestamp_check(self, disable_event_timestamp_check):
        if disable_event_timestamp_check == True or disable_event_timestamp_check == False:
            self.disable_event_timestamp_check = disable_event_timestamp_check

    def set_dynamic_vlan(self, dynamic_vlan):
        self.dynamic_vlan = dynamic_vlan

    def set_enabled(self, m_enabled):
        if m_enabled == True or m_enabled == False:
            self.m_enabled = m_enabled

    def set_type(self, m_type):
        if m_type == "standard" or m_type == "airespace-interface-name":
            self.m_type = m_type

    def set_vlans(self, vlans):
        self.vlans = vlans

    def set_default_vlan_id(self, default_vlan_id):
        if default_vlan_id > 0 and default_vlan_id < 4095:
            self.default_vlan_id = default_vlan_id

    def set_radsec(self, radsec):
        self.radsec = radsec

    def set_server_name(self, server_name):
        self.server_name = server_name

    def set_dns_server_rewrite(self, dns_server_rewrite):
        self.dns_server_rewrite = dns_server_rewrite

    def set_radius_groups(self, radius_groups):
        self.radius_groups = radius_groups

class QoS:

    def __init__(self):
        self.m_class = "best_effort"
        self.overwrite = False

    def set_class(self, value):
        self.m_class = value

    def set_overwrite(self, value):
        self.overwrite = value


class Ssid:

    def __init__(self, ssid="", ssid_enabled=True, auth=Auth()):
        self.ssid = ssid
        self.dtim = 2
        self.hide_ssid = False
        self.disable_uapsd = False
        self.ssid_enabled = ssid_enabled
        self.auth = auth
        self.roam_mode = "none"
        self.apply_to = ""
        self.wxtag_ids = []
        self.ap_ids = []
        self.band = "both"
        self.band_steer = False
        self.band_steer_force_band5 = False
        self.isolaton = False
        self.arp_filter = False
        self.limit_bcast = False
        self.allow_mdns = False
        self.allow_ipv6_ndp = False
        self.no_static_ip = False
        self.no_static_dns = False
        self.enable_wireless_bridging = True
        self.vlan_enabled = False
        self.vlan_id = 0
        self.vlan_pooling = False
        self.schedule = ""
        self.hours = ""
        self.max_idletime = 1880
        self.sle_excluded = False


    #     "portal_allowed_hostnames": [],
    #     "org_id": "203d3d02-dbc0-4c1b-9f41-76896a3330f4",
       
    #     "wxtunnel_id": null,
    #     "allow_mdns": false,
    #     "portal_api_secret": "",
    #     "apply_to": "site",
    #     "roam_mode": "NONE",
    #     "app_limit": {
    #         "enabled": false,
    #         "apps": {},
    #         "wxtag_ids": {}
    #     },
    #     "id": "afe918bb-bc9d-4bcf-b164-64cc5a2d8e2b",
    #     "vlan_id": null,
    #     "wxtag_ids": null,
    #     "mxtunnel_id": null,
    #     "ssid": "WLAN1",
    #     "vlan_pooling": false,
    #     "disable_11ax": false,
    #     "wlan_limit_down": 20000,
    #     "dns_server_rewrite": null,
    #     "auth_servers_nas_id": "",
    #     "no_static_ip": false,
    #     "auth_servers_nas_ip": "",
    #     "site_id": "fa018c13-008b-46ae-aa18-1eeb894a96c4",
    #     "disable_wmm": false,
    #     "airwatch": {
    #         "username": "",
    #         "api_key": "",
    #         "console_url": "",
    #         "password": "",
    #         "enabled": false
    #     },
    #     "schedule": {
    #         "hours": {},
    #         "enabled": false
    #     },
    #     "dynamic_vlan": null,
    #     "max_idletime": 1800,
    #     "client_limit_up": 512,
    #     "coa_server": null,
    #     "auth": {
    #         "private_wlan": false,
    #         "key_idx": 1,
    #         "keys": [
    #             null,
    #             null,
    #             null,
    #             null
    #         ],
    #         "eap_reauth": false,
    #         "enable_mac_auth": false,
    #         "multi_psk_only": false,
    #         "type": "open"
    #     },
    #     "auth_servers": [],
    #     "limit_bcast": false,
    #     "band": "both",
    #     "wxtunnel_remote_id": null,
    #     "portal": {
    #         "bypass_when_cloud_down": true,
    #         "facebook_client_id": "",
    #         "forward_url": "",
    #         "sms_enabled": false,
    #         "facebook_client_secret": "",
    #         "passphrase_enabled": false,
    #         "amazon_email_domains": [],
    #         "google_enabled": false,
    #         "email_enabled": false,
    #         "external_portal_url": "",
    #         "google_email_domains": [],
    #         "privacy": false,
    #         "microsoft_email_domains": [],
    #         "azure_enabled": false,
    #         "microsoft_enabled": false,
    #         "forward": false,
    #         "azure_client_secret": "",
    #         "amazon_enabled": false,
    #         "auth": "none",
    #         "google_client_secret": "",
    #         "amazon_client_secret": "",
    #         "expire": 480,
    #         "facebook_enabled": false,
    #         "azure_tenant_id": "",
    #         "password": "",
    #         "amazon_client_id": "",
    #         "google_client_id": "",
    #         "facebook_email_domains": [],
    #         "azure_client_id": "",
    #         "enabled": false,
    #         "sms_provider": "manual",
    #         "microsoft_client_secret": "",
    #         "microsoft_client_id": "",
    #         "smsMessageFormat": "Code {{code}} expires in {{duration}} minutes."
    #     },
    #     "modified_time": 1565627060,
    #     "interface": "all",
    #     "portal_allowed_subnets": [],
    #     "cisco_cwa": {
    #         "enabled": false,
    #         "allowed_subnets": [],
    #         "allowed_hostnames": []
    #     },
    #     "portal_template_url": "https://papi-production.s3.amazonaws.com/portal_template/afe918bb-bc9d-4bcf-b164-64cc5a2d8e2b.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600&X-Amz-Date=20190930T125852Z&X-Amz-SignedHeaders=host&X-Amz-Security-Token=AgoJb3JpZ2luX2VjEOP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMSJHMEUCIQD7PuleZQjX4j%2FSaDlk9Vqu2vbvxIleVdgPL9oXynzA%2FgIgQngpt7YMSb%2FSL4v6vRvbbKPTFaMXqdBkDh9wxyJHUqcq4wMIvP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARABGgw2NjA2MTAwMzQ5NjYiDP8v%2BjxsLnQj9Xe%2BNiq3A5wzaPKC8%2Fne0mGYYDVC%2Byx0%2FS8GoXy9nqqEg9movanbTEagiKffc7b4o0TlDoc1BnnHrdjUSmP1EOlj8VVAt91i0B0eTFuiDza%2F4r%2FKGAh6RR4uSNH%2BIA6PgCNi7K1c5U5ULcMkNm8QvBMjy1SI75HX%2Fs65Vysbn7prOmoBIi7YtVmr5mYqwYVoE6z787uP61B%2BWqQ%2B0xfOM1f2THdMN8l5BA5A7SWBzEKY%2Fjv1gM2U%2FNytYTI8pO7dx3pPELlNfMs05pwLznSaD2StzIOdwI9ty7PMk%2BybeO8lPLizB07GRT%2F1ntOjQfZ4CE1IWhmbCONiukXOiJ6NJEWECRTiLg1MKDWOBqcMyLQlOlCaoZgh1U77t9pwmznwKzqBVM0pI3Cu94ozoVp35R6Eew%2B4TZAqyxbtzLNJqaPw73giuk%2FmQ8bw59ZCQHYHiI8wLv%2F%2BuHeH0H8sYy%2BxvMw6%2BR35rbjfjJ6vjXn5NjQI0o3LDbvMQyrTJLAhkXyINoFsonWnm%2F8ypgMg2bHHI1A5rZrawbD0I3kGY8wkLIeCp15Y5o6zmxjAfR8iaSnJjbr3sTkg5qgnQZcfeKYwtr%2FH7AU6tAHbaq2HeqY3M4Y1f4PNxU8AWdkIELds7iMg5f%2BigZ3XMt8%2B7ut01P06XpJS7Je8S8hi%2BuzJhyeiVxHxWXGrUqeROxQQMKJFlSVY5aJAmEJGnDBj%2FKZdH2rZ19HonX0PlHLrK5JWTGvHI0Pozj1%2F62sjlN%2BdnzpYajfHLfZ3Lczi8HVRr%2FamSPFXx8vAUV32XBTx12Xq8BrauBSENWe9lXKr%2BxV2yHa4o6Lhp3jbuWeTC1MPqOc%3D&X-Amz-Credential=ASIAZTT3NFULGQXE5JPG%2F20190930%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=d5b416673af7a011ec194fa348de65aae2d776f803708fe5819bbc8c4a36e10a",
    #     "client_limit_down": 1000,
    #     "use_eapol_v1": false,
    #     "ap_ids": null,
    #     "rateset": {
    #         "24": {
    #             "template": "no-legacy",
    #             "min_rssi": 0
    #         },
    #         "5": {
    #             "template": "no-legacy",
    #             "min_rssi": 0
    #         }
    #     },
    #     "enabled": true,
    #     "vlan_enabled": false,
    #     "arp_filter": false,
    #     "vlan_ids": [],
    #     "for_site": true,
    #     "band_steer": false,
    #     "no_static_dns": false,
    #     "portal_denied_hostnames": [],
    #     "radsec": {
    #         "enabled": false,
    #         "server_name": "",
    #         "servers": []
    #     },
    #     "app_qos": {
    #         "enabled": false,
    #         "apps": {}
    #     },
    #     "template_id": null,
    #     "wlan_limit_up": 10000
    # },
