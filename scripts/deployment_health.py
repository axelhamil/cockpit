import json
import re
import sys

BROKEN = {"FAILED", "CRASHED"}
REPORT_LIMIT = 5
NAME_LIMIT = 30


def plain(name):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(name))[:NAME_LIMIT] or "unnamed"


def nodes(container):
    return [edge["node"] for edge in container["edges"]]


def deployments(project):
    for environment in nodes(project["environments"]):
        for instance in nodes(environment["serviceInstances"]):
            deployment = instance.get("latestDeployment") or {}
            yield environment.get("name"), instance.get("serviceName"), deployment.get("status")


def main():
    try:
        seen = list(deployments(json.load(sys.stdin)))
    except (AttributeError, KeyError, TypeError, ValueError):
        print("health: not checked, the answer from Railway could not be read")
        return

    broken = [
        (environment, service, status)
        for environment, service, status in seen
        if isinstance(status, str) and status in BROKEN
    ]

    for environment, service, status in broken[:REPORT_LIMIT]:
        print('health: PROBLEM, service "{}" in environment "{}" is {}'.format(plain(service), plain(environment), status))

    if len(broken) > REPORT_LIMIT:
        print("health: PROBLEM, {} more services are failing".format(len(broken) - REPORT_LIMIT))


main()
