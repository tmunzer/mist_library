"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to extract and filter the Webhook deliveries.


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
-w, --webhook_id            Webhook ID

-t, --topic=                Webhook topic to filter one
-f, --filters=              Comma separated list of payload filters
                            to filter the webhook deliveries
-d, --duration              duration of the events to look at
                            default: 1d

--headers                   Comma separated list of headers to include in the CSV file
-c, --csv_file=             Path to the CSV file where to save the result
                            default: ./list_webhook_deliveries.csv

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./list_webhook_deliveries.py
python3 ./list_webhook_deliveries.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -w 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t alarms -f marvis
"""

#### IMPORTS ####
import sys
import getopt
import logging
import csv

MISTAPI_MIN_VERSION = "0.52.4"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
except:
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
CSV_FILE = "./list_webhook_deliveries.csv"
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
def _retrieve_org_deliveries(
    apisession: mistapi.APISession,
    org_id: str,
    webhook_id: str,
    topic: str | None = None,
    duration: str = "1d",
) -> list:
    PB.log_title("Retrieve Webhook Deliveries", False, False)
    print()
    PB.log_message("This can take some time", False)
    deliveries = []
    try:
        response = mistapi.api.v1.orgs.webhooks.searchOrgWebhooksDeliveries(
            apisession,
            org_id=org_id,
            webhook_id=webhook_id,
            topic=topic,
            duration=duration,
            limit=1000,
        )
        if response:
            deliveries = mistapi.get_all(apisession, response)
        PB.log_success("Successfully retrieved webhook deliveries", False, False)
    except Exception:
        PB.log_failure("Failed to retrieve webhook deliveries", False, False)
        LOGGER.error("Exception occurred", exc_info=True)
    return deliveries


def _filter_deliveries(deliveries: list, filters: list = [], headers:list=[]) -> tuple:
    if filters:
        deliveries = [
            d
            for d in deliveries
            if all(f in d.get("req_payload", "").replace("\\", '"') for f in filters)
        ]
    if not headers:
        for d in deliveries:
            for k in d.keys():
                if k not in headers:
                    headers.append(k)
    return headers, deliveries


###################################################################################################
################################# START
def start(
    mist_session: mistapi.APISession,
    org_id: str,
    webhook_id: str,
    duration: str = "1d",
    topic: str | None = None,
    filters: list = [],
    csv_file: str = CSV_FILE,
    headers: list = [],
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
    webhook_id : str
        webhook_id of the webhook to retrieve deliveries for. This parameter cannot be used if "site_id"
        is used. If no webhook_id and not site_id are defined, the script will show a menu to
        select the webhook.
    duration : str, default 1d
        duration of the events to look at
    topic : str|None
        topic of the webhook to retrieve deliveries for. This parameter cannot be used if "site_id"
        is used. If no topic and not site_id are defined, the script will show a menu to
        select the topic.
    text : str|None
        text to filter the webhook deliveries by. This parameter cannot be used if "site_id"
        is used. If no text and not site_id are defined, the script will show a menu to
        select the text.
    csv_file : str
        Path to the CSV file where to save the result
    headers : list
        List of headers to include in the CSV file
    """

    print()
    print()
    print()
    deliveries = _retrieve_org_deliveries(
        apisession=mist_session,
        org_id=org_id,
        webhook_id=webhook_id,
        topic=topic,
        duration=duration,
    )
    total_count = len(deliveries)
    headers, deliveries = _filter_deliveries(deliveries, filters, headers)
    filtered_count = len(deliveries)

    PB.log_message("Saving results to CSV file", False)
    try:
        with open(csv_file, "w") as f:
            cw = csv.writer(f)
            cw.writerow(headers)
            for d in deliveries:
                cw.writerow([d.get(h, "") for h in headers])
        PB.log_success("Results saved to CSV file", False, False)
    except Exception:
        PB.log_failure("Failed to save results to CSV file", False, False)
        LOGGER.error("Exception occurred", exc_info=True)

    print()
    print()
    PB.log_message(
        f"Total deliveries: {total_count}, Filtered deliveries: {filtered_count}", False
    )


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
Python script to extract and filter the Webhook deliveries.


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
-w, --webhook_id            Webhook ID

-t, --topic=                Webhook topic to filter one
-f, --filters=              Comma separated list of payload filters
                            to filter the webhook deliveries
-d, --duration              duration of the events to look at
                            default: 1d

--headers                   Comma separated list of headers to include in the CSV file
-c, --csv_file=             Path to the CSV file where to save the result
                            default: ./list_webhook_deliveries.csv

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./list_webhook_deliveries.py
python3 ./list_webhook_deliveries.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -w 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
        -d 1w -t alarms -f marvis
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
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "he:o:w:t:f:d:l:c:",
            [
                "help",
                "env_file=",
                "org_id=",
                "webhook_id=",
                "topic=",
                "filters=",
                "duration=",
                "headers=",
                "log_file=",
                "csv_file=",
            ],
        )
    except getopt.GetoptError as err:
        usage(err.msg)

    ENV_FILE = None
    ORG_ID = ""
    WEBHOOK_ID = ""
    TOPIC = None
    DURATION = "1d"
    FILTER = []
    HEADERS = []
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-e", "--env_file"]:
            ENV_FILE = a
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-w", "--webhook_id"]:
            WEBHOOK_ID = a
        elif o in ["-c", "--csv_file"]:
            CSV_FILE = a
        elif o in ["-t", "--topic"]:
            TOPIC = a
        elif o in ["-f", "--filters"]:
            FILTER = a.split(",") if a else []
        elif o in ["--headers"]:
            HEADERS = a.split(",") if a else []
        elif o in ["-d", "--duration"]:
            if not a.endswith(("m", "h", "d", "w")):
                usage(
                    f'Invalid -d / --duration parameter value, should be something like "10m", "2h", "7d", "1w". Got "{a}".'
                )
            DURATION = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(APISESSION, ORG_ID, WEBHOOK_ID, DURATION, TOPIC, FILTER, CSV_FILE, HEADERS)
