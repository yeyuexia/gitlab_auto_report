# coding: utf8

_STORE = dict()


def simplecache(func):
    def _(self, *args, **kw):
        key = (
            func.__name__ +
            "_".join([str(x) for x in args]) + "+"
            "_".join("%s~%s" % (k, v) for k, v in sorted(kw.items()))
        )
        res = _STORE.get(key)
        if res is None:
            res = func(self, *args, **kw)
            _STORE[key] = res
        return res
    return _
