import os, sys
import json
import asyncio
import threading
import subprocess
from threading import Thread
from multiprocessing import Process


def get_app_root_path():
    root_path = os.path.dirname(sys.argv[0])
    return f"{root_path}/" if root_path else ""


def create_dir_when_none(dir_name):
    """Check if a directory exist or create one.
    return: bool."""
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
        return False
    else:
        return True


async def run_coro_threadsafe(coro, other_loop, our_loop=None, many=False):
    """Schedules coro in other_loop, awaits until coro has run and returns
    its result.
    """
    loop = our_loop or asyncio.get_event_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, other_loop)
    # fut = other_loop.call_soon_threadsafe(coro)
    # set up a threading.Event that fires when the future is finished
    finished = threading.Event()

    def fut_finished_cb(_):
        finished.set()

    fut.add_done_callback(fut_finished_cb)
    # wait on that event in an executor, yielding control to our_loop
    await loop.run_in_executor(None, finished.wait)
    # coro's result is now available in the future object
    return fut.result()


def start_thread(method, args=None, daemon=False):
    kwargs = dict(target=method)
    if args is not None:
        kwargs['args'] = args
    thread = Thread(**kwargs)
    if daemon:
        thread.setDaemon(True)
    thread.start()
    return thread


def start_process(method, args=None, kwargs=None, daemon=True):
    proc_kwargs = dict(target=method, daemon=daemon)
    if args is not None:
        proc_kwargs['args'] = args
    if kwargs is not None:
        proc_kwargs['kwargs'] = kwargs
    proc = Process(**proc_kwargs)
    proc.start()
    return proc


def is_json(myjson):
    try:
        json.loads(myjson)
    except Exception:
        return False
    return True


def _exec(*command, stdout_on=False, cwd=None):
    if stdout_on:
        result = subprocess.check_output(command).decode('utf-8')
        return result
    else:
        if cwd:
            subprocess.Popen(command, cwd=cwd)
        else:
            subprocess.Popen(command)
