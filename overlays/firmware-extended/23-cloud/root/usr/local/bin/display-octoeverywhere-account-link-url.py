import re
from typing import Optional


def does_file_exist(file_path:str) -> bool:
    try:
        with open(file_path, 'r'):
            return True
    except FileNotFoundError:
        return False


def get_account_link_url(log_file_path:str) -> Optional[str]:
    try:
        with open(log_file_path, 'r') as log_file:
            for line in log_file:
                match = re.search(r'account-linking-url:<(https://octoeverywhere\.com/getstarted\?printerid=[^>]+)>', line)
                if match:
                    return match.group(1)
    except FileNotFoundError:
        return None
    return None


if __name__ == "__main__":
    log_file_path = '/home/lava/printer_data/logs/octoeverywhere.log'

    print('')
    print('')

    accountLinkUrl = get_account_link_url(log_file_path)
    if accountLinkUrl is not None:
        print('Use this URL to link this printer with your OctoEverywhere account:')
        print(accountLinkUrl)
    else:
        logFileExists = does_file_exist(log_file_path)
        if not logFileExists:
            print("The OctoEverywhere Plugin Is Not Running.")
            print("Enable it using the firmware config page under in Remote Access.")
        else:
            print("!! The OctoEverywhere Account Link URL Was Not Found In The Log File !!")
            print("Contact Support: https://octoeverywhere.com/support")
    print('')
    print('If you need help, follow this guide:')
    print('https://octoeverywhere.com/s/snapmaker-u1')
    print('')
    print('')
