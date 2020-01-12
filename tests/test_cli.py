# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import os
import time
import requests
import subprocess


# session
# -------
class TestCli(object):

    def test_status(self, client, celery):
        # submit tasks via api
        response = client.post('/ping')
        assert response.status_code == 200
        assert response.json['result'] == 'pong'

        # workers should be running
        output = subprocess.check_output('flask celery status', stderr=subprocess.STDOUT, shell=True).decode('utf-8')
        assert 'online' in output
        assert 'OK' in output
        return

    def test_worker(self, celery):
        worker = 'test_worker'

        # specific worker not running
        output = subprocess.check_output('flask celery status', stderr=subprocess.STDOUT, shell=True).decode('utf-8')
        assert worker not in output

        # start worker
        args = 'flask celery worker -n {}@%h'.format(worker).split(' ')
        celery.processes[worker] = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

        # wait for status checking to return
        timeout = 0
        while timeout < 5:
            output = subprocess.check_output('flask celery status', stderr=subprocess.STDOUT, shell=True).decode('utf-8')
            if 'online' in output and worker in output:
                break
            timeout += 1

        # assert specific worker is running
        assert worker in output
        return

    def test_cluster(self, client, celery):
        # start cluster
        args = 'flask celery cluster -f'.split(' ')
        celery.processes['cluster'] = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

        # check cluster status
        output = subprocess.check_output('flask celery status', shell=True).decode('utf-8')
        assert 'online' in output
        assert 'OK' in output

        # submit tasks via api
        # submit tasks via api
        response = client.post('/submit')
        assert response.status_code == 200
        assert len(response.json) == 5
        tasks = response.json

        # monitor results
        sleep = tasks[3]
        response = client.get('/monitor/{}'.format(sleep))
        assert response.status_code == 200
        assert response.json == {'status': 'PENDING'}

        # wait for something to finish and check statuses of other tasks
        celery.get(sleep).result()
        success = 0
        for task in tasks:
            response = client.get('/monitor/{}'.format(task))
            assert response.status_code == 200
            if 'SUCCESS' in response.json['status']:
                success += 1
        assert success > 0

        # wait for flower availability
        response, tries = None, 0
        while tries < 5:
            try:
                response = requests.get('http://localhost:5555/api/workers')
                break
            except requests.exceptions.ConnectionError:
                tries += 1
                time.sleep(0.5)
        assert response is not None
        return


class TestSetupPatterns:

    def test_direct(self, celery):
        env = os.environ.copy()
        env['FLASK_APP'] = 'tests.resources.direct'
        env['FLASK_ENV'] = 'development'
        celery.processes['factory'] = subprocess.Popen(['flask', 'run', '--port=5002'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, env=env)

        # wait for server to start
        response, tries = None, 0
        while tries < 5:
            try:
                response = requests.get('http://localhost:5002')
                assert response.json() == {'status': 'ok'}
                break
            except requests.exceptions.ConnectionError:
                tries += 1
                time.sleep(0.5)
        assert response is not None

        # ping
        response = requests.get('http://localhost:5002/ping')
        assert response.json() == {'msg': 'pong'}

        # task
        response = requests.get('http://localhost:5002/task')
        assert response.json() == {'success': True}
        return
