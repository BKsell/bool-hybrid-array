# test_pypy.py
from bool_hybrid_array import *
import time,gc,timeit,ctypes

arr = BoolHybridArr([T,F,F,F,T,T,F,F,F,T])
arr2 = BoolHybridArr([F,F,F,F,T,T,F,T,T,F])

arr3 = BHA_List([arr,arr2])

Create_BHA("single_bool_array",arr3)

gc.disable()
s = time.perf_counter()
result = Ask_BHA("single_bool_array")
e = time.perf_counter()
print(f"解析结果:\n{result}\n\n耗时:{e-s}")
x = timeit.timeit(lambda:Ask_BHA("single_bool_array"),number = 1000)
print(f'1000次耗时：{x}')
x = timeit.timeit(lambda:Ask_BHA("single_bool_array"),number = 10000)
print(f'10000次耗时：{x}')
x = timeit.timeit(lambda:Ask_BHA("single_bool_array"),number = 100000)
print(f'100000次耗时：{x}')
x = timeit.timeit(lambda:Ask_BHA("single_bool_array"))
print(f'100000次耗时：{x}')
gc.enable()
gc.collect()