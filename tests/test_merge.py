import unittest
import os
import logging
from merge import workflow
from almapiwrapper.users import User, NewUser
import pandas as pd

class TestMergeWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        cls.data_file = os.path.join('data', 'test_merge.csv')
        df = pd.read_csv(cls.data_file, dtype=str)
        # Met à jour la colonne Merge status pour le nouveau workflow
        df['Merge_status'] = 'NOT PROCESSED'
        df.to_csv(cls.data_file, index=False)
        u1 = User('0000767261781304@test.eduid.ch', 'UBS', 'S')
        u1.data['user_note'] = []
        u1.update()
        u1.data['primary_id'] = '0000767261781304d@test.eduid.ch'
        u1.data['user_identifier'][0]['value'] += 'suffix'
        NewUser(data=u1._data, zone='UBS', env='S').create()

    def test_merge_workflow(self):
        try:
            workflow(self.data_file)
        except Exception as e:
            logging.error(f"[test_merge_workflow] Exception: {e}")
            self.fail(f"Exception raised during workflow: {e}")

        df = pd.read_csv(self.data_file, dtype=str)
        merged_rows = df[df['Merge_status'] == 'SUCCESS']
        self.assertGreater(len(merged_rows), 0)

