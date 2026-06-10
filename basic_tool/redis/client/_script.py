"""
Lua 脚本操作 Mixin。

提供 Redis Lua 脚本执行能力。
包括 eval/evalsha/register_script。
"""

from typing import Any

from redis.commands.core import Script


class ScriptMixin:
    """
    Lua 脚本操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def eval(
        self, script: str, numkeys: int, *keys_and_args: Any
    ) -> Any:
        """
        执行 Lua 脚本。

        脚本通过 EVAL 命令发送到 Redis 执行，每次调用都会发送脚本全文。
        如果需要多次执行同一脚本，建议使用 register_script() 注册后调用。

        Args:
            script: Lua 脚本源码
            numkeys: KEY[] 的数量
            *keys_and_args: 先是 numkeys 个 key，然后是 ARGV[] 参数

        Returns:
            Any: 脚本返回值

        用法:
            result = await cache.eval(
                'if redis.call("get", KEYS[1]) == ARGV[1] then return 1 else return 0 end',
                1, "mykey", "mytoken"
            )
        """
        return await self.client.eval(script, numkeys, *keys_and_args)

    async def evalsha(self, sha: str, numkeys: int, *keys_and_args: Any) -> Any:
        """
        通过 SHA1 校验和执行已缓存的 Lua 脚本。

        比 eval() 更高效，不传输脚本全文。
        如果服务端未缓存该脚本，会抛出 NoscriptError，此时应回退到 eval()。

        Args:
            sha: 脚本的 SHA1 校验和
            numkeys: KEY[] 的数量
            *keys_and_args: key 和参数

        Returns:
            Any: 脚本返回值
        """
        return await self.client.evalsha(sha, numkeys, *keys_and_args)

    def register_script(self, script: str) -> Script:
        """
        注册 Lua 脚本，返回可复用的 Script 对象。

        Script 对象会自动处理 EVALSHA + EVAL 回退逻辑：
        首次调用用 EVAL（同时缓存 SHA），后续用 EVALSHA。

        Args:
            script: Lua 脚本源码

        Returns:
            Script: 可复用的脚本对象

        用法:
            release_lock = cache.register_script('''
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
            ''')
            result = await release_lock(keys=["lock:123"], args=["token_xyz"])
        """
        return self.client.register_script(script)
