#include "init.c"
#include "getargs.c"
#include "getargsfast.c"
#include "int_ops.c"
#include "float_ops.c"
#include "str_ops.c"
#include "bytes_ops.c"
#include "list_ops.c"
#include "dict_ops.c"
#include "set_ops.c"
#include "tuple_ops.c"
#include "exc_ops.c"
#include "misc_ops.c"
#include "generic_ops.c"
#include "pythonsupport.c"
#include "__native_core.h"
#include "__native_internal_core.h"
static PyMethodDef module_methods[] = {
    {NULL, NULL, 0, NULL}
};

int CPyExec_bool_hybrid_array___core(PyObject *module)
{
    PyObject* modname = NULL;
    modname = PyObject_GetAttrString((PyObject *)CPyModule_bool_hybrid_array___core__internal, "__name__");
    CPyStatic_globals = PyModule_GetDict(CPyModule_bool_hybrid_array___core__internal);
    if (unlikely(CPyStatic_globals == NULL))
        goto fail;
    if (CPyGlobalsInit() < 0)
        goto fail;
    char result = CPyDef___top_level__();
    if (result == 2)
        goto fail;
    Py_DECREF(modname);
    return 0;
    fail:
    Py_CLEAR(CPyModule_bool_hybrid_array___core__internal);
    Py_CLEAR(modname);
    return -1;
}
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "bool_hybrid_array.core",
    NULL, /* docstring */
    0,       /* size of per-interpreter state of the module */
    module_methods,
    NULL,
};

PyObject *CPyInit_bool_hybrid_array___core(void)
{
    if (CPyModule_bool_hybrid_array___core__internal) {
        Py_INCREF(CPyModule_bool_hybrid_array___core__internal);
        return CPyModule_bool_hybrid_array___core__internal;
    }
    CPyModule_bool_hybrid_array___core__internal = PyModule_Create(&module);
    if (unlikely(CPyModule_bool_hybrid_array___core__internal == NULL))
        goto fail;
    if (CPyExec_bool_hybrid_array___core(CPyModule_bool_hybrid_array___core__internal) != 0)
        goto fail;
    return CPyModule_bool_hybrid_array___core__internal;
    fail:
    return NULL;
}

char CPyDef___top_level__(void) {
    PyObject *cpy_r_r0;
    PyObject *cpy_r_r1;
    char cpy_r_r2;
    PyObject *cpy_r_r3;
    PyObject *cpy_r_r4;
    char cpy_r_r5;
    char cpy_r_r6;
    cpy_r_r0 = CPyModule_builtins;
    cpy_r_r1 = (PyObject *)&_Py_NoneStruct;
    cpy_r_r2 = cpy_r_r0 != cpy_r_r1;
    if (cpy_r_r2) goto CPyL3;
    cpy_r_r3 = CPyStatics[3]; /* 'builtins' */
    cpy_r_r4 = PyImport_Import(cpy_r_r3);
    if (unlikely(cpy_r_r4 == NULL)) {
        CPy_AddTraceback("bool_hybrid_array\\core.py", "<module>", -1, CPyStatic_globals);
        goto CPyL5;
    }
    CPyModule_builtins = cpy_r_r4;
    CPy_INCREF(CPyModule_builtins);
    CPy_DECREF(cpy_r_r4);
CPyL3: ;
    PyErr_SetString(PyExc_RuntimeError, "Reached allegedly unreachable code!");
    cpy_r_r5 = 0;
    if (unlikely(!cpy_r_r5)) {
        CPy_AddTraceback("bool_hybrid_array\\core.py", "<module>", 2, CPyStatic_globals);
        goto CPyL5;
    }
    CPy_Unreachable();
CPyL5: ;
    cpy_r_r6 = 2;
    return cpy_r_r6;
}

int CPyGlobalsInit(void)
{
    static int is_initialized = 0;
    if (is_initialized) return 0;
    
    CPy_Init();
    CPyModule_bool_hybrid_array___core = Py_None;
    CPyModule_builtins = Py_None;
    if (CPyStatics_Initialize(CPyStatics, CPyLit_Str, CPyLit_Bytes, CPyLit_Int, CPyLit_Float, CPyLit_Complex, CPyLit_Tuple, CPyLit_FrozenSet) < 0) {
        return -1;
    }
    is_initialized = 1;
    return 0;
}

PyObject *CPyStatics[4];
const char * const CPyLit_Str[] = {
    "\001\bbuiltins",
    "",
};
const char * const CPyLit_Bytes[] = {
    "",
};
const char * const CPyLit_Int[] = {
    "",
};
const double CPyLit_Float[] = {0};
const double CPyLit_Complex[] = {0};
const int CPyLit_Tuple[] = {0};
const int CPyLit_FrozenSet[] = {0};
CPyModule *CPyModule_bool_hybrid_array___core__internal = NULL;
CPyModule *CPyModule_bool_hybrid_array___core;
PyObject *CPyStatic_globals;
CPyModule *CPyModule_builtins;
char CPyDef___top_level__(void);

static int exec_core__mypyc(PyObject *module)
{
    int res;
    PyObject *capsule;
    PyObject *tmp;
    
    extern PyObject *CPyInit_bool_hybrid_array___core(void);
    capsule = PyCapsule_New((void *)CPyInit_bool_hybrid_array___core, "bool_hybrid_array.core__mypyc.init_bool_hybrid_array___core", NULL);
    if (!capsule) {
        goto fail;
    }
    res = PyObject_SetAttrString(module, "init_bool_hybrid_array___core", capsule);
    Py_DECREF(capsule);
    if (res < 0) {
        goto fail;
    }
    
    return 0;
    fail:
    return -1;
}
static PyModuleDef module_def_core__mypyc = {
    PyModuleDef_HEAD_INIT,
    .m_name = "bool_hybrid_array.core__mypyc",
    .m_doc = NULL,
    .m_size = -1,
    .m_methods = NULL,
};
PyMODINIT_FUNC PyInit_core__mypyc(void) {
    static PyObject *module = NULL;
    if (module) {
        Py_INCREF(module);
        return module;
    }
    module = PyModule_Create(&module_def_core__mypyc);
    if (!module) {
        return NULL;
    }
    if (exec_core__mypyc(module) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    return module;
}
