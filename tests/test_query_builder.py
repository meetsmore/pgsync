"""QueryBuilder tests."""

from types import SimpleNamespace

import pytest
import sqlalchemy as sa

from pgsync.base import Base
from pgsync.node import Node
from pgsync.querybuilder import QueryBuilder


def test_get_foreign_keys_returns_copy_for_new_and_cached_values():
    metadata = sa.MetaData()
    parent = sa.Table(
        "parent",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        schema="public",
    )
    child = sa.Table(
        "child",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("parent_id", sa.ForeignKey("public.parent.id")),
        schema="public",
    )
    relationship = SimpleNamespace(foreign_key=None)

    class NodeStub:
        def __init__(self, table):
            self.model = SimpleNamespace(original=table)
            self.relationship = relationship

    parent_node = NodeStub(parent)
    child_node = NodeStub(child)
    query_builder = QueryBuilder()

    first = query_builder.get_foreign_keys(child_node, parent_node)
    first["public.child"].clear()

    second = query_builder.get_foreign_keys(child_node, parent_node)

    assert second == {
        "public.child": ["parent_id"],
        "public.parent": ["id"],
    }


def test_get_through_foreign_keys_returns_cache_copy():
    query_builder = QueryBuilder()
    node_a = object()
    node_b = object()
    cache_key = (node_a, node_b)
    query_builder._cache[cache_key] = {
        "public.join_table": ["parent_id", "child_id"]
    }

    first = query_builder._get_foreign_keys(node_a, node_b)
    first["public.join_table"].clear()

    second = query_builder._get_foreign_keys(node_a, node_b)

    assert second == {"public.join_table": ["parent_id", "child_id"]}


def test_get_column_foreign_keys_does_not_mutate_input():
    query_builder = QueryBuilder()
    foreign_keys = {
        "public.join_table": ["A", "B", "X", "Y"],
    }

    result = query_builder._get_column_foreign_keys(
        ["B"],
        foreign_keys,
        table="join_table",
        schema="public",
    )

    assert result == ["B"]
    assert foreign_keys == {
        "public.join_table": ["A", "B", "X", "Y"],
    }

    unscoped_result = query_builder._get_column_foreign_keys(
        ["A", "B", "X", "Y"],
        foreign_keys,
    )
    unscoped_result.clear()

    assert foreign_keys == {
        "public.join_table": ["A", "B", "X", "Y"],
    }


@pytest.mark.usefixtures("table_creator")
class TestQueryBuilder(object):
    """QueryBuilder tests."""

    def test__json_build_object(self, connection):
        pg_base = Base(connection.engine.url.database)
        query_builder = QueryBuilder()

        with pytest.raises(RuntimeError) as excinfo:
            query_builder._json_build_object([])
        assert "invalid expression" == str(excinfo.value)
        node = Node(
            models=pg_base.models,
            table="book",
            schema="public",
        )
        expression = query_builder._json_build_object(node.columns)
        assert expression is not None
        expected = (
            "CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_1, book_1.isbn, "
            ":JSON_BUILD_OBJECT_2, book_1.title, :JSON_BUILD_OBJECT_3, "
            "book_1.description, :JSON_BUILD_OBJECT_4, book_1.copyright, "
            ":JSON_BUILD_OBJECT_5, book_1.publisher_id, :JSON_BUILD_OBJECT_6, "
            "book_1.buyer_id, :JSON_BUILD_OBJECT_7, book_1.seller_id, "
            ":JSON_BUILD_OBJECT_8, book_1.tags) AS JSONB)"
        )
        assert str(expression) == expected
        expression = query_builder._json_build_object(
            node.columns, chunk_size=2
        )
        assert expression is not None
        expected = (
            "CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_1, book_1.isbn) AS "
            "JSONB) || CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_2, "
            "book_1.title) AS JSONB) || CAST(JSON_BUILD_OBJECT(:"
            "JSON_BUILD_OBJECT_3, book_1.description) AS JSONB) || "
            "CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_4, book_1.copyright) "
            "AS JSONB) || CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_5, "
            "book_1.publisher_id) AS JSONB) || CAST(JSON_BUILD_OBJECT("
            ":JSON_BUILD_OBJECT_6, book_1.buyer_id) AS JSONB) || "
            "CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_7, book_1.seller_id) "
            "AS JSONB) || CAST(JSON_BUILD_OBJECT(:JSON_BUILD_OBJECT_8, "
            "book_1.tags) AS JSONB)"
        )
        assert str(expression) == expected

    def test__get_column_foreign_keys(self, connection):
        pg_base = Base(connection.engine.url.database)
        query_builder = QueryBuilder()

        foreign_keys = {
            "public.subject": ["column_a", "column_b", "column_X"],
            "schema.table_b": ["column_x"],
        }

        subject = Node(
            models=pg_base.models,
            table="subject",
            schema="public",
            relationship={
                "type": "one_to_many",
                "variant": "scalar",
                "through_tables": ["book_subject"],
            },
        )
        left_foreign_keys = query_builder._get_column_foreign_keys(
            subject.columns,
            foreign_keys,
            table=subject.name,
            schema=subject.schema,
        )
        assert left_foreign_keys == ["column_b"]

    def test__get_child_keys(self):
        pass

    def test__root(self):
        pass

    def test__children(self):
        pass

    def test__through(self):
        pass

    def test__non_through(self):
        pass
