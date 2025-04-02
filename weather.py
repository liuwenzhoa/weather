from typing import Any
# 用于发送 HTTP 请求
import httpx
# 用于创建 MCP 服务
from mcp.server.fastmcp import FastMCP

# 初始化一个MCP服务实例，服务名称就是weather，这将作为 MCP 客户端或大模型识别服务的标识
mcp = FastMCP("weather")

# 定义OpenWeatherMap API 的基础URL
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
# API 密钥
OPENWEATHER_API_KEY = "01axxx"
# API 调用的身份识别
USER_AGENT = "weather-app/1.0"

# 核心工具函数：负责向OpenWeatherMap API 发送请求并处理响应
async def make_weather_request(url: str) -> dict[str, Any] | None:
    """向OpenWeatherMap API 发送请求并处理响应，包括适当的错误处理。

    Args:
        url (str): 完整的OpenWeatherMap API 请求URL
        
    Returns:
        dict[str, Any]
        None: 如果请求成功，返回响应的JSON数据，否则返回None
    """
    # 设置请求头,包含User-Agent标识
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # 创建异步Http客户端会话
    async with httpx.AsyncClient() as client:
        try:
            # 发送GET请求，并设置请求头和超时
            response = await client.get(url, headers=headers, timeout=30.0)
            # 检查HTTP状态，非2XX状态码会抛出异常
            response.raise_for_status()
            # 解析JSON响应数据并返回
            return response.json()
        except Exception as e:
            print(f"错误 {e}")
            return None

# 辅助函数：将当前JSON格式的天气数据转换为可读的文本格式
def format_weather_data(data: dict, units: str = "metric") -> str:
    """将JSON格式的天气数据转换为可读的文本字符串格式
    
    Args:
        data (dict): JSON格式的天气数据
        
    Returns:
        str: 格式化的天气信息文本
    """
    # 检查data是否为空
    if not data:
        return "无法获取天气数据"
    
    # 从 API 响应中提取关键天气信息
    # 获取国家代码
    country_code = data.get("sys", {}).get("country", "未知")
    # 获取城市名称
    city_name = data.get("name", "未知")
    # 获取天气描述
    weather_desc = data.get("weather", [{}])[0].get("description", "未知")
    # 获取当前温度（摄氏度）
    temp = data.get("main", {}).get("temp", "未知")
    # 获取体感温度（摄氏度）
    feels_like = data.get("main", {}).get("feels_like", "未知")
    # 获取湿度(百分比)
    humidity = data.get("main", {}).get("humidity", "未知")
    # 获取风速(m/s)
    wind_speed = data.get("wind", {}).get("speed", "未知")

    # 根据 units 参数确定温度和风速的单位
    temp_unit = "°C" if units == "metric" else "°F"
    wind_speed_unit = "m/s" if units == "metric" else "mph"

    # 构建格式化的天气信息字符串
    return f"""
    城市: {city_name}
    国家: {country_code}
    天气: {weather_desc}
    温度: {temp} {temp_unit}
    体感温度: {feels_like} {temp_unit}
    湿度: {humidity}%
    风速: {wind_speed} {wind_speed_unit}
    """

# @mcp.tool() 是一个装饰器，用于将函数注册为 MCP 工具，允许大模型进行调用
# @mcp.tool(name="get_weather", description="获取指定城市的当前天气信息, 如果用户使用中文询问某城市天气，你必须将城市名转换为相应的英文名称再调用API。")
@mcp.tool()
# MCP 工具1：根据城市获取当前的天气信息，由大模型调用这个函数，函数参数由大模型传入
async def get_weather(city: str, country_code: str = None, state_code: str = None, units: str = "metric", lang: str = "zh_cn") -> str:
    """获取指定城市的当前天气信息，如果用户使用中文询问某城市天气，你必须将城市名转换为相应的英文名称再调用API。

    Args:
        city: 城市名称 (例如：Beijing, Shanghai, New York)
        country_code: 国家代码(可选，例如：CN, US, JP)
        state_code: 州/省代码(可选，例如：BJ, SH, NY)
        units: 测量单位(可选，默认metric)
        lang: 语言(可选，默认zh_cn)
    
    Returns:
        str: 格式化的当前天气信息文本
    """
    # 构建位置查询参数，支持城市名称、州代码和国家代码组合
    location_query = city
    if state_code and country_code:
        # 格式：城市，州代码，国家代码
        location_query = f"{city},{state_code},{country_code}"
    if country_code:
        # 格式：城市，国家代码
        location_query = f"{city},{country_code}"
    
    # 构建API请求URL,参数包含位置查询、API密钥、测量单位和语言
    url = f"{OPENWEATHER_API_BASE}/weather?q={location_query}&appid={OPENWEATHER_API_KEY}&units={units}&lang={lang}"
    
    # 发送请求并获取响应数据
    data = await make_weather_request(url)

    # 检查 API 响应中的错误代码
    if "cod" in data and data["cod"] != 200:
        return f"获取天气信息失败，错误：{data.get('message', '未知错误')}"
    
    # 使用辅助函数格式化天气信息并返回，传入data和units参数
    return format_weather_data(data, units)

# MCP 工具2：提供5天天气预报的查询功能，传入城市名称、国家代码(可选)、州代码(可选)、测量单位(可选)和语言(可选)
@mcp.tool()
async def get_forecast(city: str, country_code: str = None, state_code: str = None, units: str = "metric", lang: str = "zh_cn") -> str:
    """获取指定城市的5天天气预报信息，如果用户使用中文询问某城市5天天气预报，你必须将城市名转换为相应的英文名称再调用API。
    
    Args:
        city: 城市名称 (例如：Beijing, Shanghai, New York)
        country_code: 国家代码(可选，例如：CN, US, JP)
        state_code: 州/省代码(可选，例如：BJ, SH, NY)
        units: 测量单位(可选，默认metric)
        lang: 语言(可选，默认zh_cn)
    
    Returns:
        str: 格式化的5天天气预报信息文本
    """
    # 构建位置查询参数，支持城市名称、州代码和国家代码组合
    location_query = city
    if state_code and country_code:
        # 格式：城市，州代码，国家代码
        location_query = f"{city},{state_code},{country_code}"
    if country_code:
        # 格式：城市，国家代码
        location_query = f"{city},{country_code}"
    
    # 构建API请求URL,参数包含位置查询、API密钥、测量单位和语言
    url = f"{OPENWEATHER_API_BASE}/forecast?q={location_query}&appid={OPENWEATHER_API_KEY}&units={units}&lang={lang}"

    # 发送请求并获取响应数据
    data = await make_weather_request(url)

    # 检查data是否为空
    if not data:
        return "无法获取天气数据"
    
    # 检查 API 响应中的错误代码
    if "cod" in data and data["cod"] != "200":
        return f"获取5天天气预报信息失败，错误：{data.get('message', '未知错误')}"
    
    # 提取5天天气预报信息
    forecast_list = data.get("list", [])
    # 如果天气数组为空
    if not forecast_list:
        return "无法获取5天天气预报信息"
    
    # 构建格式化的5天天气预报信息数组
    forecast_data = []
    # 遍历5天天气预报信息,并提取日期和时间
    for forecast in forecast_list:
        # 提取日期和时间
        date_time = forecast.get("dt_txt", "")
        # 提取天气描述
        weather_desc = forecast.get("weather", [{}])[0].get("description", "未知")
        # 提取温度
        temp = forecast.get("main", {}).get("temp", "未知")
        # 提取湿度
        humidity = forecast.get("main", {}).get("humidity", "未知")
        # 提取风速
        wind_speed = forecast.get("wind", {}).get("speed", "未知")
        # 根据 units 参数确定温度和风速的单位
        temp_unit = "°C" if units == "metric" else "°F"
        wind_speed_unit = "m/s" if units == "metric" else "mph"
        # 构建格式化的5天天气预报信息字符串
        forecast_str = f"""
        日期: {date_time}
        天气: {weather_desc}
        温度: {temp} {temp_unit}
        湿度: {humidity}%
        风速: {wind_speed} {wind_speed_unit}
        """
        # 提取天气预报数据
        forecast_data.append(forecast_str)
    # 返回格式化的5天天气预报信息数组，使用分隔符链接所有天气预报
    return "\n---\n".join(forecast_data)

# 这个就是告诉大模型你应该使用什么文本形式给我答案
# mcp.prompt() 是一个装饰器，用于将函数注册为 MCP 提示，允许大模型进行调用
@mcp.prompt()
# 那么这个函数接收的数据是由大模型传入的，也就是说它把天气数据传入进来。
async def weather_prompt(city: str, weather_desc: str, temp: float, humidity: float, wind_speed: float, temp_unit: str, speed_unit: str) -> str:
    """用于生成天气报告的提示模板

    Args:
        city: 城市名称
        weather_desc: 天气描述
        temp: 温度
        humidity: 湿度
        wind_speed: 风速
        temp_unit: 温度单位
        speed_unit: 风速单位
    """
    # 构建天气报告的格式化文本
    return f"""请你作为专业的气象播报员，根据以下天气数据生成一份简介、易懂的天气报告:

    城市: {city}
    天气: {weather_desc}
    温度: {temp} {temp_unit}
    湿度: {humidity}%
    风速: {wind_speed} {speed_unit}

    报告内容包括：
    1.今日天气概况
    2.根据温度和湿度分析体感情况
    3.根据天气状况提供穿衣建议
    4.适合的户外活动推荐

    最后请使用自然、专业的语言，避免过于技术性的术语，要贴近生活。
    """

# mcp工具3：获取指定城市的天气信息并提供报告模板
@mcp.tool()
async def weather_report(city: str, country_code: str = None, state_code: str = None, units: str = "metric", lang: str = "zh_cn") -> dict:
    """获取指定城市的天气信息并提供报告模板

    Args:
        city: 城市名称
        country_code: 国家代码(可选，例如：CN, US, JP)
        state_code: 州/省代码(可选，例如：BJ, SH, NY)
        units: 测量单位(可选，默认metric)
        lang: 语言(可选，默认zh_cn)
    
    Returns:
        dict: 包含天气数据和提示模板信息的字典
    """
    # 获取原始天气信息
    weather_result = await get_weather(city, country_code, state_code, units, lang)

    # 解析天气文本获取关键信息
    import re
    # 使用正则表达式提取天气信息
    city_match = re.search(r'城市: (.*?)(?:\n|$)', weather_result)
    weather_match = re.search(r'天气: (.*?)(?:\n|$)', weather_result)
    temp_match = re.search(r'温度: ([\d.]+)(.*?)(?:\n|$)', weather_result)
    humidity_match = re.search(r'湿度: ([\d.]+)%', weather_result)
    wind_match = re.search(r'风速: ([\d.]+) (.*?)(?:\n|$)', weather_result)

    # 提取数据值，如果无法提取则使用默认值
    city_name = city_match.group(1) if city_match else city
    weather_desc = weather_match.group(1) if weather_match else "未知"
    temp_value = float(temp_match.group(1)) if temp_match else 0.0
    temp_unit = temp_match.group(2) if temp_match and len(temp_match.groups()) > 1 else "°C"
    humidity_value = int(float(humidity_match.group(1))) if humidity_match else 0
    wind_speed = float(wind_match.group(1)) if wind_match else 0.0
    speed_unit = wind_match.group(2) if wind_match and len(wind_match.groups()) > 1 else "m/s"

    # 构建返回结果，包含三个部分：原始的数据，模板名称，模板参数
    # 大模型调用这个工具会收到包含原始数据，模板名称，模板参数的结构化返回结果
    # 大模型识别到prompt_template字段指向 weather_report 这个函数模板，会调用这个函数，并传入模板参数
    # 大模型自动用 template_args 中的值填充 weather_report 模板中的对应参数。
    # 填充后的模板会成为大模型自己的 “思考提示”，然后大模型会根据这个提示，生成最终的回答。
    # 这就像我们去餐厅点餐:
    # mcp.prompt()的定义就相当于菜单上的标准食谱
    # weather_prompt 函数相当于收集食材
    # 当模型调用这个weather_report工具时，模型接收到了食谱(prompt_template)和食材(template_args)
    # 模型就相当于厨师，按照食谱(提示模板)，使用食材(模板参数)烹饪菜品(回答)
    return {
        "raw_data": weather_result,
        "prompt_template": "weather_prompt",
        "template_args": {
            "city": city_name,
            "weather_desc": weather_desc,
            "temp": temp_value,
            "temp_unit": temp_unit,
            "humidity": humidity_value,
            "wind_speed": wind_speed,
            "speed_unit": speed_unit,
        }
    }

# 程序入口点
if __name__ == "__main__":
    # 初始化并运行 MCP 服务，使用标准输入输出作为传输方式
    mcp.run(transport='stdio')