from lprof import profile, dump_perf_stats

class Testme():
    def __init__(self):
        pass

    @profile
    def test1(self):
        print('Hello')
        print('Hello2')

    @profile
    def test2(self):
        import time
        from threading import Thread

        for i in range(10):
            time.sleep(0.1)
            print(i)

        def runner(x):
            for i in range(x):
                time.sleep(0.2)
                print(i)

        def fac(n):
            if n == 0:
                return 1
            else:
                return n * fac(n-1)

        print(fac(5))

        t = Thread(target=runner, args=(10,))
        t2 = Thread(target=runner, args=(10, ))
        t.start()
        t2.start()
        t.join()
        t2.join()

t = Testme()
t.test1()
t.test2()

dump_perf_stats()
