import copy


def endponint(topic, message, *args, **kwargs):
    print(f"inside endpoint: topic:{topic} message:{message}")


def middleware1(topic, message, cb):
    print("middleware1 before")
    cb(topic, message, cb)
    print("middleware1 after")


def middleware2(topic, message, cb):
    print("middleware2 before")
    cb(topic, message, cb)
    print("middleware2 after")


def middleware3(topic, message, cb):
    print("middleware3 before")
    cb(topic, message, cb)
    print("middleware3 after")


def middleware4(topic, message, cb):
    print("middleware4 before")
    cb(topic, message, cb)
    print("middleware4 after")


def get_mdlwr(middleware, callback, next_func, is_endpoint=False):
    def next_wrap(topic, message, cb=None):
        print(f"next: {middleware.__name__}")
        return middleware(topic, message, callback)

    print(f"registered {middleware.__name__}")
    return next_wrap


def main(ms, c):
    func_with_mdlwr = c
    for i, m in enumerate(ms):
        try:
            next_m = ms[i + 1]
            is_endpoint = False
        except:
            next_m = c
            is_endpoint = True
        func_with_mdlwr = get_mdlwr(m, func_with_mdlwr, next_m, is_endpoint)
    count = 0
    for _ in range(100):
        count += 1
        func_with_mdlwr("main", str(count))


if __name__ == "__main__":
    main(reversed([middleware1, middleware2, middleware3, middleware4]), endponint)
