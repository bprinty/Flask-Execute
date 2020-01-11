# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import json
import atexit
import requests
import subprocess


# config
# ------
PROCESSES = []


def monitor(func):
    def _(*args, **kwargs):
        global PROCESSES
        proc = func(*args, **kwargs)
        PROCESSES.append(proc)
        return proc
    return _


subprocess.Popen = monitor(subprocess.Popen)


# session
# -------
class TestCli(object):

    @classmethod
    def teardown_class(cls):
        global PROCESSES
        for proc in PROCESSES:
            proc.terminate()
            proc.kill()
            proc.wait()
        return

    def test_status(self, client):
        # submit tasks via api
        response = client.post('/ping')
        assert response.status_code == 200
        assert response.json['result'] == 'pong'

        # workers should be running
        output = subprocess.check_output('flask celery status', stderr=subprocess.STDOUT, shell=True).decode('utf-8')
        assert 'online' in output
        assert 'OK' in output
        return

    def test_worker(self):
        worker = 'test_worker'

        # specific worker not running
        output = subprocess.check_output('flask celery status', stderr=subprocess.STDOUT, shell=True).decode('utf-8')
        assert worker not in output

        # start workers
        subprocess.Popen('flask celery worker -n {}@%h'.format(worker), stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        subprocess.Popen('flask celery worker', stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)

        # wait for status checking to return
        timeout = 0
        while timeout < 5:
            output = subprocess.check_output('flask celery status', stderr=subprocess.STDOUT, shell=True).decode('utf-8')
            if 'online' in output:
                break
            timeout += 1

        # assert specific worker is running
        assert worker in output
        return

    def test_flower(self):
        # start flower
        proc = subprocess.popen('exec flask celery flower --port=9162', shell=True)

        # ping and make assertions
        response = requests.post('https://localhost:9162/ping')
        assert False
        return

    def test_cluster(self):
        # check celery status to make sure no workers running
        output = subprocess.check_output('flask celery status', shell=True)
        assert False

        # start cluster
        proc = subprocess.popen('flask celery cluster', shell=True)
        assert False

        # check cluster status
        output = subprocess.check_output('flask celery status', shell=True)
        assert False

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

        # stop cluster and check status
        proc.terminate()
        output = subprocess.check_output('flask celery status', shell=True)
        assert False
        return
