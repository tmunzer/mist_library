"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list all WLANs from orgs/sites and their parameters, and save
it to a CSV file.
You can configure which fields you want to retrieve/save, and where the script
will save the CSV file.


It is possible to customize the columns to include in the report by modifying
the `REPORT_HEADERS` list.
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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./org_report_wlans.csv"
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"
-------
Examples:
python3 ./org_report_wlans.py
python3 ./org_report_wlans.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#### IMPORTS ####
import sys
import argparse
import csv
import logging

MISTAPI_MIN_VERSION = "0.56.0"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
except ImportError:
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
ENV_FILE = "~/.mist_env"
CSV_FILE = "./org_report_wlans.csv"
LOG_FILE = "./script.log"
CSV_DELIMITER = ","
REPORT_HEADERS = [
    "org_name",
    "org_id",
    "site_name",
    #"site_id",
    "site_country_code",
    #"id",
    "ssid",
    "for_site",
    "enabled",
    #"auth",
    #"auth_servers",
    #"acct_servers",
    "band",
    "interface",
    "vlan_id",
    #"dynamic_vlan",
    "hide_ssid",
    "template_id",
    # roam_mode,
    # auth_servers_nas_id,
    # auth_servers_nas_ip,
    # auth_servers_timeout,
    # auth_servers_retries,
    # acct_interim_interval,
    # band_steer,
    # band_steer_force_band5,
    # disable_11ax,
    # vlan_enabled,
    # vlan_pooling,
    # wxtunnel_id,
    # wxtunnel_remote_id,
    # mxtunneL_id,
    # dtim,
    # disable_wmm,
    # disable_uapsd,
    # use_eapol_v1,
    # legacy_overds,
    # hostname_id,
    # isolation,
    # arp_filter,
    # limit_bcast,
    # allow_mdns,
    # allow_ipv6_ndp,
    # no_static_ip,
    # no_static_dns,
    # enable_wireless_bridging,
    # apply_to,
    # wxtag_ids,
    # ap_ids,
    # wlan_limit_up_enabled,
    # wlan_limit_up,
    # wlan_limit_down_enabled,
    # wlan_limit_down,
    # client_limit_up_enabled,
    # client_limit_up,
    # client_limit_down_enabled,
    # client_limit_down,
    # max_idletime,
    # sle_excluded,
    # portal_template_url,
    # portal_image,
    # thumbnail,
    # portal_api_secret,
    # portal_sso_url,
    # portal_allowed_subnets,
    # portal_allowed_hostnames,
    # portal_denied_hostnames,
]

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """
    PROGRESS BAR AND DISPLAY
    """

    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print("Progress: ", end="")
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
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning("%s: Warning", message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info("%s", message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()

#### FUNCTIONS ####
def _retrieve_org_name(api_session:mistapi.APISession, org_id: str) -> dict:
    message = "Retrieving organization information"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.orgs.getOrg(api_session, org_id)
        if response.status_code == 200 and isinstance(response.data, dict):
            PB.log_success(message, inc=True)
            return response.data
        PB.log_failure(message, inc=True)
        sys.exit(2)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)

def _retrieve_sites_info(api_session:mistapi.APISession, site_ids:list) -> list:
    sites = []
    for site_id in site_ids:
        message = f"Retrieving information from site {site_id}"
        PB.log_message(message)
        try:
            response = mistapi.api.v1.sites.sites.getSiteInfo(api_session, site_id)
            if response.status_code == 200 and isinstance(response.data, dict):
                PB.log_success(message, inc=True)
                sites.append(response.data)
            else:
                PB.log_failure(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)
    return sites

def _retrieve_sites_wlans(api_session:mistapi.APISession, sites:list, org_info:dict, _) -> list:
    """Retrieve WLANs from specified sites."""
    wlans = []
    for site in sites:
        message = f"Retrieving WLANs from site {site['name']}"
        PB.log_message(message)
        try:
            response = mistapi.api.v1.sites.wlans.listSiteWlansDerived(
                api_session, site["id"]
            )
            if response.status_code == 200 and isinstance(response.data, list):
                for site_wlan in response.data:
                    site_wlan["org_name"] = org_info["name"]
                    site_wlan["org_id"] = org_info["id"]
                    site_wlan["site_name"] = site["name"]
                    site_wlan["site_id"] = site["id"]
                    site_wlan["site_country_code"] = site.get("country_code", "N/A")
                    wlans.append(site_wlan)
                PB.log_success(message, inc=True)
            else:
                PB.log_failure(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)
    return wlans


def _format_data(data_list: list) -> list:
    formatted = []
    # message = "Formatting results..."
    # PB.log_message(message, display_pbar=False)
    formatted.append(REPORT_HEADERS)
    for data in data_list:
        tmp = []
        for header in REPORT_HEADERS:
            tmp.append(data.get(header, ""))
        formatted.append(tmp)
    return formatted

def _save_as_csv(data: list, csv_file: str):
    PB.log_title(f"Saving report to {csv_file}", display_pbar=False)
    with open(csv_file, "w", encoding="UTF8", newline="") as f:
        csv_writer = csv.writer(f, delimiter=CSV_DELIMITER)
        csv_writer.writerows(data)
    PB.log_success("Saving to file ", display_pbar=False)


def _display_report(data: list):
    PB.log_title("Displaying report", display_pbar=False)
    print(mistapi.cli.tabulate(data[1:], headers=data[0], tablefmt="rounded_grid"))


def start(
    api_session: mistapi.APISession,
    org_id: str,
    site_ids: list,
    csv_file: str = CSV_FILE,
):
    """Main function to start the script."""
    if not org_id:
        org_id = mistapi.cli.select_org(api_session, allow_many=False)[0]
        site_ids = mistapi.cli.select_site(api_session, org_id=org_id, allow_many=True)
    if not site_ids:
        site_ids = mistapi.cli.select_site(api_session, org_id=org_id, allow_many=True)

    print("\n")
    PB.set_steps_total(len(site_ids) * 2 + 1)
    
    org_info = _retrieve_org_name(api_session, org_id)
    org_sites = _retrieve_sites_info(api_session, site_ids)
    wlans = _retrieve_sites_wlans(api_session, org_sites, org_info, site_ids)

    formatted_data = _format_data(wlans)
    _save_as_csv(formatted_data, csv_file)
    _display_report(formatted_data)

    # REPORT_HEADERS.insert(0, "origin")
    # REPORT_HEADERS.insert(1, "org_name")
    # REPORT_HEADERS.insert(2, "org_id")
    # REPORT_HEADERS.insert(3, "site_name")
    # REPORT_HEADERS.insert(4, "site_id")
    # REPORT_HEADERS.insert(5, "country_code")

    # print(mistapi.cli.tabulate(wlans_summarized, REPORT_HEADERS))

    # print("saving to file...")
    # with open(CSV_FILE, "w") as f:
    #     for column in REPORT_HEADERS:
    #         f.write(f"{column},")
    #     f.write("\r\n")
    #     for row in wlans_summarized:
    #         for field in row:
    #             f.write(field)
    #             f.write(CSV_SEPARATOR)
    #         f.write("\r\n")


def usage(message: str | None = None):
    """Display usage information."""
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list all WLANs from orgs/sites and their parameters, and save
it to a CSV file.
You can configure which fields you want to retrieve/save, and where the script
will save the CSV file.


It is possible to customize the columns to include in the report by modifying
the `REPORT_HEADERS` list.
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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./org_report_wlans.csv"
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"
-------
Examples:
python3 ./org_report_wlans.py
python3 ./org_report_wlans.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

""")
    if message:
        CONSOLE.error(message)


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
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to generate WLAN reports")
    parser.add_argument(
        "-e", "--env_file", help="define the env file to use", default=None
    )
    parser.add_argument(
        "-o",
        "--org_id",
        help="ID of the Mist Organization",
        default="",
    )
    parser.add_argument(
        "-s",
        "--site_ids",
        help="comma separated list of site IDs, e.g. 'site_id1,site_id2'",
        default="",
    )
    parser.add_argument(
        "-l",
        "--log_file",
        help="define the filepath/filename where to write the logs",
        default=LOG_FILE,
    )
    parser.add_argument(
        "-c",
        "--csv_file",
        help="Path to the CSV file where to save the result",
        default=CSV_FILE,
    )

    args = parser.parse_args()

    ENV_FILE = args.env_file
    ORG_ID = args.org_id
    SITE_IDS = args.site_ids.split(",")
    LOG_FILE = args.log_file
    CSV_FILE = args.csv_file

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    API_SESSION = mistapi.APISession(env_file=ENV_FILE)
    API_SESSION.login()

    start(API_SESSION, ORG_ID, [])
