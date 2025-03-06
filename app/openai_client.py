import json
import logging

from aiogram import types, Bot
from openai import AsyncOpenAI, OpenAI

from database import AsyncSessionLocal
from models import UserValue
from utils import generate_unique_name, cleanup_files
from config import Settings


class OpenAIService:
    def __init__(self, assistant_id: str,api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        self.thread=None
        self.run=None
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

    async def submit_result(self, thread_id: str, run_id: str, success: bool,tool_call_id=None):
        await self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=[{
                "tool_call_id": tool_call_id,
                "output": json.dumps({"success": success})
            }]
        )

    async def identify_value(self, user_input: str) -> dict:
        try:
            thread = await self.client.beta.threads.create()
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                content=user_input,
                role="user"
            )
            self.thread=thread

            run = await self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
                tools=self.tools
            )
            self.run=run

            if run.status == "requires_action":
                return self._handle_function_call(run)

            if run.status == "completed":
                messages = await self.client.beta.threads.messages.list(thread.id)
                return {"response": messages.data[0].content[0].text.value}

            return {"error": f"Неизвестный статус выполнения: {run.status}"}

        except Exception as e:
            logging.error(f"OpenAI Error: {str(e)}")
            return {"error": str(e)}

    def _handle_function_call(self, run) -> dict:
        try:
            tool_call = run.required_action.submit_tool_outputs.tool_calls[0]
            if tool_call.function.name == "save_value":
                return {
                    "function_call": {
                        "name": "save_value",
                        "arguments": json.loads(tool_call.function.arguments)
                    }
                }
            return {"error": f"Неизвестная функция: {tool_call.function.name}"}

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logging.error(f"Ошибка обработки функции: {str(e)}")
            return {"error": f"Некорректный формат запроса: {str(e)}"}

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



async def validate_value(description: str,client:OpenAIService) -> bool:
    """Validate value description using GPT-4"""


    try:
        response = await client.client.chat.completions.create(
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


async def process_assistant_response(
        user_id,
        client_ai: OpenAIService,
        input_text: str,
        is_voice: bool = False,
        bot: Bot = None
):
    audio_path = None
    audio=None
    speech_path = None
    session = None
    response_text=""
    try:
        async with AsyncSessionLocal() as session:
            result = await client_ai.identify_value(input_text)

            if "error" in result:
                return f"Ошибка: {result['error']}"

            if "function_call" in result:
                # Обработка сохранения ценности
                args = result["function_call"]["arguments"]
                tool_call = client_ai.run.required_action.submit_tool_outputs.tool_calls[0]
                if await validate_value(args["description"],client_ai):
                    value = UserValue(
                        user_id=user_id,
                        value_name=args["name"],
                        description=args["description"]
                    )
                    session.add(value)
                    await session.commit()
                    response_text = "✅ Ценность сохранена!"
                    await client_ai.submit_result(client_ai.thread.id,client_ai.run.id,True,tool_call.id)
                else:
                    response_text = "🚫 Некорректное описание. Попробуйте снова."
                    await client_ai.submit_result(client_ai.thread.id, client_ai.run.id, False,tool_call.id)

                if not is_voice:
                    return response_text

            else:
                response_text = result["response"]

            if is_voice:
                speech_path = f"speech_{generate_unique_name()}.mp3"

                response = await client_ai.client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=response_text
                )

                response.stream_to_file(speech_path)

                with open(speech_path, "rb") as audio_file:
                    audio = types.BufferedInputFile(
                        audio_file.read(),
                        filename="response.mp3"
                    )


    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await session.rollback()
        response_text = f"🚨 Ошибка: {str(e)}"

    finally:
        cleanup_files(audio_path, speech_path)
        return response_text,audio