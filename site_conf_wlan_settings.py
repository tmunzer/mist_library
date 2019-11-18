wlan={
    "ssid": "mistworkshop",
    "enabled": True,
    "auth": {
        "type": "psk",
        "psk": "mistworkshop",
    },
    "roam_mode": "none",
    "band": "both",
    "band_steer": False,
    "rateset": {
        "24": {
            "min_rssi": 0,
            "template": "high-density"
        },
        "5": {
            "min_rssi": -70,
            "template": "high-density"
        }
    },
    "disable_11ax": False,
    "vlan_enabled": False,
    "hide_ssid": False,
    # filters
    "isolation": False,
    "arp_filter": True,
    "limit_bcast": False,
    "allow_mdns": False,

    # apply_to
    "apply_to": "site",
    "wxtag_ids": [],
    "ap_ids": [],

    "schedule": {
        "enabled": False
    },

    "qos": {
        "overwrite": False
    }

}
