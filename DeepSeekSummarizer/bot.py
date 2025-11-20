import os
import logging
import httpx
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PyPDF2 import PdfReader
from docx import Document
import io



try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv غير مثبت، سيتم قراءة المتغيرات من البيئة مباشرة



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

async def summarize_with_deepseek(text: str) -> str:
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "أنت مساعد ذكي متخصص في تلخيص النصوص. قم بتلخيص النص المقدم بشكل واضح ومختصر."
            },
            {
                "role": "user",
                "content": f"الرجاء تلخيص النص التالي:\n\n{text}"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            summary = result['choices'][0]['message']['content']
            return summary
    except httpx.TimeoutException:
        logger.error("DeepSeek API timeout")
        return "⏱️ عذراً، استغرق التلخيص وقتاً طويلاً. الرجاء المحاولة مرة أخرى بنص أقصر."
    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP error: {e}")
        if e.response.status_code == 401:
            return "🔑 عذراً، هناك مشكلة في مفتاح DeepSeek API. الرجاء التواصل مع مدير البوت."
        elif e.response.status_code == 429:
            return "⏳ عذراً، تم تجاوز حد الطلبات. الرجاء الانتظار قليلاً والمحاولة مرة أخرى."
        else:
            return f"❌ عذراً، حدث خطأ في الخدمة (رمز الخطأ: {e.response.status_code}). الرجاء المحاولة لاحقاً."
    except httpx.ConnectError:
        logger.error("DeepSeek API connection error")
        return "🌐 عذراً، لا يمكن الاتصال بخدمة التلخيص. الرجاء التحقق من الاتصال بالإنترنت."
    except KeyError as e:
        logger.error(f"DeepSeek API response format error: {e}")
        return "📋 عذراً، تلقينا رداً غير متوقع من خدمة التلخيص. الرجاء المحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"Unexpected error calling DeepSeek API: {e}")
        return "❌ عذراً، حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى."

def extract_text_from_pdf(file_content: bytes) -> Optional[str]:
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return None

def extract_text_from_docx(file_content: bytes) -> Optional[str]:
    try:
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting DOCX: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = """
مرحباً! 👋

أنا بوت تلخيص النصوص باستخدام DeepSeek AI

يمكنني مساعدتك في:
📝 تلخيص النصوص المباشرة
📄 تلخيص ملفات PDF
📋 تلخيص ملفات Word (DOCX)

كيفية الاستخدام:
1️⃣ أرسل لي نصاً مباشرة وسأقوم بتلخيصه
2️⃣ أرسل لي ملف PDF أو Word وسأقوم باستخراج النص وتلخيصه

جرب الآن! 🚀
"""
    if update.message:
        await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = """
📖 المساعدة - كيفية استخدام البوت

✅ لتلخيص نص:
   - أرسل النص مباشرة في الرسالة

✅ لتلخيص ملف PDF:
   - أرسل الملف كمرفق (PDF)

✅ لتلخيص ملف Word:
   - أرسل الملف كمرفق (DOCX)

⚠️ ملاحظات:
- تأكد من أن النص أو الملف يحتوي على محتوى قابل للقراءة
- قد يستغرق التلخيص بضع ثوانٍ حسب طول النص

للأسئلة أو المساعدة، استخدم الأمر /help
"""
    if update.message:
        await update.message.reply_text(help_message)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    
    user_text = update.message.text
    
    if not user_text or len(user_text.strip()) < 10:
        await update.message.reply_text("⚠️ الرجاء إرسال نص كافٍ للتلخيص (على الأقل 10 أحرف)")
        return
    
    await update.message.reply_text("⏳ جارٍ التلخيص... الرجاء الانتظار")
    
    summary = await summarize_with_deepseek(user_text)
    
    await update.message.reply_text(f"📝 ملخص النص:\n\n{summary}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document:
        return
    
    document = update.message.document
    file_name = document.file_name
    
    if not file_name:
        await update.message.reply_text("⚠️ لم أتمكن من التعرف على اسم الملف")
        return
    
    file_name_lower = file_name.lower()
    
    if not (file_name_lower.endswith('.pdf') or file_name_lower.endswith('.docx')):
        await update.message.reply_text("⚠️ عذراً، أدعم فقط ملفات PDF و Word (DOCX)\n\nملاحظة: ملفات .doc القديمة غير مدعومة، الرجاء تحويلها إلى .docx")
        return
    
    try:
        await update.message.reply_text("📥 جارٍ تحميل الملف...")
        
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        await update.message.reply_text("🔍 جارٍ استخراج النص من الملف...")
        
        extracted_text = None
        error_details = ""
        
        if file_name_lower.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(bytes(file_content))
            if not extracted_text:
                error_details = "تأكد من أن ملف PDF يحتوي على نص قابل للقراءة (وليس مجرد صور)"
        elif file_name_lower.endswith('.docx'):
            extracted_text = extract_text_from_docx(bytes(file_content))
            if not extracted_text:
                error_details = "تأكد من أن ملف Word يحتوي على نصوص وليس مجرد صور أو جداول فارغة"
        
        if not extracted_text:
            await update.message.reply_text(
                f"❌ عذراً، لم أتمكن من استخراج النص من الملف.\n\n{error_details}"
            )
            return
        
        if len(extracted_text.strip()) < 10:
            await update.message.reply_text("⚠️ الملف لا يحتوي على نص كافٍ للتلخيص (على الأقل 10 أحرف)")
            return
        
        await update.message.reply_text("⏳ جارٍ تلخيص المحتوى... الرجاء الانتظار")
        
        summary = await summarize_with_deepseek(extracted_text)
        
        await update.message.reply_text(f"📄 ملخص الملف ({file_name}):\n\n{summary}")
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ أثناء معالجة الملف: {str(e)}\n\nالرجاء المحاولة مرة أخرى أو إرسال ملف آخر."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء معالجة طلبك. الرجاء المحاولة مرة أخرى.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        error_msg = """
        ❌ ERROR: TELEGRAM_BOT_TOKEN not found in environment variables!
        
        Please set the TELEGRAM_BOT_TOKEN secret in Replit Secrets.
        You can get a bot token from @BotFather on Telegram.
        """
        logger.error(error_msg)
        print(error_msg)
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    
    if not DEEPSEEK_API_KEY:
        error_msg = """
        ❌ ERROR: DEEPSEEK_API_KEY not found in environment variables!
        
        Please set the DEEPSEEK_API_KEY secret in Replit Secrets.
        You can get an API key from https://platform.deepseek.com/
        """
        logger.error(error_msg)
        print(error_msg)
        raise ValueError("DEEPSEEK_API_KEY is required")
    
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        
        application.add_error_handler(error_handler)
        
        logger.info("Bot started successfully!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
