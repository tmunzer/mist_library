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

It is recomended to use an environment file to store the required information
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
import getopt

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
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
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

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

    def log_debug(self, message):
        LOGGER.debug(f"{message}")

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
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


#####################################################################
#### WLAN TEMPLATE ####
def _get_wlan_template(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
):
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
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wlan_template(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
):
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
                f"_deploy_wlan_template:unable to create {template.get('name')} in dst org"
            )
            return None
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.debug(
            f"_deploy_wlan_template:unable to create {template.get('name')} in dst org"
        )
        LOGGER.error("Exception occurred", exc_info=True)
        return None


########################
def _get_wlans(src_session: mistapi.APISession, src_oid: str, src_template_id: str):
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
    except:
        PB.log_failure(message, display_pbar=False)
        return wlans


def _deploy_wlans(dst_session: mistapi.APISession, dst_oid: str, wlan: dict):
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
                f"_deploy_wlans:unable to create {wlan.get('ssid')} in dst org"
            )
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.debug(f"_deploy_wlans:unable to create {wlan.get('ssid')} in dst org")
        LOGGER.error("Exception occurred", exc_info=True)
    return old_id, new_id


########################
def _get_wxrules(src_session: mistapi.APISession, src_oid: str, src_template_id: str):
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
    except:
        PB.log_failure(message, display_pbar=False)
        return wxrules


def _deploy_wxrules(dst_session: mistapi.APISession, dst_oid: str, wxrules: list):
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
                    f"_deploy_wxrules:unable to create wxrule {wxrules.get('order')} in dst org"
                )
        except:
            PB.log_failure(message, display_pbar=False)
            LOGGER.debug(
                f"_deploy_wxrules:unable to create wxrule {wxrules.get('order')} in dst org"
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
    except:
        PB.log_failure(message, display_pbar=False)
        return wxtags


def _get_dst_wxtags(dst_session: mistapi.APISession, dst_oid: str):
    wxtags = []
    try:
        message = f"WXTAGS: retrieving existing in the dest org"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wxtags.listOrgWxTags(dst_session, dst_oid)
        if resp.status_code == 200:
            wxtags = mistapi.get_all(dst_session, resp)
            PB.log_success(message, display_pbar=False)
            return wxtags
        else:
            PB.log_failure(message, display_pbar=False)
            return wxtags
    except:
        PB.log_failure(message, display_pbar=False)
        return wxtags


def _deploy_wxtags(dst_session: mistapi.APISession, dst_oid: str, wxtag: dict):
    new_id = None
    try:
        message = f"WXTAG: deploying {wxtag.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.wxtags.createOrgWxTag(dst_session, dst_oid, wxtag)
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            new_id = resp.data.get("id")
            LOGGER.debug(
                f"_deploy_wxtags:{wxtag.get('name')} created in dst org. New id is {new_id}"
            )
        else:
            PB.log_failure(message, display_pbar=False)
            LOGGER.debug(
                f"_deploy_wxtags:unable to create {wxtag.get('name')} in dst org"
            )
    except:
        PB.log_failure(message, display_pbar=False)
        LOGGER.debug(f"_deploy_wxtags:unable to create {wxtag.get('name')} in dst org")
        LOGGER.error("Exception occurred", exc_info=True)
    return new_id


def _find_or_create_wxtags(
    dst_session: mistapi.APISession,
    dst_oid: str,
    src_wxtag: dict,
    dst_wxtags: list,
    wlan_mapping: list,
):
    src_wxtag_id = src_wxtag.get("id")
    src_wxtag_name = src_wxtag.get("name")
    LOGGER.debug(f"_find_or_create_wxtags:{src_wxtag_id} is named {src_wxtag_name}")
    try:
        dst_wxtag = next(
            tag for tag in dst_wxtags if tag.get("name") == src_wxtag_name
        )
        dst_wxtag_id = dst_wxtag.get("id")
        dst_wxtag_name = dst_wxtag.get("name")
        LOGGER.debug(
            f"_find_or_create_wxtags:{src_wxtag_name} already exists in dst org with id {dst_wxtag_id}"
        )
        message = f"WXTAG: {dst_wxtag_name} already exists in dest org"
        PB.log_message(message, display_pbar=False)
        PB.log_success(message, display_pbar=False)
    except:
        LOGGER.debug(
            f"_find_or_create_wxtags:{src_wxtag_name} does not exists in dst org"
        )
        if src_wxtag.get("match") == "wlan_id":
            LOGGER.debug(
                f"_find_or_create_wxtags:{src_wxtag_name} is a wlan_id wxtag"
            )
            tmp_wlan_id = []
            for wlan_id in src_wxtag.get("values", []):
                if wlan_mapping.get(wlan_id):
                    tmp_wlan_id.append(wlan_mapping.get(wlan_id))
            LOGGER.debug(
                f"_find_or_create_wxtags:{src_wxtag_name} replacing {src_wxtag['values']} with {tmp_wlan_id}"
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
    wlan_mapping: list,
):
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
            LOGGER.debug(f"_process_wxrules:processing {wxtag_type}")
            tmp_wxtags = []
            for wxtag_id in wxrule.get(wxtag_type, []):
                if wxtag_mapping.get(wxtag_id):
                    LOGGER.debug(
                        f"_process_wxrules:src wxtag id {wxtag_id} already mapped"
                    )
                    tmp_wxtags.append(wxtag_mapping.get(wxtag_id))
                else:
                    LOGGER.debug(f"_process_wxrules:src wxtag id {wxtag_id} not mapped")
                    try:
                        src_wxtag = next(t for t in src_wxtags if t["id"] == wxtag_id)
                        LOGGER.debug(
                            f"_process_wxrules:src wxtag id {wxtag_id} config: {src_wxtag}"
                        )
                        dst_wxtag_id = _find_or_create_wxtags(
                            dst_session, dst_oid, src_wxtag, dst_wxtags, wlan_mapping
                        )
                        LOGGER.debug(
                            f"_process_wxrules:src wxtag id {wxtag_id} mapped to {dst_wxtag_id}"
                        )
                        wxtag_mapping[wxtag_id] = dst_wxtag_id
                        tmp_wxtags.append(dst_wxtag_id)
                    except:
                        LOGGER.error("Exception occurred", exc_info=True)

            LOGGER.debug(
                f"_process_wxrules:{wxtag_type} is {wxrule[wxtag_type]} replaced with {tmp_wxtags}"
            )
            wxrule[wxtag_type] = tmp_wxtags
        _deploy_wxrules(dst_session, dst_oid, wxrules)


def clone_wlan_template(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_name: str = None,
):
    template = _get_wlan_template(src_session, src_oid, src_template_id)
    dst_template_id = None
    wlans = _get_wlans(src_session, src_oid, src_template_id)
    if dst_template_name:
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
):
    try:
        message = f"Retrieving network template {src_template_id}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplate(
            src_session, src_oid, src_template_id
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
            return resp.data
        else:
            PB.log_failure(message, display_pbar=False)
            return None
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_switch_template(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
):
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
    except:
        PB.log_failure(message, display_pbar=False)


def clone_switch_template(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_name: str = None,
):
    template = _get_switch_template(src_session, src_oid, src_template_id)
    if dst_template_name:
        template["name"] = dst_template_name
    if template:
        _deploy_switch_template(dst_session, dst_oid, template)


#####################################################################
#### WAN TEMPLATE ####
def _get_wan_template(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
):
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
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_template(dst_session: mistapi.APISession, dst_oid: str, template: dict):
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
    except:
        PB.log_failure(message, display_pbar=False)


########################
#### HUB PROFILE ####
def _get_device_profile(
    src_session: mistapi.APISession, src_oid: str, src_template_id: str
):
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
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_device_profile(
    dst_session: mistapi.APISession, dst_oid: str, template: dict
):
    try:
        message = f"Deploying gateway template {template.get('name')}"
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfiles(
            dst_session, dst_oid, template
        )
        if resp.status_code == 200:
            PB.log_success(message, display_pbar=False)
        else:
            PB.log_failure(message, display_pbar=False)
    except:
        PB.log_failure(message, display_pbar=False)


########################
def _get_wan_services(src_session: mistapi.APISession, src_oid: str):
    try:
        message = f"Retrieving gateway services"
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
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_services(dst_session: mistapi.APISession, dst_oid: str, service: dict):
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
    except:
        PB.log_failure(message, display_pbar=False)


########################
def _get_wan_servicepolicies(src_session: mistapi.APISession, src_oid: str):
    try:
        message = f"Retrieving gateway service policies"
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
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_servicepolicy(
    dst_session: mistapi.APISession, dst_oid: str, servicepolicy: dict, uuid_map: dict
):
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
    except:
        PB.log_failure(message, display_pbar=False)


########################
def _get_wan_networks(src_session: mistapi.APISession, src_oid: str):
    try:
        message = f"Retrieving gateway networks"
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
    except:
        PB.log_failure(message, display_pbar=False)
        return None


def _deploy_wan_networks(dst_session: mistapi.APISession, dst_oid: str, network: dict):
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
    except:
        PB.log_failure(message, display_pbar=False)


########################
def clone_wan_template(
    src_session: mistapi.APISession,
    dst_session: mistapi.APISession,
    src_oid: str,
    dst_oid: str,
    src_template_id: str,
    dst_template_name: str = None,
    deviceprofile: bool = False,
):
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
        for port, config in template.get("port_config", {}).items():
            for network in config.get("networks", []):
                if not network in network_names:
                    network_names.append(network)

        # PROCESS SERVICE POLICIES FROM TEMPLATE
        for servicepolicy in template.get("service_policies", []):
            if servicepolicy.get("servicepolicy_id"):
                if not servicepolicy["servicepolicy_id"] in servicepolicy_ids:
                    servicepolicy_ids.append(servicepolicy["servicepolicy_id"])
            else:
                for service in servicepolicy.get("services", []):
                    if not service in service_names:
                        service_names.append(service)

        # PROCESS NETWORKS FROM SRC ORG
        if network_names:
            src_networks = _get_wan_networks(src_session, src_oid)
            for network in src_networks:
                if network.get("name") in network_names:
                    dst_networks.append(network)

        # PROCESS SERVICE POLICIES FROM SRC ORG
        if servicepolicy_ids:
            src_servicepolicies = _get_wan_servicepolicies(src_session, src_oid)
            for servicepolicy in src_servicepolicies:
                if servicepolicy.get("id") in servicepolicy_ids:
                    dst_servicepolicies.append(servicepolicy)
                    for service in servicepolicy.get("services", []):
                        if not service in service_names:
                            service_names.append(service)

        # PROCESS SERVICES FROM SRC ORG
        if service_names:
            src_services = _get_wan_services(src_session, src_oid)
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


def _print_new_step(message):
    print()
    print("".center(80, "*"))
    print(f" {message} ".center(80, "*"))
    print("".center(80, "*"))
    print()
    print()
    LOGGER.info(f"{message}")


#######
#######
def _check_org_name(
    apisession: mistapi.APISession, dst_org_id: str, org_type: str, org_name: str = None
):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            f"To avoid any error, please confirm the current {org_type} orgnization name: "
        )
        if resp == org_name:
            return True
        else:
            print()
            print("The orgnization names do not match... Please try again...")


#######
#######
def _select_org(org_type: str, mist_session=None):
    org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]
    _check_org_name(mist_session, org_id, org_type, org_name)
    return org_id, org_name


def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = None
):
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
):
    if dst_org_id and dst_org_name:
        return _check_org_name_in_script_param(dst_apisession, dst_org_id, dst_org_name)
    elif dst_org_id and not dst_org_name:
        return _check_org_name(dst_apisession, dst_org_id, "destination")
    elif not dst_org_id and not dst_org_name:
        _print_new_step("DESTINATION Org")
        return _select_org("destination", dst_apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)


def _select_template_type():
    while True:
        print()
        print("Type of template to clone")
        for i, template in enumerate(TEMPLATE_TYPES):
            print(f"{i}) {template}")

        resp = input(
            f"Which type of template do you want to clone (0-{len(TEMPLATE_TYPES)-1})? "
        )
        try:
            resp_int = int(resp)
            return TEMPLATE_VALUES[resp_int]
        except:
            print(
                f"Invalid input. Only numbers between 0 and {len(TEMPLATE_TYPES)-1} are allowed"
            )


def _retrieve_template_list(
    src_session: mistapi.APISession, src_oid: str, template_type: str
):
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
        print(f"unknown tempate type {template_type}")
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
        resp = input(f"Which template do you want to clone (0-{len(templates)-1})? ")
        try:
            resp_int = int(resp)
            return templates[resp_int].get("id")
        except:
            print(
                f"Invalid input. Only numbers between 0 and {len(templates)-1} are allowed"
            )


def start(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession = None,
    src_org_id: str = None,
    dst_org_id: str = None,
    dst_org_name=None,
    template_type: str = None,
    template_id: str = None,
    dst_template_name: str = None,
):
    """
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    :param  mistapi.APISession  src_apisession      mistapi session with `Super User` access the source Org, already logged in
    :param  mistapi.APISession  dst_apisession      Optional, mistapi session with `Super User` access the source Org, already logged in.
                                                    If not defined, the src_apissession will be reused
    :param  str                 src_org_id          Optional, org_id of the org where the template to clone is
    :param  str                 dst_org_id          Optional, org_id of the org where to clone the tempalte
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

    if not template_type or not template_type in TEMPLATE_VALUES:
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

    _print_new_step("Process finised")


###############################################################################
#### USAGE ####
def usage():
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

It is recomended to use an environment file to store the required information
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


def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        LOGGER.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )


###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hl:b:s:d:",
            [
                "help",
                "src_oid=",
                "dst_oid=",
                "dst_org_name=",
                "dst_env=",
                "src_env=",
                "log_file=",
                "template_type=",
                "template_id=",
                "dst_template_name=",
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    SRC_ORG_ID = None
    DST_ORG_ID = None
    DST_ORG_NAME = None
    SRC_ENV_FILE = None
    DST_ENV_FILE = None
    SRC_APISESSION = None
    DST_APISESSION = None
    TEMPLATE_TYPE = None
    TEMPLATE_ID = None
    DST_TEMPLATE_NAME = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["--src_env"]:
            SRC_ENV_FILE = a
        elif o in ["--src_oid"]:
            SRC_ORG_ID = a
        elif o in ["--dst_env"]:
            DST_ENV_FILE = a
        elif o in ["--dst_oid"]:
            DST_ORG_ID = a
        elif o in ["--dst_org_name"]:
            DST_ORG_NAME = a
        elif o in ["--template_type"]:
            TEMPLATE_TYPE = a
        elif o in ["--template_id"]:
            TEMPLATE_ID = a
        elif o in ["--dst_template_name"]:
            DST_TEMPLATE_NAME = a
        else:
            assert False, "unhandled option"

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
