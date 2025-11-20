import os
import logging
import httpx
from typing import Optional
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from PyPDF2 import PdfReader
from docx import Document
import io


logging.basicConfig(
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


app = FastAPI()
telegram_app: Application = None


async def summarize_with_deepseek(text: str) -> str:
headers = {
"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
"Content-Type": "application/json"
}


payload = {
"model": "deepseek-chat",
"messages": [
{"role": "system", "content": "أنت مساعد متخصص في تلخيص النصوص."},
{"role": "user", "content": text}
],
"temperature": 0.7,
"max_tokens": 2000
}


try:
async with httpx.AsyncClient(timeout=30.0) as client:
response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
response.raise_for_status()
result = response.json()
return result['choices'][0]['message']['content']


except Exception as e:
logger.error(f"DeepSeek API Error: {e}")
return "❌ حدث خطأ أثناء الاتصال بخدمة التلخيص."




def extract_text_from_pdf(file_content: bytes) -> Optional[str]:
try:
pdf_file = io.BytesIO(file_content)
pdf_reader = PdfReader(pdf_file)
text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
return text.strip() if text else None
except:
return None




def extract_text_from_docx(file_content: bytes) -> Optional[str]:
try:
doc = Document(io.BytesIO(file_content))
text = "\n".join(p.text for p in doc.paragraphs)
return text.strip()
except:
return None




async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("أهلاً! أرسل نص أو PDF أو DOCX لألخصه لك.")




async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("أرسل أي نص أو ملف وسأقوم بالتلخيص.")




async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
await update.message.reply_text("⏳ جارٍ التلخيص...")
summary = await summarize_with_deepseek(text)
await update.message.reply_text(summary)




async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
doc = update.message.document
file = await context.bot.get_file(doc.file_id)
file_content = await file.download_as_bytearray()


extracted = None


if doc.file_name.endswith('.pdf'):
logger.info("🚀 Webhook Registered Successfully!")
