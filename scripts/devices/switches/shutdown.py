"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to shutdown a switch device in the Mist Cloud.
The script is creating a websocket connection to the Mist Cloud to send and 
approve the shutdown command to the specified switch device.

For failed shutdown attempts, the script will log the error in the log file
(default in ./script.log).
For the error "Shell API call failed: 400 - {'detail': 'data temporary unavailable'}",
this is mostly the switch already disconnected from the Mist Cloud.

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
-h, --help              display this help
-s, --site_id=          Set the site_id
-d, --device_ids=       Set the device_ids (comma-separated if multiple)

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./shutdown.py --site_id=your_site_id_here --device_ids=device_id_1,device_id_2

"""
#### IMPORTS ####
import logging
import sys
import argparse



MISTAPI_MIN_VERSION = "0.64.0"

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

#####################################################################
#### PARAMETERS #####
DEFAULT_BACKUP_FOLDER = "./org_backup"
BACKUP_FILE = "./org_inventory_file.json"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"



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
        self.steps_count = min(self.steps_count, self.steps_total)

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

    def set_steps_total(self, steps_total: int) -> None:
        """
        Set the total number of steps for the progress bar.
        :param steps_total: The total number of steps
        """
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True) -> None:
        """
        Log a message in the progress bar.
        :param message: The message to log
        :param display_pbar: If True, the progress bar will be displayed after the message
        """
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_debug(self, message) -> None:
        """
        Log a debug message.
        :param message: The debug message to log
        """
        LOGGER.debug(message)

    def log_success(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a success message in the progress bar.
        :param message: The success message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the success
        """
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a warning message in the progress bar.
        :param message: The warning message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the warning
        """
        LOGGER.warning(message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a failure message in the progress bar.
        :param message: The failure message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the failure
        """
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True) -> None:
        """
        Log a title message in the progress bar.
        :param message: The title message to log
        :param end: If True, the progress bar will not be displayed after the title
        :param display_pbar: If True, the progress bar will be displayed after the title
        """
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()
#####################################################################

def shutdown(session: mistapi.APISession, site_id: str, device_id: str, verbose: bool = False) -> None:
    """
    Shutdown the specified switch.
    :param session: The Mist API session
    :param site_id: The ID of the site containing the switch
    :param device_id: The ID of the device to shut down
    """
    
    message = f"Shutting down device {device_id}"
    PB.log_title(message)
    shell_output = ""
    try:
        with mistapi.device_utils.ex.createShellSession(session, site_id, device_id) as shell_session:
            shell_session.send_commands(["request system power-off all-members at now", "y"])
            while True:
                data = shell_session.recv(timeout=0.5)
                if data is None:
                    break
                if verbose:
                    print(data.decode("utf-8", errors="replace"), end="")
                shell_output += data.decode("utf-8", errors="replace")
            if "System going down IMMEDIATELY" in shell_output:
                PB.log_success(message, inc=1)
            else:
                PB.log_failure(message, inc=1)
    except Exception as e:
        PB.log_failure(message, inc=1)
        LOGGER.error("Failed to shut down device %s: %s", device_id, str(e))

def start(session: mistapi.APISession, site_id: str, device_ids: list, verbose: bool = False) -> None:
    """
    Start the shutdown process for the specified switches by invoking the shutdown function for each device.
    :param session: The Mist API session
    :param site_id: The ID of the site containing the switches
    :param device_ids: A list of device IDs to shut down
    :param verbose: If True, print detailed output from the shutdown commands
    """
    if not site_id:
        CONSOLE.error("Site ID is required")
        return
    if not device_ids:
        CONSOLE.error("Device IDs are required")
        return
    PB.set_steps_total(len(device_ids))
    for device_id in device_ids:
        shutdown(session, site_id, device_id, verbose)


#####################################################################
#### CHECK MISTAPI VERSION ####
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
            mistapi.__version__
        )

#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shutdown one or multiple switches")
    parser.add_argument("-s", "--site-id", help="ID of the site")
    parser.add_argument("-d", "--device-ids", help="IDs of the devices, comma-separated")
    parser.add_argument("-e", "--env-file", default=ENV_FILE, help="Path to the environment file")
    parser.add_argument("-l", "--log-file", default=LOG_FILE, help="Path to the log file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose display by showing the switches outputs")
    args = parser.parse_args()
    
    SITE_ID = args.site_id
    DEVICE_IDS = args.device_ids.split(",") if args.device_ids else []
    ENV_FILE = args.env_file
    LOG_FILE = args.log_file
    VERBOSE = args.verbose
    
    #### LOGS ####
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    LOGGER.setLevel(logging.INFO)
    check_mistapi_version()
    #### START ####
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(session=APISESSION, site_id=SITE_ID, device_ids=DEVICE_IDS, verbose=VERBOSE)