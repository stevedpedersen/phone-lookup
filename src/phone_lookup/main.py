import argparse
import base64
import json
import os
import urllib.error
import urllib.request
import webbrowser
from importlib.resources import files

import phonenumbers
from phonenumbers import PhoneNumberType, carrier, geocoder, timezone

TWILIO_LOOKUP_URL = "https://lookups.twilio.com/v2/PhoneNumbers/{}?Fields=caller_name,line_type_intelligence"


def parse_number(raw: str) -> phonenumbers.PhoneNumber:
    """Accepts pretty much any US format: 5595551234, (559) 555-1234, +1 559.555.1234, etc."""
    return phonenumbers.parse(raw, "US")


def offline_info(num: phonenumbers.PhoneNumber) -> dict[str, str]:
    """Free, offline facts from Google's libphonenumber data. Location is by area code/exchange, not the caller."""
    return {
        "Valid number": "yes" if phonenumbers.is_valid_number(num) else "NO (likely spoofed)",
        "Location": geocoder.description_for_number(num, "en") or "unknown",
        "Time zone": ", ".join(timezone.time_zones_for_number(num)) or "unknown",
        "Line type": PhoneNumberType.to_string(phonenumbers.number_type(num)),
        "Original carrier": carrier.name_for_number(num, "en") or "unknown",
    }


def twilio_info(num: phonenumbers.PhoneNumber) -> dict[str, str] | None:
    """Caller ID name (CNAM) + current carrier/line type via Twilio Lookup. ~2 cents per lookup.

    Only runs when TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are set.
    """
    sid, token = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")
    if not (sid and token):
        return None

    e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    req = urllib.request.Request(TWILIO_LOOKUP_URL.format(urllib.request.quote(e164)))
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except urllib.error.URLError as e:
        return {"Error": str(e)}

    cname = data.get("caller_name") or {}
    line = data.get("line_type_intelligence") or {}
    return {
        "Caller name": cname.get("caller_name") or "not listed",
        "Caller type": cname.get("caller_type") or "unknown",
        "Line type": line.get("type") or "unknown",
        "Carrier": line.get("carrier_name") or "unknown",
    }


def site_urls(num: phonenumbers.PhoneNumber) -> list[tuple[str, str]]:
    digits = str(num.national_number)
    parts = {"area": digits[:3], "prefix": digits[3:6], "line": digits[6:]}
    sites = json.loads(files("phone_lookup").joinpath("sites.json").read_text())
    return [(s["name"], s["url"].format(**parts)) for s in sites]


def print_section(title: str, info: dict[str, str]):
    print(f"\n{title}")
    width = max(map(len, info))
    for k, v in info.items():
        print(f"  {k:<{width}}  {v}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reverse phone number lookup.")
    parser.add_argument("number", nargs="?", help="phone number in any format (prompted if omitted)")
    parser.add_argument("-o", "--open", nargs="?", type=int, const=0, metavar="N",
                        help="open lookup sites in the browser (all of them, or just the first N)")
    args = parser.parse_args(argv)

    raw = args.number or input("Phone number: ")
    try:
        num = parse_number(raw)
    except phonenumbers.NumberParseException as e:
        print(f"Couldn't parse {raw!r}: {e}")
        return 1
    if not phonenumbers.is_possible_number(num):
        print(f"{raw!r} doesn't look like a full phone number (wrong number of digits?)")
        return 1

    print(phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL))
    print_section("Number info (offline)", offline_info(num))

    twilio = twilio_info(num)
    if twilio:
        print_section("Caller ID (Twilio)", twilio)
    else:
        print("\n(Set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN to look up the caller ID name.)")

    urls = site_urls(num)
    if args.open is not None:
        for name, url in urls[: args.open or None]:
            webbrowser.open(url)
    else:
        print("\nLookup sites (cmd-click to open, or rerun with --open):")
        for name, url in urls:
            print(f"  {name:<17} {url}")
    return 0
