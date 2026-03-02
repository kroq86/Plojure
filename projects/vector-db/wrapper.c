#include <immintrin.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

extern double py_dot_product(double* v1, double* v2, int length);
extern double py_vector_norm(double* v, int length);
extern double py_squared_distance(double* v1, double* v2, int length);

static double dot_product_scalar(const double* v1, const double* v2, int length) {
    double sum = 0.0;
    for (int i = 0; i < length; ++i) {
        sum += v1[i] * v2[i];
    }
    return sum;
}

static double squared_distance_scalar(const double* v1, const double* v2, int length) {
    double sum = 0.0;
    for (int i = 0; i < length; ++i) {
        double diff = v1[i] - v2[i];
        sum += diff * diff;
    }
    return sum;
}

static double vector_norm_scalar(const double* v, int length) {
    return sqrt(dot_product_scalar(v, v, length));
}

static float dot_product_scalar_f32(const float* v1, const float* v2, int length) {
    float sum = 0.0f;
    for (int i = 0; i < length; ++i) {
        sum += v1[i] * v2[i];
    }
    return sum;
}

static float squared_distance_scalar_f32(const float* v1, const float* v2, int length) {
    float sum = 0.0f;
    for (int i = 0; i < length; ++i) {
        float diff = v1[i] - v2[i];
        sum += diff * diff;
    }
    return sum;
}

static float vector_norm_scalar_f32(const float* v, int length) {
    return sqrtf(dot_product_scalar_f32(v, v, length));
}

#if defined(__x86_64__) || defined(__i386__)
__attribute__((target("avx2,fma")))
static inline double hsum256_pd(__m256d value) {
    __m128d high = _mm256_extractf128_pd(value, 1);
    __m128d low = _mm256_castpd256_pd128(value);
    __m128d sum = _mm_add_pd(low, high);
    __m128d swapped = _mm_unpackhi_pd(sum, sum);
    return _mm_cvtsd_f64(_mm_add_sd(sum, swapped));
}

__attribute__((target("avx2,fma")))
static inline float hsum256_ps(__m256 value) {
    __m128 low = _mm256_castps256_ps128(value);
    __m128 high = _mm256_extractf128_ps(value, 1);
    __m128 sum = _mm_add_ps(low, high);
    __m128 shuf = _mm_movehdup_ps(sum);
    sum = _mm_add_ps(sum, shuf);
    shuf = _mm_movehl_ps(shuf, sum);
    sum = _mm_add_ss(sum, shuf);
    return _mm_cvtss_f32(sum);
}

__attribute__((target("avx2,fma")))
static double dot_product_avx2(const double* v1, const double* v2, int length) {
    int i = 0;
    __m256d acc = _mm256_setzero_pd();
    for (; i + 3 < length; i += 4) {
        __m256d lhs = _mm256_loadu_pd(v1 + i);
        __m256d rhs = _mm256_loadu_pd(v2 + i);
        acc = _mm256_fmadd_pd(lhs, rhs, acc);
    }

    double sum = hsum256_pd(acc);
    for (; i < length; ++i) {
        sum += v1[i] * v2[i];
    }
    return sum;
}

__attribute__((target("avx2,fma")))
static double squared_distance_avx2(const double* v1, const double* v2, int length) {
    int i = 0;
    __m256d acc = _mm256_setzero_pd();
    for (; i + 3 < length; i += 4) {
        __m256d lhs = _mm256_loadu_pd(v1 + i);
        __m256d rhs = _mm256_loadu_pd(v2 + i);
        __m256d diff = _mm256_sub_pd(lhs, rhs);
        acc = _mm256_fmadd_pd(diff, diff, acc);
    }

    double sum = hsum256_pd(acc);
    for (; i < length; ++i) {
        double diff = v1[i] - v2[i];
        sum += diff * diff;
    }
    return sum;
}

__attribute__((target("avx2,fma")))
static double vector_norm_avx2(const double* v, int length) {
    return sqrt(dot_product_avx2(v, v, length));
}

__attribute__((target("avx2,fma")))
static float dot_product_avx2_f32(const float* v1, const float* v2, int length) {
    int i = 0;
    __m256 acc = _mm256_setzero_ps();
    for (; i + 7 < length; i += 8) {
        __m256 lhs = _mm256_loadu_ps(v1 + i);
        __m256 rhs = _mm256_loadu_ps(v2 + i);
        acc = _mm256_fmadd_ps(lhs, rhs, acc);
    }

    float sum = hsum256_ps(acc);
    for (; i < length; ++i) {
        sum += v1[i] * v2[i];
    }
    return sum;
}

__attribute__((target("avx2,fma")))
static float squared_distance_avx2_f32(const float* v1, const float* v2, int length) {
    int i = 0;
    __m256 acc = _mm256_setzero_ps();
    for (; i + 7 < length; i += 8) {
        __m256 lhs = _mm256_loadu_ps(v1 + i);
        __m256 rhs = _mm256_loadu_ps(v2 + i);
        __m256 diff = _mm256_sub_ps(lhs, rhs);
        acc = _mm256_fmadd_ps(diff, diff, acc);
    }

    float sum = hsum256_ps(acc);
    for (; i < length; ++i) {
        float diff = v1[i] - v2[i];
        sum += diff * diff;
    }
    return sum;
}

__attribute__((target("avx2,fma")))
static float vector_norm_avx2_f32(const float* v, int length) {
    return sqrtf(dot_product_avx2_f32(v, v, length));
}

static int simd_available(void) {
    return __builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma");
}
#else
static int simd_available(void) {
    return 0;
}
#endif

static double dot_product_native(const double* v1, const double* v2, int length) {
#if defined(__x86_64__) || defined(__i386__)
    if (simd_available()) {
        return dot_product_avx2(v1, v2, length);
    }
#endif
    return dot_product_scalar(v1, v2, length);
}

static double squared_distance_native(const double* v1, const double* v2, int length) {
#if defined(__x86_64__) || defined(__i386__)
    if (simd_available()) {
        return squared_distance_avx2(v1, v2, length);
    }
#endif
    return squared_distance_scalar(v1, v2, length);
}

static double vector_norm_native(const double* v, int length) {
#if defined(__x86_64__) || defined(__i386__)
    if (simd_available()) {
        return vector_norm_avx2(v, length);
    }
#endif
    return vector_norm_scalar(v, length);
}

static float dot_product_native_f32(const float* v1, const float* v2, int length) {
#if defined(__x86_64__) || defined(__i386__)
    if (simd_available()) {
        return dot_product_avx2_f32(v1, v2, length);
    }
#endif
    return dot_product_scalar_f32(v1, v2, length);
}

static float squared_distance_native_f32(const float* v1, const float* v2, int length) {
#if defined(__x86_64__) || defined(__i386__)
    if (simd_available()) {
        return squared_distance_avx2_f32(v1, v2, length);
    }
#endif
    return squared_distance_scalar_f32(v1, v2, length);
}

static float vector_norm_native_f32(const float* v, int length) {
#if defined(__x86_64__) || defined(__i386__)
    if (simd_available()) {
        return vector_norm_avx2_f32(v, length);
    }
#endif
    return vector_norm_scalar_f32(v, length);
}

void py_batch_dot_product_scores(
    double* query,
    double* vectors,
    int num_vectors,
    int dimensions,
    double* output
) {
    for (int i = 0; i < num_vectors; ++i) {
        double* current = vectors + ((size_t)i * (size_t)dimensions);
        output[i] = dot_product_native(query, current, dimensions);
    }
}

void py_batch_cosine_scores(
    double* query,
    double* vectors,
    int num_vectors,
    int dimensions,
    double* output
) {
    double query_norm = vector_norm_native(query, dimensions);
    if (query_norm == 0.0) {
        for (int i = 0; i < num_vectors; ++i) {
            output[i] = 0.0;
        }
        return;
    }

    for (int i = 0; i < num_vectors; ++i) {
        double* current = vectors + ((size_t)i * (size_t)dimensions);
        double current_norm = vector_norm_native(current, dimensions);
        if (current_norm == 0.0) {
            output[i] = 0.0;
            continue;
        }
        double dot = dot_product_native(query, current, dimensions);
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
        double squared = squared_distance_native(query, current, dimensions);
        output[i] = -sqrt(squared);
    }
}

static void insert_topk_result(
    int* out_indices,
    double* out_scores,
    int* current_size,
    int k,
    int candidate_index,
    double candidate_score
) {
    int size = *current_size;
    if (k <= 0) {
        return;
    }

    if (size < k) {
        int insert_at = size;
        while (insert_at > 0 && candidate_score > out_scores[insert_at - 1]) {
            out_scores[insert_at] = out_scores[insert_at - 1];
            out_indices[insert_at] = out_indices[insert_at - 1];
            insert_at--;
        }
        out_scores[insert_at] = candidate_score;
        out_indices[insert_at] = candidate_index;
        *current_size = size + 1;
        return;
    }

    if (candidate_score <= out_scores[k - 1]) {
        return;
    }

    int insert_at = k - 1;
    while (insert_at > 0 && candidate_score > out_scores[insert_at - 1]) {
        out_scores[insert_at] = out_scores[insert_at - 1];
        out_indices[insert_at] = out_indices[insert_at - 1];
        insert_at--;
    }
    out_scores[insert_at] = candidate_score;
    out_indices[insert_at] = candidate_index;
}

int py_batch_topk_scores(
    double* query,
    double* vectors,
    int num_vectors,
    int dimensions,
    int metric_code,
    int k,
    int* out_indices,
    double* out_scores
) {
    if (k <= 0 || num_vectors <= 0) {
        return 0;
    }

    int limit = k < num_vectors ? k : num_vectors;
    for (int i = 0; i < limit; ++i) {
        out_indices[i] = -1;
        out_scores[i] = -INFINITY;
    }

    double query_norm = 0.0;
    if (metric_code == 0) {
        query_norm = vector_norm_native(query, dimensions);
    }

    int current_size = 0;
    for (int i = 0; i < num_vectors; ++i) {
        double* current = vectors + ((size_t)i * (size_t)dimensions);
        double score = 0.0;

        if (metric_code == 0) {
            if (query_norm == 0.0) {
                score = 0.0;
            } else {
                double current_norm = vector_norm_native(current, dimensions);
                if (current_norm == 0.0) {
                    score = 0.0;
                } else {
                    double dot = dot_product_native(query, current, dimensions);
                    score = dot / (query_norm * current_norm);
                }
            }
        } else if (metric_code == 1) {
            double squared = squared_distance_native(query, current, dimensions);
            score = -sqrt(squared);
        } else {
            score = dot_product_native(query, current, dimensions);
        }

        insert_topk_result(out_indices, out_scores, &current_size, limit, i, score);
    }

    return current_size;
}

int py_batch_topk_scores_f32(
    float* query,
    float* vectors,
    int num_vectors,
    int dimensions,
    int metric_code,
    int k,
    int* out_indices,
    double* out_scores
) {
    if (k <= 0 || num_vectors <= 0) {
        return 0;
    }

    int limit = k < num_vectors ? k : num_vectors;
    for (int i = 0; i < limit; ++i) {
        out_indices[i] = -1;
        out_scores[i] = -INFINITY;
    }

    float query_norm = 0.0f;
    if (metric_code == 0) {
        query_norm = vector_norm_native_f32(query, dimensions);
    }

    int current_size = 0;
    for (int i = 0; i < num_vectors; ++i) {
        float* current = vectors + ((size_t)i * (size_t)dimensions);
        double score = 0.0;

        if (metric_code == 0) {
            if (query_norm == 0.0f) {
                score = 0.0;
            } else {
                float current_norm = vector_norm_native_f32(current, dimensions);
                if (current_norm == 0.0f) {
                    score = 0.0;
                } else {
                    float dot = dot_product_native_f32(query, current, dimensions);
                    score = (double)(dot / (query_norm * current_norm));
                }
            }
        } else if (metric_code == 1) {
            float squared = squared_distance_native_f32(query, current, dimensions);
            score = -(double)sqrtf(squared);
        } else {
            score = (double)dot_product_native_f32(query, current, dimensions);
        }

        insert_topk_result(out_indices, out_scores, &current_size, limit, i, score);
    }

    return current_size;
}

void py_lsh_signatures_f32(
    float* vector,
    float* projections,
    int num_hash_functions,
    int dimensions,
    uint8_t* output
) {
    float norm = vector_norm_native_f32(vector, dimensions);
    if (norm == 0.0f) {
        for (int i = 0; i < num_hash_functions; ++i) {
            output[i] = 0;
        }
        return;
    }

    for (int i = 0; i < num_hash_functions; ++i) {
        float* current = projections + ((size_t)i * (size_t)dimensions);
        float dot = dot_product_native_f32(vector, current, dimensions);
        output[i] = (uint8_t)((dot / norm) > 0.0f);
    }
}
