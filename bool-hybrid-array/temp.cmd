chcp 65001
python -OO temp.py
python -O temp.py
python temp.py
python -m bool_hybrid_array.__init__
python -O -m bool_hybrid_array.__init__
python -OO -m bool_hybrid_array.__init__


pypy -OO -m bool_hybrid_array.__init__

python -OO -m bool_hybrid_array
pypy -OO -m bool_hybrid_array
python -c "from bool_hybrid_array import *;(x:=int_array.IntHybridArray([1,3,2,6,5,4,7,0,9])).sort(),print(x)"
pypy test_pypy.py
pause