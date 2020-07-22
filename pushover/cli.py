try:
    import configparser
except ImportError:  # Python 2
    import ConfigParser as configparser

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os
from pushover import Pushover


def read_config(config_path):
    config_path = os.path.expanduser(config_path)
    config = configparser.RawConfigParser()
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
            except configparser.NoOptionError:
                user["device"] = None
            params["users"][name] = user
    return params


def main():
    parser = ArgumentParser(
        description="Send a message to pushover.",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""
For more details and bug reports, see: https://github.com/Thibauth/python-pushover""",
    )
    parser.add_argument("--token", help="API token")
    parser.add_argument(
        "--user",
        "-u",
        help="User key or section name in the configuration",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--config",
        help="configuration file\
                        (default: ~/.pushoverrc)",
        default="~/.pushoverrc",
    )
    parser.add_argument("message", help="message to send")
    parser.add_argument("--url", help="additional url")
    parser.add_argument("--url-title", help="url title")
    parser.add_argument("--title", "-t", help="message title")
    parser.add_argument(
        "--priority", "-p", help="notification priority (-1, 0, 1 or 2)", type=int
    )
    parser.add_argument(
        "--retry",
        "-r",
        help="resend interval in seconds (required for priority 2)",
        type=int,
    )
    parser.add_argument(
        "--expire",
        "-e",
        help="expiration time in seconds (required for priority 2)",
        type=int,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        help="output version information and exit",
        version="""
%(prog)s 1.0
Copyright (C) 2013-2018 Thibaut Horel <thibaut.horel@gmail.com>
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""",
    )

    args = parser.parse_args()
    params = read_config(args.config)
    if args.priority == 2 and (args.retry is None or args.expire is None):
        parser.error("priority of 2 requires expire and retry")
    if args.user in params["users"]:
        user_key = params["users"][args.user]["user_key"]
        device = params["users"][args.user]["device"]
    else:
        user_key = args.user
        device = None
    token = args.token or params["token"]

    Pushover(token).message(
        user_key,
        args.message,
        device=device,
        title=args.title,
        priority=args.priority,
        url=args.url,
        url_title=args.url_title,
        timestamp=True,
        retry=args.retry,
        expire=args.expire,
    )


if __name__ == "__main__":
    main()
