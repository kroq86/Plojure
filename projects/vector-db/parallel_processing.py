"""
Parallel Processing Module for Hybrid Analytics Platform
Модуль параллельной обработки для ускорения векторных вычислений
"""

import multiprocessing as mp
from multiprocessing import Pool, cpu_count
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Callable
import pandas as pd
from functools import partial
import time
import psutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import math


def compute_similarities_chunk(args: Tuple) -> List[Tuple[str, float]]:
    """
    Вычисление сходства для чанка данных
    
    Args:
        args: (query_vector, chunk_data, similarity_func)
        
    Returns:
        Список (key, similarity)
    """
    query_vector, chunk_data, similarity_metric = args
    
    results = []
    for key, vector in chunk_data:
        if similarity_metric == "cosine":
            similarity = cosine_similarity_pure(query_vector, vector)
        elif similarity_metric == "euclidean":
            similarity = euclidean_distance_pure(query_vector, vector)
        else:  # dot_product
            similarity = dot_product_pure(query_vector, vector)
        
        results.append((key, similarity))
    
    return results


def cosine_similarity_pure(v1: List[float], v2: List[float]) -> float:
    """Чистая Python реализация косинусного сходства"""
    v1_np = np.array(v1)
    v2_np = np.array(v2)
    
    dot_product = np.dot(v1_np, v2_np)
    norm_v1 = np.linalg.norm(v1_np)
    norm_v2 = np.linalg.norm(v2_np)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def euclidean_distance_pure(v1: List[float], v2: List[float]) -> float:
    """Чистая Python реализация евклидова расстояния"""
    v1_np = np.array(v1)
    v2_np = np.array(v2)
    diff = v1_np - v2_np
    return -np.sqrt(np.sum(diff * diff))  # Отрицательное для сортировки


def dot_product_pure(v1: List[float], v2: List[float]) -> float:
    """Чистая Python реализация скалярного произведения"""
    return np.dot(np.array(v1), np.array(v2))


def batch_similarity_search_parallel(query_vector: List[float],
                                    vectors_data: List[Tuple[str, List[float]]],
                                    similarity_metric: str = "cosine",
                                    num_processes: Optional[int] = None,
                                    chunk_size: Optional[int] = None) -> List[Tuple[str, float]]:
    """
    Параллельный поиск по сходству для больших батчей
    
    Args:
        query_vector: Вектор запроса
        vectors_data: Список (key, vector) пар
        similarity_metric: Метрика сходства
        num_processes: Количество процессов (по умолчанию CPU count)
        chunk_size: Размер чанка (автоматически если None)
        
    Returns:
        Список (key, similarity) отсортированный по убыванию
    """
    if not vectors_data:
        return []
    
    # Определяем оптимальные параметры
    if num_processes is None:
        num_processes = min(cpu_count(), 8)  # Ограничиваем 8 процессами
    
    if chunk_size is None:
        # Автоматический расчет размера чанка
        total_vectors = len(vectors_data)
        chunk_size = max(100, total_vectors // (num_processes * 4))
    
    # Разбиваем данные на чанки
    chunks = []
    for i in range(0, len(vectors_data), chunk_size):
        chunk = vectors_data[i:i + chunk_size]
        chunks.append((query_vector, chunk, similarity_metric))
    
    # Параллельная обработка
    all_results = []
    
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        # Отправляем задачи
        future_to_chunk = {
            executor.submit(compute_similarities_chunk, chunk): chunk 
            for chunk in chunks
        }
        
        # Собираем результаты
        for future in as_completed(future_to_chunk):
            try:
                chunk_results = future.result()
                all_results.extend(chunk_results)
            except Exception as e:
                print(f"Ошибка обработки чанка: {e}")
    
    # Сортируем результаты
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results


def parallel_batch_insert(vectors_data: List[Tuple[str, List[float]]],
                         db_instances: List,
                         num_processes: Optional[int] = None) -> None:
    """
    Параллельная вставка векторов в несколько экземпляров БД
    
    Args:
        vectors_data: Данные для вставки
        db_instances: Список экземпляров базы данных
        num_processes: Количество процессов
    """
    if num_processes is None:
        num_processes = min(cpu_count(), len(db_instances))
    
    # Разбиваем данные между процессами
    chunk_size = len(vectors_data) // num_processes
    chunks = [
        vectors_data[i:i + chunk_size] 
        for i in range(0, len(vectors_data), chunk_size)
    ]
    
    def insert_chunk(args):
        chunk_data, db_instance = args
        for key, vector in chunk_data:
            db_instance.insert(key, vector)
    
    # Параллельная вставка
    with Pool(processes=num_processes) as pool:
        pool.map(insert_chunk, zip(chunks, db_instances[:num_processes]))


class ParallelVectorProcessor:
    """
    Класс для параллельной обработки векторных операций
    """
    
    def __init__(self, num_processes: Optional[int] = None):
        self.num_processes = num_processes or min(cpu_count(), 8)
        self.stats = {
            'total_processed': 0,
            'processing_time': 0.0,
            'speedup_factor': 1.0
        }
    
    def parallel_search(self, 
                       query_vector: List[float],
                       vectors_data: List[Tuple[str, List[float]]],
                       similarity_metric: str = "cosine",
                       top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Параллельный поиск с бенчмаркингом
        """
        start_time = time.time()
        
        # Параллельная обработка
        results = batch_similarity_search_parallel(
            query_vector=query_vector,
            vectors_data=vectors_data,
            similarity_metric=similarity_metric,
            num_processes=self.num_processes
        )
        
        processing_time = time.time() - start_time
        
        # Обновляем статистику
        self.stats['total_processed'] += len(vectors_data)
        self.stats['processing_time'] += processing_time
        
        return results[:top_k]
    
    def benchmark_parallel_vs_sequential(self,
                                       query_vector: List[float],
                                       vectors_data: List[Tuple[str, List[float]]],
                                       similarity_metric: str = "cosine") -> Dict[str, Any]:
        """
        Сравнение производительности параллельной и последовательной обработки
        """
        print(f"🔬 Бенчмарк: {len(vectors_data)} векторов, "
              f"{len(query_vector)} измерений")
        
        # Последовательная обработка
        start_time = time.time()
        sequential_results = []
        for key, vector in vectors_data:
            if similarity_metric == "cosine":
                similarity = cosine_similarity_pure(query_vector, vector)
            elif similarity_metric == "euclidean":
                similarity = euclidean_distance_pure(query_vector, vector)
            else:
                similarity = dot_product_pure(query_vector, vector)
            sequential_results.append((key, similarity))
        
        sequential_time = time.time() - start_time
        sequential_results.sort(key=lambda x: x[1], reverse=True)
        
        # Параллельная обработка
        start_time = time.time()
        parallel_results = batch_similarity_search_parallel(
            query_vector=query_vector,
            vectors_data=vectors_data,
            similarity_metric=similarity_metric,
            num_processes=self.num_processes
        )
        parallel_time = time.time() - start_time
        
        # Вычисляем ускорение
        speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0
        self.stats['speedup_factor'] = speedup
        
        # Проверяем корректность (первые 10 результатов должны совпадать)
        accuracy = self._check_accuracy(sequential_results[:10], 
                                      parallel_results[:10])
        
        return {
            'sequential_time': sequential_time,
            'parallel_time': parallel_time,
            'speedup': speedup,
            'accuracy': accuracy,
            'vectors_processed': len(vectors_data),
            'vectors_per_second_sequential': len(vectors_data) / sequential_time,
            'vectors_per_second_parallel': len(vectors_data) / parallel_time,
            'num_processes': self.num_processes,
            'efficiency': speedup / self.num_processes
        }
    
    def _check_accuracy(self, seq_results: List, par_results: List) -> float:
        """Проверка точности параллельных вычислений"""
        if len(seq_results) != len(par_results):
            return 0.0
        
        matches = 0
        for (key1, sim1), (key2, sim2) in zip(seq_results, par_results):
            if key1 == key2 and abs(sim1 - sim2) < 1e-10:
                matches += 1
        
        return matches / len(seq_results)
    
    def get_optimal_chunk_size(self, 
                              total_vectors: int,
                              vector_dim: int) -> int:
        """
        Вычисление оптимального размера чанка на основе характеристик системы
        """
        # Базовый размер чанка
        base_chunk_size = 1000
        
        # Корректировка на основе размерности векторов
        if vector_dim > 512:
            base_chunk_size //= 2
        elif vector_dim < 128:
            base_chunk_size *= 2
        
        # Корректировка на основе общего количества векторов
        optimal_chunks_per_process = 4
        target_chunk_size = total_vectors // (self.num_processes * optimal_chunks_per_process)
        
        # Выбираем минимум для баланса нагрузки
        return max(100, min(base_chunk_size, target_chunk_size))
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики производительности"""
        return {
            **self.stats,
            'num_processes': self.num_processes,
            'cpu_count': cpu_count(),
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024
        }


def create_test_data(num_vectors: int = 10000, 
                    vector_dim: int = 128) -> List[Tuple[str, List[float]]]:
    """
    Создание тестовых данных для бенчмарков
    """
    np.random.seed(42)
    vectors_data = []
    
    for i in range(num_vectors):
        key = f"vector_{i}"
        vector = np.random.rand(vector_dim).tolist()
        vectors_data.append((key, vector))
    
    return vectors_data


if __name__ == "__main__":
    print("🚀 Тестирование параллельной обработки векторов")
    print("=" * 50)
    
    # Создаем тестовые данные
    print("📊 Создание тестовых данных...")
    test_data = create_test_data(num_vectors=5000, vector_dim=256)
    query_vector = np.random.rand(256).tolist()
    
    # Инициализируем процессор
    processor = ParallelVectorProcessor()
    
    # Запускаем бенчмарк
    print("⚡ Запуск бенчмарка...")
    benchmark_results = processor.benchmark_parallel_vs_sequential(
        query_vector=query_vector,
        vectors_data=test_data,
        similarity_metric="cosine"
    )
    
    # Выводим результаты
    print("\n📈 Результаты бенчмарка:")
    print(f"  Последовательно: {benchmark_results['sequential_time']:.3f}s")
    print(f"  Параллельно:     {benchmark_results['parallel_time']:.3f}s")
    print(f"  Ускорение:       {benchmark_results['speedup']:.2f}x")
    print(f"  Эффективность:   {benchmark_results['efficiency']:.2f}")
    print(f"  Точность:        {benchmark_results['accuracy']:.2%}")
    print(f"  Процессов:       {benchmark_results['num_processes']}")
    print(f"  Векторов/сек:    {benchmark_results['vectors_per_second_parallel']:.0f}")
    
    print("\n✅ Тестирование завершено!") 