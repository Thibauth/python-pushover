# pushover 1.0
#
# Copyright (C) 2013-2018  Thibaut Horel <thibaut.horel@gmail.com>

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
import requests

BASE_URL = "https://api.pushover.net/1/"
MESSAGE_URL = BASE_URL + "messages.json"
USER_URL = BASE_URL + "users/validate.json"
SOUND_URL = BASE_URL + "sounds.json"
RECEIPT_URL = BASE_URL + "receipts/"
GLANCE_URL = BASE_URL + "glances.json"

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
    status code. The request is sent on instantiation and raises
    a :class:`RequestError` exception when the request is rejected.
    """

    def __init__(self, method, url, payload):
        files = {}
        if "attachment" in payload:
            files["attachment"] = payload["attachment"]
            del payload["attachment"]
        self.payload = payload
        self.files = files
        request = getattr(requests, method)(url, params=payload, files=files)
        self.answer = request.json()
        if 400 <= request.status_code < 500:
            raise RequestError(self.answer["errors"])

    def __str__(self):
        return str(self.answer)


class MessageRequest(Request):
    """This class represents a message request to the Pushover API. You do not
    need to create it yourself, but the :func:`Pushover.message` function
    returns :class:`MessageRequest` objects.

    The :attr:`answer` attribute contains a JSON representation of the answer
    made by the Pushover API. When sending a message with a priority of 2, you
    can poll the status of the notification with the :func:`poll` function.
    """

    params = {"expired": "expires_at",
            "called_back": "called_back_at",
            "acknowledged": "acknowledged_at"}

    def __init__(self, payload):
        Request.__init__(self, "post", MESSAGE_URL, payload)
        self.status = {"done": True}
        if payload.get("priority", 0) == 2:
            self.url = RECEIPT_URL + self.answer["receipt"]
            self.status["done"] = False
            for param, when in MessageRequest.params.iteritems():
                self.status[param] = False
                self.status[when] = 0

    def poll(self):
        """If the message request has a priority of 2, Pushover keeps sending
        the same notification until the client acknowledges it. Calling the
        :func:`poll` function fetches the status of the :class:`MessageRequest`
        object until the notifications either expires, is acknowledged by the
        client, or the callback url is reached. The status is available in the
        ``status`` dictionary.

        Returns ``True`` when the request has expired or been acknowledged and
        ``False`` otherwise so that a typical handling of a priority-2
        notification can look like this::

            request = p.message("Urgent!", priority=2, expire=120, retry=60)
            while not request.poll():
                # do something
                time.sleep(5)

            print request.status
        """
        if not self.status["done"]:
            r = Request("get", self.url + ".json", {"token": self.payload["token"]})
            for param, when in MessageRequest.params.iteritems():
                self.status[param] = bool(r.answer[param])
                self.status[when] = int(r.answer[when])
            for param in ["acknowledged_by", "acknowledged_by_device"]:
                self.status[param] = r.answer[param]
            self.status["last_delivered_at"] = int(r.answer["last_delivered_at"])
            if any(self.status[param] for param in MessageRequest.params):
                self.status["done"] = True
        return self.status["done"]

    def cancel(self):
        """If the message request has a priority of 2, Pushover keeps sending
        the same notification until it either reaches its ``expire`` value or
        is aknowledged by the client. Calling the :func:`cancel` function
        cancels the notification early.
        """
        if not self.status["done"]:
            return Request("post", self.url + "/cancel.json", {"token": self.payload["token"]})


class Pushover:
    """This is the main class of the module. It represents a Pushover app and
    is tied to a unique API token.

    * ``token``: Pushover API token
    """

    _SOUNDS = None
    message_keywords = ["title", "priority", "sound", "callback", "timestamp", "url", "url_title", "device", "retry", "expire", "html", "attachment"]
    glance_keywords = ["title", "text", "subtext", "count", "percent", "device"]

    def __init__(self, token):
        self.token = token

    @property
    def sounds(self):
        """Return a dictionary of sounds recognized by Pushover and that can be
        used in a notification message.
        """
        if not Pushover._SOUNDS:
            request = Request("get", SOUND_URL, {"token": self.token})
            Pushover._SOUNDS = request.answer["sounds"]
        return Pushover._SOUNDS


    def verify(self, user, device=None):
        """Verify that the `user` and optional `device` exist. Returns
        `None` when the user/device does not exist or a list of the user's
        devices otherwise.
        """
        payload = {"user": user, "token": self.token}
        if device:
            payload["device"] = device
        try:
            request = Request("post", USER_URL, payload)
        except RequestError:
            return None
        else:
            return request.answer["devices"]


    def message(self, user, message, **kwargs):
        """Send `message` to the user specified by `user`. It is possible
        to specify additional properties of the message by passing keyword
        arguments. The list of valid keywords is ``title, priority, sound,
        callback, timestamp, url, url_title, device, retry, expire and html``
        which are described in the Pushover API documentation.
        
        For convenience, you can simply set ``timestamp=True`` to set the
        timestamp to the current timestamp.

        An image can be attached to a message by passing a file-like object
        to the `attachment` keyword argument.

        This method returns a :class:`MessageRequest` object.
        """

        payload = {"message": message, "user": user, "token": self.token}
        for key, value in kwargs.iteritems():
            if key not in Pushover.message_keywords:
                raise ValueError("{0}: invalid message parameter".format(key))
            elif key == "timestamp" and value is True:
                    payload[key] = int(time.time())
            elif key == "sound" and value not in self.sounds:
                    raise ValueError("{0}: invalid sound".format(value))
            else:
                payload[key] = value

        return MessageRequest(payload)

    def glance(self, user, **kwargs):
        """Send a glance to the user. The default property is ``text``, as this
        is used on most glances, however a valid glance does not need to
        require text and can be constructed using any combination of valid
        keyword properties. The list of valid keywords is ``title, text,
        subtext, count, percent and device`` which are  described in the
        Pushover Glance API documentation.

        This method returns a :class:`GlanceRequest` object.
        """
        payload = {"user": user, "token": self.token}

        for key, value in kwargs.iteritems():
            if key not in Pushover.glance_keywords:
                raise ValueError("{0}: invalid glance parameter".format(key))
            else:
                payload[key] = value

        return Request("post", GLANCE_URL, payload)

def main():
    from ConfigParser import RawConfigParser, NoSectionError, NoOptionError
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    import os

    def read_config(config_path):
        config_path = os.path.expanduser(config_path)
        config = RawConfigParser()
        params = {"users": {}}
        files = config.read(config_path)
        if not files:
            return params
        params["token"] = config.get("main", "token")
        for name in config.sections():
            if name != "main":
                user = {}
                user["user_key"] = config.get(name, "user_key")
                try:
                    user["device"] = config.get(name, "device")
                except NoOptionError:
                    user["device"] = None
                params["users"][name] = user
        return params

    parser = ArgumentParser(description="Send a message to pushover.",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog="""
For more details and bug reports, see: https://github.com/Thibauth/python-pushover""")
    parser.add_argument("--token", help="API token")
    parser.add_argument("--user", "-u", help="User key or section name in the configuration", required=True)
    parser.add_argument("-c", "--config", help="configuration file\
                        (default: ~/.pushoverrc)", default="~/.pushoverrc")
    parser.add_argument("message", help="message to send")
    parser.add_argument("--url", help="additional url")
    parser.add_argument("--url-title", help="url title")
    parser.add_argument("--title", "-t", help="message title")
    parser.add_argument("--priority", "-p", help="notification priority (-1, 0, 1 or 2)", type=int)
    parser.add_argument("--retry", "-r", help="resend interval in seconds (required for priority 2)", type=int)
    parser.add_argument("--expire", "-e", help="expiration time in seconds (required for priority 2)", type=int)
    parser.add_argument("--version", "-v", action="version",
                        help="output version information and exit",
                        version="""
%(prog)s 1.0
Copyright (C) 2013-2018 Thibaut Horel <thibaut.horel@gmail.com>
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""")

    args = parser.parse_args()
    params = read_config(args.config)
    if args.priority==2 and (args.retry is None or args.expire is None):
        parser.error("priority of 2 requires expire and retry")
    if args.user in params["users"]:
        user_key = params["users"][args.user]["user_key"]
        device = params["users"][args.user]["device"]
    else:
        user_key = args.user
        device = None
    token = args.token or params["token"]

    Pushover(token).message(user_key, args.message, device=device,
            title=args.title, priority=args.priority, url=args.url,
            url_title=args.url_title, timestamp=True, retry=args.retry,
            expire=args.expire)

if __name__ == "__main__":
    main()
