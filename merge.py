from dotenv import load_dotenv
from utils.mergeprocess import AlmaMerger, MergeProcessError
from utils.staff import TempStaffUser
import pandas as pd
import sys
import logging

from almapiwrapper.configlog import config_log
import time

config_log()
load_dotenv()

file_path = sys.argv[1]
df = pd.read_excel(file_path, dtype=str)
accounts = {zone: data for zone, data in df.groupby('zone')}
logging.info(f'Starting user merge process: {len(df)} accounts to process.')

nb_zones = len(accounts)
zone_nb = 0
for zone, data in accounts.items():
    zone_nb += 1
    logging.info(f'Processing {zone} ({zone_nb} / {nb_zones}): {len(data)} merges to perform.')
    temp_staff = TempStaffUser(f'automation_{zone.lower()}@slsp.ch', zone).create_staff_account()

    merger = AlmaMerger(temp_staff, headless=True)
    merger.login()
    merger.open_merge_users_page()

    for i, row in data.iterrows():
        from_user = row['from_user']
        to_user = row['to_user']
        logging.info(f'Processing {row["zone"]} ({i+1}/{len(data)}): from {from_user} to {to_user}')

        try:
            merger.merge_users(from_user, to_user)
        except MergeProcessError as e:
            logging.error(f'Failed to merge {from_user} into {to_user}: {e}')
            merger.driver.get(temp_staff.alma_url)
            time.sleep(5)
            merger.open_merge_users_page()

    merger.driver.quit()
    temp_staff.delete()

config_log()
staff_user = TempStaffUser('automation@slsp.ch', 'ISR').create_staff_account()


