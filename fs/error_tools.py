from __future__ import print_function
from __future__ import unicode_literals

import errno
from contextlib import contextmanager
import sys

from . import errors

from six import reraise


class _ConvertOSErrors(object):
    """Context manager to convert OSErrors in to FS Errors."""

    ERRORS = {
        64: errors.RemoteConnectionError,  # ENONET
        errno.ENOENT: errors.ResourceNotFound,
        errno.EFAULT: errors.ResourceNotFound,
        errno.ESRCH: errors.ResourceNotFound,
        errno.ENOTEMPTY: errors.DirectoryNotEmpty,
        errno.EEXIST: errors.DirectoryExists,
        183: errors.DirectoryExists,
        errno.ENOTDIR: errors.DirectoryExpected,
        errno.EISDIR: errors.FileExpected,
        errno.EINVAL: errors.ResourceInvalid,
        errno.ENOSPC: errors.InsufficientStorage,
        errno.EPERM: errors.PermissionDenied,
        errno.ENETDOWN: errors.RemoteConnectionError,
        errno.ECONNRESET: errors.RemoteConnectionError,
        errno.ENAMETOOLONG: errors.PathError,
        errno.EOPNOTSUPP: errors.Unsupported,
        errno.ENOSYS: errors.Unsupported
    }

    def __init__(self, opname, path):
        self._opname = opname
        self._path = path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and isinstance(exc_value, EnvironmentError):
            _errno = exc_value.errno
            fserror = self.ERRORS.get(_errno, errors.OperationFailed)
            if _errno == errno.EACCES and sys.platform == "win32":
                if getattr(exc_value, 'args', None) == 32:  # pragma: no cover
                    fserror = errors.ResourceLocked
            reraise(
                fserror,
                fserror(
                    self._path,
                    exc=exc_value
                ),
                traceback
            )

# Stops linter complaining about invalid class name
convert_os_errors = _ConvertOSErrors


@contextmanager
def unwrap_errors(path_replace):
    """
    A context manager to re-write the paths in resource exceptions to be
    in the same context as the wrapped filesystem.

    The only parameter may be the path from the parent, if only one path
    is to be unwrapped. Or it may be a dictionary that maps wrapped
    paths on to unwrapped paths.

    """
    try:
        yield
    except errors.ResourceError as e:
        if hasattr(e, 'path'):
            if isinstance(path_replace, dict):
                e.path = path_replace.get(e.path, e.path)
            else:
                e.path = path_replace
        reraise(type(e), e)
