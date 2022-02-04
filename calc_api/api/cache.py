import hashlib
import os
from calc_api.models import FileCache


def hash(string: str):
    h = hashlib.md5()
    h.update(string.encode())
    return h.hexdigest()


files = dict()
CACHEDIR = 'filecache'
LOCKED = 'locked'


def cached(serialize, deserialize):
    def sd_cached(func):
        def cached_func(*args, **kargs):
            key = ' '.join(
                [func.__name__]
                + [f"'{a}'" for a in args]
                + [f"'{ka}'" for ka in kargs.items()]
            )
            path = f'{CACHEDIR}/{hash(key)}'
            try:
                fc = FileCache.objects.get(key=key)
                if not os.path.isfile(fc.path):
                    fc.delete()
                    raise FileCache.DoesNotExist
            except FileCache.DoesNotExist:
                fc = FileCache(
                    key=key,
                    function=func.__name__,
                    args=','.join([f'{a}' for a in args]) if args else None,
                    kargs=','.join([f'{k}={v}' for k, v in kargs.items()]),
                    path=path,
                    locked=True)
                fc.save()

                try:
                    # here's the call to func in case the result isn't cached
                    result = func(*args, **kargs)

                    with open(path, 'w') as cached_file:
                        cached_file.write(serialize(result))

                    fc.locked = False
                    fc.save()
                except Exception:
                    fc.delete()
                    raise

            while fc.locked:
                from time import sleep
                del fc  # perhaps that's not the proper way to do it, however
                #         the idea is to avoid locking any other process down
                sleep(1)
                fc = FileCache.objects.get(key=key)

            with open(fc.path) as cached_file:
                return deserialize(cached_file)

        return cached_func
    return sd_cached
