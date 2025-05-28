#!/usr/bin/env python3
"""
Parallel Processing Demo - Hybrid Analytics Platform
Демонстрация мультипроцессинга для ускорения векторных вычислений
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import time
from hybrid_analytics import VectorDB, create_sample_data


def demo_parallel_performance():
    """
    Демонстрация производительности параллельной обработки
    """
    print("🚀 ДЕМОНСТРАЦИЯ МУЛЬТИПРОЦЕССИНГА")
    print("=" * 60)
    
    # Создаем большой набор данных для тестирования
    print("\n📊 Создание большого набора данных...")
    large_data = create_sample_data(
        num_documents=10000,  # Увеличиваем количество для демонстрации
        embedding_dim=256,    # Большая размерность
        categories=['AI', 'ML', 'DL', 'NLP', 'CV', 'robotics', 'quantum']
    )
    
    print(f"✅ Создано {len(large_data)} документов с векторами размерности 256")
    
    # Инициализация с параллельной обработкой
    print("\n🔧 Инициализация базы данных...")
    db_parallel = VectorDB(enable_parallel=True)
    db_parallel.load_embeddings(large_data, table_name="large_dataset")
    
    # Инициализация без параллельной обработки для сравнения
    db_sequential = VectorDB(enable_parallel=False)
    db_sequential.load_embeddings(large_data, table_name="large_dataset")
    
    # Создаем запрос
    query_vector = np.random.rand(256).tolist()
    
    print("\n⚡ ТЕСТ 1: Сравнение производительности поиска")
    print("-" * 50)
    
    # Последовательный поиск
    print("🐌 Последовательный поиск...")
    start_time = time.time()
    sequential_results = db_sequential.hybrid_search(
        query_vector=query_vector,
        table_name="large_dataset",
        limit=20,
        use_parallel=False
    )
    sequential_time = time.time() - start_time
    
    # Параллельный поиск
    print("🚀 Параллельный поиск...")
    start_time = time.time()
    parallel_results = db_parallel.hybrid_search(
        query_vector=query_vector,
        table_name="large_dataset",
        limit=20,
        use_parallel=True
    )
    parallel_time = time.time() - start_time
    
    # Результаты
    speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0
    
    print(f"\n📈 РЕЗУЛЬТАТЫ ТЕСТА 1:")
    print(f"  Последовательно: {sequential_time:.3f}s")
    print(f"  Параллельно:     {parallel_time:.3f}s")
    print(f"  Ускорение:       {speedup:.2f}x")
    print(f"  Найдено результатов: {len(parallel_results)}")
    
    print("\n⚡ ТЕСТ 2: Детальный бенчмарк")
    print("-" * 50)
    
    # Запускаем детальный бенчмарк
    benchmark_results = db_parallel.benchmark_search_performance(
        query_vector=query_vector,
        table_name="large_dataset"
    )
    
    if "error" not in benchmark_results:
        print(f"📊 ДЕТАЛЬНЫЕ МЕТРИКИ:")
        print(f"  Векторов обработано: {benchmark_results['vectors_processed']}")
        print(f"  Последовательно:     {benchmark_results['sequential_time']:.3f}s")
        print(f"  Параллельно:         {benchmark_results['parallel_time']:.3f}s")
        print(f"  Ускорение:           {benchmark_results['speedup']:.2f}x")
        print(f"  Эффективность:       {benchmark_results['efficiency']:.2f}")
        print(f"  Точность:            {benchmark_results['accuracy']:.2%}")
        print(f"  Процессов:           {benchmark_results['num_processes']}")
        print(f"  Векторов/сек (посл): {benchmark_results['vectors_per_second_sequential']:.0f}")
        print(f"  Векторов/сек (пар):  {benchmark_results['vectors_per_second_parallel']:.0f}")
    
    print("\n⚡ ТЕСТ 3: Батчевый поиск")
    print("-" * 50)
    
    # Создаем несколько запросов
    query_vectors = [np.random.rand(256).tolist() for _ in range(5)]
    
    print("🔍 Батчевый поиск по 5 запросам...")
    start_time = time.time()
    batch_results = db_parallel.parallel_batch_search(
        query_vectors=query_vectors,
        table_name="large_dataset",
        limit=10
    )
    batch_time = time.time() - start_time
    
    print(f"📊 РЕЗУЛЬТАТЫ БАТЧЕВОГО ПОИСКА:")
    print(f"  Время обработки: {batch_time:.3f}s")
    print(f"  Запросов:        {len(query_vectors)}")
    print(f"  Время на запрос: {batch_time/len(query_vectors):.3f}s")
    print(f"  Результатов:     {sum(len(r) for r in batch_results)}")
    
    return db_parallel, large_data


def demo_real_world_scenario():
    """
    Демонстрация реального сценария использования
    """
    print("\n\n🌍 РЕАЛЬНЫЙ СЦЕНАРИЙ: Поиск в корпоративной базе знаний")
    print("=" * 60)
    
    # Создаем данные, имитирующие корпоративную базу знаний
    print("📚 Создание корпоративной базы знаний...")
    knowledge_base = create_sample_data(
        num_documents=25000,  # Большая база знаний
        embedding_dim=384,    # Размерность как у BERT
        categories=[
            'техническая_документация', 'политики_компании', 
            'FAQ', 'инструкции', 'отчеты', 'презентации',
            'код_проектов', 'архитектура', 'безопасность'
        ]
    )
    
    print(f"✅ База знаний: {len(knowledge_base)} документов")
    
    # Инициализация
    kb_db = VectorDB(enable_parallel=True)
    kb_db.load_embeddings(knowledge_base, table_name="knowledge_base")
    
    # Сценарий 1: Поиск технической документации
    print("\n🔍 СЦЕНАРИЙ 1: Поиск технической документации")
    tech_query = np.random.rand(384).tolist()
    
    start_time = time.time()
    tech_results = kb_db.hybrid_search(
        query_vector=tech_query,
        table_name="knowledge_base",
        filters={'category': 'техническая_документация'},
        limit=15,
        use_parallel=True
    )
    search_time = time.time() - start_time
    
    print(f"  Найдено документов: {len(tech_results)}")
    print(f"  Время поиска: {search_time:.3f}s")
    print(f"  Средняя релевантность: {tech_results['similarity'].mean():.3f}")
    
    # Сценарий 2: Множественные запросы от разных пользователей
    print("\n👥 СЦЕНАРИЙ 2: Множественные запросы пользователей")
    user_queries = [np.random.rand(384).tolist() for _ in range(10)]
    
    start_time = time.time()
    user_results = kb_db.parallel_batch_search(
        query_vectors=user_queries,
        table_name="knowledge_base",
        limit=5
    )
    multi_search_time = time.time() - start_time
    
    print(f"  Обработано запросов: {len(user_queries)}")
    print(f"  Общее время: {multi_search_time:.3f}s")
    print(f"  Время на запрос: {multi_search_time/len(user_queries):.3f}s")
    print(f"  Общий throughput: {len(user_queries)/multi_search_time:.1f} запросов/сек")
    
    return kb_db


def demo_scalability_analysis():
    """
    Анализ масштабируемости
    """
    print("\n\n📈 АНАЛИЗ МАСШТАБИРУЕМОСТИ")
    print("=" * 60)
    
    dataset_sizes = [1000, 5000, 10000, 20000]
    results = []
    
    for size in dataset_sizes:
        print(f"\n🔬 Тестирование с {size} документами...")
        
        # Создаем данные
        test_data = create_sample_data(
            num_documents=size,
            embedding_dim=128,
            categories=['test_category']
        )
        
        # Инициализация
        test_db = VectorDB(enable_parallel=True)
        test_db.load_embeddings(test_data, table_name="test_data")
        
        # Бенчмарк
        query = np.random.rand(128).tolist()
        benchmark = test_db.benchmark_search_performance(
            query_vector=query,
            table_name="test_data"
        )
        
        if "error" not in benchmark:
            results.append({
                'size': size,
                'sequential_time': benchmark['sequential_time'],
                'parallel_time': benchmark['parallel_time'],
                'speedup': benchmark['speedup'],
                'efficiency': benchmark['efficiency']
            })
            
            print(f"  Ускорение: {benchmark['speedup']:.2f}x")
            print(f"  Эффективность: {benchmark['efficiency']:.2f}")
    
    # Выводим сводную таблицу
    if results:
        print(f"\n📊 СВОДНАЯ ТАБЛИЦА МАСШТАБИРУЕМОСТИ:")
        print(f"{'Размер':<8} {'Посл.(с)':<10} {'Пар.(с)':<10} {'Ускорение':<10} {'Эффект.':<10}")
        print("-" * 50)
        for r in results:
            print(f"{r['size']:<8} {r['sequential_time']:<10.3f} "
                  f"{r['parallel_time']:<10.3f} {r['speedup']:<10.2f} "
                  f"{r['efficiency']:<10.2f}")


if __name__ == "__main__":
    print("🎯 HYBRID ANALYTICS PLATFORM - МУЛЬТИПРОЦЕССИНГ")
    print("Демонстрация параллельной обработки векторов")
    print("=" * 70)
    
    try:
        # Основная демонстрация производительности
        db, data = demo_parallel_performance()
        
        # Реальный сценарий
        kb_db = demo_real_world_scenario()
        
        # Анализ масштабируемости
        demo_scalability_analysis()
        
        print("\n" + "=" * 70)
        print("✅ ВСЕ ТЕСТЫ МУЛЬТИПРОЦЕССИНГА ЗАВЕРШЕНЫ!")
        print("\n💡 Ключевые преимущества:")
        print("  • Значительное ускорение для больших наборов данных")
        print("  • Автоматическое определение оптимального количества процессов")
        print("  • Fallback на последовательную обработку при необходимости")
        print("  • Сохранение точности результатов")
        print("  • Эффективное использование многоядерных процессоров")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время демонстрации: {e}")
        print("Убедитесь, что модуль parallel_processing доступен") 