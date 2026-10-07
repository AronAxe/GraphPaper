"""Owned external process lifetime, including descendants; never targets unrelated processes."""
from __future__ import annotations
import os
import signal
import subprocess
import time


class _WindowsJob:
    def __init__(self, pid: int):
        import ctypes
        from ctypes import wintypes as w
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class Basic(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
        class Extended(ctypes.Structure):
            _fields_ = [('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR]; k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]; k.SetInformationJobObject.restype=w.BOOL
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; k.OpenProcess.restype=w.HANDLE
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]; k.AssignProcessToJobObject.restype=w.BOOL
        k.CloseHandle.argtypes=[w.HANDLE]; k.CloseHandle.restype=w.BOOL
        self.k=k; self.handle=k.CreateJobObjectW(None,None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        try:
            limits=Extended(); limits.BasicLimitInformation.LimitFlags=0x2000  # KILL_ON_JOB_CLOSE
            if not k.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            process=k.OpenProcess(0x0100|0x0001,False,pid)  # SET_QUOTA | TERMINATE
            if not process: raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not k.AssignProcessToJobObject(self.handle,process):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally: k.CloseHandle(process)
        except BaseException:
            self.close(); raise

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle=None


class OwnedProcess:
    """Launch a separate process tree and always reclaim it, including on normal exit."""
    def __init__(self, args, **kwargs):
        self.job=None
        if os.name=='nt': kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
        else: kwargs['start_new_session']=True
        self.proc=subprocess.Popen(args,**kwargs)
        if os.name=='nt':
            try:
                self.job=_WindowsJob(self.proc.pid)
            except OSError:
                # A very fast probe may have already exited. A live uncontained
                # worker must not continue after we lose lifecycle control.
                if self.proc.poll() is None:
                    self.proc.kill(); self.proc.wait(timeout=5)
                    raise RuntimeError('Windows could not isolate the Graphify process tree; no extraction was continued.')

    def close(self):
        if self.job is not None:
            self.job.close()
        elif os.name!='nt':
            try: os.killpg(self.proc.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        elif self.proc.poll() is None:
            self.proc.terminate()
        try: self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            if os.name!='nt':
                try: os.killpg(self.proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            else: self.proc.kill()
            self.proc.wait(timeout=5)
        if os.name!='nt':
            # Reap a descendant that ignored TERM even if its parent has exited.
            try: os.killpg(self.proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass

        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            if stream is not None and not stream.closed: stream.close()

    def __enter__(self): return self.proc
    def __exit__(self,*args): self.close()
