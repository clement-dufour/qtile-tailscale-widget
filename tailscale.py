# Copyright (c) 2022 Clément Dufour
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import subprocess
import json

from libqtile.widget import base
from libqtile.log_utils import logger


def run_cmd(parent_name):
    '''Calls the tailscale status command and returns the status of the connection.'''

    args = ["tailscale", "status", "--active=true" ,"--json=true", "--self=true"]

    try:
        cmd = subprocess.run(args, capture_output=True, check=True)

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logger.warning(
            "%s: Failed to connect to local tailscaled.",
            parent_name,
        )
        raise

    except FileNotFoundError:
        logger.warning(
            "%s: Tailscale command not found.",
            parent_name,
        )
        raise

    cmd_output = json.loads(cmd.stdout.decode("utf-8"))

    return cmd_output


def parse_cmd_output(cmd_output):
    '''Parses the tailscale command output and returns the tailscale status.'''

    tailscale_status = {
        "BackendState": "",
        "TailscaleIPs": {
            "v4": "",
            "v6": "",
        },
        "PublicIP": "",
        "LocalIP": "",
        "ExitNode": {
            "HostName": "",
            "TailscaleIPs": {
                "v4": "",
                "v6": "",
            },
            "PublicIP": "",
        },
    }

    if "BackendState" in cmd_output:
        tailscale_status["BackendState"] = cmd_output["BackendState"]

    if "Self" in cmd_output:
        if "TailscaleIPs" in cmd_output["Self"]:
            if isinstance(cmd_output["Self"]["TailscaleIPs"], list):
                if len(cmd_output["Self"]["TailscaleIPs"]) == 2:
                    tailscale_status["TailscaleIPs"]["v4"] = cmd_output["Self"]["TailscaleIPs"][0]
                    tailscale_status["TailscaleIPs"]["v6"] = cmd_output["Self"]["TailscaleIPs"][1]

        if "Addrs" in cmd_output["Self"]:
            if isinstance(cmd_output["Self"]["Addrs"], list):
                if len(cmd_output["Self"]["Addrs"]) == 2:
                    tailscale_status["PublicIP"] = cmd_output["Self"]["Addrs"][0].split(":")[0]
                    tailscale_status["LocalIP"] = cmd_output["Self"]["Addrs"][1].split(":")[0]

    if "ExitNodeStatus" in cmd_output:
        for peer in cmd_output["Peer"].values():
            if peer["ID"] == cmd_output["ExitNodeStatus"]["ID"]:
                tailscale_status["ExitNode"]["HostName"] = peer["HostName"]
                tailscale_status["ExitNode"]["TailscaleIPs"]["v4"] = peer["TailscaleIPs"][0]
                tailscale_status["ExitNode"]["TailscaleIPs"]["v6"] = peer["TailscaleIPs"][1]
                tailscale_status["ExitNode"]["PublicIP"] = peer["CurAddr"].split(":")[0]

                if tailscale_status["BackendState"] == "Running":
                    tailscale_status["BackendState"] = "RunningUsingExitNode"

    return tailscale_status


class Tailscale(base.ThreadPoolText):
    '''A widget displaying the Tailscale VPN connection status.'''

    defaults = [
        (
            "display_formats",
            {},
            "Formats dictionary."
        ),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(Tailscale.defaults)
        self.text = ""
        self.default_foreground = self.foreground
        self.default_background = self.background


    def poll(self):
        '''Returns the formatted current state of the tailscale status.'''

        self.format = "{backend_state}"
        self.foreground = self.default_foreground
        self.background = self.default_background

        try:
            cmd_output = run_cmd(self.__class__.__name__)

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError):
            return None

        tailscale_status = parse_cmd_output(cmd_output)

        if tailscale_status["BackendState"] in self.display_formats:
            display_format = self.display_formats[tailscale_status["BackendState"]]

            if "format" in display_format:
                self.format = display_format["format"]

            if "foreground" in display_format:
                self.foreground = display_format["foreground"]

            if "background" in display_format:
                self.background = display_format["background"]

        return self.format.format(
            backend_state = tailscale_status["BackendState"],
            tailscale_ipv4 = tailscale_status["TailscaleIPs"]["v4"],
            tailscale_ipv6 = tailscale_status["TailscaleIPs"]["v6"],
            public_ip = tailscale_status["PublicIP"],
            local_ip = tailscale_status["LocalIP"],
            exit_node_hostname = tailscale_status["ExitNode"]["HostName"],
            exit_node_ipv4 = tailscale_status["ExitNode"]["TailscaleIPs"]["v4"],
            exit_node_ipv6 = tailscale_status["ExitNode"]["TailscaleIPs"]["v6"],
            exit_node_public_ip = tailscale_status["ExitNode"]["PublicIP"],
        )
