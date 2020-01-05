# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import requests


# session
# -------
class TestCli(object):

    def test_status(self):
        return

    def test_worker(self):
        # start worker and test if running
        return

    def test_flower(self):
        return

    def test_cluster(self):
        # start cluster and run diagnostics

        # submit tasks via api
        response = requests.post('https://localhost:5000/submit')
        assert response.status_code == 200
        assert len(response.json) == 3

        # monitor sleep results
        task = response.json[-1]
        response = requests.get('https://localhost:5000/monitor/{}'.format(task))
        assert response.status_code == 200
        assert response.json == {'status': 'PENDING'}

        # monitor add results
        task = response.json[0]
        response = requests.get('https://localhost:5000/monitor/{}'.format(task))
        assert response.status_code == 200
        assert response.json == {'status': 'COMPLETED'}
        return
