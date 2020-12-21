"""
Session class for interacting with the FiftyOne App.

| Copyright 2017-2020, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
from collections import defaultdict
from functools import wraps
import json
import logging
import random
import time
import webbrowser

import fiftyone as fo
import fiftyone.constants as focn
import fiftyone.core.dataset as fod
import fiftyone.core.client as foc
import fiftyone.core.context as focx
import fiftyone.core.service as fos
from fiftyone.core.state import StateDescription


logger = logging.getLogger(__name__)

#
# Session globals
#
# _session is the proxy `Session` for `launch_app()` and `close_app()` calls
# _server_services maintains active servers
# _subscribed_sessions maintains sessions subscribed to an active server
#
# Both maps use port as the key, so the main python process is always aware
# of what servers can be killed
#
# Note that a server process is killed via deletion of its
# `fiftyone.core.service.ServerService` instance
#
_session = None
_server_services = {}
_subscribed_sessions = defaultdict(set)


_APP_DESKTOP_MESSAGE = """
Desktop App launched.
"""

_APP_WEB_MESSAGE = """
App launched. Point your web browser to http://localhost:{0}
"""

_APP_NOTEBOOK_MESSAGE = """
Session launched. Run `session.show()` to open the App in a cell output.
"""

_REMOTE_INSTRUCTIONS = """
You have launched a remote App on port {0}. To connect to this App from another
machine, issue the following command:

fiftyone app connect --destination [<username>@]<hostname> --port {0}

where `[<username>@]<hostname>` refers to your current machine. Alternatively,
you can manually configure port forwarding on another machine as follows:

ssh -N -L 5151:127.0.0.1:{0} [<username>@]<hostname>

The App can then be viewed in your browser at http://localhost:5151.

See https://voxel51.com/docs/fiftyone/user_guide/app.html#remote-sessions
for more information about remote sessions.
"""

_WAIT_INSTRUCTIONS = """
A session appears to have terminated shortly after it was started. If you
intended to start an App instance or a remote session from a script, you should
call `session.wait()` to keep the session (and the script) alive.
"""


def launch_app(
    dataset=None,
    view=None,
    port=5151,
    remote=False,
    desktop=None,
    auto=True,
    height=800,
):
    """Launches the FiftyOne App.

    Only one app instance can be opened at a time. If this method is
    called when another app exists, the existing app is closed.

    Args:
        dataset (None): an optional :class:`fiftyone.core.dataset.Dataset` to
            load
        view (None): an optional :class:`fiftyone.core.view.DatasetView` to
            load
        port (5151): the port number to use
        remote (False): whether this is a remote session, and opening the App
            should not be attempted
        desktop (None): whether to launch the App in the browser (False) or as
            a desktop App (True). If None, ``fiftyone.config.desktop_app`` is
            used. Not applicable to notebook contexts (e.g., Jupyter and Colab)
        auto (True): whether to automatically show a new App window
            whenever the state of the session is updated. Only applicable
            in notebook contexts
        height (800): a height, in pixels, for the App. Only applicable in
            notebook contexts

    Raises:
        VaueError: if ``desktop`` is ``True`` but the desktop App package is
            not installed

    Returns:
        a :class:`Session`
    """
    global _session  # pylint: disable=global-statement
    #
    # Note, we always `close_app()` here rather than just calling
    # `session.open()` if a session already exists, because the app may have
    # been closed in some way other than `session.close()` --- e.g., the user
    # closing the GUI --- in which case the underlying Electron process may
    # still exist; in this case, `session.open()` does not seem to reopen the
    # app
    #
    # @todo this can probably be improved
    #
    close_app()

    _session = Session(
        dataset=dataset,
        view=view,
        port=port,
        remote=remote,
        desktop=desktop,
        auto=auto,
        height=height,
    )

    if _session.remote:
        logger.info(_REMOTE_INSTRUCTIONS.strip().format(_session.server_port))
    elif _session.desktop:
        logger.info(_APP_DESKTOP_MESSAGE.strip())
    elif focx._get_context() != focx._NONE and not auto:
        logger.info(_APP_NOTEBOOK_MESSAGE.strip())
    elif focx._get_context() == focx._NONE:
        logger.info(_APP_WEB_MESSAGE.strip().format(port))

    return _session


def close_app():
    """Closes the FiftyOne App, if necessary.
    If no app is currently open, this method has no effect.
    """
    global _session  # pylint: disable=global-statement
    if _session is not None:
        _session.close()
        _session = None


def _update_state(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.state.datasets = fod.list_datasets()
        self._update_state()
        return result

    return wrapper


class Session(foc.HasClient):
    """Session that maintains a 1-1 shared state with the FiftyOne App.

    **Basic Usage**

    -   Use :func:`launch_app` to launch the app and retrieve its
        corresponding :class:`Session` instance.

    -   To open a dataset in the app, simply set the
        :attr:`Session.dataset` property of the session to your
        :class:`fiftyone.core.dataset.Dataset`.

    -   To load a specific view into your dataset, simply set the
        :attr:`Session.view` property of the session to your
        :class:`fiftyone.core.view.DatasetView`.

    -   Use :meth:`Session.refresh` to refresh the App if you update a dataset
        outside of the App

    -   Use :attr:`Session.selected` to retrieve the IDs of the currently
        selected samples in the app.

    -   Use :func:`Session.close` and :func:`Session.open` to temporarily close
        and reopen the app without creating a new :class:`Session`
        instance.

    -   Use :func:`close_app` to programmatically close the app and
        terminate the session.

    Args:
        dataset (None): an optional :class:`fiftyone.core.dataset.Dataset` to
            load
        view (None): an optional :class:`fiftyone.core.view.DatasetView` to
            load
        port (5151): the port number to use
        remote (False): whether this is a remote session, and opening the App
            should not be attempted
        desktop (None): whether to launch the App in the browser (False) or as
            a desktop App (True). If None, ``fiftyone.config.desktop_app`` is
            used. Not applicable to notebook contexts (e.g., Jupyter and Colab)
        auto (True): whether to automatically show a new App window
            whenever the state of the session is updated. Only applicable
            in notebook contexts
        height (800): a height, in pixels, for the App. Only applicable in
            notebook contexts
    """

    _HC_NAMESPACE = "state"
    _HC_ATTR_NAME = "state"
    _HC_ATTR_TYPE = StateDescription

    def __init__(
        self,
        dataset=None,
        view=None,
        port=5151,
        remote=False,
        desktop=None,
        auto=True,
        height=800,
    ):
        self._context = focx._get_context()
        self._port = port
        self._remote = remote
        # maintain a reference to prevent garbage collection
        self._get_time = time.perf_counter
        self._WAIT_INSTRUCTIONS = _WAIT_INSTRUCTIONS
        self._disable_wait_warning = False
        self._auto = auto
        self._height = height

        global _server_services  # pylint: disable=global-statement
        if port not in _server_services:
            _server_services[port] = fos.ServerService(
                port, do_not_track=fo.config.do_not_track
            )

        global _subscribed_sessions  # pylint: disable=global-statement
        _subscribed_sessions[port].add(self)
        super().__init__(self._port)

        if view is not None:
            self.view = view
        elif dataset is not None:
            self.dataset = dataset

        if desktop is None:
            if self._context == focx._NONE:
                desktop = fo.config.desktop_app
            else:
                desktop = False

        self._desktop = desktop

        self._start_time = self._get_time()

        if self._remote and (self._context != focx._NONE):
            raise ValueError("Remote sessions cannot be run from a notebook")

        if self._remote:
            return

        if self._context == focx._NONE:
            if self._desktop:
                try:
                    import fiftyone.desktop
                except ImportError as e:
                    if not focn.DEV_INSTALL:
                        raise ValueError(
                            "You must install the 'fiftyone-desktop' package in "
                            "order to launch a desktop App instance"
                        ) from e

                self._app_service = fos.AppService(server_port=port)
            else:
                self.open()
        elif self._desktop:
            raise ValueError(
                "Cannot open a Desktop App instance from a notebook. Use "
                "`session.show()` to open the App."
            )

    def __repr__(self):
        return self.summary()

    def __del__(self):
        """Deletes the Session by removing it from the `_subscribed_sessions`
        global and deleting (stopping) the associated
        :class:`fiftyone.core.service.ServerService` if no other sessions are
        subscribed.
        """
        try:
            if (
                not self._disable_wait_warning
                and self._get_time() - self._start_time < 2.5
            ):
                # logger may already have been garbage-collected
                print(self._WAIT_INSTRUCTIONS)

            global _subscribed_sessions  # pylint: disable=global-statement
            _subscribed_sessions[self._port].discard(self)

            if len(_subscribed_sessions[self._port]) == 0:
                global _server_services  # pylint: disable=global-statement
                if self._port in _server_services:
                    service = _server_services.pop(self._port)
                    service.stop()
        except:
            # e.g. globals were already garbage-collected
            pass
        super().__del__()

    @property
    def remote(self):
        """Whether the session is remote."""
        return self._remote

    @property
    def desktop(self):
        """Whether the session is connected to a desktop App."""
        return self._desktop

    @_update_state
    def show(self, height=800):
        """Opens the App in the output of the current notebook cell.

        Only usable when working in notebook (e.g., Jupyter or Colab)
        environments.

        Args:
            height (800): a height, in pixels, for the App

        Raises:
            RuntimeError: if this command is run in a non-notebook environment
        """
        if self._context == focx._NONE:
            logger.warn("`Session.show()` is a no-op outside of notebooks")
            return
        if self.dataset is not None:
            self.dataset._doc.reload()
        self.state.datasets = fod.list_datasets()
        if height != 800:
            pass
        elif self._height != 800:
            height = self._height
        display(self._port, height=height)

    @property
    def dataset(self):
        """The :class:`fiftyone.core.dataset.Dataset` connected to the session.
        """
        if self.state.view is not None:
            return self.state.view._dataset

        return self.state.dataset

    @dataset.setter
    @_update_state
    def dataset(self, dataset):
        if dataset is not None:
            dataset._reload()

        self.state.dataset = dataset
        self.state.view = None
        self.state.selected = []
        self.state.selected_objects = []
        self.state.filters = {}
        self._auto_show()

    @_update_state
    def clear_dataset(self):
        """Clears the current :class:`fiftyone.core.dataset.Dataset` from the
        session, if any.
        """
        self.state.dataset = None

    @property
    def server_port(self):
        """The server port for the session."""
        return self._port

    @property
    def view(self):
        """The :class:`fiftyone.core.view.DatasetView` connected to the
        session, or ``None`` if no view is connected.
        """
        return self.state.view

    @view.setter
    @_update_state
    def view(self, view):
        self.state.view = view
        if view is not None:
            self.state.dataset = self.state.view._dataset
            self.state.dataset._reload()

        self.state.selected = []
        self.state.selected_objects = []
        self.state.filters = {}
        self._auto_show()

    @_update_state
    def clear_view(self):
        """Clears the current :class:`fiftyone.core.view.DatasetView` from the
        session, if any.
        """
        self.state.view = None
        self._auto_show()

    @property
    def selected(self):
        """A list of sample IDs of the currently selected samples in the App,
        if any.
        """
        return list(self.state.selected)

    @property
    def selected_objects(self):
        """A list of objects currently selected in the App.

        Items are dictionaries with the following keys:

            -   ``object_id``: the internal ID of the object
            -   ``sample_id``: the ID of the sample containing the object
            -   ``field``: the field name containing the object
            -   ``frame_number``: the frame number containing the object (only
                applicable to video samples)
        """
        return list(self.state.selected_objects)

    @property
    def url(self):
        """The URL of the session."""
        if self._context == focx._COLAB:
            # pylint: disable=no-name-in-module,import-error
            from google.colab.output import eval_js

            url = eval_js(
                "google.colab.kernel.proxyPort(%d)" % self.server_port
            )
            return "%s?fiftyoneColab=true" % url

        return "http://localhost:%d" % self.server_port

    @_update_state
    def refresh(self):
        """Refreshes the App, reloading the current dataset/view."""
        # @todo achieve same behavoir as if CTRL + R were pressed in the App
        self._auto_show()

    def open(self):
        """Opens the session.

        This opens the App, if necessary.
        """
        if self._remote:
            raise ValueError("Remote sessions cannot launch the FiftyOne App")

        if self._context != focx._NONE:
            raise ValueError(
                "Notebook sessions cannot launch the FiftyOne App; use "
                "`session.show()` instead"
            )

        if not self._desktop:
            webbrowser.open(self.url, new=2)
            return

        self._app_service.start()

    def close(self):
        """Closes the session.

        This terminates the FiftyOne Desktop App, if necessary.
        """
        if self._remote:
            return

        self.state.close = True
        self._update_state()

    def summary(self):
        """Returns a string summary of the session.

        Returns:
            a string summary
        """
        if self.dataset:
            dataset_name = self.dataset.name
            media_type = self.dataset.media_type
        else:
            dataset_name = None
            media_type = "N/A"

        elements = ["Dataset:          %s" % dataset_name]

        if self.dataset:
            num_samples = len(self.view) if self.view else len(self.dataset)
            elements.extend(
                [
                    "Media type:       %s" % media_type,
                    "Num samples:      %d" % num_samples,
                    "Selected samples: %d" % len(self.selected),
                    "Selected objects: %d" % len(self.selected_objects),
                ]
            )

        elements.extend(["URL:              %s" % self.url])

        if self.view:
            elements.extend(
                ["View stages:", self.view._make_view_stages_str()]
            )

        return "\n".join(elements)

    def wait(self):
        """Waits for the session to be closed by the user.

        For local sessions, this will wait until the app is closed by the user.
        For remote sessions, this will wait until the server shuts down, which
        typically requires interrupting the calling process with Ctrl-C.
        """
        try:
            if self._remote or not self._desktop:
                try:
                    _server_services[self._port].wait()
                except:
                    while True:
                        time.sleep(1)
            else:
                self._app_service.wait()
        except KeyboardInterrupt:
            self._disable_wait_warning = True
            raise

    # PRIVATE #################################################################

    def _update_state(self):
        # see fiftyone.core.client if you would like to understand this
        self.state = self.state

    def _auto_show(self):
        if self._context != focx._NONE and self._auto:
            self.show()


def display(port=None, height=None):
    """Display a running FiftyOne instance.

    Args:
      port: The port on which the FiftyOne server is listening, as an
        `int`.
      height: The height of the frame into which to render the FiftyOne
        UI, as an `int` number of pixels, or `None` to use a default value
        (currently 800).
    """
    _display(port=port, height=height)


def _display(port=None, height=None):
    """Internal version of `display`.

    Args:
      port: As with `display`.
      height: As with `display`.
    """
    if height is None:
        height = 800

    fn = {focx._COLAB: _display_colab, focx._IPYTHON: _display_ipython}[
        focx._get_context()
    ]
    return fn(port, height)


def _display_colab(port, height):
    """Display a FiftyOne instance in a Colab output frame.

    The Colab VM is not directly exposed to the network, so the Colab runtime
    provides a service worker tunnel to proxy requests from the end user's
    browser through to servers running on the Colab VM: the output frame may
    issue requests to https://localhost:<port> (HTTPS only), which will be
    forwarded to the specified port on the VM.

    It does not suffice to create an `iframe` and let the service worker
    redirect its traffic (`<iframe src="https://localhost:6006">`), because for
    security reasons service workers cannot intercept iframe traffic. Instead,
    we manually fetch the FiftyOne index page with an XHR in the output frame,
    and inject the raw HTML into `document.body`.
    """
    import IPython.display

    shell = """
        (async () => {
            const url = new URL(await google.colab.kernel.proxyPort(%PORT%, {'cache': true}));
            url.searchParams.set('fiftyoneColab', 'true');
            url.searchParams.set('notebook', 'true');
            const iframe = document.createElement('iframe');
            iframe.src = url;
            iframe.setAttribute('width', '100%');
            iframe.setAttribute('height', '%HEIGHT%');
            iframe.setAttribute('frameborder', 0);
            document.body.appendChild(iframe);
        })();
    """
    replacements = [
        ("%PORT%", "%d" % port),
        ("%HEIGHT%", "%d" % height),
    ]
    for (k, v) in replacements:
        shell = shell.replace(k, v)
    script = IPython.display.Javascript(shell)

    IPython.display.display(script)


def _display_ipython(port, height):
    import IPython.display

    src = "http://localhost:%d/?notebook=true" % port
    iframe = IPython.display.IFrame(src, height=height, width="100%")
    IPython.display.display(iframe)
