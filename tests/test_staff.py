from almapiwrapper.users import User
from almapiwrapper.configlog import config_log
import unittest
from unittest.mock import patch, MagicMock
import string
from utils.staff import TempStaffUser

import logging

config_log()
logging.getLogger().setLevel(logging.INFO)

class TestTempStaffUserUBS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary_id = 'test_automation@slsp.ch'
        cls.zone = 'UBS'
        User(cls.primary_id, cls.zone, 'S').delete()
        cls.user = TempStaffUser(cls.primary_id, cls.zone)

    def test_generate_password_length(self):
        password = TempStaffUser.generate_password(16)
        self.assertEqual(len(password), 16)

    def test_generate_password_charset(self):
        password = TempStaffUser.generate_password(12)
        allowed = set(string.ascii_letters + string.digits + string.punctuation)
        self.assertTrue(all(c in allowed for c in password))

    def test_get_template(self):
        template = self.user.get_template(self.primary_id, self.zone)
        self.assertEqual(template.content['primary_id'], self.primary_id)
        self.assertEqual(template.content['user_role'][0]['scope']['value'], self.user.iz_info['iz_codes'][self.zone])

    def test_get_alma_url(self):
        url = self.user.get_alma_url(self.zone)
        self.assertTrue(url.startswith('https://'))

    def test_create_staff_account(self):
        self.user.create_staff_account()
        u = User(self.primary_id, self.zone, 'S')
        self.assertEqual(self.primary_id, u.data['primary_id'])
        self.assertEqual(self.zone, u.zone)
        self.user.delete()
        u = User(self.primary_id, self.zone, 'S')
        _ = u.data
        self.assertTrue(u.error)


class TestTempStaffUserHPH(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary_id = 'test_automation@slsp.ch'
        cls.zone = 'HPH'
        User(cls.primary_id, cls.zone, 'S').delete()
        cls.user = TempStaffUser(cls.primary_id, cls.zone)

    def test_create_staff_account(self):
        self.user.create_staff_account()
        u = User(self.primary_id, self.zone, 'S')
        self.assertEqual(self.primary_id, u.data['primary_id'])
        self.assertEqual(self.zone, u.zone)
        self.user.delete()
        u = User(self.primary_id, self.zone, 'S')
        _ = u.data
        self.assertTrue(u.error)


if __name__ == '__main__':
    unittest.main()
