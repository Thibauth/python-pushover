"""After being imported, the module must be initialized by calling the :func:`init`
function with a valid application token before sending messages.

A typical use of the module looks like this::

    import pushover

    pushover.init("token")
    client = Client("client-id")
    client.send_message("Hello!", title="Hello", priority=1)
"""

import requests
import time

__all__ = ["init", "get_sounds", "Client", "MessageRequest",
           "InitError", "RequestError"]

BASE_URL = "https://api.pushover.net/1/"
MESSAGE_URL = BASE_URL + "messages.json"
USER_URL = BASE_URL + "users/validate.json"
SOUND_URL = BASE_URL + "sounds.json"
RECEIPT_URL = BASE_URL + "receipts/"

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
        return "Init the pushover module by calling the init function"

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
        print self.answer

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
        self.parameters = ["expired", "called_back", "acknowledged"]
        for parameter in self.parameters:
            setattr(self, parameter, False)
            setattr(self, parameter + "_at", 0)

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

            request = client.send_message("Urgent notification", priority=2)
            while not request.poll():
                # do something
                time.sleep(5)
        """
        if (self.receipt and not any(getattr(self, parameter)
                                     for parameter in self.parameters)):
            request = Request("get", RECEIPT_URL + self.receipt + ".json", {})
            for parameter in self.parameters:
                setattr(self, parameter, request.answer[parameter])
                setattr(self, parameter + "_at",
                        request.answer[parameter + "_at"])
            return request

class Client:
    """This is the main class of the module. It represents a specific Pushover
    user to whom messages will be sent when calling the :func:`send_message`
    method.

    * ``user``: the Pushover's ID of the user.
    * ``device``: if not ``None`` further ties the Client object to the
      specified device.
    """

    def __init__(self, user, device=None):
        self.user = user
        self.device = device
        self.devices = []

    def verify(self, device=None):
        """Verify that the Client object is tied to an existing Pushover user
        and fetches a list of this user active devices accessible in the
        :attr:`devices` attribute. Returns a boolean depending of the validity
        of the user.
        """
        payload = {"user": self.user}
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
        url_title, device, retry and expire`` which are described in the
        Pushover API documentation. For convenience, you can simply set
        ``timestamp=True`` to set the timestamp to the current timestamp.

        This method returns a :class:`MessageRequest` object.
        """
        valid_keywords = ["title", "priority", "sound", "callback",
                          "timestamp", "url", "url_title", "device",
                          "retry", "expire"]

        payload = {"message": message, "user": self.user}
        if self.device:
            payload["device"] = self.device

        for key, value in kwords.iteritems():
            if key not in valid_keywords:
                raise ValueError("{0}: invalid message parameter".format(key))

            if key == "timestamp" and value:
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


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Send a message to pushover.")
    parser.add_argument("--token", help="Pushover application token",
                        required=True)
    parser.add_argument("--client", "-c", help="Pushover client ID",
                        required=True)
    parser.add_argument("message", help="message to send")
    parser.add_argument("--title", "-t", help="message title")
    parser.add_argument("--priority", "-p", help="message priority")
    parser.add_argument("--url", help="additional url")
    parser.add_argument("--url-title", help="additional url title")

    args = parser.parse_args()
    init(args.token)
    Client(args.client).send_message(args.message, title=args.title,
                                     priority=args.priority, url=args.url,
                                     url_title=args.url_title, timestamp=True)
