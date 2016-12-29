# pushover 0.2
#
# Copyright (C) 2013-2014  Thibaut Horel <thibaut.horel@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import time
from ConfigParser import RawConfigParser, NoSectionError
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os

import requests

__all__ = ["init", "get_sounds", "Client", "MessageRequest",
           "InitError", "RequestError", "UserError"]

BASE_URL = "https://api.pushover.net/1/"
MESSAGE_URL = BASE_URL + "messages.json"
USER_URL = BASE_URL + "users/validate.json"
SOUND_URL = BASE_URL + "sounds.json"
RECEIPT_URL = BASE_URL + "receipts/"
GLANCE_URL = BASE_URL + "glances.json"

SOUNDS = None
TOKEN = None


def get_sounds():
    """Fetch and return a list of sounds (as a list of strings) recognized by
    Pushover and that can be used in a notification message.

    The result is cached: a request is made to the Pushover server only
    the first time this function is called.
    """
    global SOUNDS
    if not SOUNDS:
        request = Request("get", SOUND_URL, {})
        SOUNDS = request.answer["sounds"]
    return SOUNDS


def init(token, sound=False):
    """Initialize the module by setting the application token which will be
    used to send messages. If ``sound`` is ``True`` also returns the list of
    valid sounds by calling the :func:`get_sounds` function.
    """
    global TOKEN
    TOKEN = token
    if sound:
        return get_sounds()


class InitError(Exception):
    """Exception which is raised when trying to send a message before
    initializing the module.
    """

    def __str__(self):
        return ("No api_token provided. Init the pushover module by "
                "calling the init function")


class UserError(Exception):
    """Exception which is raised when initializing a :class:`Client` class
    without specifying a :attr:`user_key` attribute.
    """

    def __str__(self):
        return "No user_key attribute provided."


class RequestError(Exception):
    """Exception which is raised when Pushover's API returns an error code.

    The list of errors is stored in the :attr:`errors` attribute.
    """

    def __init__(self, errors):
        Exception.__init__(self)
        self.errors = errors

    def __str__(self):
        return "\n==> " + "\n==> ".join(self.errors)


class Request:
    """Base class to send a request to the Pushover server and check the return
    status code. The request is sent on the instance initialization and raises
    a :class:`RequestError` exception when the request is rejected.
    """

    def __init__(self, request_type, url, payload):
        if not TOKEN:
            raise InitError

        payload["token"] = TOKEN
        request = getattr(requests, request_type)(url, params=payload)
        self.answer = request.json()
        if 400 <= request.status_code < 500:
            raise RequestError(self.answer["errors"])

    def __str__(self):
        return str(self.answer)


class MessageRequest(Request):
    """Class representing a message request to the Pushover API. You do not
    need to create them yourself, but the :func:`Client.send_message` function
    returns :class:`MessageRequest` objects if you need to inspect the requests
    after they have been answered by the Pushover server.

    The :attr:`answer` attribute contains a JSON representation of the answer
    made by the Pushover API. In the case where you have sent a message with
    a priority of 2, you can poll the status of the notification with the
    :func:`poll` function.
    """

    def __init__(self, payload):
        Request.__init__(self, "post", MESSAGE_URL, payload)
        self.receipt = None
        if payload.get("priority", 0) == 2:
            self.receipt = self.answer["receipt"]
        self.parameters = {"expired": "expires_at",
                           "called_back": "called_back_at",
                           "acknowledged": "acknowledged_at"}
        for param, when in self.parameters.iteritems():
            setattr(self, param, False)
            setattr(self, when, 0)

    def poll(self):
        """If the message request has a priority of 2, Pushover will keep
        sending the same notification until the client acknowledges it. Calling
        the :func:`poll` function will update the status of the
        :class:`MessageRequest` object until the notifications either expires,
        is acknowledged by the client, or the callback url is reached. The
        attributes of interest are: ``expired, called_back, acknowledged`` and
        their *_at* variants as explained in the API documentation.

        This function returns ``None`` when the request has expired or been
        acknowledged, so that a typical handling of a priority-2 notification
        can look like this::

            request = client.send_message("Urgent notification", priority=2,
                                          expire=120, retry=60)
            while request.poll():
                # do something
                time.sleep(5)

            print request.acknowledged_at, request.acknowledged_by
        """
        if (self.receipt and not any(getattr(self, parameter)
                                     for parameter in self.parameters)):
            request = Request("get", RECEIPT_URL + self.receipt + ".json", {})
            for param, when in self.parameters.iteritems():
                setattr(self, param, bool(request.answer[param]))
                setattr(self, when, request.answer[when])
            for param in ["last_delivered_at", "acknowledged_by",
                          "acknowledged_by_device"]:
                setattr(self, param, request.answer[param])
            return request

    def cancel(self):
        """If the message request has a priority of 2, Pushover will keep
        sending the same notification until it either reaches its ``expire``
        value or is aknowledged by the client. Calling the :func:`cancel`
        function will cancel the notification early.
        """
        if (self.receipt and not any(getattr(self, parameter)
                                     for parameter in self.parameters)):
            request = Request("post", RECEIPT_URL + self.receipt
                              + "/cancel.json", {})
            return request


class GlanceRequest(Request):
    """Class representing a glance request to the Pushover API. This is
    a heavily simplified version of the MessageRequest class, with all
    polling-related features removed.
    """

    def __init__(self, payload):
        Request.__init__(self, "post", GLANCE_URL, payload)


class Client:
    """This is the main class of the module. It represents a specific Pushover
    user to whom messages will be sent when calling the :func:`send_message`
    method.

    * ``user_key``: the Pushover's ID of the user.
    * ``device``: if provided further ties the Client object to the specified
      device.
    * ``api_token``: if provided and the module wasn't previously initialized,
      call the :func:`init` function to initialize it.
    * ``config_path``: configuration file from which to import unprovided
      parameters. See Configuration_.
    * ``profile``: section of the configuration file to import parameters from.
    """

    def __init__(self, user_key=None, device=None, api_token=None,
                 config_path="~/.pushoverrc", profile="Default"):
        params = _get_config(profile, config_path, user_key, api_token, device)
        self.user_key = params["user_key"]
        if not self.user_key:
            raise UserError
        self.device = params["device"]
        self.devices = []

    def verify(self, device=None):
        """Verify that the Client object is tied to an existing Pushover user
        and fetches a list of this user active devices accessible in the
        :attr:`devices` attribute. Returns a boolean depending of the validity
        of the user.
        """
        payload = {"user": self.user_key}
        device = device or self.device
        if device:
            payload["device"] = device
        try:
            request = Request("post", USER_URL, payload)
        except RequestError:
            return False

        self.devices = request.answer["devices"]
        return True

    def send_message(self, message, **kwords):
        """Send a message to the user. It is possible to specify additional
        properties of the message by passing keyword arguments. The list of
        valid keywords is ``title, priority, sound, callback, timestamp, url,
        url_title, device, retry, expire and html`` which are described in the
        Pushover API documentation. For convenience, you can simply set
        ``timestamp=True`` to set the timestamp to the current timestamp.

        This method returns a :class:`MessageRequest` object.
        """
        valid_keywords = ["title", "priority", "sound", "callback",
                          "timestamp", "url", "url_title", "device",
                          "retry", "expire", "html"]

        payload = {"message": message, "user": self.user_key}
        if self.device:
            payload["device"] = self.device

        for key, value in kwords.iteritems():
            if key not in valid_keywords:
                raise ValueError("{0}: invalid message parameter".format(key))

            if key == "timestamp" and value is True:
                payload[key] = int(time.time())
            elif key == "sound":
                if not SOUNDS:
                    get_sounds()
                if value not in SOUNDS:
                    raise ValueError("{0}: invalid sound".format(value))
                else:
                    payload[key] = value
            elif value:
                payload[key] = value

        return MessageRequest(payload)

    def send_glance(self, text=None, **kwords):
        """Send a glance to the user. The default property is ``text``,
        as this is used on most glances, however a valid glance does not
        need to require text and can be constructed using any combination
        of valid keyword properties. The list of valid keywords is ``title,
        text, subtext, count and percent`` which are  described in the
        Pushover Glance API documentation.

        This method returns a :class:`GlanceRequest` object.
        """
        valid_keywords = ["title", "text", "subtext", "count", "percent"]

        payload = {"user": self.user_key}
        if text:
            payload["text"] = text
        if self.device:
            payload["device"] = self.device

        for key, value in kwords.iteritems():
            if key not in valid_keywords:
                raise ValueError("{0}: invalid message parameter".format(key))
            payload[key] = value

        return GlanceRequest(payload)


def _get_config(profile='Default', config_path='~/.pushoverrc',
                user_key=None, api_token=None, device=None):
    config_path = os.path.expanduser(config_path)
    config = RawConfigParser()
    config.read(config_path)
    params = {"user_key": None, "api_token": None, "device": None}
    try:
        params.update(dict(config.items(profile)))
    except NoSectionError:
        pass
    if user_key:
        params["user_key"] = user_key
    if api_token:
        params["api_token"] = api_token
    if device:
        params["device"] = device

    if not TOKEN:
        init(params["api_token"])
        if not TOKEN:
            raise InitError

    return params


def main():
    parser = ArgumentParser(description="Send a message to pushover.",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog="""
For more details and bug reports, see: https://github.com/Thibauth/python-pushover""")
    parser.add_argument("--api-token", help="Pushover application token")
    parser.add_argument("--user-key", "-u", help="Pushover user key")
    parser.add_argument("message", help="message to send")
    parser.add_argument("--title", "-t", help="message title")
    parser.add_argument("--priority", "-p", help="message priority (-1, 0, 1 or 2)")
    parser.add_argument("--url", help="additional url")
    parser.add_argument("--url-title", help="additional url title")
    parser.add_argument("-c", "--config", help="configuration file\
                        (default: ~/.pushoverrc)", default="~/.pushoverrc")
    parser.add_argument("--profile", help="profile to read in the\
                        configuration file (default: Default)",
                        default="Default")
    parser.add_argument("--version", "-v", action="version",
                        help="output version information and exit",
                        version="""
%(prog)s 0.2
Copyright (C) 2013-2016 Thibaut Horel <thibaut.horel@gmail.com>
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""")

    args = parser.parse_args()
    Client(args.user_key, None, args.api_token, args.config,
           args.profile).send_message(args.message, title=args.title,
                                      priority=args.priority, url=args.url,
                                      url_title=args.url_title, timestamp=True)

if __name__ == "__main__":
    main()
