from logging import getLogger
from asyncio import Queue, Task, CancelledError


L = getLogger(__name__)
BLOCK_DELIMITER = '\u0001'
VALUE_DELIMITER = '\u0002'


def strip_leading_e(s):
    return s.lstrip('E_')


def clear_queue(q: Queue):
    for _ in range(q.qsize()):
        q.get_nowait()
    # noinspection PyProtectedMember, PyUnresolvedReferences
    for _ in range(q._unfinished_tasks):
        q.task_done()


def on_future_task_callback(future: Task):
    # noinspection PyProtectedMember, PyUnresolvedReferences
    name = future._coro.__qualname__
    try:
        future.result()
    except CancelledError:
        pass
    except Exception:
        L.exception('Exception happened in %s coro', name)
        return
    L.info('%s coro finished successfully', name)


def exception_handler(loop, context):
    ex = context.get('exception')
    if ex is None:
        return
    L.error('Unhandled exception happened in future %s with message %s',
            context.get('future'), context.get('message'), exc_info=ex)
