import hashlib
import json
import dataclasses
import datetime


HASH_FUNCS = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1
}


def file_checksum(filename, hash_func):
    if hash_func is None:
        return None

    hf = HASH_FUNCS[hash_func]()
    ba = bytearray(128 * 1024)
    mv = memoryview(ba)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            hf.update(mv[:n])
    hashsum = hf.hexdigest()
    return f'{hash_func}:{hashsum}'


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Adapted from https://death.andgravity.com/stable-hashing
def json_default(thing):
    try:
        return dataclasses.asdict(thing)
    except TypeError:
        pass
    try:
        return thing.__dict__
    except TypeError:
        pass
    if isinstance(thing, datetime.datetime):
        return thing.isoformat(timespec='microseconds')
    raise TypeError(f"object of type {type(thing).__name__} not serializable")


def get_hash(thing):
    dump = json.dumps(
        thing,
        default=json_default,
        ensure_ascii=False,
        sort_keys=True,
        indent=None,
        separators=(',', ':'),
    )
    return hashlib.md5(dump.encode('utf-8')).digest().hex()
