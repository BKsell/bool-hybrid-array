# -*- coding: utf-8 -*-
from .__init__ import *

# 创建实例

arr = BoolHybridArr([True, False, True, False, True])

arr2 = TruesArray(3)#7.9.0新增

arr3 = FalsesArray(3)#7.9.0新增

# 访问元素
print(arr[0])  # 输出: True；

print(arr[1:4])  # 输出:  BoolHybridArr([False, True, False])；

print(arr2)# 输出:  BoolHybridArr([True, True, True])；

print(arr3)  # 输出:  BoolHybridArr([False, False, False])；

arr[2] = False

print(arr)  # 输出: BoolHybridArr([True, False, False, False, True])

# 创建包含大量布尔值的数组（大部分为False）

big_arr = BoolHybridArr([i % 100 == 0 for i in range(10000)])

# 查看存储模式（此时应为稀疏模式）

print(repr(big_arr))  # 输出: BoolHybridArray(split_index=100,size=10000,is_sparse=True,small_len=100,large_len=)不好意思large_len我不知道

# 自动优化存储

big_arr.optimize()

# 统计True的数量

print(arr.count(True))  # 输出: 2

# 检查是否至少有一个True

print(any(arr))  # 输出: True

# 检查是否全为True

print(all(arr))  # 输出: False

# 复制数组（7.9.1新增）

arr_copy = arr.copy()

arr_copy[0] = False

print(arr[0])      # 输出: True（原数组不变）

print(arr_copy[0]) # 输出: False（拷贝数组已修改）

#寻找一个元素出现的索引(7.9.2新增)

arr_find = BoolHybridArr([i % 2 for i in range(10)])

print(arr_find.find(True))#输出：[1,3,5,7,9]

print(arr_find.find(False))#输出：[2,4,6,8,10]

# 查找第一个/最后一个出现的位置（7.10.3新增）

print(arr_find.index(True))   # 输出：1（第一个True的位置）

print(arr_find.rindex(True))  # 输出：9（最后一个True的位置）

#index/rindex的空数组处理（7.10.4新增）

none_arr =  BoolHybridArr([])
try:print(none_arr.index(True))#ValueError：无法在空的 BoolHybridArray 中查找元素
except ValueError as e:print(e)

#查看是否需要优化（7.10.7新增，7.10.20+能用）

print(big_arr.memory_usage(detail=True))
'''样例输出（瞎编，但格式是这样）
{
    "总占用(字节)": 210,
    "密集区占用": 180,
    "稀疏区占用": 30,
    "对比原生list节省": "99.5%",
    "对比numpy节省": "79.0%",
    "是否需要优化": "是",
    "优化理由/说明": "稀疏区索引密度过高，优化后可转为密集存储提升速度"
}
'''
big_arr.optimize()  # 调用优化方法

print(big_arr.memory_usage(detail=True)["是否需要优化"])#"否"

'''当处理动态变化的布尔数组（如频繁增删元素）时，建议在关键操作后调用memory_usage(detail=True)检查状态，通过optimize()保持最优性能。'''

#将数组转为int类型（7.11.0新增）：

print(int(arr))#输出：17（0b10001）

#位运算（7.13.0新增）

arr1 = BoolHybridArr([True, False, True, False])  # 0b1010

arr2 = BoolHybridArr([True, True, False, False])   # 0b1100

print(arr1 & arr2)  # 输出：BoolHybridArr([True,False,False,False])  # 0b1000

print(arr1 | arr2)  # 输出：BoolHybridArr([True,True,True,False])  # 0b1110

print([True, False] | arr1[:2])  # 反向运算：[True,False] | [True,False] → [True,False]

print(arr1 ^ arr2)  # 输出：BoolHybridArr([False,True,True,False])  # 0b0110

print(~arr1)  # 输出：BoolHybridArr([False,True,False,True])  # 0b0101（对应整数 ~10 = -11 的二进制布尔逻辑）

arr = BoolHybridArr([True, False, True])  # 0b101

arr <<= 2  # 左移2位：尾部补2个False → [True,False,True,False,False]（0b10100）

print(arr)

arr >>= 3  # 右移3位：尾部删3个元素 → [True,False]（0b10）

print(arr)

print(arr << -1)  # 负数左移：等价于右移1位 → [True]

#兼容numpy数组（8.0.0版本新增）

arr_BoolHybridArray = BoolHybridArr([])
arr_BoolHybridArray <<= 10
arr_BoolHybridArray <<= 10000
array_numpy = np.array([arr_BoolHybridArray,arr_BoolHybridArray],dtype = object)

#支持哈希（8.2.0版本新增）

set_ = {arr_BoolHybridArray}#不会报错呦

_2darr = BHA_List([BoolHybridArr([1,0,0,0,1],Type = BHA_Bool),TruesArray(5,Type = bool),FalsesArray(5,Type = np.bool_)])

print(_2darr)

'''输出：

BHA_List([
BoolHybridArr([True,False,False,False,True]),
BoolHybridArr([True,True,True,True,True]),
BoolHybridArr([False,False,False,False,False]),
])
'''

#BoolHybridArray是布尔数组，那是什么布尔数组呢？numpy.bool_？原生bool？其他库的布尔类型？还是本库的BHA_Bool？Type参数，支持指定！

#还更新了用BHA_List的排版模拟二维布尔数组！

#二维数组的optimize与memory_usage（9.1.0新增）：

_2darr.optimize()

_2darr.memory_usage(detail=T)

'''
输出格式：
 {
"占用(字节)": 【占用内存（字节）】,
"对比原生list节省": 【6位百分比】,
"对比numpy节省": 【6位百分比】}
'''

#注：BoolHybridArray的memory_usage的百分比也变成了六位小数

#关闭哈希复用（9.4.0新增）

_2darr2 = BHA_List(BoolHybridArr((i%100 for i in range(1000)),hash_ = F) for i in range(1000))

#关闭哈希复用可以增快创建速度

#ResurrectMeta元类（9.5.0新增）

class MyClass(metaclass=ResurrectMeta):
	pass

#用装饰器给实例添加动态方法（9.6.0新增）：

arr = BoolHybridArr([T,F,T])

@arr
def toggle_range(self, start: int, end: int):
    """翻转从 start 到 end（含）的布尔值"""
    for i in range(start, end + 1):
        self[i] = not self[i]  # 通过 self 操作实例的元素
    print(f"翻转 {start}-{end} 后：", self)

arr.toggle_range(0,1)

print(arr) #输出：翻转 {0}-{1} 后：BoolHybridArr(False,True,True)

toggle_range(arr,0,1) #输出：翻转 {0}-{1} 后：BoolHybridArr(True,False,True)

#view方法（9.7.0新增）：

arr2 = arr.view()

arr2.extend([F,T])

arr2[2] = F

print(arr) #输出：BoolHybridArr([True,False,False,False,True])

#python 3.9以下的版本泛型、联合类型支持（9.8.0新增）

print(BHA_List[BoolHybridArray])#输出：bool_hybrid_array.BHA_List[bool_hybrid_array.BoolHybridArray]

print(BHA_List|BoolHybridArray)#输出：typing.Union[bool_hybrid_array.BHA_List, bool_hybrid_array.BoolHybridArray] （python 3.9以下）或 bool_hybrid_array.BHA_List|bool_hybrid_array.BoolHybridArray（python 3.10以上）

#BHA_Function动态创建函数（9.9.0新增）：

toggle_range = BHA_Function.string_define(
name = 'toggle_range',
text = 
'''
    for i in range(start, end + 1):
        self[i] = not self[i]  # 通过 self 操作实例的元素
    print(f"翻转 {start}-{end} 后：", self)''',
positional = ('self','start', 'end'),
default = {})
toggle_range([0,0,1],0,1)#输出：翻转 0-1 后： [True, True, 1]


#开放ProtectedBuiltinsDict类型（9.9.3+）

Dict = ProtectedBuiltinsDict({'1':1,'2':2},protected_names = ['1','3'],name = 'Dict')

Dict['2'] = 1

print(Dict) #输出：{'1':1,'2':1}

try:Dict['1'] = 2
except Exception as e:print(e) #输出：禁止修改内置常量：__Dict__['1']

#Ask_BHA和Create_BHA（9.10.0新增）：

arr = BoolHybridArr([T,F,F,F,T,T,F,F,F,T])
arr2 = BoolHybridArr([F,F,F,F,T,T,F,T,T,F])

arr3 = BHA_List([arr,arr2])

Create_BHA("single_bool_array",arr3)#自动生成single_bool_array.bha文件

print(Ask_BHA("single_bool_array"))

'''
输出：
BHA_List([
BoolHybridArr([True,False,False,False,True,True,False,False,False,True]),
BoolHybridArr([False,False,False,False,True,True,False,True,True,False]),
])
'''

#numba_opt函数优化（9.10.4版本新增）
try:numba_opt()
except:print("请先安装numba库！！！")


#int_array模块（9.10.10新增）：

max_num = (1 << 256) - 1
min_num = -max_num

# 1. IntHybridArray：257位完美存储
arr_hybrid = int_array.IntHybridArray([max_num, min_num, 123456, 1], bit_length=257)
print("✅ IntHybridArray存储结果：")
print(f"最大值：{arr_hybrid[0]}")
print(f"最小值：{arr_hybrid[1]}")
print(f"整个数组：{arr_hybrid}")


# 2. NumPy：用最大的int64尝试存储（必然失败）
try:
    arr_np = np.array([max_num, min_num, 123456], dtype=np.int64)
    print("\n❌ NumPy存储结果：", arr_np)
except OverflowError as e:
    print(f"\n❌ NumPy存储失败：{e}")


#BHA_Queue（9.11.5版本新增）

q = BHA_Queue([T, F, T, T, F])

print(f"初始化队列: {q}")  # 输出：BHA_Queue([T,F,T,T,F])

q.enqueue(T)

q.enqueue(F)

print(f"入队2个元素后: {q}")  # 输出：BHA_Queue([T,F,T,T,F,T,F])

# 3. 出队（dequeue，均摊O(1)，仅首次触发转移）

print(f"第一次出队: {q.dequeue()}")  # 输出：T（触发 self.a → self.b 转移，仅1次）

print(f"第二次出队: {q.dequeue()}")  # 输出：F（直接从 self.b 弹出，纯O(1)）

print(f"出队2个元素后: {q}")  # 输出：BHA_Queue([T,T,F,T,F])


