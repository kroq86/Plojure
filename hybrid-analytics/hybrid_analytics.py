"""
Hybrid Analytics Platform
Гибридная аналитическая платформа для работы с векторными данными

Основной модуль для интеграции векторного поиска с классической аналитикой
"""

import numpy as np
from typing import List, Dict, Any, Optional, Union
import pandas as pd

from duckdb_vec import DuckDBVectorDB


class VectorDB:
    """
    Основной класс для работы с гибридными аналитическими запросами
    
    Позволяет совмещать векторный поиск с классической SQL-аналитикой
    в едином интерфейсе
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Инициализация базы данных
        
        Args:
            db_path: Путь к файлу базы данных 
                (если None, используется in-memory)
        """
        self.db = DuckDBVectorDB(db_path)
        self.conn = self.db.conn
        
    def load_embeddings(self,
                        data_source: Union[str, pd.DataFrame],
                        table_name: str = "documents",
                        embedding_column: str = "embedding",
                        **kwargs) -> None:
        """
        Загрузка данных с эмбеддингами
        
        Args:
            data_source: Путь к файлу или DataFrame с данными
            table_name: Имя таблицы для создания
            embedding_column: Название колонки с векторами
        """
        if isinstance(data_source, str):
            # Загрузка из файла
            if data_source.endswith('.parquet'):
                df = pd.read_parquet(data_source)
            elif data_source.endswith('.csv'):
                df = pd.read_csv(data_source)
            else:
                raise ValueError(
                    f"Неподдерживаемый формат файла: {data_source}")
        else:
            df = data_source
            
        # Создание таблицы в DuckDB
        self.conn.register(table_name, df)
        
    def hybrid_search(self,
                      query_vector: List[float],
                      table_name: str = "documents",
                      embedding_column: str = "embedding",
                      filters: Optional[Dict[str, Any]] = None,
                      similarity_metric: str = "cosine",
                      limit: int = 10) -> pd.DataFrame:
        """
        Гибридный поиск: векторное сходство + фильтрация по метаданным
        
        Args:
            query_vector: Вектор запроса
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            filters: Фильтры по метаданным 
                {'column': 'value', 'date': '>2023-01-01'}
            similarity_metric: Метрика сходства 
                ('cosine', 'euclidean', 'dot_product')
            limit: Количество результатов
            
        Returns:
            DataFrame с результатами поиска
        """
        # Построение WHERE условий
        where_conditions = []
        if filters:
            for column, condition in filters.items():
                if isinstance(condition, str) and condition.startswith(
                        ('>', '<', '>=', '<=', '!=')):
                    where_conditions.append(f"{column} {condition}")
                else:
                    where_conditions.append(f"{column} = '{condition}'")
        
        where_clause = (" AND ".join(where_conditions) 
                       if where_conditions else "1=1")
        
        # Выбор функции сходства
        similarity_functions = {
            'cosine': 'cosine_similarity',
            'euclidean': 'euclidean_distance', 
            'dot_product': 'dot_product'
        }
        
        similarity_func = similarity_functions.get(
            similarity_metric, 'cosine_similarity')
        
        # SQL запрос
        query = f"""
        SELECT *,
               {similarity_func}({embedding_column}, ?) AS similarity
        FROM {table_name}
        WHERE {where_clause}
        ORDER BY similarity DESC
        LIMIT {limit}
        """
        
        result = self.conn.execute(query, [query_vector]).fetchdf()
        return result
        
    def analyze_clusters(self,
                         table_name: str = "documents",
                         embedding_column: str = "embedding",
                         similarity_threshold: float = 0.8,
                         group_by: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Анализ кластеров похожих документов
        
        Args:
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            similarity_threshold: Порог сходства для кластеризации
            group_by: Колонки для группировки
            
        Returns:
            DataFrame с анализом кластеров
        """
        group_columns = ", ".join(group_by) if group_by else "'all'"
        
        query = f"""
        WITH similarity_pairs AS (
            SELECT 
                a.id as id1,
                b.id as id2,
                {group_columns} as cluster_group,
                cosine_similarity(a.{embedding_column}, 
                                  b.{embedding_column}) as similarity
            FROM {table_name} a
            CROSS JOIN {table_name} b
            WHERE a.id != b.id
            AND cosine_similarity(a.{embedding_column}, 
                                  b.{embedding_column}) > {similarity_threshold}
        )
        SELECT 
            cluster_group,
            COUNT(DISTINCT id1) as documents_count,
            AVG(similarity) as avg_similarity,
            MAX(similarity) as max_similarity,
            MIN(similarity) as min_similarity
        FROM similarity_pairs
        GROUP BY cluster_group
        ORDER BY documents_count DESC
        """
        
        result = self.conn.execute(query).fetchdf()
        return result
        
    def similarity_trends(self,
                          reference_vector: List[float],
                          table_name: str = "documents",
                          embedding_column: str = "embedding",
                          time_column: str = "date",
                          period: str = "month") -> pd.DataFrame:
        """
        Анализ временной динамики похожести
        
        Args:
            reference_vector: Референсный вектор для сравнения
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            time_column: Колонка с датой/временем
            period: Период агрегации ('day', 'week', 'month', 'year')
            
        Returns:
            DataFrame с временной динамикой
        """
        # Функции для группировки по времени
        time_functions = {
            'day': f"DATE_TRUNC('day', {time_column})",
            'week': f"DATE_TRUNC('week', {time_column})",
            'month': f"DATE_TRUNC('month', {time_column})",
            'year': f"DATE_TRUNC('year', {time_column})"
        }
        
        time_func = time_functions.get(period, time_functions['month'])
        
        query = f"""
        SELECT 
            {time_func} as period,
            COUNT(*) as documents_count,
            AVG(cosine_similarity({embedding_column}, ?)) as avg_similarity,
            MAX(cosine_similarity({embedding_column}, ?)) as max_similarity,
            MIN(cosine_similarity({embedding_column}, ?)) as min_similarity
        FROM {table_name}
        GROUP BY {time_func}
        ORDER BY period
        """
        
        result = self.conn.execute(
            query, [reference_vector, reference_vector, reference_vector]
        ).fetchdf()
        return result
        
    def execute_sql(self, query: str, 
                    parameters: Optional[List] = None) -> pd.DataFrame:
        """
        Выполнение произвольного SQL запроса
        
        Args:
            query: SQL запрос
            parameters: Параметры для запроса
            
        Returns:
            DataFrame с результатами
        """
        if parameters:
            result = self.conn.execute(query, parameters).fetchdf()
        else:
            result = self.conn.execute(query).fetchdf()
        return result
        
    def create_vector_index(self,
                            table_name: str,
                            embedding_column: str,
                            index_type: str = "hnsw") -> None:
        """
        Создание индекса для ускорения векторного поиска
        
        Args:
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            index_type: Тип индекса
        """
        # Пока что заглушка - в будущем можно добавить поддержку индексов
        print(f"Создание индекса {index_type} для {table_name}."
              f"{embedding_column}")
        
    def get_statistics(self, table_name: str) -> Dict[str, Any]:
        """
        Получение статистики по таблице
        
        Args:
            table_name: Имя таблицы
            
        Returns:
            Словарь со статистикой
        """
        stats_query = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT embedding) as unique_embeddings
        FROM {table_name}
        """
        
        result = self.conn.execute(stats_query).fetchone()
        
        return {
            'total_rows': result[0],
            'unique_embeddings': result[1]
        }


# Удобные функции для быстрого старта
def quick_search(data_file: str,
                 query_vector: List[float],
                 filters: Optional[Dict[str, Any]] = None,
                 limit: int = 10) -> pd.DataFrame:
    """
    Быстрый поиск без создания объекта VectorDB
    
    Args:
        data_file: Путь к файлу с данными
        query_vector: Вектор запроса
        filters: Фильтры
        limit: Количество результатов
        
    Returns:
        DataFrame с результатами
    """
    db = VectorDB()
    db.load_embeddings(data_file)
    return db.hybrid_search(query_vector, filters=filters, limit=limit)


def create_sample_data(num_documents: int = 1000,
                       embedding_dim: int = 128,
                       categories: List[str] = None) -> pd.DataFrame:
    """
    Создание тестовых данных для демонстрации
    
    Args:
        num_documents: Количество документов
        embedding_dim: Размерность эмбеддингов
        categories: Список категорий
        
    Returns:
        DataFrame с тестовыми данными
    """
    if categories is None:
        categories = ['технологии', 'наука', 'спорт', 'политика', 'культура']
    
    np.random.seed(42)
    
    data = {
        'id': range(num_documents),
        'title': [f'Документ {i}' for i in range(num_documents)],
        'text': [f'Текст документа {i}' for i in range(num_documents)],
        'embedding': [np.random.rand(embedding_dim).tolist() 
                      for _ in range(num_documents)],
        'category': np.random.choice(categories, num_documents),
        'date': pd.date_range('2023-01-01', periods=num_documents, 
                              freq='D')[:num_documents]
    }
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Пример использования
    print("🚀 Hybrid Analytics Platform - Демонстрация")
    
    # Создание тестовых данных
    print("\n1. Создание тестовых данных...")
    sample_data = create_sample_data(100, 128)
    print(f"Создано {len(sample_data)} документов")
    
    # Инициализация базы данных
    print("\n2. Инициализация базы данных...")
    db = VectorDB()
    db.load_embeddings(sample_data)
    
    # Гибридный поиск
    print("\n3. Гибридный поиск...")
    query_vector = np.random.rand(128).tolist()
    results = db.hybrid_search(
        query_vector=query_vector,
        filters={'category': 'технологии'},
        limit=5
    )
    print(f"Найдено {len(results)} похожих документов в категории "
          "'технологии'")
    print(results[['id', 'title', 'category', 'similarity']].head())
    
    # Анализ кластеров
    print("\n4. Анализ кластеров...")
    clusters = db.analyze_clusters(group_by=['category'])
    print("Анализ кластеров по категориям:")
    print(clusters)
    
    print("\n✅ Демонстрация завершена!") 