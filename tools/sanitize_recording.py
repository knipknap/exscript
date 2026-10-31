#!/usr/bin/env python3
"""
Sanitizes a recording from tools/record_session.py before it is committed.

The sanitizer replaces, consistently within a recording:

- IPv4 and IPv6 addresses with documentation addresses (it keeps loopback,
  unspecified, link-local, multicast, netmask and documentation addresses);
- MAC addresses with locally administered ones (it keeps multicast MACs);
- values after password, secret, key and community keywords, crypt hashes,
  and the content of XML elements with such names;
- serial numbers after common labels;
- the literal strings given with ``--replace OLD=NEW`` (host names, user names,
  site names, and anything else the patterns miss).

Consecutive output events are merged first, so a value split between two reads
is still found. NETCONF 1.1 chunks are re-framed with their original sizes.

The sanitizer prints every replacement and the prompts it saw, but it cannot
know every identifier: read the result before committing it. Example::

    uv run tools/sanitize_recording.py raw.jsonl tests/recordings/ios/ios-15.9-ssh.jsonl \\
        --replace core-rtr-01=router1 --replace jdoe=admin
"""

import argparse
import collections
import ipaddress
import itertools
import json
import re
import sys

EOM = b']]>]]>'
NETCONF_BASE_11 = b'urn:ietf:params:netconf:base:1.1'
REMOVED = 'REMOVED'
FRAME_HEADER = re.compile(rb'\n#(#|\d+)\n')
IPV4 = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\w|\.\d|-[A-Za-z])')  # not 6.1.2.3-generic
IPV6 = re.compile(
    r'(?<![\w:.])[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?:\.\d{1,3}){0,3}(?![\w:])'
)
MAC = re.compile(
    r'(?<![\w:.-])(?:[0-9A-Fa-f]{2}([:-])(?:[0-9A-Fa-f]{2}\1){4}[0-9A-Fa-f]{2}'
    r'|[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4})(?![\w:-]|\.\w)'
)
CRYPT = re.compile(r'(?<![\w$])\$(?:1|2[aby]?|5|6|8|9|y|sha1)\$[^\s"\';<]+')
SECRET = re.compile(
    r'(?i)\b(password|passwd|secret|community|key-string|pre-shared-key|authentication-key'
    r'|encrypted-password|md5|key)([ \t]+(?:[0-9][ \t]+)?)("[^"\r\n]*"|[^\s"]+)'
)
XML_SECRET = re.compile(
    r'(?i)(<(?:[\w.-]+:)?[\w-]*(?:password|secret|key|community)[\w-]*\b[^>]*(?<!/)>)([^<]+)(?=</)'
)
SERIAL = re.compile(
    r'(?i)\b(serial(?:[ -]?(?:number|num|no\.?))?|board id|S/N|SN)([ \t]*[:#=][ \t]*|[ \t]+)'
    r'((?=[\w/-]*\d)[A-Z0-9][\w/-]{3,})'
)
DOCUMENTATION_V4 = [
    ipaddress.ip_network(n) for n in ('192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24')
]
BENCHMARK_V4 = ipaddress.ip_network('198.18.0.0/15')
DOCUMENTATION_V6 = ipaddress.ip_network('2001:db8::/32')


def is_mask(address):
    value = int(address)
    inverse = value ^ 0xFFFFFFFF
    return value & (value + 1) == 0 or inverse & (inverse + 1) == 0


class Sanitizer:
    def __init__(self, replacements, keep):
        self.replacements = sorted(replacements, key=lambda item: -len(item[0]))
        self.keep = set(keep)
        self.report = collections.Counter()
        self._mapping = {}
        networks = [*DOCUMENTATION_V4, BENCHMARK_V4]
        self._ipv4 = itertools.chain.from_iterable(network.hosts() for network in networks)
        self._counter = itertools.count(1)

    def text(self, text):
        for old, new in self.replacements:
            if old in text:
                self.report['literal', old, new] += text.count(old)
                text = text.replace(old, new)
        text = IPV6.sub(self._ipv6, text)
        text = IPV4.sub(self._ipv4_address, text)
        text = MAC.sub(self._mac, text)
        text = CRYPT.sub(lambda m: self._remove('hash', m.group()), text)
        text = SECRET.sub(
            lambda m: m.group(1) + m.group(2) + self._remove('secret', m.group(3)), text
        )
        text = XML_SECRET.sub(lambda m: m.group(1) + self._remove('xml secret', m.group(2)), text)
        return SERIAL.sub(
            lambda m: m.group(1) + m.group(2) + self._remove('serial', m.group(3)), text
        )

    def _map(self, kind, key, original, new):
        if key not in self._mapping:
            self._mapping[key] = new()
        self.report[kind, original, self._mapping[key]] += 1
        return self._mapping[key]

    def _ipv4_address(self, match):
        value = match.group()
        try:
            address = ipaddress.IPv4Address(value)
        except ValueError:
            return value
        keep = (
            address.is_loopback
            or address.is_unspecified
            or address.is_link_local
            or address.is_multicast
            or is_mask(address)
            or any(address in network for network in [*DOCUMENTATION_V4, BENCHMARK_V4])
        )
        if keep or value in self.keep:
            return value
        return self._map('ipv4', address, value, lambda: str(next(self._ipv4)))

    def _ipv6(self, match):
        value = match.group()
        try:
            address = ipaddress.IPv6Address(value)
        except ValueError:
            return value
        keep = address.is_loopback or address.is_unspecified or address.is_multicast
        if keep or address in DOCUMENTATION_V6 or value in self.keep:
            return value
        return self._map('ipv6', address, value, lambda: f'2001:db8::{next(self._counter):x}')

    def _mac(self, match):
        value = match.group()
        digits = re.sub(r'[^0-9A-Fa-f]', '', value).lower()
        if int(digits[:2], 16) & 1 or digits == '0' * 12 or value in self.keep:
            return value
        if digits not in self._mapping:
            self._mapping[digits] = f'020000{next(self._counter):06x}'
        new = self._mapping[digits]
        if '.' in value:
            formatted = '.'.join((new[0:4], new[4:8], new[8:12]))
        else:
            formatted = value[2].join(new[i : i + 2] for i in range(0, 12, 2))
        if value.upper() == value:
            formatted = formatted.upper()
        self.report['mac', value, formatted] += 1
        return formatted

    def _remove(self, kind, value):
        quoted = len(value) > 1 and value[0] == value[-1] == '"'
        if value.strip('"') == REMOVED or value in self.keep:
            return value
        self.report[kind, value[:2] + '...', REMOVED] += 1
        return f'"{REMOVED}"' if quoted else REMOVED


def merge_output(events):
    merged = []
    for event in events:
        if merged and event['dir'] == 'recv' and merged[-1]['dir'] == 'recv':
            merged[-1]['data'] += event['data']
        else:
            merged.append(dict(event))
    return merged


def decode_messages(stream, chunked):
    """Splits NETCONF data into complete (message, chunk sizes) tuples and the rest."""
    if not chunked:
        *complete, rest = stream.split(EOM)
        return [(message, []) for message in complete], rest
    messages, message, sizes = [], b'', []
    start = pos = 0
    while match := FRAME_HEADER.match(stream, pos):
        if match.group(1) == b'#':
            messages.append((message, sizes))
            message, sizes = b'', []
            start = pos = match.end()
            continue
        end = match.end() + int(match.group(1))
        if end > len(stream):
            break
        message += stream[match.end() : end]
        sizes.append(end - match.end())
        pos = end
    return messages, stream[start:]


def encode_message(message, chunked, sizes=()):
    """Frames a NETCONF message, with the given chunk sizes if chunked (last chunk takes the rest)."""
    if not chunked:
        return message + EOM
    chunks, pos = [], 0
    for size in sizes[:-1]:
        if pos + size >= len(message):
            break
        chunks.append(message[pos : pos + size])
        pos += size
    chunks.append(message[pos:])
    return b''.join(b'\n#%d\n%s' % (len(chunk), chunk) for chunk in chunks) + b'\n##\n'


def sanitize_netconf(events, clean):
    hellos = {}
    for event in events:
        if event['dir'] not in ('recv', 'send') or event.get('secret'):
            continue
        data = event['data'].encode('latin-1')
        if event['dir'] not in hellos:
            hello, rest = data.split(EOM, 1)
            hellos[event['dir']] = hello
            messages, chunked = [(hello, [])], False
        else:
            chunked = all(NETCONF_BASE_11 in hello for hello in hellos.values())
            messages, rest = decode_messages(data, chunked)
        if rest.strip():
            sys.exit(f'Incomplete NETCONF message at t={event["t"]}; record the session again.')
        encoded = b''.join(
            encode_message(clean(message), chunked, sizes) for message, sizes in messages
        )
        event['data'] = (encoded + rest).decode('latin-1')


def prompts(events):
    """Returns the last output lines before each input, which usually contain the host name."""
    seen = []
    for previous, event in itertools.pairwise(events):
        if previous['dir'] == 'recv' and event['dir'] == 'send':
            line = previous['data'].rsplit('\n', 1)[-1].strip()
            if line and line not in seen:
                seen.append(line)
    return seen


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().split('\n\n')[0])
    parser.add_argument('input', help='raw recording')
    parser.add_argument('output', help='sanitized recording')
    parser.add_argument(
        '--replace', action='append', default=[], metavar='OLD=NEW', help='literal replacement'
    )
    parser.add_argument(
        '--keep', action='append', default=[], metavar='VALUE', help='value to keep as is'
    )
    args = parser.parse_args()
    replacements = [tuple(item.split('=', 1)) for item in args.replace]
    if any(len(item) != 2 or not item[0] for item in replacements):
        parser.error('--replace needs OLD=NEW')

    with open(args.input, encoding='utf-8') as fp:
        header, *events = [json.loads(line) for line in fp if line.strip()]
    sanitizer = Sanitizer(replacements, args.keep)
    events = merge_output(events)
    if header['protocol'] == 'netconf':
        sanitize_netconf(
            events, lambda message: sanitizer.text(message.decode('latin-1')).encode('latin-1')
        )
    else:
        for event in events:
            if event['data']:
                event['data'] = sanitizer.text(event['data'])
    ssh = header.get('ssh') or {}
    if ssh.get('banner'):
        ssh['banner'] = sanitizer.text(ssh['banner'])
    if ssh.get('interactive'):
        query = ssh['interactive']
        query['instructions'] = sanitizer.text(query['instructions'])
        query['prompts'] = [[sanitizer.text(prompt), echo] for prompt, echo in query['prompts']]
    header['sanitized'] = True

    with open(args.output, 'w', encoding='ascii', newline='\n') as fp:
        for item in [header, *events]:
            fp.write(json.dumps(item) + '\n')

    for (kind, old, new), count in sorted(sanitizer.report.items()):
        print(f'{kind:10} {old!r} -> {new!r} ({count}x)')
    if header['protocol'] != 'netconf':
        print('Prompts (check for host names):', ', '.join(map(repr, prompts(events))) or 'none')
    print(f'{len(events)} events written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
