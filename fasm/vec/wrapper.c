#include <stdint.h>

extern double dot_product(double* v1, double* v2, int length);

double py_dot_product(double* v1, double* v2, int length) {
    return dot_product(v1, v2, length);
}
