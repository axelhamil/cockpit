import os

from app_state import read_apps

ONE_APP = "cockpit: requests about {} go through the cockpit skill, and changes to its code follow the code-changes steps."
SEVERAL_APPS = "cockpit: requests about the saved apps go through the cockpit skill, and changes to their code follow the code-changes steps."


def reminder(state_home: str) -> str:
    complete = [app for app in read_apps(state_home) if app.onboarding == "complete"]

    if not complete:
        return ""

    if len(complete) == 1:
        return ONE_APP.format(complete[0].slug)

    return SEVERAL_APPS


def main():
    state_home = os.environ.get("COCKPIT_HOME") or os.path.join(
        os.path.expanduser("~"), ".cockpit"
    )

    try:
        line = reminder(state_home)
    except Exception:
        return

    if line:
        print(line)


if __name__ == "__main__":
    main()
