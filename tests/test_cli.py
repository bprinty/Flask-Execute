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
class TestCli:

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
