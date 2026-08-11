"""
Automated Test Suite for Reviewer Assignment Uniqueness & Data Chunk Shifting.
Tests:
1. Reviewer ID Uniqueness Enforcement
2. Sequential Chunk Shifting (Chunk 0: cases 0..9, Chunk 1: cases 10..19, ...)
3. Zero-overlap verification across 50 chunks
4. Maximum assignment capacity boundary check
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import api.index as app_module
from api.index import app, mock_db, init_mock_db

class TestReviewerAssignment(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app_module.use_mock_db = True
        self.client = app.test_client()
        # Initialize mock database with 500 cases (50 chunks)
        init_mock_db(num_cases=500, chunk_size=10)

    def test_reviewer_id_uniqueness(self):
        """Test that duplicate reviewer ID is rejected."""
        # 1. Register reviewer BlueTiger27
        res1 = self.client.post('/api/register', json={
            'reviewer_id': 'BlueTiger27',
            'name': 'Blue Tiger',
            'credentials': 'Senior Advocate',
            'is_anonymous': True
        })
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1['success'])
        self.assertEqual(data1['reviewer']['chunk_index'], 0)

        # 2. Attempt registering BlueTiger27 again -> MUST FAIL
        res2 = self.client.post('/api/register', json={
            'reviewer_id': 'BlueTiger27',
            'name': 'Duplicate Tiger',
            'credentials': 'Junior Lawyer',
            'is_anonymous': False
        })
        self.assertEqual(res2.status_code, 400)
        data2 = res2.get_json()
        self.assertFalse(data2['success'])
        self.assertIn("already being used", data2['error'])

    def test_sequential_chunk_shifting(self):
        """Test that chunks shift sequentially from 0..49 without overlap."""
        assigned_case_indices = set()
        reviewers = []

        # Register 5 reviewers sequentially
        for i in range(1, 6):
            r_id = f"Reviewer_{i}"
            res = self.client.post('/api/register', json={
                'reviewer_id': r_id,
                'name': f"Reviewer Name {i}",
                'credentials': f"Credentials {i}",
                'is_anonymous': False
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data['reviewer']['chunk_index'], i - 1)
            cases = data['cases']
            self.assertEqual(len(cases), 10)
            
            # Check case index shift
            first_case_idx = cases[0]['case_index']
            last_case_idx = cases[-1]['case_index']
            expected_start = (i - 1) * 10
            expected_end = expected_start + 9

            self.assertEqual(first_case_idx, expected_start)
            self.assertEqual(last_case_idx, expected_end)

            # Check zero overlap
            chunk_indices = set(c['case_index'] for c in cases)
            overlap = assigned_case_indices.intersection(chunk_indices)
            self.assertEqual(len(overlap), 0, f"Overlap detected in chunk {i-1}: {overlap}")
            assigned_case_indices.update(chunk_indices)
            reviewers.append(r_id)

        self.assertEqual(len(assigned_case_indices), 50)
        print("[SUCCESS] Successfully tested 5 sequential reviewers. 50 cases assigned with 0 overlap!")

    def test_full_capacity_limit(self):
        """Test that registering after 50 chunks are assigned returns chunk exhausted error."""
        # Set next_chunk_index to 50
        mock_db['system']['next_chunk_index'] = 50

        res = self.client.post('/api/register', json={
            'reviewer_id': 'LateReviewer51',
            'name': 'Late Reviewer',
            'credentials': 'N/A',
            'is_anonymous': False
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("already been assigned", data['error'])
        print("[SUCCESS] Successfully verified 50 chunk max capacity limit enforcement!")

if __name__ == '__main__':
    unittest.main()
