"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to toggle the "managed" status of Mist devices (Switch, Gateway).
When a device is set to "unmanaged", Mist will stop pushing configuration
updates to the device, but will continue to monitor it.
The devices can be identified by their MAC Address or Serial Number in the CSV
file.

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
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file.
The allowed values are listed below.

-------
CSV Parameters:
Required:
- mac (MAC Address format does not matter) or serial

-------
CSV Example:
Example 1:
#mac
5c:5b:35:c0:ff:ee
2c:6b:f5:c0:ff:ee


Example 2:
#serial
A012345678901
HV0123456789

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           Mist Org ID where the devices are claimed to
-c, --csv_file=         CSV File to use.
                        default is "./update_managed_status.csv"
-m, --managed=          set to "true" to set the devices to managed,
                        "false" to set them to unmanaged.

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./update_managed_status.py
python3 ./update_managed_status.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -m true

"""

#####################################################################
#### IMPORTS ####
import logging
import sys
import csv
import re
import argparse

MISTAPI_MIN_VERSION = "0.50.0"

try:
    import mistapi
    from mistapi.__logger import console
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


#####################################################################
#### PARAMETERS #####
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
CSV_FILE = "./update_managed_status.csv"

#####################################################################
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
        print(f" {text} ".center(size, "-"), "\n\n")
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
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()
#####################################################################
#### FUNCTIONS ####


def _update_devices(apisession: mistapi.APISession, devices: list, managed: bool):
    LOGGER.debug("_update_devices -> managed:%s", managed)
    for device_info in devices:
        device_id = device_info.get("id")
        device_name = device_info.get("name")
        device_site_id = device_info.get("site_id")
        message = f"Updating device {device_name}"
        PB.log_message(message)
        if not device_id:
            PB.log_failure(message)
            LOGGER.error(
                "_update_devices:unable to find the device_id for device %s",
                device_info,
            )
        elif not device_site_id:
            PB.log_failure(message)
            LOGGER.error(
                "_update_devices:unable to find the site_id for device %s. "
                "It is possible this device is still in the Org inventory",
                device_info,
            )
        else:
            try:
                if managed :
                    disable_auto_config = False
                else:
                    disable_auto_config = True
                resp = mistapi.api.v1.sites.devices.updateSiteDevice(
                    apisession,
                    site_id=device_site_id,
                    device_id=device_id,
                    body={"disable_auto_config": disable_auto_config, "managed": managed},
                )
                if resp.status_code == 200:
                    mist_disable_auto_config = resp.data.get("disable_auto_config")
                    mist_managed = resp.data.get("managed")
                    if (
                        mist_disable_auto_config == disable_auto_config
                        and mist_managed == managed
                    ):
                        LOGGER.info(
                            '_update_devices:new device managed state is "%s"',
                            mist_managed,
                        )
                        PB.log_success(message, inc=True)
                    else:
                        LOGGER.warning(
                            "_update_devices:seems device %s"
                            " has not been updated. Managed state is %s",
                            device_info,
                            mist_managed,
                        )
                        PB.log_warning(message, inc=True)
                else:
                    LOGGER.error(
                        "_update_devices:unable to rename"
                        " device %s. Got HTTP%d from Mist",
                        device_info,
                        resp.status_code,
                    )
                    PB.log_failure(message, inc=True)
            except Exception:
                PB.log_failure(message, inc=True)


def _retrieve_org_inventory(apisession: mistapi.APISession, org_id: str) -> list:
    LOGGER.debug("_retrieve_org_inventory")
    LOGGER.debug("_retrieve_org_inventory:parameter:org_id:%s", org_id)
    message = "Retrieve Org Inventory"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.inventory.getOrgInventory(
            apisession, org_id, limit=1000
        )
        inventory = mistapi.get_all(apisession, resp)
        PB.log_success(message, display_pbar=False)
        LOGGER.debug(
            "_retrieve_org_inventory:got %d devices from the org inventory",
            len(inventory),
        )
        return inventory
    except Exception:
        PB.log_failure(message, display_pbar=False)
        sys.exit(255)


def _read_csv_file(csv_file: str) -> tuple[str, list]:
    LOGGER.debug("_read_csv_file")
    LOGGER.debug("_read_csv_file:parameter:csv_file:%s", csv_file)
    fields = []
    devices = []
    info_field = "None"  # will be eith "mac" or "serial"
    column_info_field = -1
    PB.log_message("Processing CSV file", display_pbar=False)
    with open(csv_file, "r", encoding="utf-8") as f:
        data_from_csv = csv.reader(f, skipinitialspace=True, quotechar='"')
        data_from_csv = [
            [c.replace("\ufeff", "") for c in row] for row in data_from_csv
        ]
        for line in data_from_csv:
            LOGGER.debug("_read_csv_file:%s", line)
            # this is for the first line of the CSV file
            if not fields:
                i = 0
                for column in line:
                    column = re.sub("[^a-zA-Z_]", "", column)
                    LOGGER.debug("_read_csv_file:%s", column)
                    fields.append(column)
                    if column == "serial":
                        info_field = "serial"
                        if column_info_field < 0:
                            column_info_field = i
                        else:
                            console.error(
                                'Either "serial" or "mac" can be used, not both.'
                            )
                            sys.exit(0)
                    elif column == "mac":
                        info_field = "mac"
                        if column_info_field < 0:
                            column_info_field = i
                        else:
                            console.error(
                                'Either "serial" or "mac" can be used, not both.'
                            )
                            sys.exit(0)
                    i += 1

                if column_info_field < 0:
                    console.error(
                        "Unable to find `serial` or `mac` field in the CSV file. "
                        "Please check the file format"
                    )
                    sys.exit(0)

            # this is for the other lines, containing the data
            else:
                info = line[column_info_field]
                if info_field == "mac":
                    info = re.sub("[^a-f0-9]", "", info.lower())
                    if len(info) != 12:
                        console.error(f"MAC Address format if wrong at line {line}")
                        sys.exit(0)
                else:
                    info = info.upper()
                if not info:
                    console.error(f'Unable to get "{info_field}" at line {line}')
                    sys.exit(0)
                else:
                    devices.append(info)
                    LOGGER.debug("_read_csv_file:new device:%s", info)

    LOGGER.debug(
        "_read_csv_file:got %d devices to rename from %s", len(devices), csv_file
    )
    PB.log_success("Processing CSV file", display_pbar=False, inc=False)
    return info_field, devices


def _processing_data(info_field: str, devices_from_csv: list, inventory: list) -> list:
    LOGGER.debug("_processing_data")
    message = "Processing inventory"
    PB.log_message(message, display_pbar=False)
    try:
        result = []
        for device in inventory:
            device_info = device[info_field]
            if device_info in devices_from_csv:
                LOGGER.debug("_processing_data:device %s will be renamed", device_info)
                data = {
                    "site_id": device.get("site_id"), 
                    "id": device.get("id"),
                    "name": device.get("name"),
                    }
                result.append(data)
                LOGGER.debug("_processing_data:%s", data)
        PB.log_success(message, display_pbar=False)
        return result
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        console.critical("Unable to process data. Please check the logs. Exiting...")
        sys.exit(255)


def _prepare_data(apisession: mistapi.APISession, org_id: str, csv_file: str) -> list:
    LOGGER.debug("_prepare_data")
    LOGGER.debug("_prepare_data:parameter:org_id:%s", org_id)
    LOGGER.debug("_prepare_data:parameter:csv_file:%s", csv_file)
    PB.log_title("Processing data", display_pbar=False)
    info_field, devices_from_csv = _read_csv_file(csv_file)
    inventory = _retrieve_org_inventory(apisession, org_id)
    LOGGER.debug(inventory)
    data = _processing_data(info_field, devices_from_csv, inventory)
    LOGGER.debug(data)
    return data


def start(apisession: mistapi.APISession, org_id: str, csv_file: str, managed: bool):
    """
    Start the process to rename the devices

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session, already logged in
    org_id : str
        only if the destination org already exists. org_id where to deploy the
        configuration
    csv_file : str
        Path to the csv_file where the information are stored.
        default: "./update_managed_status.csv"
    managed : str
        Set to "true" to set the devices to managed, "false" to set them to unmanaged.
    """
    LOGGER.debug("start")
    LOGGER.debug("start:parameter:org_id:%s", org_id)
    LOGGER.debug("start:parameter:csv_file:%s", csv_file)
    LOGGER.debug("start:parameter:managed:%s", managed)
    if not org_id:
        org_id = mistapi.cli.select_org(apisession, allow_many=True)[0]
    if not csv_file:
        csv_file = CSV_FILE

    devices = _prepare_data(apisession, org_id, csv_file)
    PB.set_steps_total(len(devices))
    _update_devices(apisession, devices, managed)


#####################################################################
##### USAGE ####
def usage(error_message: str | None = None):
    """
    display usage

    PARAMS
    -------
    error_message : str
        if error_message is set, display it after the usage
    """
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to toggle the "managed" status of Mist devices (Switch, Gateway).
When a device is set to "unmanaged", Mist will stop pushing configuration
updates to the device, but will continue to monitor it.
The devices can be identified by their MAC Address or Serial Number in the CSV
file.

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
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file.
The allowed values are listed below.

-------
CSV Parameters:
Required:
- mac (MAC Address format does not matter) or serial

-------
CSV Example:
Example 1:
#mac
5c:5b:35:c0:ff:ee
2c:6b:f5:c0:ff:ee


Example 2:
#serial
A012345678901
HV0123456789

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           Mist Org ID where the devices are claimed to
-c, --csv_file=         CSV File to use.
                        default is "./update_managed_status.csv"
-m, --managed=          set to "true" to set the devices to managed,
                        "false" to set them to unmanaged.

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./update_managed_status.py
python3 ./update_managed_status.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -m true

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


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Report the usage of WAN Services across Gateway Templates, Hub Profiles, Service Policies and Gateways."
    )
    parser.add_argument("-e", "--env_file", type=str, help="define the env file to use")
    parser.add_argument("-o", "--org_id", type=str, help="Organization ID")
    parser.add_argument(
        "-c",
        "--csv_file",
        type=str,
        default=CSV_FILE,
        help="Path to the CSV file where to save the detailed result",
    )
    parser.add_argument(
        "-m",
        "--managed",
        type=str,
        help='set to "true" to set the devices to managed, '
        '"false" to set them to unmanaged. ',
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
    CSV_FILE = args.csv_file
    LOG_FILE = args.log_file
    MANAGED = None
    
    if args.managed.lower() == "true":
        MANAGED = True
    elif args.managed.lower() == "false":
        MANAGED = False
    
    if MANAGED is None:
        console.error(
            "Please specify if the devices must be set to managed or unmanaged "
            "using the -m or --managed option."
        )
        sys.exit(0)

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(APISESSION, ORG_ID, CSV_FILE, MANAGED)
