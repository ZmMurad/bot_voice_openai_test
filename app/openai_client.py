import json
import logging

from openai import AsyncOpenAI, OpenAI
from config import Settings


class OpenAIService:
    def __init__(self, assistant_id: str,api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "save_value",
                    "description": "Save identified user value to database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Short name of the value (1-3 words)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Brief explanation of the value (max 100 chars)"
                            }
                        },
                        "required": ["name", "description"]
                    }
                }
            }
        ]

    async def identify_value(self, user_input: str) -> dict:
        try:
            thread = await self.client.beta.threads.create()
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                content=user_input,
                role="user"
            )

            run = await self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
                tools=self.tools
            )

            if run.status == "requires_action":
                return self._handle_function_call(run)

            messages = await self.client.beta.threads.messages.list(thread.id)
            return {"response": messages.data[0].content[0].text.value}

        except Exception as e:
            logging.error(f"OpenAI Error: {str(e)}")
            print(f"OpenAI Error: {str(e)}")
            return {"error": str(e)}

    def _handle_function_call(self, run) -> dict:
        """Обработка вызова функции save_value"""
        try:
            tool_call = run.required_action.submit_tool_outputs.tool_calls[0]
            if tool_call.function.name == "save_value":
                args = json.loads(tool_call.function.arguments)
                return {
                    "function_call": {
                        "name": "save_value",
                        "arguments": args
                    }
                }
            return {"error": "Unknown function requested"}
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logging.error(f"Function handling error: {str(e)}")
            print(f"Function handling error: {str(e)}")
            return {"error": "Invalid function call format"}

    async def process_message(self, text: str) -> str:
        try:
            thread = await self.client.beta.threads.create()
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                content=text,
                role="user"
            )

            run = await self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )

            if run.status == "completed":
                messages = await self.client.beta.threads.messages.list(thread.id)
                return messages.data[0].content[0].text.value
            else:
                return f"❌ Ошибка обработки: {run.status}"

        except Exception as e:
            return f"⛔️ OpenAI Error: {str(e)}"



def validate_value(description: str) -> bool:
    """Validate value description using GPT-4"""
    client = OpenAI(api_key=Settings().OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{
                "role": "system",
                "content": """
                Validate if the input is a legitimate personal value. 
                Return JSON: {"valid": boolean}
                Criteria:
                1. Minimum 3 words
                2. No offensive content
                3. Meaningful concept
                """
            }, {
                "role": "user",
                "content": description
            }],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result.get("valid", False)

    except Exception as e:
        print(f"Validation error: {str(e)}")
        return False