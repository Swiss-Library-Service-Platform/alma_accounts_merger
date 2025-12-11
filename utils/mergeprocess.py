from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from dotenv import load_dotenv
import os
import time
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, ElementNotInteractableException, ElementClickInterceptedException
from almapiwrapper.users import User

from utils.staff import TempStaffUser


load_dotenv()

import logging

class MergeProcessError(Exception):
    """Custom exception for merge process errors."""
    pass

class AlmaMerger:
    """Class to handle merging users in Alma using Selenium WebDriver."""
    def __init__(self, temp_staff: TempStaffUser, headless: bool = True):
        """
        Initialize the AlmaMerger with a Selenium WebDriver.

        args:
            temp_staff (TempStaffUser): The staff user object with login credentials.
            headless (bool): Whether to run the browser in headless mode. Default is True.
        """
        self.temp_staff = temp_staff
        self.env = os.getenv('ALMA_ENV', 'prod')
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")

        # Initialize WebDriver
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 30)

    def login(self):
        """Log in to Alma using the temporary staff user credentials."""
        # Navigate to Alma login page
        self.driver.get(self.temp_staff.alma_url)
        user = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        pwd = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
        user.clear()
        user.send_keys(self.temp_staff.primary_id)
        pwd.clear()
        pwd.send_keys(self.temp_staff.password)

        # Click submit button to log in
        submit = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        submit.click()

        # Accept cookies if prompted
        accept_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        accept_btn.click()

    def open_merge_users_page(self):
        """Open the merge users page in Alma using Selenium WebDriver.
        """
        admin_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Admin']")))
        admin_btn.click()

        li_merge = self.wait.until(EC.element_to_be_clickable((
            By.XPATH, "//a[@id='MENU_LINK_ID_comexlibrisdpsadmgeneralmenuadvancedgeneralgeneralHeaderMergeUsers']"
        )))
        li_merge.click()

    def merge_users(self, from_user: str, to_user: str):
        """Merge two users in Alma using Selenium WebDriver.

        Args:
            from_user (str): The primary ID of the user to merge from.
            to_user (str): The primary ID of the user to merge to.

        Returns:
            None

        Raises:
            MergeProcessError: If any step fails during the merge process.
        """
        try:
            self.copy_internal_blocks(from_user, to_user)
        except Exception as e:
            logging.error(f"[merge_users] Error at copy_internal_blocks: {e}")
            raise MergeProcessError(f"copy_internal_blocks: {e}")

        try:
            add_job = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//a[normalize-space()='Add Job']"
            )))
            add_job.click()
        except Exception as e:
            logging.error(f"[merge_users] Error at Add Job button: {e}")
            raise MergeProcessError(f"Add Job button: {e}")
        try:
            pickup_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID,"PICKUP_ID_pageBeandisplayNameOfFromUserOrUserIdendifier"))
            )
            pickup_btn.click()
        except Exception as e:
            logging.error(f"[merge_users] Error at Pickup 'from user' button: {e}")
            raise MergeProcessError(f"Pickup 'from user' button: {e}")
        try:
            self.search_user_in_iframe(from_user)
        except Exception as e:
            logging.error(f"[merge_users] Error at search_user_in_iframe (from_user): {e}")
            raise MergeProcessError(f"search_user_in_iframe (from_user): {e}")
        try:
            pickup_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "PICKUP_ID_pageBeandisplayNameOfToUserOrUserIdendifier")))
            pickup_btn.click()
        except Exception as e:
            logging.error(f"[merge_users] Error at Pickup 'to user' button: {e}")
            raise MergeProcessError(f"Pickup 'to user' button: {e}")
        try:
            self.search_user_in_iframe(to_user)
        except Exception as e:
            logging.error(f"[merge_users] Error at search_user_in_iframe (to_user): {e}")
            raise MergeProcessError(f"search_user_in_iframe (to_user): {e}")
        try:
            time.sleep(2)
            for param in [
                'PARAM_COPY_ATTACHMENTS',
                'PARAM_COPY_NOTES',
                'PARAM_COPY_DEMERITS',
                'PARAM_COPY_PROXY_OF'
            ]:
                for attempt in range(3):
                    try:
                        checkbox_input = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//input[@type='checkbox' and @value='{param}']")))
                        if not checkbox_input.is_selected():
                            checkbox_label = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//input[@type='checkbox' and @value='{param}']/following-sibling::label[1]")))
                            checkbox_label.click()
                        break
                    except (StaleElementReferenceException, NoSuchElementException, TimeoutException, ElementNotInteractableException, ElementClickInterceptedException) as e:
                        logging.error(f"[merge_users] Error at checkbox {param}: {e}")
                        if attempt == 2:
                            raise MergeProcessError(f"Checkbox {param}: {e}")
                        time.sleep(0.5)
        except Exception as e:
            logging.error(f"[merge_users] Error at merge options: {e}")
            raise MergeProcessError(f"merge options: {e}")
        try:
            merge_btn = self.wait.until(EC.element_to_be_clickable((By.ID, 'PAGE_BUTTONS_cbuttonmerge')))
            merge_btn.click()
        except Exception as e:
            logging.error(f"[merge_users] Error at merge button: {e}")
            raise MergeProcessError(f"merge button: {e}")
        try:
            start_btn = self.wait.until(EC.element_to_be_clickable((By.ID, 'PAGE_BUTTONS_cbuttonconfirmationconfirm')))
            start_btn.click()
        except Exception as e:
            logging.error(f"[merge_users] Error at start button: {e}")
            raise MergeProcessError(f"start button: {e}")

    def search_user_in_iframe(self, primary_id: str):
        """Search for a user by primary ID within an iframe and select the first result.

        Args:
            primary_id (str): The primary ID of the user to search for.
        Raises:
            MergeProcessError: If any step fails during the search process.
        """
        try:
            iframe = self.wait.until(EC.presence_of_element_located((By.ID, "iframePopupIframe")))
            self.driver.switch_to.frame(iframe)
            time.sleep(2)
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at switching to iframe: {e}")
            raise MergeProcessError(f"switching to iframe: {e}")
        try:
            search_type = self.wait.until(EC.element_to_be_clickable((By.ID, "simpleSearchIndexButton")))
            search_type.click()
            time.sleep(1)
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at search type button: {e}")
            raise MergeProcessError(f"search type button: {e}")
        try:
            primary_id_option = self.wait.until(EC.element_to_be_clickable((By.ID, "TOP_NAV_Search_index_HFrUser.user_name")))
            primary_id_option.click()
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at primary id option: {e}")
            raise MergeProcessError(f"primary id option: {e}")
        try:
            search_user = self.wait.until(EC.element_to_be_clickable((By.ID, "ALMA_MENU_TOP_NAV_Search_Text")))
            search_user.clear()
            search_user.send_keys(primary_id)
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at search field: {e}")
            raise MergeProcessError(f"search field: {e}")
        try:
            search_button = self.wait.until(EC.element_to_be_clickable((By.ID, "simpleSearchBtn")))
            search_button.click()
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at search button: {e}")
            raise MergeProcessError(f"search button: {e}")
        try:
            user_table = self.wait.until(EC.presence_of_element_located((By.ID, "TABLE_DATA_userList")))
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at user table: {e}")
            raise MergeProcessError(f"user table: {e}")
        try:
            first_row = self.wait.until(lambda d: (
                    (rows := user_table.find_elements(By.CSS_SELECTOR, "tbody tr")) and
                    EC.element_to_be_clickable(rows[0])(d) and rows[0]
            ))
            first_row.click()
        except Exception as e:
            logging.warning(f"No user found: {e}")
            raise MergeProcessError(f"fNo user found: {e}")
        try:
            self.driver.switch_to.default_content()
        except Exception as e:
            logging.error(f"[search_user_in_iframe] Error at switch to default content: {e}")
            raise MergeProcessError(f"switch to default content: {e}")

    def copy_internal_blocks(self, from_user: str, to_user: str) -> None:
        """Copy internal blocks from one user to another.

        Args:
            from_user (User): The user to copy blocks from.
            to_user (User): The user to copy blocks to.

        Raises:
            MergeProcessError: If any step fails during the block copying process.
        """
        u_from = User(from_user, self.temp_staff.zone, self.env)
        _ = u_from.data
        if u_from.error:
            logging.error(f"User from {from_user} does not exist.")
            raise MergeProcessError(f"User from {from_user} does not exist.")

        u_to = User(to_user, self.temp_staff.zone, self.env)
        _ = u_to.data
        if u_to.error:
            logging.error(f"User to {to_user} does not exist.")
            raise MergeProcessError(f"User to {to_user} does not exist.")

        u_to.data['user_block'] += [block for block in u_from.data['user_block'] if block['segment_type']=='Internal']
        u_to.update()
        if u_to.error:
            logging.error(f"Failed to update user {to_user} after copying blocks: {u_to.error_msg}")
            raise MergeProcessError(f"Failed to update user {to_user} after copying blocks: {u_to.error_msg}")



if __name__ == '__main__':
    pass



    # def iterate_users_to_merge(self, users: list[Tuple[str, str]],
    #                            zone: str, driver:, wait:) -> None:
    #     """Iterate over a list of user pairs to merge them in Alma.
    #
    #     Args:
    #         users (list[Tuple[str, str]]): A list of tuples containing pairs of user primary IDs to merge.
    #         zone (str): The zone in which to operate.
    #
    #     Returns:
    #         None
    #     """
    #
    #     for from_user, to_user in users:
    #         merge_users(from_user, to_user, zone, driver, wait)
    #         time.sleep(2)
# except (StaleElementReferenceException, NoSuchElementException):
