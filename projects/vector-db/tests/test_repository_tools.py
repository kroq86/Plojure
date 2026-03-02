from duckdb_vec import DuckDBVectorDatabase
import numpy as np


def test_upsert_and_search_document_chunk():
    db = DuckDBVectorDatabase(":memory:")
    db.upsert_document_chunk(
        key="src/app.py:1-3",
        content="def add(a, b):\n    return a + b\n",
        path="src/app.py",
        start_line=1,
        end_line=2,
    )

    results = db.search_document_chunks("add function", k=1)

    assert len(results) == 1
    assert results[0]["path"] == "src/app.py"
    assert "return a + b" in results[0]["content"]


def test_index_repository_and_ask_context(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text(
        "def multiply(a, b):\n"
        "    return a * b\n"
        "\n"
        "def divide(a, b):\n"
        "    return a / b\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        "# Example\n\nThis repository contains arithmetic helpers.\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:")
    index_result = db.index_repository(str(repo), chunk_size_lines=20, overlap_lines=5)
    context_result = db.ask_repository_context("Where is the divide function?", k=2)

    assert index_result["indexed_files"] == 2
    assert index_result["indexed_chunks"] >= 2
    assert any(match["path"] == "main.py" for match in context_result["matches"])
    assert "divide" in context_result["context"]


def test_search_symbols_and_refresh_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "main.py"
    source.write_text(
        "def refresh_me():\n"
        "    return 'first'\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:")
    db.index_workspace(str(repo))
    symbol_results = db.search_symbols("refresh_me", k=1)

    source.write_text(
        "def refresh_me():\n"
        "    return 'second'\n",
        encoding="utf-8",
    )
    refresh_result = db.refresh_path(str(repo), "main.py")
    context_result = db.ask_repository_context("refresh_me second", k=1)

    assert symbol_results[0]["matched_symbols"] == ["refresh_me"]
    assert refresh_result["indexed_files"] == 1
    assert "second" in context_result["context"]


def test_refresh_path_skips_unchanged_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "main.py"
    source.write_text(
        "def stable():\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    first = db.refresh_path(str(repo), "main.py")
    second = db.refresh_path(str(repo), "main.py")

    assert first["indexed_files"] == 1
    assert second["indexed_files"] == 0
    assert second["skipped_files"] == 1


def test_search_symbols_finds_c_function_with_path_hint(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "wrapper.c"
    source.write_text(
        "void py_batch_cosine_scores(double* query, double* vectors) {\n"
        "    return;\n"
        "}\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.refresh_path(str(repo), "wrapper.c")
    results = db.search_symbols("wrapper.c py_batch_cosine_scores", k=1)

    assert results
    assert results[0]["path"] == "wrapper.c"
    assert "py_batch_cosine_scores" in results[0]["matched_symbols"]


def test_search_document_chunks_prefers_explicit_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mcp_vector_server.py").write_text(
        "self._write_lock = threading.RLock()\n"
        "with self._write_lock:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (repo / "other.py").write_text(
        "self._write_lock = threading.RLock()\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))
    results = db.search_document_chunks(
        "In mcp_vector_server.py where is _write_lock created?",
        k=1,
    )

    assert results
    assert results[0]["path"] == "mcp_vector_server.py"


def test_search_symbols_refresh_removes_stale_symbol(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "main.py"
    source.write_text(
        "def old_name():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))

    source.write_text(
        "def new_name():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    db.refresh_path(str(repo), "main.py")

    assert db.search_symbols("old_name", k=3) == []
    fresh = db.search_symbols("new_name", k=1)
    assert fresh
    assert fresh[0]["matched_symbols"] == ["new_name"]


def test_search_symbols_prefers_declaration_over_mention(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "defs.py").write_text(
        "def py_batch_cosine_scores():\n"
        "    return 'decl'\n",
        encoding="utf-8",
    )
    (repo / "notes.py").write_text(
        "def helper():\n"
        "    return 'py_batch_cosine_scores is mentioned here'\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))
    results = db.search_symbols("py_batch_cosine_scores", k=3)

    assert results
    assert results[0]["path"] == "defs.py"
    assert results[0]["matched_symbols"] == ["py_batch_cosine_scores"]


def test_search_symbols_finds_python_async_definition(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "service.py").write_text(
        "class Worker:\n"
        "    async def fetch_data(self):\n"
        "        return 42\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))
    results = db.search_symbols("fetch_data", k=1)

    assert results
    assert results[0]["path"] == "service.py"
    assert results[0]["matched_symbols"] == ["fetch_data"]


def test_search_symbols_finds_typescript_arrow_and_interface(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "api.ts").write_text(
        "export interface RequestPayload {\n"
        "  id: string;\n"
        "}\n"
        "export const loadUser = async (id: string): Promise<string> => {\n"
        "  return id;\n"
        "};\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))

    interface_results = db.search_symbols("RequestPayload", k=1)
    function_results = db.search_symbols("loadUser", k=1)

    assert interface_results
    assert interface_results[0]["path"] == "api.ts"
    assert interface_results[0]["matched_symbols"] == ["requestpayload"]
    assert function_results
    assert function_results[0]["path"] == "api.ts"
    assert function_results[0]["matched_symbols"] == ["loaduser"]


def test_search_symbols_finds_cpp_namespace_struct_and_method(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "engine.cpp").write_text(
        "namespace vecdb {\n"
        "struct Engine {\n"
        "    static double score(const double* lhs, const double* rhs) {\n"
        "        return 1.0;\n"
        "    }\n"
        "};\n"
        "}\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))

    namespace_results = db.search_symbols("vecdb", k=1)
    struct_results = db.search_symbols("Engine", k=1)
    method_results = db.search_symbols("score", k=1)

    assert namespace_results
    assert namespace_results[0]["matched_symbols"] == ["vecdb"]
    assert struct_results
    assert struct_results[0]["matched_symbols"] == ["engine"]
    assert method_results
    assert method_results[0]["matched_symbols"] == ["score"]


def test_native_lsh_hash_matches_numpy_path():
    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash", use_asm=True)
    projections = np.ascontiguousarray(
        np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0, 0.0],
                [-1.0, 0.5, 0.0, 0.0],
            ],
            dtype=np.float32,
        )
    )
    vector = [0.25, 0.75, 0.0, 0.0]

    native = db._hash_vector_native_f32(vector, projections)
    normalized = np.asarray(vector, dtype=np.float64)
    normalized /= np.linalg.norm(normalized)
    expected = (projections.astype(np.float64) @ normalized > 0).astype(int).tolist()

    assert native == expected


def test_float32_partition_topk_matches_numpy_order():
    db_asm = DuckDBVectorDatabase(":memory:", embedding_provider="hash", use_asm=True, similarity_metric="cosine")
    db_py = DuckDBVectorDatabase(":memory:", embedding_provider="hash", use_asm=False, similarity_metric="cosine")

    vectors = [
        ("a", [1.0, 0.0, 0.0, 0.0]),
        ("b", [0.8, 0.2, 0.0, 0.0]),
        ("c", [0.0, 1.0, 0.0, 0.0]),
        ("d", [0.6, 0.6, 0.0, 0.0]),
    ]
    rows = [(key, db_asm._serialize_vector(vec), len(vec)) for key, vec in vectors]
    batch = db_asm._build_partition_batch(rows)
    query = [1.0, 0.1, 0.0, 0.0]

    native = db_asm._topk_partition_batch(batch, query, 3)
    python = db_py._topk_partition_batch(batch, query, 3)

    assert [key for key, _ in native] == [key for key, _ in python]


def test_index_repository_excludes_core_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text(
        "def live_symbol():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    core_dir = repo / "core"
    core_dir.mkdir()
    (core_dir / "main.py").write_text(
        "def stale_symbol():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))

    assert db.search_symbols("live_symbol", k=3)
    assert db.search_symbols("stale_symbol", k=3) == []


def test_index_repository_skips_duplicate_content(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    content = (
        "def duplicate_symbol():\n"
        "    return 'same'\n"
    )
    (repo / "one.py").write_text(content, encoding="utf-8")
    nested = repo / "nested"
    nested.mkdir()
    (nested / "two.py").write_text(content, encoding="utf-8")

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    result = db.index_repository(str(repo))
    matches = db.search_symbols("duplicate_symbol", k=10)

    assert result["indexed_files"] == 1
    assert result["skipped_files"] >= 1
    assert len(matches) == 1


def test_semantic_search_approximate_handles_mixed_vector_dimensions(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text(
        "def stable_search():\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )

    db = DuckDBVectorDatabase(":memory:", embedding_provider="hash")
    db.index_repository(str(repo))
    db.insert("legacy-fastembed-vector", [0.1, 0.2, 0.3])

    results = db.search_document_chunks(
        "stable_search",
        k=3,
        method="approximate",
    )

    assert results
    assert any(result["path"] == "main.py" for result in results)
