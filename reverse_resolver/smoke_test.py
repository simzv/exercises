from datetime import datetime
from pprint import pprint

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

from main import ReverseResolver
from main import WhoisCaller


@inlineCallbacks
def process_ip_addr(ip_addr):
    item = {
        'datetime': datetime.now(),
        'ip_addr': ip_addr,
        'name': None,
        'whois': None,
        'status': 'pending'
    }
    try:
        yield resolver.enqueue(item)
        yield whois_caller.enqueue(item)
        item['status'] = 'success'
    except Exception as e:
        item['status'] = 'error'
        print('IP: {}. Got exception {}'.format(ip_addr, e))
    pprint(item)


def doit():
    ip_addr_list = [
        # lenta.ru
        '81.19.72.36',
        '81.19.72.38',
        '81.19.72.37',
        '81.19.72.39',
        # mail.ru
        '94.100.180.199',
        '217.69.139.202',
        '94.100.180.202',
        '217.69.139.199',
        # errors:
        'wer',
        123,
        # yandex.ru
        '5.255.255.55',
        '77.88.55.70',
        '77.88.55.66',
        '5.255.255.70',
    ]
    map(process_ip_addr, ip_addr_list)

if __name__ == "__main__":
    command = ['whois', 'mail.ru']
    resolver = ReverseResolver(3)
    whois_caller = WhoisCaller(1)
    reactor.callLater(1, doit)
    reactor.callLater(10, reactor.stop)
    reactor.run()
