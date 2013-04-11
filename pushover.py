import requests
import time

BASE_URL = "https://api.pushover.net/1/"
MESSAGE_URL = BASE_URL + "messages.json"
USER_URL = BASE_URL + "users/validate.json"
SOUND_URL = BASE_URL + "sounds.json"
RECEIPT_URL = BASE_URL + "receipts/"

SOUNDS = None
TOKEN = None

def get_sounds():
    global SOUNDS
    request = Request("get", SOUND_URL, {})
    SOUNDS = request.answer["sounds"]

def init(token, sound=False):
    global TOKEN
    TOKEN = token
    if sound:
        get_sounds()

class InitError(Exception):

    def __str__(self):
        return "Init the pushover module by calling the init function"

class RequestError(Exception):

    def __init__(self, errors):
        Exception.__init__(self)
        self.errors = errors

    def __str__(self):
        return "\n==> " + "\n==> ".join(self.errors)

class Request:

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

    def __init__(self, payload):
        Request.__init__(self, "post", MESSAGE_URL, payload)
        self.receipt = None
        if payload.get("priority", 0) == 2:
            self.receipt = self.answer["receipt"]
        self.parameters = ["expired", "called_back", "expired"]
        for parameter in self.parameters:
            setattr(self, parameter, False)
            setattr(self, parameter + "_at", 0)

    def poll(self):
        if (self.receipt and not any(getattr(self, parameter)
                                     for parameter in self.parameters)):
            request = Request("get", RECEIPT_URL + self.receipt + ".json", {})
            for parameter in self.parameters:
                setattr(self, parameter, request.answer[parameter])
                setattr(self, parameter + "_at",
                        request.answer[parameter + "_at"])
            return request

class Client:

    def __init__(self, user, device=None):
        self.user = user
        self.device = device
        self.devices = []

    def verify(self, device=None):
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
        valid_keywords = ["title", "priority", "sound", "callback",
                          "timestamp", "url", "url_title", "device"]

        payload = {"message": message, "user": self.user}
        if self.device:
            payload["device"] = self.device

        for key, value in kwords.iteritems():
            if key not in valid_keywords:
                raise ValueError("{0}: invalid message parameter".format(key))

            if key == "timestamp" and value:
                payload[key] = time.time()
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
