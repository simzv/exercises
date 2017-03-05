from copy import deepcopy
from datetime import datetime

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import maybeDeferred
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import ProcessProtocol
from twisted.names import client
from twisted.python.failure import Failure
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.util import redirectTo


# ------------------------------------------------------------------------------


class AsyncLimitedProcessor(object):

    def __init__(self, limit):
        self._queue = []
        self._active_count = 0
        self._limit = limit

    def _next(self):
        if self._queue:
            handler_args = self._queue.pop(0)
            self._process(*handler_args)

    def _callback(self, handler_result, process_result):
        process_result.callback(handler_result)
        self._active_count -= 1
        self._next()

    def _errback(self, handler_fail, process_result):
        process_result.errback(handler_fail)
        self._active_count -= 1
        self._next()

    def _handle_item(self, item):
        raise NotImplementedError("Override in subclasses!!!")

    def _process(self, process_result, item):
        self._active_count += 1
        handler_result = maybeDeferred(self._handle_item, item)
        handler_callbacks_args = (process_result,)
        handler_result.addCallbacks(
            self._callback,
            errback=self._errback,
            callbackArgs=handler_callbacks_args,
            errbackArgs=handler_callbacks_args
        )

    def enqueue(self, item):
        process_result = Deferred()
        handler_args = (process_result, item)
        if self._active_count < self._limit:
            self._process(*handler_args)
        else:
            self._queue.append(handler_args)
        return process_result


# ------------------------------------------------------------------------------

class ReverseResolver(AsyncLimitedProcessor):

    def _reverse_name_by_ip_addr(self, ip_addr):
        return '.'.join(reversed(ip_addr.split('.'))) + '.in-addr.arpa'

    @inlineCallbacks
    def _handle_item(self, item):
        reversed_name = self._reverse_name_by_ip_addr(item['ip_addr'])
        resolve_results = yield client.lookupPointer(reversed_name)
        item['name'] = resolve_results[0][0].payload.name.name


# ------------------------------------------------------------------------------


class WhoisProcessProtocol(ProcessProtocol):

    def __init__(self, item, handler_result):
        self._item = item
        self._handler_result = handler_result
        self._out = None
        self._error_message = None

    def outReceived(self, data):
        self._out = data

    def errReceived(self, data):
        self._error_message = data

    def processEnded(self, reason):
        if reason.value.exitCode > 0:
            message = self._error_message or reason.value.message
            self._handler_result.errback(Failure(RuntimeError(message)))
        else:
            self._item['whois'] = self._out
            self._handler_result.callback(None)


class WhoisCaller(AsyncLimitedProcessor):

    def _handle_item(self, item):
        handler_result = Deferred()
        command = ['whois', item['name']]
        processProtocol = WhoisProcessProtocol(item, handler_result)
        reactor.spawnProcess(
            processProtocol,
            command[0],
            args=command,
        )
        return handler_result


# ------------------------------------------------------------------------------

class ResolveHistory(object):

    def __init__(self):
        self._history = []
        self._resolver = ReverseResolver(3)
        self._whois_caller = WhoisCaller(1)

    @inlineCallbacks
    def _process_item(self, item):
        try:
            yield self._resolver.enqueue(item)
            yield self._whois_caller.enqueue(item)
            item['status'] = 'success'
        except Exception as e:
            item['status'] = 'error'
            # TODO: use logger
            print('IP: {}. Got exception {}'.format(item['ip_addr'], e))

    def add(self, ip_addr):
        item = {
            'datetime': datetime.now(),
            'ip_addr': ip_addr,
            'name': None,
            'whois': None,
            'status': 'pending'
        }
        self._history.append(item)
        self._process_item(item)

    def get_items(self):
        return deepcopy(self._history)

    def clear(self):
        self._history = []


# ------------------------------------------------------------------------------

PAGE_TEMPLATE = """
<html>
    <head><title>%(title)s</title></head>
    <body>
        <nav>
            <a href="/">Main Page</a>
            <a href="/history">History Page</a>
        </nav>
        %(content)s
    </body>
</html>
"""


CHECK_IP_FORM = """
<form method="post" action="/new">
    <label for="ip_addr">IP Address to check:</label>
    <input type="text" name="ip_addr" size="15"/>
    <br/>
    <input type="submit" value="Check">
</form>
"""


CLEAR_HISTORY_FORM = """
<form method="post" action="/clear">
    <input type="submit" value="Clear History"/>
</form>
"""


HISTORY_TABLE_TEMPLATE = """
<table>
    <thead>
        <tr>
            <th>DateTime</th>
            <th>IP Address</th>
            <th>Status</th>
            <th>Domain Name</th>
            <th>WHOIS Domain</th>
        </tr>
    </thead>
    <tbody>
        %(rows)s
    </tbody>
</table>
"""


HISTORY_ROW_TEMPLATE = """
<tr>
    <td>%(datetime)s</td>
    <td>%(ip_addr)s</td>
    <td>%(status)s</td>
    <td>%(name)s</td>
    <td><pre>%(whois)s</pre></td>
</tr>
"""


# ------------------------------------------------------------------------------

class Root(Resource):

    def getChild(self, path, request):
        if not path:
            return self
        return Resource.getChild(self, path, request)

    def render_GET(self, request):
        context = {
            'content': CHECK_IP_FORM,
            'title': 'Check IP'
        }
        return PAGE_TEMPLATE % context


class New(Resource):

    isLeaf = True

    def render_POST(self, request):
        request.site.history.add(request.args['ip_addr'][0])
        return redirectTo('/', request)


class History(Resource):

    isLeaf = True

    def render_GET(self, request):
        header = "<h1>History Page</hq>"
        rows = []
        for item in request.site.history.get_items():
            rows.append(HISTORY_ROW_TEMPLATE % item)
        table = HISTORY_TABLE_TEMPLATE % {'rows': '\n'.join(rows)}
        content = '\n'.join([
            header,
            table,
            CLEAR_HISTORY_FORM
        ])
        context = {
            'content': content,
            'title': 'History Page'
        }
        return PAGE_TEMPLATE % context


class Clear(Resource):

    isLeaf = True

    def render_POST(self, request):
        request.site.history.clear()
        return redirectTo('/history', request)


# ------------------------------------------------------------------------------

class MySite(Site):

    def __init__(self, resource, history, requestFactory=None, *args, **kwargs):
        Site.__init__(self, resource, requestFactory=requestFactory,
                             *args, **kwargs)
        self._history = history

    @property
    def history(self):
        return self._history


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    root = Root()
    root.putChild('new', New())
    root.putChild('history', History())
    root.putChild('clear', Clear())
    site = MySite(root, ResolveHistory())
    endpoint = TCP4ServerEndpoint(reactor, 8080)
    endpoint.listen(site)
    reactor.run()
