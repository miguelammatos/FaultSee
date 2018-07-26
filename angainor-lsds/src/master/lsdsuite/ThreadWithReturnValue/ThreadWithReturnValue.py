from threading import Thread
from builtins import super    # https://stackoverflow.com/a/30159479

_thread_target_key = '_target'
_thread_args_key = '_args'
_thread_kwargs_key = '_kwargs'


class ThreadWithReturn(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._return = None

    def run(self):
        target = getattr(self, _thread_target_key)
        if not target is None:
            self._return = target(*getattr(self, _thread_args_key), **getattr(self, _thread_kwargs_key))

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        return self._return