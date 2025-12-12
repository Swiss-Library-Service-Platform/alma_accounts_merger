import os

from almapiwrapper.users import User, NewUser
from almapiwrapper.configlog import config_log
from almapiwrapper.record import JsonData
import string
import secrets

from importlib.resources import files
from dotenv import load_dotenv
from copy import deepcopy


load_dotenv()

class TempStaffUser:

    staff_template = JsonData(filepath=files('utils').joinpath('staff.json'))
    iz_info = JsonData(filepath=files('utils').joinpath('iz_info.json')).content

    """Temporary class to hold staff user data."""
    def __init__(self, primary_id: str, zone: str):
        self.primary_id = primary_id
        self.password = self.generate_password()
        self.zone = zone
        self.env = os.getenv('ALMA_ENV', 'prod')
        self.alma_url = self.get_alma_url(zone)
        self.temp_user = None

    @staticmethod
    def generate_password(length: int = 12) -> str:
        """Generate a secure random password.
        Args:
            length (int): The length of the password to generate. Default is 12.

        Returns:
            str: The generated password.
        """
        # Define the character set: letters, digits, and punctuation
        characters = string.ascii_letters + string.digits + string.punctuation

        # Generate a secure random password
        password = ''.join(secrets.choice(characters) for _ in range(length))

        return password

    def get_template(self, primary_id: str, zone: str) -> JsonData:
        """Update the staff template with the primary ID and password.

        Args:
            template (JsonData): The staff template JSON data.

        Returns:
            JsonData: The updated staff template.
        """
        staff_template = deepcopy(self.staff_template)
        staff_template.content['primary_id'] = primary_id
        staff_template.content['user_role'][0]['scope']['value'] = self.iz_info['iz_codes'][zone]
        return staff_template

    def get_alma_url(self, zone: str) -> str:
        """Get the Alma URL for the specified zone.

        Args:
            zone (str): The zone in which to create the staff account.

        Returns:
            str: The Alma URL for the specified zone.
        """
        return self.iz_info['alma_urls'][zone][os.getenv('ALMA_ENV', 'prod')]

    def create_staff_account(self) -> User:
        """Create a staff account in the specified zone using a template JSON file.

        Args:
            zone (str): The zone in which to create the staff account.

        Returns:
            User: The created staff user object.
        """
        # Open the staff.json resource file using importlib.resources
        staff_template = self.get_template(self.primary_id, self.zone)
        self.temp_user = NewUser(data=staff_template,
                    zone=self.zone,
                    env=os.getenv('ALMA_ENV', 'prod')
        ).create(password=self.password)

        return self

    def delete(self):
        """Delete the staff account."""
        User(self.primary_id, self.zone, os.getenv('ALMA_ENV', 'prod')).delete()


if __name__ == '__main__':
    staff_user = TempStaffUser('automation@slsp.ch', 'NZ').create_staff_account()
    staff_user.delete()
