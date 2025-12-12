import unittest
from typing import FrozenSet

from utils.mergeprocess import AlmaMerger, MergeProcessError
from utils.staff import TempStaffUser
from dotenv import load_dotenv
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from almapiwrapper.users import User, NewUser
from almapiwrapper.configlog import config_log
import logging

load_dotenv()
config_log()
logging.getLogger().setLevel(logging.INFO)


class TestMergeProcess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary_id = 'test_automation_2@slsp.ch'
        cls.from_user = '0000767261781304d@test.eduid.ch'
        cls.to_user = '0000767261781304@test.eduid.ch'
        cls.zone = 'UBS'
        User(cls.primary_id, cls.zone, 'S').delete()
        cls.temp_staff = TempStaffUser(cls.primary_id, cls.zone).create_staff_account()
        u1 = User(cls.to_user, cls.zone, 'S')
        u1.data['user_note'] = []
        u1.update()
        u1.data['primary_id'] = cls.from_user
        u1.data['user_identifier'][0]['value'] += 'suffix'
        NewUser(data=u1._data, zone=cls.zone, env='S').create()

    @classmethod
    def tearDownClass(cls):
        cls.temp_staff.delete()
        User(cls.from_user, cls.zone, 'S').delete()

    def test_workflow(self):
        merger = AlmaMerger(self.temp_staff, headless=False)
        merger.login()
        merger.open_merge_users_page()
        try:
            merger.merge_users(self.from_user, self.to_user)
        except MergeProcessError:
            self.fail("MergeProcessError raised during merge_users")
        merger.driver.quit()

if __name__ == '__main__':
    unittest.main()
