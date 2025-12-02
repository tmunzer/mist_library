"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python Script to report the usage of the WAN Services across Gateway Templates,
Hub Profiles, Service Policies and Gateways.
The script will generate two CSV files:
- A detailed file showing the usage of each WAN service per Gateway Template,
  Hub Profile, Service Policy and Gateway
- A summary file showing if a WAN service is used or not used across the 
  Organization.


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
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Organization ID

-d, --csv_details=          Path to the CSV file where to save the detailed result
                            default: ./report_wan_services_usage.csv
-s, --csv_summary=          Path to the CSV file where to save the summary result
                            default: ./report_wan_services_usage_summary.csv

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./report_wan_services_usage.py
python3 ./report_wan_services_usage.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx 
"""

#### IMPORTS ####
import sys
import argparse
import logging
import csv
from typing import Tuple

MISTAPI_MIN_VERSION = "0.52.4"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
except ImportError:
    print(
        """
        Critical:
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)

#### PARAMETERS #####
ENV_FILE = "~/.mist_env"
CSV_DETAILS_FILE = "./report_wan_services_usage.csv"
CSV_SUMMARY_FILE = "./report_wan_services_usage_summary.csv"
LOG_FILE = "./script.log"

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


#####################################################################
#### FUNCTIONS ####
def _retrieve_services(mist_session: mistapi.APISession, org_id: str) -> list:
    """
    Retrieve the WAN services of an Org

    PARAMS
    -------
    mist_session : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where to retrieve the WAN services

    RETURN
    -------
    list of WAN services
    """
    services = []
    message = "Retrieving WAN services"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.services.listOrgServices(
            mist_session, org_id=org_id, limit=1000
        )
        if resp.status_code == 200:
            services = mistapi.get_all(mist_session, resp)
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Response: %s", resp.raw_data)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
    return services


def _retrieve_gatewaytemplates(mist_session: mistapi.APISession, org_id: str) -> list:
    """
    Retrieve the Gateway Templates of an Org

    PARAMS
    -------
    mist_session : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where to retrieve the Gateway Templates

    RETURN
    -------
    list of Gateway Templates
    """
    templates = []
    message = "Retrieving Gateway Templates"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates(
            mist_session, org_id=org_id, limit=1000
        )
        if resp.status_code == 200:
            templates = mistapi.get_all(mist_session, resp)
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Response: %s", resp.raw_data)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
    return templates


def _retrieve_org_hubprofiles(mist_session: mistapi.APISession, org_id: str) -> list:
    """
    Retrieve the Hub Profiles of an Org

    PARAMS
    -------
    mist_session : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where to retrieve the Hub Profiles

    RETURN
    -------
    list of Hub Profiles
    """
    profiles = []
    message = "Retrieving Hub Profiles"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles(
            mist_session, org_id=org_id, type="gateway", limit=1000
        )
        if resp.status_code == 200:
            profiles = mistapi.get_all(mist_session, resp)
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Response: %s", resp.raw_data)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
    return profiles


def _retrieve_org_servicepolicies(
    mist_session: mistapi.APISession, org_id: str
) -> list:
    """
    Retrieve the Service Policies of an Org

    PARAMS
    -------
    mist_session : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where to retrieve the Service Policies

    RETURN
    -------
    list of Service Policies
    """
    policies = []
    message = "Retrieving Service Policies"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies(
            mist_session, org_id=org_id, limit=1000
        )
        if resp.status_code == 200:
            policies = mistapi.get_all(mist_session, resp)
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Response: %s", resp.raw_data)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
    return policies


def _retrieve_gateways(mist_session: mistapi.APISession, org_id: str) -> list:
    """
    Retrieve the Gateways of an Org

    PARAMS
    -------
    mist_session : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where to retrieve the Gateways

    RETURN
    -------
    list of Gateways
    """
    gateways = []
    message = "Retrieving Gateways Inventory"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.inventory.getOrgInventory(
            mist_session, org_id=org_id, type="gateway", limit=1000
        )
        if resp.status_code == 200:
            devices = mistapi.get_all(mist_session, resp)
            PB.log_success(message, display_pbar=False)
            LOGGER.debug("Total Gateways found: %d", len(devices))
            LOGGER.debug(devices)
            for device in devices:
                if device.get("site_id") and device.get("id"):
                    message = f'Retrieving Gateway details for "{device.get("name", device["mac"])}"'
                    PB.log_message(message, display_pbar=False)
                    data = mistapi.api.v1.sites.devices.getSiteDevice(
                        mist_session, site_id=device["site_id"], device_id=device["id"]
                    )
                    if data.status_code == 200:
                        gateways.append(data.data)
                        PB.log_success(message, display_pbar=False)
                    else:
                        PB.log_failure(message, display_pbar=False)
                        LOGGER.error("Response: %s", data.raw_data)
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.error("Response: %s", resp.raw_data)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
    return gateways


def _process_row(
    data_type: str, data_list: list, service_names: list
) -> Tuple[list, list]:
    result = []
    services_in_use = []
    for data in data_list:
        row = [data_type, data.get("name", ""), data.get("id", "")]
        for service_policy in data.get("service_policies", []):
            for service in service_policy.get("services", []):
                if service not in services_in_use:
                    services_in_use.append(service)
        for service in service_names:
            if service in services_in_use:
                row.append("X")
            else:
                row.append("")
        result.append(row)
    return result, services_in_use


def _process_service_usage(
    services: list,
    templates: list,
    profiles: list,
    policies: list,
    gateways: list,
) -> Tuple[list, dict]:
    """
    Process the WAN services usage data

    PARAMS
    -------
    services : list
        list of WAN services
    templates : list
        list of Gateway Templates
    profiles : list
        list of Hub Profiles
    policies : list
        list of Service Policies
    gateways : list
        list of Gateways

    RETURN
    -------
    processed data as a list of dicts
    """

    message = "Processing WAN services usage data"
    PB.log_message(message, display_pbar=False)
    processed_data = []
    service_names = []
    summary = {}

    headers = ["type", "name", "id"]
    for service in services:
        if service.get("name"):
            service_names.append(service["name"])
    service_names.sort()
    for service_name in service_names:
        headers.append(service_name)
        summary[service_name] = "Not Used"
    processed_data.append(headers)

    rows, services_in_use = _process_row("Gateway Template", templates, service_names)
    processed_data.extend(rows)
    for service in services_in_use:
        summary[service] = "Used"

    rows, services_in_use = _process_row("Hub Profile", profiles, service_names)
    processed_data.extend(rows)
    for service in services_in_use:
        summary[service] = "Used"

    rows, services_in_use = _process_row("Service Policy", policies, service_names)
    processed_data.extend(rows)
    for service in services_in_use:
        summary[service] = "Used"

    rows, services_in_use = _process_row("Gateway", gateways, service_names)
    processed_data.extend(rows)
    for service in services_in_use:
        summary[service] = "Used"

    PB.log_success(message, display_pbar=False)
    return processed_data, summary


###################################################################################################
################################# START
def start(
    mist_session: mistapi.APISession,
    org_id: str,
    csv_details_file: str = CSV_DETAILS_FILE,
    csv_summary_file: str = CSV_SUMMARY_FILE,
):
    """
    Start the process

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with `Super User` access the Org, already logged in
    org_id : str
        org_id where the webhook guests be added. This parameter cannot be used if "site_id"
        is used. If no org_id and not site_id are defined, the script will show a menu to
        select the org/the site.
    csv_details_file : str
        Path to the CSV file where to save the detailed result
    csv_summary_file : str
        Path to the CSV file where to save the summary result
    """

    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]

    print()
    print()
    print()

    services = _retrieve_services(mist_session, org_id)
    templates = _retrieve_gatewaytemplates(mist_session, org_id)
    profiles = _retrieve_org_hubprofiles(mist_session, org_id)
    policies = _retrieve_org_servicepolicies(mist_session, org_id)
    gateways = _retrieve_gateways(mist_session, org_id)

    processed_data, summary = _process_service_usage(
        services, templates, profiles, policies, gateways
    )

    PB.log_message("Saving results to CSV file", False)
    try:
        with open(csv_details_file, "w", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in processed_data:
                writer.writerow(row)
        PB.log_success("Results saved to CSV file", False, False)
    except Exception:
        PB.log_failure("Failed to save results to CSV file", False, False)
        LOGGER.error("Exception occurred", exc_info=True)
    PB.log_message("Saving summary to CSV file", False)
    try:
        with open(csv_summary_file, "w", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in summary.items():
                writer.writerow(row)
        PB.log_success("Results saved to CSV file", False, False)
    except Exception:
        PB.log_failure("Failed to save results to CSV file", False, False)
        LOGGER.error("Exception occurred", exc_info=True)

    print()
    print()


def usage(error_message: str | None = None):
    """
    show script usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python Script to report the usage of WAN Services across Gateway Templates,
Hub Profiles, Service Policies and Gateways.
The script will generate two CSV files:
- A detailed file showing the usage of each WAN service per Gateway Template,
  Hub Profile, Service Policy and Gateway
- A summary file showing if a WAN service is used or not used across the 
  Organization.


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
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Organization ID

-d, --csv_details=          Path to the CSV file where to save the detailed result
                            default: ./report_wan_services_usage.csv
-s, --csv_summary=          Path to the CSV file where to save the summary result
                            default: ./report_wan_services_usage_summary.csv

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./report_wan_services_usage.py
python3 ./report_wan_services_usage.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx 
"""
    )
    if error_message:
        CONSOLE.critical(error_message)
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
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Report the usage of WAN Services across Gateway Templates, Hub Profiles, Service Policies and Gateways."
    )
    parser.add_argument("-e", "--env_file", type=str, help="define the env file to use")
    parser.add_argument("-o", "--org_id", type=str, help="Organization ID")
    parser.add_argument(
        "-c",
        "--csv_details",
        type=str,
        default=CSV_DETAILS_FILE,
        help="Path to the CSV file where to save the detailed result",
    )
    parser.add_argument(
        "-s",
        "--csv_summary",
        type=str,
        default=CSV_SUMMARY_FILE,
        help="Path to the CSV file where to save the summary result",
    )
    parser.add_argument(
        "-l",
        "--log_file",
        type=str,
        default=LOG_FILE,
        help="define the filepath/filename where to write the logs",
    )

    args = parser.parse_args()

    ENV_FILE = args.env_file
    ORG_ID = args.org_id or ""
    CSV_DETAILS_FILE = args.csv_details
    CSV_SUMMARY_FILE = args.csv_summary
    LOG_FILE = args.log_file

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(APISESSION, ORG_ID, CSV_DETAILS_FILE, CSV_SUMMARY_FILE)
