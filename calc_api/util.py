import hashlib
import json
import dataclasses
import datetime
from functools import partial
from uuid import UUID

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
def json_default(thing, include_class=True):
    # try:
    #     return dataclasses.asdict(thing)
    # except TypeError:
    #     pass
    try:
        # Add the class to the dictionary to avoid namespace clashes
        # Maybe it would be better to keep jobs in tables names after the jobs but we're in neck deep now.
        thing_dict = thing.__dict__
        if include_class:
            thing_dict['__class__'] = type(thing).__name__
        return thing_dict
    except TypeError:
        pass
    if isinstance(thing, datetime.datetime):
        return thing.isoformat(timespec='microseconds')
    raise TypeError(f"object of type {type(thing).__name__} not serializable with the calc_api utils")


def encode(thing, include_class=True):
    return json.dumps(
        thing,
        default=partial(json_default, include_class=include_class),
        ensure_ascii=False,
        sort_keys=True,
        indent=None,
        separators=(',', ':'),
    )


def get_hash(thing):
    dump = encode(thing)
    hexcode = hashlib.md5(dump.encode('utf-8')).hexdigest()
    return UUID(hex=hexcode)


def get_args_dict(name, *args, **kwargs):
    args_dict = {str(i): a for i, a in enumerate(args)}
    args_dict.update({'name': name})
    args_dict.update(kwargs)
    return args_dict
