#include <math.h>
#include <stddef.h>

extern double py_dot_product(double* v1, double* v2, int length);
extern double py_vector_norm(double* v, int length);
extern double py_squared_distance(double* v1, double* v2, int length);

void py_batch_dot_product_scores(
    double* query,
    double* vectors,
    int num_vectors,
    int dimensions,
    double* output
) {
    for (int i = 0; i < num_vectors; ++i) {
        double* current = vectors + ((size_t)i * (size_t)dimensions);
        output[i] = py_dot_product(query, current, dimensions);
    }
}

void py_batch_cosine_scores(
    double* query,
    double* vectors,
    int num_vectors,
    int dimensions,
    double* output
) {
    double query_norm = py_vector_norm(query, dimensions);
    if (query_norm == 0.0) {
        for (int i = 0; i < num_vectors; ++i) {
            output[i] = 0.0;
        }
        return;
    }

    for (int i = 0; i < num_vectors; ++i) {
        double* current = vectors + ((size_t)i * (size_t)dimensions);
        double current_norm = py_vector_norm(current, dimensions);
        if (current_norm == 0.0) {
            output[i] = 0.0;
            continue;
        }
        double dot = py_dot_product(query, current, dimensions);
        output[i] = dot / (query_norm * current_norm);
    }
}

void py_batch_euclidean_scores(
    double* query,
    double* vectors,
    int num_vectors,
    int dimensions,
    double* output
) {
    for (int i = 0; i < num_vectors; ++i) {
        double* current = vectors + ((size_t)i * (size_t)dimensions);
        double squared = py_squared_distance(query, current, dimensions);
        output[i] = -sqrt(squared);
    }
}
