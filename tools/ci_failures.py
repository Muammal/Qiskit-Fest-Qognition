"""Turns a pytest JUnit file into GitHub annotations, so failures show without opening the logs.

python tools/ci_failures.py results.xml
"""

import sys
import xml.etree.ElementTree as ET

ANNOTATION_LIMIT = 10  # GitHub shows at most ten errors per step.
MESSAGE_LIMIT = 900


def failures(path):
    for case in ET.parse(path).getroot().iter("testcase"):
        for problem in (*case.findall("failure"), *case.findall("error")):
            yield f"{case.get('classname')}.{case.get('name')}", f"{problem.get('message', '')}\n{problem.text or ''}"


def escape(text):
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    found = list(failures(sys.argv[1]))
    print(f"{len(found)} failures")
    for name, message in found[:ANNOTATION_LIMIT]:
        print(f"::error title={escape(name)}::{escape(message[-MESSAGE_LIMIT:])}")


if __name__ == "__main__":
    main()
