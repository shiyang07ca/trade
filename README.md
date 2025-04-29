# 交易策略分析工具

这是一个基于 backtrader 的交易策略分析工具包，用于开发、测试和评估交易策略。

## 模块

## 配置管理模块

本模块使用 pydantic-settings 对 `.env` 文件进行管理，提供统一的配置访问接口。

### 特性

- 基于 pydantic-settings 和 pydantic 的类型安全配置管理
- 支持从环境变量和 `.env` 文件加载配置
- 提供默认值和配置验证
- 支持不同环境（开发、测试、生产）的配置管理
- 类型提示和文档

### 使用方法
TODO



## 开发

安装开发依赖:

```bash
uv pip install -e ".[dev]"
```

运行测试:

```bash
pytest
```

## 贡献

欢迎提交 Pull Requests 或 Issues 来改进此项目。

## 许可证

MIT
