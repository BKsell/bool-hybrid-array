#include <Python.h>

PyMODINIT_FUNC
PyInit_core(void)
{
    PyObject *tmp;
    if (!(tmp = PyImport_ImportModule("bool_hybrid_array.core__mypyc"))) return NULL;
    PyObject *capsule = PyObject_GetAttrString(tmp, "init_bool_hybrid_array___core");
    Py_DECREF(tmp);
    if (capsule == NULL) return NULL;
    void *init_func = PyCapsule_GetPointer(capsule, "bool_hybrid_array.core__mypyc.init_bool_hybrid_array___core");
    Py_DECREF(capsule);
    if (!init_func) {
        return NULL;
    }
    return ((PyObject *(*)(void))init_func)();
}

// distutils sometimes spuriously tells cl to export CPyInit___init__,
// so provide that so it chills out
PyMODINIT_FUNC PyInit___init__(void) { return PyInit_core(); }
