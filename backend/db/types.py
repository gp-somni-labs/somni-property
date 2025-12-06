"""
Custom SQLAlchemy Types
Backend-agnostic types that work with both PostgreSQL and SQLite
"""

from sqlalchemy import TypeDecorator, String, Text, ARRAY as SQLAlchemy_ARRAY
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID, INET as PostgreSQL_INET, JSONB as PostgreSQL_JSONB, ARRAY as PostgreSQL_ARRAY
import uuid
import json


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available,
    otherwise uses String(36) for SQLite.
    """
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        else:
            return value


class INET(TypeDecorator):
    """
    Platform-independent INET type for IP addresses.

    Uses PostgreSQL's INET type when available,
    otherwise uses String(50) for SQLite.
    """
    impl = String(50)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_INET())
        else:
            return dialect.type_descriptor(String(50))


class JSONB(TypeDecorator):
    """
    Platform-independent JSONB type for JSON data.

    Uses PostgreSQL's JSONB type when available,
    otherwise uses Text for SQLite with JSON serialization.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name != 'postgresql':
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name != 'postgresql' and isinstance(value, str):
            return json.loads(value)
        return value


def ARRAY(item_type=None):
    """
    Platform-independent ARRAY type factory function.

    Returns PostgreSQL's ARRAY type for PostgreSQL,
    or a custom TypeDecorator using Text with JSON serialization for other databases.
    """
    class ArrayType(TypeDecorator):
        impl = Text
        cache_ok = True

        def load_dialect_impl(self, dialect):
            if dialect.name == 'postgresql':
                return dialect.type_descriptor(PostgreSQL_ARRAY(item_type))
            else:
                return dialect.type_descriptor(Text())

        def process_bind_param(self, value, dialect):
            if value is None:
                return value
            elif dialect.name != 'postgresql':
                return json.dumps(value) if value else None
            return value

        def process_result_value(self, value, dialect):
            if value is None:
                return value
            elif dialect.name != 'postgresql' and isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return []
            return value

    return ArrayType()
