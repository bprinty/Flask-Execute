# -*- coding: utf-8 -*-
#
# Objects for managing futures and pools of
# future objects.
#
# ------------------------------------------------


# imports
# -------
from celery.result import ResultSet


# classes
# -------
class Future(object):
    """
    Wrapper around celery.AsyncResult to provide an API similar
    to the ``concurrent.futures`` API.

    Arguments:
        result (AsyncResult): ``celery.result.AsyncResult`` object
            containing task information and celery context.
    """

    def __init__(self, result):
        self.__proxy__ = result
        self.id = self.__proxy__.id
        return

    def __getattr__(self, key):
        return getattr(self.__proxy__, key)

    def result(self, timeout=None):
        """
        Wait for task to finish and return result.

        Arguments:
            timeout (int): Number of seconds to wait for
                result to finish before timing out and raising
                an error.
        """
        self.__proxy__.wait(timeout=timeout)
        return self.__proxy__.result

    def cancel(self, *args, **kwargs):
        """
        Attempt to cancel the call. If the call is currently
        being executed or finished running and cannot be cancelled
        then the method will return False, otherwise the call will
        be cancelled and the method will return True.

        Arguments and keyword arguments passed to this function will
        be passed into the internal AsyncResult.revoke() method.
        """
        if self.__proxy__.state in ['STARTED', 'FAILURE', 'SUCCESS', 'REVOKED']:
            return False
        kwargs.setdefault('terminate', True)
        kwargs.setdefault('wait', True)
        kwargs.setdefault('timeout', 1 if kwargs['wait'] else None)
        self.__proxy__.revoke(*args, **kwargs)
        return True

    def cancelled(self):
        """
        Return ``True`` if the call was successfully cancelled.
        """
        return self.__proxy__.state == 'REVOKED'

    def running(self):
        """
        Return ``True`` if the call is currently being
        executed and cannot be cancelled.
        """
        return self.__proxy__.state in ['STARTED', 'PENDING']

    def done(self):
        """
        Return True if the call was successfully cancelled
        or finished running.
        """
        return self.__proxy__.state in ['FAILURE', 'SUCCESS', 'REVOKED']

    def exception(self, timeout=None):
        """
        Return the exception raised by the call. If the call hasn’t yet
        completed then this method will wait up to ``timeout`` seconds. If the
        call hasn’t completed in ``timeout`` seconds. If the call completed
        without raising, None is returned.

        Arguments:
            timeout (int): Number of seconds to wait for
                result to finish before timing out and raising
                an error.
        """
        try:
            self.__proxy__.wait(timeout=timeout)
        except Exception as exe:
            return exe
        return

    def add_done_callback(self, fn):
        """
        Attaches the callable fn to the future. fn will be called, with
        the task as its only argument, when the future is cancelled
        or finishes running.

        Arguments:
            fn (callable): Callable object to issue after task has
                finished executing.
        """
        self.__proxy__.then(fn)
        return self


class FuturePool(object):
    """
    Class for managing pool of futures for grouped operations.

    Arguments:
        futures (list, tuple): Iterable of ``celery.result.AsyncResult``
            objects to manage as a group of tasks.
    """

    def __init__(self, futures):
        self.futures = futures
        self.__proxy__ = ResultSet([future.__proxy__ for future in futures])
        return

    def __getattr__(self, key):
        return getattr(self.__proxy__, key)

    def __iter__(self):
        for future in self.futures:
            yield future
        return

    def __len__(self):
        return len(self.futures)

    @property
    def status(self):
        """
        Return status of future pool.
        """
        statuses = [future.status for future in self]
        for stat in ['PENDING', 'STARTED', 'RETRY', 'REVOKED', 'FAILURE', 'SUCCESS']:
            if stat in statuses:
                return stat
        return 'SUCCESS'

    @property
    def state(self):
        """
        Return state of future pool.
        """
        return self.status

    def add(self, future):
        """
        Add future object to pool.

        Arguments:
            future (Future): Future object to add to pool.
        """
        if not isinstance(future, Future):
            raise AssertionError('No rule for adding {} type to FuturePool.'.format(type(future)))
        self.futures.append(future)
        return

    def result(self, timeout=0):
        """
        Wait for entire future pool to finish and return result.

        Arguments:
            timeout (int): Number of seconds to wait for
                result to finish before timing out and raising
                an error.
        """
        return [
            future.result(timeout=timeout)
            for future in self.futures
        ]

    def cancel(self, *args, **kwargs):
        """
        Cancel all running tasks in future pool. Return value will be
        ``True`` if *all* tasks were successfully cancelled and ``False``
        if *any* tasks in the pool were running or done at the time of
        cancellation.

        Arguments and keyword arguments passed to this function will
        be passed into the internal AsyncResult.revoke() method.
        """
        result = True
        for future in self.futures:
            result &= future.cancel(*args, **kwargs)
        return result

    def cancelled(self):
        """
        Return ``True`` if any tasks were successfully cancelled.
        """
        for future in self.futures:
            if future.cancelled():
                return True
        return False

    def running(self):
        """
        Return boolean describing if *any* tasks in future pool
        are still running.
        """
        for future in self.futures:
            if future.running():
                return True
        return False

    def done(self):
        """
        Return boolean describing if *all* tasks in future pool
        are either finished or have been revoked.
        """
        for future in self.futures:
            if not future.done():
                return False
        return True

    def exception(self):
        """
        Return exception(s) thrown by task, if any were
        thrown during execution.
        """
        return [
            future.exception()
            for future in self.futures
        ]

    def add_done_callback(self, fn):
        """
        Attaches the callable fn to the future pool. fn will be
        called, with the task as its only argument, when the
        future is cancelled or finishes running.

        Arguments:
            fn (callable): Callable object to issue after task has
                finished executing.
        """
        self.__proxy__.then(fn)
        return self
