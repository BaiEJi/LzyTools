Task: Create basic_tool/concurrency/README.md

Outcome: COMPLETED

Checklist:
- [x] File created: basic_tool/concurrency/README.md
- [x] Sections: 概述、依赖、模块结构、API 文档（含签名和说明）、使用示例
- [x] All 7 major APIs documented: gather_with_limit, run_in_batches, gather_with_retry, with_timeout, ConcurrencyPool, TaskGroup, CompositeError, ErrorStrategy (also ConcurrencyConfig, PoolStats)
- [x] gather_with_retry examples use factory function pattern: `lambda u=u: fetch_with_retry(u)`
- [x] 7 usage examples: 有界并发执行, 分批处理, 超时保护, 带重试的批量执行, 并发池, 结构化并发 TaskGroup, 组合使用
- [x] Chinese descriptions + English code examples (matches project pattern)
- [x] No APIs beyond implementation
- [x] Factory function pattern used consistently for gather_with_retry

Pattern followed: basic_tool/redis/README.md (概述 → 依赖 → 结构 → API → 示例)
