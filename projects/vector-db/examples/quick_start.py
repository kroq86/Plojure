#!/usr/bin/env python3
"""
Hybrid Analytics Platform - Быстрый старт
Демонстрация основных возможностей для аналитиков и Data Scientists
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from hybrid_analytics import VectorDB, create_sample_data


def demo_analyst_workflow():
    """
    Демонстрация рабочего процесса аналитика
    """
    print("📊 Демонстрация для АНАЛИТИКА")
    print("=" * 50)
    
    # 1. Создание тестовых данных (новости)
    print("\n1. Создание данных о новостях...")
    news_data = create_sample_data(
        num_documents=500,
        embedding_dim=128,
        categories=['technology', 'science', 'sports', 'politics', 'economics']
    )
    
    # Добавим реалистичные заголовки
    tech_titles = [
        "New breakthrough in AI field",
        "Quantum computers become reality", 
        "Blockchain revolutionizes finance",
        "5G networks change communication world",
        "Robots in medicine"
    ]
    
    for i, row in news_data.iterrows():
        if row['category'] == 'technology':
            news_data.at[i, 'title'] = np.random.choice(tech_titles)
    
    print(f"✅ Создано {len(news_data)} новостных статей")
    print(f"Категории: {news_data['category'].value_counts().to_dict()}")
    
    # 2. Инициализация базы данных
    print("\n2. Инициализация аналитической базы...")
    db = VectorDB(db_path="analytics_news.duckdb")
    db.load_embeddings(news_data, table_name="news")
    
    # 3. Поиск похожих статей о технологиях
    print("\n3. Поиск статей о технологиях за последние 6 месяцев...")
    query_vector = np.random.rand(128).tolist()  # Эмбеддинг запроса
    
    results = db.hybrid_search(
        query_vector=query_vector,
        table_name="news",
        filters={
            'category': 'technology',
            'date': '>2023-06-01'
        },
        limit=10
    )
    
    print(f"✅ Найдено {len(results)} релевантных статей")
    print("\nТоп-5 самых похожих статей:")
    for _, row in results.head().iterrows():
        print(f"  • {row['title']} (сходство: {row['similarity']:.3f})")
    
    # 4. Аналитика по категориям
    print("\n4. Анализ распределения по категориям...")
    
    # Получаем данные по категориям через Python вместо SQL
    category_stats = []
    for category in news_data['category'].unique():
        category_data = news_data[news_data['category'] == category]
        articles_count = len(category_data)
        
        # Вычисляем среднее сходство для категории
        similarities = []
        for _, row in category_data.iterrows():
            similarity = db.db.cosine_similarity(query_vector, row['embedding'])
            similarities.append(similarity)
        
        avg_similarity = np.mean(similarities) if similarities else 0.0
        category_stats.append({
            'category': category,
            'articles_count': articles_count,
            'avg_similarity': avg_similarity
        })
    
    # Сортируем по среднему сходству
    category_stats = sorted(category_stats, key=lambda x: x['avg_similarity'], reverse=True)
    category_stats_df = pd.DataFrame(category_stats)
    
    print("📈 Статистика по категориям:")
    print(category_stats_df)
    
    # Закрываем базу данных для сохранения
    db.close()
    print("💾 База данных новостей сохранена в analytics_news.duckdb")
    
    return db, news_data


def demo_data_scientist_workflow():
    """
    Демонстрация рабочего процесса Data Scientist
    """
    print("\n\n🔬 Демонстрация для DATA SCIENTIST")
    print("=" * 50)
    
    # 1. Создание данных о товарах
    print("\n1. Создание данных о товарах...")
    products_data = create_sample_data(
        num_documents=1000,
        embedding_dim=256,  # Больше размерность для товаров
        categories=['electronics', 'clothing', 'books', 'sports', 'home']
    )
    
    # Переименуем колонки для товаров
    products_data = products_data.rename(columns={
        'title': 'product_name',
        'text': 'description'
    })
    
    # Добавим цены
    products_data['price'] = np.random.uniform(10, 1000, len(products_data))
    products_data['rating'] = np.random.uniform(1, 5, len(products_data))
    
    print(f"✅ Создано {len(products_data)} товаров")
    
    # 2. Инициализация базы данных
    print("\n2. Инициализация ML-базы...")
    db = VectorDB(db_path="ml_products.duckdb")
    db.load_embeddings(products_data, table_name="products")
    
    # 3. Построение рекомендательной системы
    print("\n3. Построение рекомендаций...")
    user_preference_vector = np.random.rand(256).tolist()
    
    recommendations = db.hybrid_search(
        query_vector=user_preference_vector,
        table_name="products",
        filters={
            'rating': '>4.0',
            'price': '<500'
        },
        limit=15
    )
    
    print(f"✅ Найдено {len(recommendations)} рекомендаций")
    print("\nТоп-5 рекомендованных товаров:")
    for _, row in recommendations.head().iterrows():
        print(f"  • {row['product_name']} "
              f"(${row['price']:.0f}, ⭐{row['rating']:.1f}, "
              f"сходство: {row['similarity']:.3f})")
    
    # 4. Анализ кластеров товаров
    print("\n4. Анализ кластеров похожих товаров...")
    clusters = db.analyze_clusters(
        table_name="products",
        similarity_threshold=0.7,
        group_by=['category']
    )
    
    print("🎯 Анализ кластеров по категориям:")
    print(clusters)
    
    # 5. A/B тестирование рекомендаций
    print("\n5. A/B тестирование алгоритмов...")
    
    # Алгоритм A: косинусное сходство
    recs_a = db.hybrid_search(
        query_vector=user_preference_vector,
        similarity_metric="cosine",
        table_name="products",
        limit=10
    )
    
    # Алгоритм B: евклидово расстояние
    recs_b = db.hybrid_search(
        query_vector=user_preference_vector,
        similarity_metric="euclidean", 
        table_name="products",
        limit=10
    )
    
    print(f"📊 Алгоритм A (косинус): средний рейтинг = "
          f"{recs_a['rating'].mean():.2f}")
    print(f"📊 Алгоритм B (евклид): средний рейтинг = "
          f"{recs_b['rating'].mean():.2f}")
    
    # Закрываем базу данных для сохранения
    db.close()
    print("💾 База данных товаров сохранена в ml_products.duckdb")
    
    return db, products_data


def demo_advanced_analytics():
    """
    Демонстрация продвинутой аналитики
    """
    print("\n\n🚀 ПРОДВИНУТАЯ АНАЛИТИКА")
    print("=" * 50)
    
    # Создание данных с временными рядами
    print("\n1. Анализ временных трендов...")
    db = VectorDB()
    
    # Создаем данные за год
    time_data = create_sample_data(
        num_documents=365,
        embedding_dim=128,
        categories=['AI', 'blockchain', 'IoT', 'cybersecurity']
    )
    
    db.load_embeddings(time_data, table_name="tech_trends")
    
    # Анализ трендов
    reference_vector = np.random.rand(128).tolist()
    trends = db.similarity_trends(
        reference_vector=reference_vector,
        table_name="tech_trends",
        period="month"
    )
    
    print("📈 Временные тренды похожести:")
    print(trends)
    
    # 2. Комплексный SQL-запрос
    print("\n2. Комплексный аналитический запрос...")
    
    # Упрощенный анализ без векторных вычислений в SQL
    simple_analysis = db.execute_sql("""
        SELECT 
            DATE_TRUNC('month', CAST(date AS DATE)) as month,
            category,
            COUNT(*) as docs_count
        FROM tech_trends
        GROUP BY DATE_TRUNC('month', CAST(date AS DATE)), category
        ORDER BY month, docs_count DESC
    """)
    
    print("📊 Распределение документов по месяцам и категориям:")
    print(simple_analysis.head(10))


if __name__ == "__main__":
    print("🎯 HYBRID ANALYTICS PLATFORM")
    print("Демонстрация для аналитиков и Data Scientists")
    print("=" * 60)
    
    try:
        # Демонстрация для аналитика
        analyst_db, analyst_data = demo_analyst_workflow()
        
        # Демонстрация для Data Scientist
        ds_db, ds_data = demo_data_scientist_workflow()
        
        # Продвинутая аналитика
        demo_advanced_analytics()
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ДЕМОНСТРАЦИИ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("\n💡 Основные преимущества платформы:")
        print("  • Единый SQL-интерфейс для векторов и метаданных")
        print("  • Высокая производительность благодаря ассемблерной оптимизации")
        print("  • Простая интеграция с существующими ML-пайплайнами")
        print("  • Поддержка различных метрик сходства")
        print("  • Гибкие возможности фильтрации и агрегации")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время демонстрации: {e}")
        print("Убедитесь, что все зависимости установлены:")
        print("  pip install -r requirements.txt") 