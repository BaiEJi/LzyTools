"""邮件模块配置。

业务创建 EmailConfig 并传入 SmtpSender，
不自行读取 .env。
"""
from pydantic import BaseModel


class EmailConfig(BaseModel):
    """SMTP 邮件发送配置。

    所有参数均有合理默认值，仅 host / username / password 必须显式设置。
    """
    # SMTP 服务器地址
    host: str
    # SMTP 端口。默认 587（STARTTLS），SSL 用 465
    port: int = 587
    # SMTP 用户名
    username: str
    # SMTP 密码
    password: str
    # 发件人地址（如 "noreply@example.com"）
    # 为空时使用 username
    sender: str = ""
    # 发件人显示名（如 "My App"）
    sender_name: str = ""
    # 是否使用 STARTTLS（端口 587）
    use_tls: bool = True
    # 是否使用 SSL（端口 465）。与 use_tls 互斥
    use_ssl: bool = False
    # 连接超时（秒）
    timeout: float = 30.0
    # 模板目录路径（Jinja2 模板文件所在目录）
    template_dir: str = ""
    # 批量发送每批数量
    bulk_batch_size: int = 50

    @property
    def from_address(self) -> str:
        """获取发件人完整地址。"""
        if self.sender_name:
            return f"{self.sender_name} <{self.sender or self.username}>"
        return self.sender or self.username
