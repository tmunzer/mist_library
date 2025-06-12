"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to clone a specific template from an organization to another (or 
the same) organization.
The script is tacking care of also cloning the other configuration used by the
template:
- WLAN Template: wlans, wxtags, wxrules
- SWITCH Templates: N/A
- WAN Templates: networks, services, service policies
- HUB Profiles: networks, services, service policies

This script will not change/create/delete any existing objects in the source
organization. It will just retrieve every single object from it. However, it 
will deploy all the configuration objects (except the devices) to the 
destination organization.

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

--src_oid=              Optional, org_id of the org to clone
--dst_oid=              Optional, org_id of the org where to clone the src_org,
                        if the org already exists
--dst_org_name=         Optional, name of the org where to clone the src_org. 
                        If dst_org_id is defined (org already exists), will be 
                        used for validation, if dst_org_id is not defined, a
                        new org will be created

--template_type=        Type of template to clone. Options are:
                        - wlan
                        - lan
                        - wan
                        - hub
--template_id=          ID of the template to clone
--dst_template_name=    Name of the cloned template. Required if the template 
                        is clone into the same org

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
--dst_env=              Optional, env file to use to access the dst org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"


-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"


-------
Examples:
python3 ./clone_template.py
python3 ./clone_template.py --src_env=~/.mist_env \
                            --src_oid=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
                            --dst_oid=b9953384-xxxx-xxxx-xxxx-ed26c44f44e9 \
                            --dst_org_name="TM LAB API" \
                            --template_type=lan \
                            --template_id=1d9293b5-xxxx-xxxx-xxxx-ad62feba6f93
"""

import sys
import json
import logging
import argparse

MISTAPI_MIN_VERSION = "0.55.5"

try:
    import mistapi
    from mistapi.__logger import console
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
LOG_FILE = "./script.log"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


TEMPLATE_TYPES = ["WLAN Template", "SWITCH Template", "WAN Template", "HUB Profile"]
TEMPLATE_VALUES = ["wlan", "lan", "wan", "hub"]


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
#### WLAN TEMPLATE ####
def _get_wlan_template(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
) -> dict | None:
    try:
        message = f"WLAN Template: retrieving {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.templates.getOrgTemplate(
            src_session, src_oid, src_template_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wlan_template(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
) -> str | None:
    try:
        message = f"WLAN Template: deploying {template.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.templates.createOrgTemplate(
            dst_session, dst_oid, template
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data.get("id")
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.debug(
                "_deploy_wlan_template:unable to create %s in dst org",
                template.get("name"),
            )
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.debug(
            "_deploy_wlan_template:unable to create %s in dst org", template.get("name")
        )
        LOGGER.error("Exception occurred", exc_info=True)
        return None


########################
def _get_wlans(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
) -> list:
    wlans = []
    try:
        message = f"WLANS: retrieving for template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wlans.listOrgWlans(src_session, src_oid)
        if resp.status_code == 200:
            data = mistapi.get_all(src_session, resp)
            for wlan in data:
                if wlan.get("template_id") == src_template_id:
                    wlans.append(wlan)
            PB.log_success(message, display_pbar=False)
            return wlans
        else:
            PB.log_failure(message, display_pbar=False)
            return wlans
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return wlans


def _deploy_wlans(
    dst_session: mistapi.APISession, dst_oid: str, wlan: dict
) -> tuple[str | None, str | None]:
    old_id = None
    new_id = None
    try:
        message = f"WLAN: deploying {wlan.get('ssid')}"
        old_id = wlan.get("id")
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wlans.createOrgWlan(dst_session, dst_oid, wlan)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            new_id = resp.data.get("id")
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.debug(
                "_deploy_wlans:unable to create %s in dst org", wlan.get("ssid")
            )
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.debug("_deploy_wlans:unable to create %s in dst org", wlan.get("ssid"))
        LOGGER.error("Exception occurred", exc_info=True)
    return old_id, new_id


########################
def _get_wxrules(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
) -> list:
    wxrules = []
    try:
        message = f"WXRULES: retrieving for template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wxrules.listOrgWxRules(src_session, src_oid)
        if resp.status_code == 200:
            data = mistapi.get_all(src_session, resp)
            for wxrule in data:
                if wxrule.get("template_id") == src_template_id:
                    wxrules.append(wxrule)
            PB.log_success(message, display_pbar=False)
            return wxrules
        else:
            PB.log_failure(message, display_pbar=False)
            return wxrules
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return wxrules


def _deploy_wxrules(
    dst_session: mistapi.APISession, dst_oid: str, wxrules: list
) -> None:
    for wxrule in wxrules:
        try:
            message = f"WXRULE: deploying {wxrule.get('id')}"
            PB.log_message(message, display_pbar=False)
            resp = mistapi.api.v1.orgs.wxrules.createOrgWxRule(
                dst_session, dst_oid, wxrule
            )
            if resp.status_code == 200:
                PB.log_success(message, display_pbar=False)
            else:
                PB.log_failure(message, display_pbar=False)
                LOGGER.debug(
                    "_deploy_wxrules:unable to create wxrule %s in dst org",
                    wxrule.get("order"),
                )
        except Exception:
            PB.log_failure(message, display_pbar=False)
            LOGGER.debug(
                "_deploy_wxrules:unable to create wxrule %s in dst org",
                wxrule.get("order"),
            )
            LOGGER.error("Exception occurred", exc_info=True)


########################
def _get_src_wxtags(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
):
    wxtags = []
    try:
        message = f"WXTAGS: retrieving for template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wxtags.listOrgWxTags(src_session, src_oid)
        if resp.status_code == 200:
            wxtags = mistapi.get_all(src_session, resp)
            PB.log_success(message, display_pbar=False)
            return wxtags
        else:
            PB.log_failure(message, display_pbar=False)
            return wxtags
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return wxtags


def _get_dst_wxtags(dst_session: mistapi.APISession, dst_oid: str) -> list:
    wxtags = []
    try:
        message = "WXTAGS: retrieving existing in the dest org"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wxtags.listOrgWxTags(dst_session, dst_oid)
        if resp.status_code == 200:
            wxtags = mistapi.get_all(dst_session, resp)
            PB.log_success(message, display_pbar=False)
            return wxtags
        else:
            PB.log_failure(message, display_pbar=False)
            return wxtags
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return wxtags


def _deploy_wxtags(
    dst_session: mistapi.APISession, dst_oid: str, wxtag: dict
) -> str | None:
    new_id = None
    try:
        message = f"WXTAG: deploying {wxtag.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wxtags.createOrgWxTag(dst_session, dst_oid, wxtag)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            new_id = resp.data.get("id")
            LOGGER.debug(
                "_deploy_wxtags:%s created in dst org. New id is %s",
                wxtag.get("name"),
                new_id,
            )
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.debug(
                "_deploy_wxtags:unable to create %s in dst org", wxtag.get("name")
            )
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.debug("_deploy_wxtags:unable to create %s in dst org", wxtag.get("name"))
        LOGGER.error("Exception occurred", exc_info=True)
    return new_id


def _find_or_create_wxtags(
    dst_session: mistapi.APISession,
    dst_oid: str,
    src_wxtag: dict,
    dst_wxtags: list,
    wlan_mapping: dict[str, str],
) -> str | None:
    src_wxtag_id = src_wxtag.get("id")
    src_wxtag_name = src_wxtag.get("name")
    LOGGER.debug("_find_or_create_wxtags:%s is named %s", src_wxtag_id, src_wxtag_name)
    try:
        dst_wxtag = next(tag for tag in dst_wxtags if tag.get("name") == src_wxtag_name)
        dst_wxtag_id = dst_wxtag.get("id")
        dst_wxtag_name = dst_wxtag.get("name")
        LOGGER.debug(
            "_find_or_create_wxtags:%s already exists in dst org with id %s",
            src_wxtag_name,
            dst_wxtag_id,
        )
        message = f"WXTAG: {dst_wxtag_name} already exists in dest org"
        PB.log_message(message, display_pbar=False)
        PB.log_success(message, display_pbar=False)
    except Exception:
        LOGGER.debug(
            "_find_or_create_wxtags:%s does not exists in dst org", src_wxtag_name
        )
        if src_wxtag.get("match") == "wlan_id":
            LOGGER.debug("_find_or_create_wxtags:%s is a wlan_id wxtag", src_wxtag_name)
            tmp_wlan_id = []
            for wlan_id in src_wxtag.get("values", []):
                if wlan_mapping.get(wlan_id):
                    tmp_wlan_id.append(wlan_mapping.get(wlan_id))
            LOGGER.debug(
                "_find_or_create_wxtags:%s replacing %s with %s",
                src_wxtag_name,
                src_wxtag["values"],
                tmp_wlan_id,
            )
            src_wxtag["values"] = tmp_wlan_id
        dst_wxtag_id = _deploy_wxtags(dst_session, dst_oid, src_wxtag)
    return dst_wxtag_id


########################
def _process_wxrules(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_id: str,
    wlan_mapping: dict[str, str],
) -> None:
    wxrules = _get_wxrules(src_session, src_oid, src_template_id)
    src_wxtags = _get_src_wxtags(src_session, src_oid, src_template_id)
    dst_wxtags = _get_dst_wxtags(dst_session, dst_oid)
    wxtag_mapping = {}
    for wxrule in wxrules:
        wxrule["template_id"] = dst_template_id
        for wxtag_type in [
            "src_wxtags",
            "dst_wxtags",
            "dst_allow_wxtags",
            "dst_deny_wxtags",
        ]:
            LOGGER.debug("_process_wxrules:processing %s", wxtag_type)
            tmp_wxtags = []
            for wxtag_id in wxrule.get(wxtag_type, []):
                if wxtag_mapping.get(wxtag_id):
                    LOGGER.debug(
                        "_process_wxrules:src wxtag id %s already mapped", wxtag_id
                    )
                    tmp_wxtags.append(wxtag_mapping.get(wxtag_id))
                else:
                    LOGGER.debug(
                        "_process_wxrules:src wxtag id %s not mapped", wxtag_id
                    )
                    try:
                        src_wxtag = next(t for t in src_wxtags if t["id"] == wxtag_id)
                        LOGGER.debug(
                            "_process_wxrules:src wxtag id %s config: %s",
                            wxtag_id,
                            src_wxtag,
                        )
                        dst_wxtag_id = _find_or_create_wxtags(
                            dst_session, dst_oid, src_wxtag, dst_wxtags, wlan_mapping
                        )
                        LOGGER.debug(
                            "_process_wxrules:src wxtag id %s mapped to %s",
                            wxtag_id,
                            dst_wxtag_id,
                        )
                        wxtag_mapping[wxtag_id] = dst_wxtag_id
                        tmp_wxtags.append(dst_wxtag_id)
                    except Exception:
                        LOGGER.error("Exception occurred", exc_info=True)

            LOGGER.debug(
                "_process_wxrules:%s is %s replaced with %s",
                wxtag_type,
                wxrule[wxtag_type],
                tmp_wxtags,
            )
            wxrule[wxtag_type] = tmp_wxtags
        _deploy_wxrules(dst_session, dst_oid, wxrules)


def clone_wlan_template(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_name: str | None = None,
) -> None:
    """
    Clone a WLAN template from one organization to another.
    :param src_session: Source organization API session
    :param dst_session: Destination organization API session
    :param src_oid: Source organization ID
    :param dst_oid: Destination organization ID
    :param src_template_id: Source template ID to clone
    :param dst_template_name: Name for the cloned template in the destination org
    """
    template = _get_wlan_template(src_session, src_oid, src_template_id)
    dst_template_id = None
    wlans = _get_wlans(src_session, src_oid, src_template_id)
    if dst_template_name and template:
        template["name"] = dst_template_name
    if template:
        if dst_template_name:
            template["name"] = dst_template_name
        dst_template_id = _deploy_wlan_template(dst_session, dst_oid, template)
    if dst_template_id:
        wlan_mapping = {}
        for wlan in wlans:
            wlan["template_id"] = dst_template_id
            old_id, new_id = _deploy_wlans(dst_session, dst_oid, wlan)
            wlan_mapping[old_id] = new_id
        _process_wxrules(
            src_session,
            dst_session,
            src_oid,
            dst_oid,
            src_template_id,
            dst_template_id,
            wlan_mapping,
        )


#####################################################################
#### SWITCH TEMPLATE ####
def _get_switch_template(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
) -> dict | None:
    try:
        message = f"Retrieving network template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplate(
            src_session, src_oid, src_template_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        PB.log_failure(message, display_pbar=False)
        return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_switch_template(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
) -> None:
    try:
        message = f"Deploying network template {template.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.networktemplates.createOrgNetworkTemplate(
            dst_session, dst_oid, template
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


def clone_switch_template(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_name: str | None = None,
) -> None:
    """Clone a SWITCH template from one organization to another.
    :param src_session: Source organization API session
    :param dst_session: Destination organization API session
    :param src_oid: Source organization ID
    :param dst_oid: Destination organization ID
    :param src_template_id: Source template ID to clone
    :param dst_template_name: Name for the cloned template in the destination org
    """
    template = _get_switch_template(src_session, src_oid, src_template_id)
    if dst_template_name and template:
        template["name"] = dst_template_name
    if template:
        _deploy_switch_template(dst_session, dst_oid, template)


#####################################################################
#### WAN TEMPLATE ####
def _get_wan_template(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
) -> dict | None:
    try:
        message = f"Retrieving gateway template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.gatewaytemplates.getOrgGatewayTemplate(
            src_session, src_oid, src_template_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_template(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
) -> None:
    try:
        message = f"Deploying gateway template {template.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.gatewaytemplates.createOrgGatewayTemplate(
            dst_session, dst_oid, template
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


########################
#### HUB PROFILE ####
def _get_device_profile(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
) -> dict | None:
    try:
        message = f"Retrieving gateway template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.deviceprofiles.getOrgDeviceProfile(
            src_session, src_oid, src_template_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_device_profile(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
) -> None:
    try:
        message = f"Deploying gateway template {template.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile(
            dst_session, dst_oid, template
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


########################
def _get_wan_services(src_session: mistapi.APISession, src_oid: str) -> list | None:
    try:
        message = "Retrieving gateway services"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.services.listOrgServices(
            src_session, src_oid, limit=1000
        )
        if resp.status_code == 200:
            data = mistapi.get_all(src_session, resp)
            PB.log_success(message, display_pbar=False)
            return data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_services(
    dst_session: mistapi.APISession, dst_oid: str, service: dict
) -> None:
    try:
        message = f"Deploying gateway service {service.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.services.createOrgService(
            dst_session, dst_oid, service
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


########################
def _get_wan_servicepolicies(
    src_session: mistapi.APISession, src_oid: str
) -> list | None:
    try:
        message = "Retrieving gateway service policies"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies(
            src_session, src_oid, limit=1000
        )
        if resp.status_code == 200:
            data = mistapi.get_all(src_session, resp)
            PB.log_success(message, display_pbar=False)
            return data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_servicepolicy(
    dst_session: mistapi.APISession, dst_oid: str, servicepolicy: dict, uuid_map: dict
) -> None:
    try:
        src_tid = servicepolicy.get("id")
        message = f"Deploying gateway service policy {servicepolicy.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.servicepolicies.createOrgServicePolicy(
            dst_session, dst_oid, servicepolicy
        )
        if resp.status_code == 200:
            dst_tid = resp.data.get("id")
            uuid_map[src_tid] = dst_tid
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


########################
def _get_wan_networks(src_session: mistapi.APISession, src_oid: str):
    try:
        message = "Retrieving gateway networks"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.networks.listOrgNetworks(
            src_session, src_oid, limit=1000
        )
        if resp.status_code == 200:
            data = mistapi.get_all(src_session, resp)
            PB.log_success(message, display_pbar=False)
            return data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except Exception:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_networks(
    dst_session: mistapi.APISession, dst_oid: str, network: dict
) -> None:
    try:
        message = f"Deploying gateway service {network.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.networks.createOrgNetwork(
            dst_session, dst_oid, network
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)


########################
def clone_wan_template(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_name: str | None = None,
    deviceprofile: bool = False,
) -> None:
    """
    Clone a WAN template from one organization to another.
    :param src_session: Source organization API session
    :param dst_session: Destination organization API session
    :param src_oid: Source organization ID
    :param dst_oid: Destination organization ID
    :param src_template_id: Source template ID to clone
    :param dst_template_name: Name for the cloned template in the destination org
    :param deviceprofile: If True, clone a device profile instead of a WAN template
    """
    uuid_map = {}
    network_names = []
    service_names = []
    servicepolicy_ids = []
    dst_networks = []
    dst_services = []
    dst_servicepolicies = []

    if not deviceprofile:
        template = _get_wan_template(src_session, src_oid, src_template_id)
    else:
        template = _get_device_profile(src_session, src_oid, src_template_id)

    if template:
        # PROCESS NETWORKS FROM TEMPLATE
        for _, config in template.get("port_config", {}).items():
            for network in config.get("networks", []):
                if network not in network_names:
                    network_names.append(network)

        # PROCESS SERVICE POLICIES FROM TEMPLATE
        for servicepolicy in template.get("service_policies", []):
            if servicepolicy.get("servicepolicy_id"):
                if servicepolicy["servicepolicy_id"] not in servicepolicy_ids:
                    servicepolicy_ids.append(servicepolicy["servicepolicy_id"])
            else:
                for service in servicepolicy.get("services", []):
                    if service not in service_names:
                        service_names.append(service)

        # PROCESS NETWORKS FROM SRC ORG
        if network_names:
            src_networks = _get_wan_networks(src_session, src_oid)
            if src_networks:
                for network in src_networks:
                    if network.get("name") in network_names:
                        dst_networks.append(network)

        # PROCESS SERVICE POLICIES FROM SRC ORG
        if servicepolicy_ids:
            src_servicepolicies = _get_wan_servicepolicies(src_session, src_oid)
            if src_servicepolicies:
                for servicepolicy in src_servicepolicies:
                    if servicepolicy.get("id") in servicepolicy_ids:
                        dst_servicepolicies.append(servicepolicy)
                        for service in servicepolicy.get("services", []):
                            if service not in service_names:
                                service_names.append(service)

        # PROCESS SERVICES FROM SRC ORG
        if service_names:
            src_services = _get_wan_services(src_session, src_oid)
            if src_services:
                for service in src_services:
                    if service.get("name") in service_names:
                        dst_services.append(service)

        # DEPLOY NETWORKS TO DST ORG
        if dst_networks:
            for network in dst_networks:
                _deploy_wan_networks(dst_session, dst_oid, network)
        # DEPLOY SERVICES TO DST ORG
        if dst_services:
            for service in dst_services:
                _deploy_wan_services(dst_session, dst_oid, service)
        # DEPLOY SERVICE POLICIES TO DST ORG
        if dst_servicepolicies:
            for servicepolicy in dst_servicepolicies:
                _deploy_wan_servicepolicy(dst_session, dst_oid, servicepolicy, uuid_map)

        if uuid_map:
            template_string = json.dumps(template)
            for sid, did in uuid_map.items():
                template_string.replace(sid, did)
            template = json.loads(template_string)

        if dst_template_name:
            template["name"] = dst_template_name

        if not deviceprofile:
            _deploy_wan_template(dst_session, dst_oid, template)
        else:
            _deploy_device_profile(dst_session, dst_oid, template)


#######
#######


def _print_new_step(message) -> None:
    print()
    print("".center(80, "*"))
    print(f" {message} ".center(80, "*"))
    print("".center(80, "*"))
    print()
    print()
    LOGGER.info(message)


#######
#######
def _check_org_name(
    apisession: mistapi.APISession, dst_org_id: str, org_type: str, org_name: str = ""
) -> tuple[str, str]:
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            f"To avoid any error, please confirm the current {org_type} organization name: "
        )
        if resp == org_name:
            return dst_org_id, org_name
        print()
        print("The organization names do not match... Please try again...")


#######
#######
def _select_org(org_type: str, mist_session: mistapi.APISession) -> tuple[str, str]:
    org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]
    _check_org_name(mist_session, org_id, org_type, org_name)
    return org_id, org_name


def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = ""
) -> tuple[str, str]:
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    if org_name == org_name_from_mist:
        return org_id, org_name
    else:
        console.critical(f"Org name {org_name} does not match the org {org_id}")
        sys.exit(0)


def _check_dst_org(
    dst_apisession: mistapi.APISession, dst_org_id: str, dst_org_name: str
) -> tuple[str, str]:
    if dst_org_id and dst_org_name:
        return _check_org_name_in_script_param(dst_apisession, dst_org_id, dst_org_name)
    elif dst_org_id and not dst_org_name:
        return _check_org_name(dst_apisession, dst_org_id, "destination")
    elif not dst_org_id and not dst_org_name:
        _print_new_step("DESTINATION Org")
        return _select_org("destination", dst_apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)


def _select_template_type() -> str:
    while True:
        print()
        print("Type of template to clone")
        for i, template in enumerate(TEMPLATE_TYPES):
            print(f"{i}) {template}")

        resp = input(
            f"Which type of template do you want to clone (0-{len(TEMPLATE_TYPES) - 1})? "
        )
        try:
            resp_int = int(resp)
            return TEMPLATE_VALUES[resp_int]
        except Exception:
            print(
                f"Invalid input. Only numbers between 0 and {len(TEMPLATE_TYPES) - 1} are allowed"
            )


def _retrieve_template_list(
    src_session: mistapi.APISession, src_oid: str, template_type: str
) -> list:
    resp = None
    if template_type == "wlan":
        resp = mistapi.api.v1.orgs.templates.listOrgTemplates(
            src_session, src_oid, limit=1000
        )
    elif template_type == "lan":
        resp = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(
            src_session, src_oid, limit=1000
        )
    elif template_type == "wan":
        resp = mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates(
            src_session, src_oid, limit=1000
        )
    elif template_type == "hub":
        resp = mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles(
            src_session, src_oid, type="gateway", limit=1000
        )
    else:
        print(f"unknown template type {template_type}")
        sys.exit(2)

    return mistapi.get_all(src_session, resp)


def _select_template_to_clone(
    src_session: mistapi.APISession, src_oid: str, template_type: str
):
    templates = _retrieve_template_list(src_session, src_oid, template_type)

    while True:
        print()
        print("Available templates:")
        for i, template in enumerate(templates):
            print(f"{i}) {template.get('name')} (id: {template.get('id')})")
        resp = input(f"Which template do you want to clone (0-{len(templates) - 1})? ")
        try:
            resp_int = int(resp)
            return templates[resp_int].get("id")
        except Exception:
            print(
                f"Invalid input. Only numbers between 0 and {len(templates) - 1} are allowed"
            )


def start(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession | None = None,
    src_org_id: str = "",
    dst_org_id: str = "",
    dst_org_name: str = "",
    template_type: str = "",
    template_id: str = "",
    dst_template_name: str = "",
) -> None:
    """
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    :param  mistapi.APISession  src_apisession      mistapi session with `Super User` access the source Org, already logged in
    :param  mistapi.APISession  dst_apisession      Optional, mistapi session with `Super User` access the source Org, already logged in.
                                                    If not defined, the src_apissession will be reused
    :param  str                 src_org_id          Optional, org_id of the org where the template to clone is
    :param  str                 dst_org_id          Optional, org_id of the org where to clone the template
    :param  str                 dst_org_name        Optional, name of the org where to clone the template (used for validation)
    :param  str                 template_type       Optional, type of template to clone (wlan, lan, wan, hub)
    :param  str                 template_id         Optional, id of the template to clone
    :param  str                 dst_template_name   Optional, name of the cloned template (required if the template is clone into the same org)

    """
    if not dst_apisession:
        dst_apisession = src_apisession
    if not src_org_id:
        src_org_id = mistapi.cli.select_org(src_apisession)[0]
    dst_org_id, dst_org_name = _check_dst_org(dst_apisession, dst_org_id, dst_org_name)

    if not template_type or template_type not in TEMPLATE_VALUES:
        template_type = _select_template_type()

    if not template_id:
        template_id = _select_template_to_clone(
            src_apisession, src_org_id, template_type
        )

    if src_org_id == dst_org_id and not dst_template_name:
        print(
            "It is not possible to have multiple templates with the same name in a single org."
        )
        print("You must enter a new name for the cloned template")
        dst_template_name = input("New template name: ")

    _print_new_step("Process Started")
    if template_type == "wlan":
        clone_wlan_template(
            src_apisession,
            dst_apisession,
            src_org_id,
            dst_org_id,
            template_id,
            dst_template_name,
        )
    elif template_type == "lan":
        clone_switch_template(
            src_apisession,
            dst_apisession,
            src_org_id,
            dst_org_id,
            template_id,
            dst_template_name,
        )
    elif template_type == "wan":
        clone_wan_template(
            src_apisession,
            dst_apisession,
            src_org_id,
            dst_org_id,
            template_id,
            dst_template_name,
        )
    elif template_type == "hub":
        clone_wan_template(
            src_apisession,
            dst_apisession,
            src_org_id,
            dst_org_id,
            template_id,
            dst_template_name,
            True,
        )

    _print_new_step("Process finished")


###############################################################################
#### USAGE ####
def usage() -> None:
    """Print the usage of the script."""
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to clone a specific template from an organization to another (or 
the same) organization.
The script is tacking care of also cloning the other configuration used by the
template:
- WLAN Template: wlans, wxtags, wxrules
- SWITCH Templates: N/A
- WAN Templates: networks, services, service policies
- HUB Profiles: networks, services, service policies

This script will not change/create/delete any existing objects in the source
organization. It will just retrieve every single object from it. However, it 
will deploy all the configuration objects (except the devices) to the 
destination organization.

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

--src_oid=              Optional, org_id of the org to clone
--dst_oid=              Optional, org_id of the org where to clone the src_org,
                        if the org already exists
--dst_org_name=         Optional, name of the org where to clone the src_org. 
                        If dst_org_id is defined (org already exists), will be 
                        used for validation, if dst_org_id is not defined, a
                        new org will be created

--template_type=        Type of template to clone. Options are:
                        - wlan
                        - lan
                        - wan
                        - hub
--template_id=          ID of the template to clone
--dst_template_name=    Name of the cloned template. Required if the template 
                        is clone into the same org

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
--dst_env=              Optional, env file to use to access the dst org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"


-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"


-------
Examples:
python3 ./clone_template.py
python3 ./clone_template.py --src_env=~/.mist_env \\
                            --src_oid=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \\
                            --dst_oid=b9953384-xxxx-xxxx-xxxx-ed26c44f44e9 \\
                            --dst_org_name="TM LAB API" \\
                            --template_type=lan \\
                            --template_id=1d9293b5-xxxx-xxxx-xxxx-ad62feba6f93
    """
    )
    sys.exit(0)


def check_mistapi_version() -> None:
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
        description="Clone a specific template from one organization to another"
    )
    parser.add_argument("--src_oid", help="org_id of the org to clone")
    parser.add_argument(
        "--dst_oid", help="org_id of the org where to clone the src_org"
    )
    parser.add_argument(
        "--dst_org_name", help="name of the org where to clone the src_org"
    )
    parser.add_argument("--dst_env", help="env file to use to access the dst org")
    parser.add_argument("--src_env", help="env file to use to access the src org")
    parser.add_argument(
        "-l",
        "--log_file",
        default="./script.log",
        help="define the filepath/filename where to write the logs",
    )
    parser.add_argument(
        "--template_type",
        choices=["wlan", "lan", "wan", "hub"],
        help="Type of template to clone",
    )
    parser.add_argument("--template_id", help="ID of the template to clone")
    parser.add_argument("--dst_template_name", help="Name of the cloned template")

    args = parser.parse_args()

    SRC_ORG_ID = args.src_oid
    DST_ORG_ID = args.dst_oid
    DST_ORG_NAME = args.dst_org_name
    SRC_ENV_FILE = args.src_env
    DST_ENV_FILE = args.dst_env
    LOG_FILE = args.log_file
    SRC_APISESSION = None
    DST_APISESSION = None
    TEMPLATE_TYPE = args.template_type
    TEMPLATE_ID = args.template_id
    DST_TEMPLATE_NAME = args.dst_template_name

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    print(" API Session to access the Source Org ".center(80, "_"))
    SRC_APISESSION = mistapi.APISession(env_file=SRC_ENV_FILE)
    SRC_APISESSION.login()

    print(" API Session to access the Destination Org ".center(80, "_"))
    DST_APISESSION = mistapi.APISession(env_file=DST_ENV_FILE)
    DST_APISESSION.login()

    ### START ###
    start(
        SRC_APISESSION,
        DST_APISESSION,
        src_org_id=SRC_ORG_ID,
        dst_org_id=DST_ORG_ID,
        dst_org_name=DST_ORG_NAME,
        template_type=TEMPLATE_TYPE,
        template_id=TEMPLATE_ID,
        dst_template_name=DST_TEMPLATE_NAME,
    )
