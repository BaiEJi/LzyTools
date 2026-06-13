# Storage Module - Decisions

## Architecture
- Self-built StorageBackend ABC + aiofiles (not fsspec)
- LocalBackend is the only v1 implementation
- MinIO fields commented out in StorageConfig
- LocalBackend NOT exported (internal detail)
- basic_tool/__init__.py NOT modified (per plan)

## Security
- Path.is_relative_to() replaces str.startswith() for traversal checks
- Empty key raises ValueError
- Leading slash keys blocked (path traversal)

## Testing
- TDD: write tests first (RED), then implement (GREEN)
- ~20 test cases: 14 from design doc + 6 from Metis review
