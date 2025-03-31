# coding: utf-8
# OpenManus MCP服务器启动脚本
# 提供启动MCP服务器的快捷方式，并解决导入问题
from app.mcp.server import MCPServer, parse_args


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()

    # 创建并运行服务器（保持原始流程）
    server = MCPServer()
    server.run(transport=args.transport)
