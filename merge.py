from dotenv import load_dotenv
from utils.mergeprocess import AlmaMerger, MergeProcessError, UserNotFoundError
from utils.staff import TempStaffUser
import pandas as pd
import sys
import logging

from almapiwrapper.configlog import config_log
import time

def workflow(file_path: str):
    """Main workflow to merge users based on an Excel file input.

    args:
        file_path (str): Path to the Excel file containing merge instructions.
    """
    import os
    load_dotenv()

    file_name = os.path.splitext(os.path.basename(file_path))[0]

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    message_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_file_name = f'log/log{"" if len(file_name) == 0 else "_"}{file_name}.txt'
    file_handler = logging.FileHandler(log_file_name)
    file_handler.setFormatter(logging.Formatter(message_format))
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(message_format))

    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    df = pd.read_excel(file_path, dtype=str)
    if 'Merge_status' not in df.columns:
        df['Merge_status'] = 'NOT PROCESSED'
    accounts = {zone: data for zone, data in df.groupby('zone')}
    logging.info(f'Starting user merge process: {len(df)} accounts to process.')

    nb_zones = len(accounts)
    zone_nb = 0
    for zone, data in accounts.items():
        zone_nb += 1
        logging.info(f'Processing {zone} ({zone_nb} / {nb_zones} zones): {len(data)} merges to perform.')
        temp_staff = TempStaffUser(f'automation_{zone.lower()}@slsp.ch', zone).create_staff_account()

        if temp_staff.temp_user.error is True:
            logging.error(f'Failed to create temp staff account for {zone}')
            continue

        try:
            merger = AlmaMerger(temp_staff, headless=True)
            merger.login()
            merger.open_merge_users_page()
        except MergeProcessError:
            logging.error(f'Failed to initialize AlmaMerger for zone {zone}: users of the zone will not be merged')
            temp_staff.delete()
            continue

        account_nb = 0
        for i, row in data.iterrows():
            from_user = row['from_user']
            to_user = row['to_user']
            account_nb += 1

            # Skip already merged rows
            if df.at[i, 'Merge_status'] == 'SUCCESS':
                logging.info(f'Skipping already merged row {i} for {row["zone"]}: from {row["from_user"]} to {row["to_user"]}')
                continue

            logging.info(f'Processing {row["zone"]} ({account_nb}/{len(data)} - row {i}): from {from_user} to {to_user}')

            try:
                merger.merge_users(from_user, to_user)
                df.at[i, 'Merge_status'] = 'SUCCESS'
                df.to_excel(file_path, index=False)
            except UserNotFoundError:
                logging.warning(f'Merge skipped due to user not found: merge {from_user} into {to_user}')
                df.at[i, 'Merge_status'] = 'FAIL'
                df.to_excel(file_path, index=False)
                continue
            except MergeProcessError:
                logging.error(f'Failed to merge {from_user} into {to_user}')
                df.at[i, 'Merge_status'] = 'FAIL'
                df.to_excel(file_path, index=False)
                merger.driver.quit()
                try:
                    merger = AlmaMerger(temp_staff, headless=True)
                    merger.login()
                    merger.open_merge_users_page()
                    logging.error(f'Merge skipped due to error: merge {from_user} into {to_user}')
                    continue
                except MergeProcessError:
                    logging.critical(f'Failed to re-initialize AlmaMerger after error for zone {zone}')
                    break

        merger.driver.quit()
        temp_staff.delete()

if __name__ == '__main__':
    file_path = sys.argv[1]
    workflow(file_path)
