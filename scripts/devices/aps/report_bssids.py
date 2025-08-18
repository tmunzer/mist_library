"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list all Access Points from orgs/sites and their associated BSSIDs,
and save it to a CSV file. You can configure which fields you want to retrieve/save,
and where the script will save the CSV file.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).


-------
Available fields:
- site_id
- site_name
- map_id
- map_name
- device_id
- device_mac
- device_name
- device_model
- device_notes
- device_ipv4
- device_ipv6
- device_bssid_mask         (note: if used, the script will create one entry for each radio)
- device_bssid_start        (note: if used, the script will create one entry for each radio)
- device_bssid_end          (note: if used, the script will create one entry for each radio)
- device_radio_band         (note: if used, the script will create one entry for each radio)
- device_radio_channel      (note: if used, the script will create one entry for each radio)
- device_radio_disabled     (note: if used, the script will create one entry for each radio)
- device_radio0_bssid_mask  (note: requires at least one enabled SSID on the radio_0)
- device_radio0_bssid_start (note: requires at least one enabled SSID on the radio_0)
- device_radio0_bssid_end   (note: requires at least one enabled SSID on the radio_0)
- device_radio0_band        (note: requires at least one enabled SSID on the radio_0)
- device_radio0_channel     (note: requires at least one enabled SSID on the radio_0)
- device_radio0_disabled
- device_radio1_bssid_mask  (note: requires at least one enabled SSID on the radio_1)
- device_radio1_bssid_start (note: requires at least one enabled SSID on the radio_1)
- device_radio1_bssid_end   (note: requires at least one enabled SSID on the radio_1)
- device_radio1_band        (note: requires at least one enabled SSID on the radio_1)
- device_radio1_channel     (note: requires at least one enabled SSID on the radio_1)
- device_radio1_disabled
- device_radio2_bssid_mask  (note: requires at least one enabled SSID on the radio_2)
- device_radio2_bssid_start (note: requires at least one enabled SSID on the radio_2)
- device_radio2_bssid_end   (note: requires at least one enabled SSID on the radio_2)
- device_radio2_band        (note: requires at least one enabled SSID on the radio_2)
- device_radio2_channel     (note: requires at least one enabled SSID on the radio_2)
- device_radio2_disabled

Deprecated fields:
- device_24_bssid_mask  (note: requires at least one enabled SSID on the 2.4GHz radio)
- device_24_bssid_start (note: requires at least one enabled SSID on the 2.4GHz radio)
- device_24_bssid_end   (note: requires at least one enabled SSID on the 2.4GHz radio)
- device_5_bssid_mask   (note: requires at least one enabled SSID on the 5GHz radio)
- device_5_bssid_start  (note: requires at least one enabled SSID on the 5GHz radio)
- device_5_bssid_end    (note: requires at least one enabled SSID on the 5GHz radio)
- device_6_bssid_mask   (note: requires at least one enabled SSID on the 6GHz radio)
- device_6_bssid_start  (note: requires at least one enabled SSID on the 6GHz radio)
- device_6_bssid_end    (note: requires at least one enabled SSID on the 6GHz radio)


-------
Options:
-h, --help          display this help

-o, --org_id=       Set the org_id
-s, --site_ids=     list of sites to use, comma separated. If not site defined, the
                    script will process all the sites from the Org.

-c, --csv_file=     Path to the CSV file where to save the output
                    default is "./validate_site_variables.csv"

-f, --fields=       list of fields to save in the CSV file
                    default fields:
                    device_name, device_mac, device_ipv4, device_ipv6,
                    device_radio0_band, device_radio0_bssid_start, device_radio0_bssid_end,
                    device_radio1_band, device_radio1_bssid_start, device_radio1_bssid_end,
                    device_radio2_band, device_radio2_bssid_start, device_radio2_bssid_end,
                    site_name, map_name

--e911              set the fields to E911 data fields (overrides -f/--fields):
                    device_name, device_ipv4, device_ipv6, device_radio_disabled,
                    device_radio_band, device_bssid_mask, site_name, map_name

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_bssids.py
python3 ./report_bssids.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#### IMPORTS #####
import sys
import logging
import getopt
import csv

MISTAPI_MIN_VERSION = "0.54.0"

try:
    import mistapi
    from mistapi.__logger import console
except Exception:
    print("""
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """)
    sys.exit(2)


#### PARAMETERS #####
CSV_SEPARATOR = ","
CSV_FILE = "./report_bssids.csv"

LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#### GLOBAL VARIABLES ####

DEFAULT_FIELDS = [
    "device_name",
    "device_ipv4",
    "device_ipv6",
    "device_radio0_disabled",
    "device_radio0_band",
    "device_radio0_bssid_start",
    "device_radio0_bssid_end",
    "device_radio1_disabled",
    "device_radio1_band",
    "device_radio1_bssid_start",
    "device_radio1_bssid_end",
    "device_radio2_disabled",
    "device_radio2_band",
    "device_radio2_bssid_start",
    "device_radio2_bssid_end",
    "site_name",
    "map_name",
]
E911_FIELDS = [
    "device_name",
    "device_ipv4",
    "device_ipv6",
    "device_radio_disabled",
    "device_radio_band",
    "device_bssid_mask",
    "site_name",
    "map_name",
]

#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print(f"Progress: ", end="")
        print(f"[{'█' * x}{'.' * (size - delta - x)}]", end="")
        print(f"{int(percent * 100)}%".rjust(5), end="")

    def _pb_new_step(
        self,
        message: str,
        result: str,
        inc: bool = False,
        size: int = 80,
        display_pbar: bool = True,
    ):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(
        self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True
    ):
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}")
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


###############################################################################
#### API FUNCTIONS ####
def _retrieve_sites_from_org(mist_session: mistapi.APISession, org_id: str):
    message = f"Retrieve the list of Site from Org {org_id}"
    try:
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.sites.listOrgSites(mist_session, org_id)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return mistapi.get_all(mist_session, resp)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error(
                "Unable to retrieve the Sites belonging to the Org... Please check the script logs."
            )
            LOGGER.error("Exiting...")
            sys.exit(255)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error(
            "Unable to retrieve the Sites belonging to the Org... Please check the script logs."
        )
        LOGGER.error("Exiting...")
        sys.exit(255)


def _retrieve_org_device_stats(apisession: mistapi.APISession, org_id: str):
    message = f"Retrieve the Device Stats from Org {org_id}"
    try:
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.stats.listOrgDevicesStats(
            apisession,
            org_id,
            type="ap",
            fields="radio_stat,ip_stat,mac,id,name,site_id,map_id,model",
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return mistapi.get_all(apisession, resp)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error(
                "Unable to retrieve the Device Stats... Please check the script logs."
            )
            LOGGER.error("Exiting...")
            sys.exit(255)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error(
            "Unable to retrieve the Device Stats... Please check the script logs."
        )
        LOGGER.error("Exiting...")
        sys.exit(255)


def _retrieve_ap_mac(apisession: mistapi.APISession, org_id: str) -> list:
    message = f"Retrieve the AP Radio MAC from Org {org_id}"
    try:
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.devices.listOrgApsMacs(apisession, org_id)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return mistapi.get_all(apisession, resp)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error(
                "Unable to retrieve the AP Radio MACs... Please check the script logs."
            )
            LOGGER.error("Exiting...")
            sys.exit(255)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error(
            "Unable to retrieve the AP Radio MACs... Please check the script logs."
        )
        LOGGER.error("Exiting...")
        sys.exit(255)


def _retrieve_site_maps(apisession: mistapi.APISession, site_id: str):
    message = f"Retrieve the list of Maps from Site {site_id}"
    try:
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.sites.maps.listSiteMaps(apisession, site_id)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return mistapi.get_all(apisession, resp)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


###############################################################################
#### FUNCTIONS ####
def _gen_entry(
    device: dict, site_data: dict, map_data: dict, radio_mac: str|None, fields: list
):
    data = []
    for field in fields:
        ### SITE
        if field == "site_id":
            data.append(site_data.get("id"))
        elif field == "site_name":
            data.append(site_data.get("name"))
        ### MAC
        elif field == "map_id":
            data.append(map_data.get("id"))
        elif field == "map_name":
            data.append(map_data.get("name"))
        ### DEVICE
        elif field == "device_id":
            data.append(device.get("id"))
        elif field == "device_mac":
            data.append(device.get("mac"))
        elif field == "device_name":
            if device.get("name"):
                data.append(device.get("name"))
            else:
                data.append(device.get("mac"))
        elif field == "device_model":
            data.append(device.get("model"))
        elif field == "device_notes":
            data.append(device.get("notes"))
        ### DEVICE IP
        elif field == "device_ipv4":
            if not device.get("ip_stat"):
                data.append(None)
            else:
                data.append(device.get("ip_stat", {}).get("ip"))
        elif field == "device_ipv6":
            if not device.get("ip_stat"):
                data.append(None)
            else:
                data.append(device.get("ip_stat", {}).get("ip6"))
        ### DEVICE MAC
        elif field == "device_bssid_mask":
            data.append(radio_mac)
        elif field == "device_bssid_start":
            data.append(radio_mac)
        elif field == "device_bssid_end":
            if radio_mac:
                data.append(hex(int(radio_mac, 16) + 15).replace("0x", ""))
            else:
                data.append(None)
        elif field == "device_radio_band":
            radio = next(
                (
                    x
                    for x in device.get("radio_stat", {}).values()
                    if x.get("mac") == radio_mac
                ),
                None,
            )
            if radio and radio.get("usage"):
                data.append(radio.get("usage") + "GHz")
            else:
                data.append(None)
        elif field == "device_radio_channel":
            try:
                radio = next(
                    (
                        x
                        for x in device.get("radio_stat", {}).values()
                        if x.get("mac") == radio_mac
                    ),
                    None,
                )
                if radio:
                    data.append(radio.get("channel", None))
            except StopIteration:
                data.append(None)
        elif field == "device_radio_disabled":
            radio = next(
                (
                    x
                    for x in device.get("radio_stat", {}).values()
                    if x.get("mac") == radio_mac
                ),
                None,
            )
            if radio:
                data.append(radio.get("disabled", False))
            else:
                data.append(True)
        ### DEVICE MAC RADIO0
        elif field == "device_radio0_bssid_mask":
            if not device.get("radio_stat", {}).get("band_24", {}).get("mac"):
                data.append(None)
            else:
                data.append(device.get("radio_stat", {}).get("band_24", {}).get("mac"))
        elif field == "device_radio0_bssid_start":
            if not device.get("radio_stat", {}).get("band_24", {}).get("mac"):
                data.append(None)
            else:
                data.append(device.get("radio_stat", {}).get("band_24", {}).get("mac"))
        elif field == "device_radio0_bssid_end":
            if not device.get("radio_stat", {}).get("band_24", {}).get("mac"):
                data.append(None)
            else:
                tmp = device.get("radio_stat", {}).get("band_24", {}).get("mac")
                if tmp:
                    data.append(hex(int(tmp, 16) + 15).replace("0x", ""))
                else:
                    data.append(None)
        elif field == "device_radio0_channel":
            data.append(
                device.get("radio_stat", {}).get("band_24", {}).get("channel", None)
            )
        elif field == "device_radio0_band":
            if not device.get("radio_stat", {}).get("band_24", {}).get("usage"):
                data.append(None)
            else:
                data.append(
                    device.get("radio_stat", {}).get("band_24", {}).get("usage") + "GHz"
                )
        elif field == "device_radio0_disabled":
            if not device.get("radio_stat", {}).get("band_24"):
                data.append(None)
            elif not device.get("radio_stat", {}).get("band_24", {}).get("disabled"):
                data.append(False)
            else:
                data.append(
                    device.get("radio_stat", {}).get("band_24", {}).get("disabled")
                )
        ### DEVICE MAC RADIO1
        elif field == "device_radio1_bssid_mask":
            if not device.get("radio_stat", {}).get("band_5", {}).get("mac"):
                data.append(None)
            else:
                data.append(device.get("radio_stat", {}).get("band_5", {}).get("mac"))
        elif field == "device_radio1_bssid_start":
            if not device.get("radio_stat", {}).get("band_5", {}).get("mac"):
                data.append(None)
            else:
                data.append(device.get("radio_stat", {}).get("band_5", {}).get("mac"))
        elif field == "device_radio1_bssid_end":
            if not device.get("radio_stat", {}).get("band_5", {}).get("mac"):
                data.append(None)
            else:
                tmp = device.get("radio_stat", {}).get("band_5", {}).get("mac")
                if tmp:
                    data.append(hex(int(tmp, 16) + 15).replace("0x", ""))
                else:
                    data.append(None)
        elif field == "device_radio1_channel":
            data.append(
                device.get("radio_stat", {}).get("band_5", {}).get("channel", None)
            )
        elif field == "device_radio1_band":
            if not device.get("radio_stat", {}).get("band_5", {}).get("usage"):
                data.append(None)
            else:
                data.append(
                    device.get("radio_stat", {}).get("band_5", {}).get("usage") + "GHz"
                )
        elif field == "device_radio1_disabled":
            if not device.get("radio_stat", {}).get("band_5"):
                data.append(None)
            elif not device.get("radio_stat", {}).get("band_5", {}).get("disabled"):
                data.append(False)
            else:
                data.append(
                    device.get("radio_stat", {}).get("band_5", {}).get("disabled")
                )
        ### DEVICE MAC RADIO2
        elif field == "device_radio2_bssid_mask":
            if not device.get("radio_stat", {}).get("band_6", {}).get("mac"):
                data.append(None)
            else:
                data.append(device.get("radio_stat", {}).get("band_6", {}).get("mac"))
        elif field == "device_radio2_bssid_start":
            if not device.get("radio_stat", {}).get("band_6", {}).get("mac"):
                data.append(None)
            else:
                data.append(device.get("radio_stat", {}).get("band_6", {}).get("mac"))
        elif field == "device_radio2_bssid_end":
            if not device.get("radio_stat", {}).get("band_6", {}).get("mac"):
                data.append(None)
            else:
                tmp = device.get("radio_stat", {}).get("band_6", {}).get("mac")
                if tmp:
                    data.append(hex(int(tmp, 16) + 15).replace("0x", ""))
                else:
                    data.append(None)
        elif field == "device_radio2_channel":
            data.append(
                device.get("radio_stat", {}).get("band_6", {}).get("channel", None)
            )
        elif field == "device_radio2_band":
            if not device.get("radio_stat", {}).get("band_6", {}).get("usage"):
                data.append(None)
            else:
                data.append(
                    device.get("radio_stat", {}).get("band_6", {}).get("usage") + "GHz"
                )
        elif field == "device_radio2_disabled":
            if not device.get("radio_stat", {}).get("band_6"):
                data.append(None)
            elif not device.get("radio_stat", {}).get("band_6", {}).get("disabled"):
                data.append(False)
            else:
                data.append(
                    device.get("radio_stat", {}).get("band_6", {}).get("disabled")
                )
    return data


def _gen_report(
    sites: list, device_stats: list, ap_radio_mac: list, fields: list, site_ids
):
    data = []
    PB.set_steps_total(len(device_stats))
    for device in device_stats:
        LOGGER.debug("_gen_report: processing device %s", device)
        device_mac = device.get("mac")
        LOGGER.debug("_gen_report: device_mac: %s", device_mac)
        site_id = device.get("site_id")
        LOGGER.debug("_gen_report: site_id: %s", site_id)
        map_id = device.get("map_id")
        LOGGER.debug("_gen_report: map_id: %s", map_id)
        site_data = {}
        map_data = {}
        radio_mac_list = []
        message = f"Processing device {device_mac}"
        PB.log_message(message)
        try:
            if site_ids and site_id not in site_ids:
                LOGGER.info(
                    "_gen_report: device %s DOES NOT belong to a site in the site_ids list (%s)... skipping it...",
                    device_mac,
                    site_id,
                )
            else:
                LOGGER.info(
                    "_gen_report: device %s DOES belong to a site in the site_ids list or the site_ids list is empty (%s)... processing it...",
                    device_mac,
                    site_id,
                )
                if device_mac:
                    radio_mac_list = next(
                        x["radio_mac"] for x in ap_radio_mac if x["mac"] == device_mac
                    )
                    LOGGER.debug("_gen_report: radio_mac_list: %s", radio_mac_list)
                if site_id:
                    site_data = next(x for x in sites if x["id"] == site_id)
                if map_id and site_data:
                    map_data = next(x for x in site_data["maps"] if x["id"] == map_id)
                if (
                    "device_bssid_mask" in fields
                    or "device_bssid_start" in fields
                    or "device_bssid_end" in fields
                    or "device_radio_band" in fields
                    or "device_radio_channel" in fields
                    or "device_radio_disabled" in fields
                ):
                    for radio_mac in radio_mac_list:
                        new_entry = _gen_entry(
                            device, site_data, map_data, radio_mac, fields
                        )
                        LOGGER.info("_gen_report: generated entry: %s", new_entry)
                        data.append(new_entry)
                else:
                    new_entry = _gen_entry(device, site_data, map_data, None, fields)
                    LOGGER.info("_gen_report: generated entry: %s", new_entry)
                    data.append(new_entry)
            PB.log_success(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)

    return data


def start(
    apisession: mistapi.APISession,
    org_id: str = "",
    site_ids: list = [],
    fields: list = DEFAULT_FIELDS,
    e911: bool = False,
    csv_file: str = CSV_FILE,
):
    """
    Main function to start the script and generate the report.
    :param apisession: mistapi.APISession object
    :param org_id: Organization ID to use (optional, will prompt if not provided)
    :param site_ids: List of Site IDs to use (optional, will prompt if not provided)
    :param fields: List of fields to include in the report (optional, defaults to DEFAULT_FIELDS)
    :param e911: Boolean to indicate if E911 fields should be used (optional, defaults to False)
    :param csv_file: Path to the CSV file where the report will be saved (optional, defaults to CSV_FILE)
    """
    LOGGER.debug("start: init script param org_id: %s", org_id)
    LOGGER.debug("start: init script param site_ids: %s", site_ids)
    LOGGER.debug("start: init script param fields: %s", fields)
    LOGGER.debug("start: init script param e911: %s", e911)
    LOGGER.debug("start: init script param csv_file: %s", csv_file)

    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
        site_ids = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=True)

    if e911:
        fields = E911_FIELDS
    elif not fields:
        fields = DEFAULT_FIELDS

    LOGGER.debug("start: post init script param org_id: %s", org_id)
    LOGGER.debug("start: post init script param site_ids: %s", site_ids)
    LOGGER.debug("start: post init script param fields: %s", fields)

    sites = _retrieve_sites_from_org(apisession, org_id)
    for site in sites:
        site["maps"] = _retrieve_site_maps(apisession, site["id"])
    device_stats = _retrieve_org_device_stats(apisession, org_id)
    ap_radio_mac = _retrieve_ap_mac(apisession, org_id)

    data = _gen_report(sites, device_stats, ap_radio_mac, fields, site_ids)
    with open(csv_file, "w") as c:
        writer = csv.writer(c)
        writer.writerow(fields)
        writer.writerows(data)

    print()
    print()
    print(mistapi.cli.tabulate(data, headers=fields))
    print()
    print()
    console.info(f"Report saved into {csv_file}")


###############################################################################
### USAGE
def usage(error_message: str | None = None):
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list all Access Points from orgs/sites and their associated BSSIDs,
and save it to a CSV file. You can configure which fields you want to retrieve/save,
and where the script will save the CSV file.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).


-------
Available fields:
- site_id
- site_name
- map_id
- map_name
- device_id
- device_mac
- device_name
- device_model
- device_notes
- device_ipv4
- device_ipv6
- device_bssid_mask         (note: if used, the script will create one entry for each radio)
- device_bssid_start        (note: if used, the script will create one entry for each radio)
- device_bssid_end          (note: if used, the script will create one entry for each radio)
- device_radio_band         (note: if used, the script will create one entry for each radio)
- device_radio_channel      (note: if used, the script will create one entry for each radio)
- device_radio_disabled     (note: if used, the script will create one entry for each radio)
- device_radio0_bssid_mask  (note: requires at least one enabled SSID on the radio_0)
- device_radio0_bssid_start (note: requires at least one enabled SSID on the radio_0)
- device_radio0_bssid_end   (note: requires at least one enabled SSID on the radio_0)
- device_radio0_band        (note: requires at least one enabled SSID on the radio_0)
- device_radio0_channel     (note: requires at least one enabled SSID on the radio_0)
- device_radio0_disabled
- device_radio1_bssid_mask  (note: requires at least one enabled SSID on the radio_1)
- device_radio1_bssid_start (note: requires at least one enabled SSID on the radio_1)
- device_radio1_bssid_end   (note: requires at least one enabled SSID on the radio_1)
- device_radio1_band        (note: requires at least one enabled SSID on the radio_1)
- device_radio1_channel     (note: requires at least one enabled SSID on the radio_1)
- device_radio1_disabled
- device_radio2_bssid_mask  (note: requires at least one enabled SSID on the radio_2)
- device_radio2_bssid_start (note: requires at least one enabled SSID on the radio_2)
- device_radio2_bssid_end   (note: requires at least one enabled SSID on the radio_2)
- device_radio2_band        (note: requires at least one enabled SSID on the radio_2)
- device_radio2_channel     (note: requires at least one enabled SSID on the radio_2)
- device_radio2_disabled

Deprecated fields:
- device_24_bssid_mask  (note: requires at least one enabled SSID on the 2.4GHz radio)
- device_24_bssid_start (note: requires at least one enabled SSID on the 2.4GHz radio)
- device_24_bssid_end   (note: requires at least one enabled SSID on the 2.4GHz radio)
- device_5_bssid_mask   (note: requires at least one enabled SSID on the 5GHz radio)
- device_5_bssid_start  (note: requires at least one enabled SSID on the 5GHz radio)
- device_5_bssid_end    (note: requires at least one enabled SSID on the 5GHz radio)
- device_6_bssid_mask   (note: requires at least one enabled SSID on the 6GHz radio)
- device_6_bssid_start  (note: requires at least one enabled SSID on the 6GHz radio)
- device_6_bssid_end    (note: requires at least one enabled SSID on the 6GHz radio)


-------
Options:
-h, --help          display this help

-o, --org_id=       Set the org_id
-s, --site_ids=     list of sites to use, comma separated. If not site defined, the
                    script will process all the sites from the Org.

-c, --csv_file=     Path to the CSV file where to save the output
                    default is "./validate_site_variables.csv"

-f, --fields=       list of fields to save in the CSV file
                    default fields:
                    device_name, device_mac, device_ipv4, device_ipv6,
                    device_radio0_band, device_radio0_bssid_start, device_radio0_bssid_end,
                    device_radio1_band, device_radio1_bssid_start, device_radio1_bssid_end,
                    device_radio2_band, device_radio2_bssid_start, device_radio2_bssid_end,
                    site_name, map_name

--e911              set the fields to E911 data fields (overrides -f/--fields):
                    device_name, device_ipv4, device_ipv6, device_radio_disabled,
                    device_radio_band, device_bssid_mask, site_name, map_name

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_bssids.py
python3 ./report_bssids.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

""")
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__,
        )


###############################################################################
### ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:s:e:l:f:",
            ["help", "org_id=", "site_ids=", "env=", "log_file=", "fields=", "e911"],
        )
    except getopt.GetoptError as err:
        usage(err.msg)

    ORG_ID = ""
    SITE_IDS = []
    E911 = False
    FIELDS = []
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-s", "--site_ids"]:
            for s in a.split(","):
                SITE_IDS.append(s.strip())
        elif o in ["-f", "--fields"]:
            for f in a.split(","):
                FIELDS.append(f.strip())
                if (
                    "device_24_" in f
                    or "device_5_" in f
                    or "device_6_" in f
                ):
                    console.warning(
                        f"The field {f} is deprecated and will be removed in a future version. "
                        "Please use the new device_radio0, device_radio1, and device_radio2 fields.",
                        
                    )
        elif o == "--e911":
            E911 = True
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    start(APISESSION, ORG_ID, SITE_IDS, FIELDS, E911)
