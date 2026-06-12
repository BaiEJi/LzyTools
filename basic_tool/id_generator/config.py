"""ID 生成器配置模型。"""

from pydantic import BaseModel, Field


class IDConfig(BaseModel):
    """ID 生成器配置。

    业务创建 IDConfig 并传入 IDGenerator / TraceGenerator，
    不自行读取 .env。

    worker_id 分配方式：
    - 配置中心分配（推荐）：从 Nacos/Consul/etcd 获取唯一编号
    - 环境变量注入：通过部署脚本设置 WORKER_ID 环境变量
    - K8s Pod ordinal：StatefulSet 的 pod ordinal 天然唯一
    - 本地开发：默认值 0

    Attributes:
        worker_id: 工作节点 ID（0-1023），分布式部署时必须唯一分配。
        epoch: 自定义 epoch（毫秒），默认 2024-01-01T00:00:00Z。
            设置后约可使用 69 年（至 ~2093 年）。
    """

    worker_id: int = Field(default=0, ge=0, le=1023)
    epoch: int = Field(default=1704067200000)
