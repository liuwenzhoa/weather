# For Server Developers - 服务端开发者指南

## MCP 是什么

MCP 是 Model Context Protocol 的缩写，是连接大模型与外部资源/工具的标准化接口服务。
说的通俗一些mcp就是标准化的function call，只不过这个function call是用于大模型与外部资源/工具之间的交互。
我们知道大模型本身只是对数据进行计算和处理，本身不具备获取外部资源和工具的能力，而mcp为大模型提供了具备调用外部资源和工具的能力，并且mcp服务的诞生可以让大模型自行调用这些资源和工具。
比如大模型没有能力调用我们本地数据库数据，然后使用特定结构的SQL查询获取数据再生成图表，那么我们现在就可以使用mcp来实现这个功能。一个 mcp 负责通过SQL查询获取数据，然后另一个 mcp 负责生成图表,比如图片格式或者HTML格式。

## 我们将构建什么

许多大语言模型目前没有能力获取天气预报和恶劣天气警报。让我们使用 MCP 来解决这个问题！

我们将构建一个服务器，提供两个工具：get-alerts 和 get-forecast。然后我们将服务器连接到 MCP 主机（在本例中是 Claude for Desktop）：

服务器可以连接到任何客户端。我们在这里选择 Claude for Desktop 是为了简单起见，但我们也有关于构建自己的客户端的指南以及此处的其他客户端列表。

由于服务器是本地运行的，MCP 目前只支持桌面主机。远程主机正在积极开发中。

## Core MCP Concepts - MCP 核心概念

MCP 服务器可以提供三种主要类型的功能：

1. Resources（资源）：客户端可以读取的类似文件的数据（如 API 响应或文件内容）
    也就是说我们自己开发好的后端API或者第三方的API接口或者是文件等，可以通过 Resource 来进行读取的。区别在于传统API调用是我们或程序主动请求和处理数据的过程，但是Resource方式则是将数据源注册为标准化URI资源，允许大模型通过统一接口直接访问，无需关心底层实现细节。也就是说我们有一个URL，这个URL可以直接接入数据库某个表的数据，然后大模型就可以直接通过这个URL来获取这个表的数据。并且不会像使用 tools 那样需要我们进行确认。这样的做法丰富了大模型的上下文信息。标准规范是 Resource 只对数据进行读取，不能进行写入。
2. Tools（工具）：LLM 可以调用的函数（需用户批准）
    也就是说我们开发的 MCP 服务可以提供很多函数，这些函数可以让大模型自行调用，比如我们开发了一个获取天气预报的函数，那么大模型就可以自己调用这个函数来获取天气预报信息。那么类比一下就好比我们传统开发后端API一样，我们自己开发了一个获取天气预报的API，然后我们自己调用这个API来获取天气预报信息。只不过这个流程是把我们自己替换成大模型而已。
3. Prompts（提示）：帮助用户完成特定任务的预写模板
    其实就是为Tools提供一个提示词，让大模型可以根据提示词模板进行回答。就比如说我通过天气预报函数过去今天的天气的同时我还想让大模型给我出门穿衣的建议，那么我就可以为这个天气函数提供一个提示词，让大模型可以根据提示词模板进行回答。

本教程将主要关注工具。

让我们开始构建我们的天气服务器！您可以在[这里](https://github.com/anthropics/modelcontextprotocol/tree/main/examples/weather-server)找到我们将构建的完整代码。

### 前置知识要求

本快速入门假设您熟悉：

* Python
* 像 Claude 这样的大语言模型

### 系统要求

* 安装 Python 3.10 或更高版本。
* 您必须使用 Python MCP SDK 1.2.0 或更高版本。

### 设置您的环境

首先，让我们安装 uv 并设置我们的 Python 项目和环境：
uv 是一个 Python 依赖管理工具，类似我们开发node项目需要使用 npm 或 npx 依赖管理工具一样。
那么 Python 的依赖管理工具我们常用的还有 pip 和 venv，比如上期视频我就使用 venv 创建了一个python的虚拟环境去启动一个mcp服务。
只不过 uv 比 pip 和 venv 更快，但实际如何其实我也没多大感受，只不过既然官方文档提供使用uv的方式，那我们就按照官方文档的内容的来做。
至于 uv 与 pip 和 venv 的特点大家可以使用 PPL MCP 服务在cursor中提问获取最新的信息进行比对即可，PPL MCP 服务是我第一个视频讲解到的。

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

之后请确保重启终端，以确保 uv 命令被正确识别。

现在，让我们创建并设置我们的项目：

```
# 为我们的项目创建一个新目录
uv init weather
cd weather
# 创建虚拟环境并激活它,我们创建一个目录 weather_env 来存放虚拟环境
uv venv weather_env
source ./weather_env/Scripts/activate
# 测试 python 是否是指定的当前虚拟环境中的python
which python
# 安装 http 依赖用于调用外部API 和 mcp cli的相关命令行工具，--active 让 uv 使用当前激活的环境安装相关依赖
uv add "mcp[cli]" httpx --active
# 创建我们的服务器文件
touch weather.py
```

现在让我们深入构建您的服务器。

## Building your server - 构建您的服务器

### 导入包并设置实例

将这些添加到您的 weather.py 顶部：

```python
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
```

FastMCP 类使用 Python 类型提示和文档字符串自动生成工具定义，使创建和维护 MCP 工具变得容易。

### 辅助函数

接下来，让我们添加用于查询和格式化来自国家气象服务 API 的数据的辅助函数：

```python
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""
```

### 实现工具执行

工具执行处理程序负责实际执行每个工具的逻辑。让我们添加它：

```python
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.
    
    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    
    if not data["features"]:
        return "No active alerts for this state."
    
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    
    if not points_data:
        return "Unable to fetch forecast data for this location."
    
    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)
    
    if not forecast_data:
        return "Unable to fetch detailed forecast."
    
    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)
    
    return "\n---\n".join(forecasts)
```

### 运行服务器

最后，让我们初始化并运行服务器：

```python
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
```

您的服务器已完成！运行 `uv run weather.py` 确认一切正常工作。

现在让我们从现有的 MCP 主机（Claude for Desktop）测试您的服务器。

## Testing your server with Claude for Desktop - 使用 Claude for Desktop 测试您的服务器

Claude for Desktop 尚未在 Linux 上可用。Linux 用户可以继续阅读构建客户端教程，以构建连接到我们刚刚构建的服务器的 MCP 客户端。

首先，确保您已安装 Claude for Desktop。您可以在[这里](https://claude.ai/desktop)安装最新版本。如果您已经安装了 Claude for Desktop，请确保它已更新到最新版本。

我们需要为您想要使用的任何 MCP 服务器配置 Claude for Desktop。为此，请在文本编辑器中打开您的 Claude for Desktop 应用配置文件，路径为 `~/Library/Application Support/Claude/claude_desktop_config.json`。如果该文件不存在，请创建它。

例如，如果您安装了 VS Code：

```
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

然后，您将在 mcpServers 键中添加您的服务器。只有当至少一个服务器正确配置时，MCP UI 元素才会在 Claude for Desktop 中显示。

在本例中，我们将添加我们的单个天气服务器，如下所示：

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather",
        "run",
        "weather.py"
      ]
    }
  }
}
```

您可能需要在 command 字段中放入 uv 可执行文件的完整路径。您可以通过在 MacOS/Linux 上运行 `which uv` 或在 Windows 上运行 `where uv` 来获取这个路径。

确保您传入服务器的绝对路径。

这告诉 Claude for Desktop：

1. 有一个名为 "weather" 的 MCP 服务器
2. 通过运行 `uv --directory /ABSOLUTE/PATH/TO/PARENT/FOLDER/weather run weather.py` 来启动它

保存文件，并重启 Claude for Desktop。

### 使用命令测试

让我们确保 Claude for Desktop 正在获取我们在天气服务器中公开的两个工具。您可以通过查找锤子图标来做到这一点：

点击锤子图标后，您应该会看到列出的两个工具：

如果您的服务器没有被 Claude for Desktop 检测到，请查看故障排除部分获取调试提示。

如果锤子图标已显示，您现在可以通过在 Claude for Desktop 中运行以下命令来测试您的服务器：

* What's the weather in Sacramento?（萨克拉门托的天气如何？）
* What are the active weather alerts in Texas?（德克萨斯州有哪些活跃的天气警报？）

由于这是美国国家气象服务，查询只对美国地点有效。

## What's happening under the hood - 内部运作原理

当您提出问题时：

1. 客户端将您的问题发送给 Claude
2. Claude 分析可用的工具并决定使用哪一个（或哪些）
3. 客户端通过 MCP 服务器执行所选工具
4. 结果被发送回 Claude
5. Claude 制定自然语言响应
6. 响应显示给您！

## Troubleshooting - 故障排除

获取 Claude for Desktop 的日志

与 MCP 相关的 Claude.app 日志写入 `~/Library/Logs/Claude` 中的日志文件：

* mcp.log 将包含有关 MCP 连接和连接失败的一般日志记录。
* 名为 mcp-server-SERVERNAME.log 的文件将包含来自指定服务器的错误（stderr）日志记录。

您可以运行以下命令列出最近的日志并跟踪任何新日志：

```bash
# 检查 Claude 的日志是否有错误
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```

服务器未在 Claude 中显示

1. 检查您的 claude_desktop_config.json 文件语法
2. 确保您的项目路径是绝对路径而不是相对路径
3. 完全重启 Claude for Desktop

工具调用无声失败

如果 Claude 尝试使用工具但它们失败：

1. 检查 Claude 的日志是否有错误
2. 验证您的服务器能否正常构建和运行
3. 尝试重启 Claude for Desktop

这些方法都不起作用。我该怎么办？

请参考我们的[调试指南](https://modelcontextprotocol.io/debugging)了解更好的调试工具和更详细的指导。

错误：无法检索网格点数据

这通常意味着：

1. 坐标在美国境外
2. NWS API 出现问题
3. 您的请求受到速率限制

解决方法：

* 验证您使用的是美国坐标
* 在请求之间添加小延迟
* 检查 NWS API 状态页面

错误：[STATE] 没有活跃警报

这不是错误 - 它只是意味着该州目前没有天气警报。尝试不同的州或在恶劣天气期间检查。

有关更高级的故障排除，请查看我们的[MCP 调试指南](https://modelcontextprotocol.io/debugging)

## Next steps - 下一步

### [Building a client - 构建客户端](https://modelcontextprotocol.io/quickstart/client)

学习如何构建可以连接到您的服务器的自己的 MCP 客户端

### [Example servers - 示例服务器](https://modelcontextprotocol.io/example-servers)

查看我们的官方 MCP 服务器和实现集合

### [Debugging Guide - 调试指南](https://modelcontextprotocol.io/debugging)

学习如何有效地调试 MCP 服务器和集成

### [Building MCP with LLMs - 使用 LLM 构建 MCP](https://modelcontextprotocol.io/building-mcp-with-llms)

学习如何使用像 Claude 这样的 LLM 加速您的 MCP 开发