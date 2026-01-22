#ifndef MYPYC_LIBRT_INTERNAL_bool_hybrid_array___core_H
#define MYPYC_LIBRT_INTERNAL_bool_hybrid_array___core_H
#include <Python.h>
#include <CPy.h>
#include "__native_core.h"

int CPyGlobalsInit(void);

extern PyObject *CPyStatics[4];
extern const char * const CPyLit_Str[];
extern const char * const CPyLit_Bytes[];
extern const char * const CPyLit_Int[];
extern const double CPyLit_Float[];
extern const double CPyLit_Complex[];
extern const int CPyLit_Tuple[];
extern const int CPyLit_FrozenSet[];
extern CPyModule *CPyModule_bool_hybrid_array___core__internal;
extern CPyModule *CPyModule_bool_hybrid_array___core;
extern PyObject *CPyStatic_globals;
extern CPyModule *CPyModule_builtins;
extern char CPyDef___top_level__(void);
#endif
