"""Prompt templates for the destination extraction agent."""
from typing import Optional


DESTINATION_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的旅行目的地提取助手。你的任务是从用户的自然语言中提取目的地信息。

请提取以下信息：
1. destination: 目的地名称（城市或地区）
2. country: 所在国家（如果可以推断）
3. confidence: 提取的置信度（0.0到1.0之间，基于文本中目的地明确程度）

规则：
- 如果没有明确的目的地，destination 设为 "unknown"
- country 尽可能提取，如果无法确定则为 null
- confidence 根据以下标准：
  * 明确提到具体城市名：0.9-1.0
  * 提到国家或地区但不具体：0.7-0.8
  * 有目的地但表述模糊：0.5-0.6
  * 无法确定或无目的地：0.0-0.4

输出格式必须是纯 JSON，不要包含任何其他文本或解释。"""


DESTINATION_EXTRACTION_USER_PROMPT = """请从以下文本中提取目的地信息：

{text}

返回 JSON 格式：
{{
  "destination": "目的地名称",
  "country": "国家名称或null",
  "confidence": 置信度数字
}}"""


def build_destination_extraction_prompt(text: str) -> str:
    """
    Build the complete prompt for destination extraction.

    Args:
        text: User's natural language input.

    Returns:
        Complete prompt string.
    """
    return f"""{DESTINATION_EXTRACTION_SYSTEM_PROMPT}

{DESTINATION_EXTRACTION_USER_PROMPT.format(text=text)}"""


# Additional specialized prompts for future extension
TRIP_PLANNING_SYSTEM_PROMPT = """你是一个专业的旅行规划助手。帮助用户制定旅行计划、推荐景点和活动。"""


BOOKING_ASSISTANT_SYSTEM_PROMPT = """你是一个专业的预订助手。帮助用户预订机票、酒店和其他旅行服务。"""


def get_prompt(prompt_type: str, context: Optional[dict] = None) -> str:
    """
    Get a prompt by type with optional context.

    Args:
        prompt_type: Type of prompt to retrieve.
        context: Optional dictionary with context variables.

    Returns:
        The formatted prompt string.

    Raises:
        ValueError: If prompt_type is unknown.
    """
    prompts = {
        "destination_extraction": build_destination_extraction_prompt,
        "trip_planning": TRIP_PLANNING_SYSTEM_PROMPT,
        "booking_assistant": BOOKING_ASSISTANT_SYSTEM_PROMPT,
    }

    if prompt_type not in prompts:
        raise ValueError(f"Unknown prompt type: {prompt_type}")

    prompt_func = prompts[prompt_type]
    if context and callable(prompt_func):
        return prompt_func(**context)
    return prompt_func
