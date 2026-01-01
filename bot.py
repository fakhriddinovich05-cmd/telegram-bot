from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import pandas as pd
from datetime import datetime
import os
import re


ADMIN_ID = 1973982768  # O‘zingizning Telegram ID

# ======================================================
# 1. EXCEL'DAN JAVOBLARNI O‘QISH
# ======================================================
def load_answers():
    df = pd.read_excel("answers.xlsx")
    df.columns = [str(c).strip() for c in df.columns]

    book_answers = {}

    for _, row in df.iterrows():
        book = str(row["book"]).strip()
        book_answers[book] = {}

        for col in df.columns:
            if col == "book":
                continue
            if pd.isna(row[col]):
                continue

            q = int(col)
            ans = str(row[col]).strip().lower()
            book_answers[book][q] = ans

    return book_answers


BOOK_ANSWERS = load_answers()

# ======================================================
# 2. NATIJANI EXCELGA YOZISH
# ======================================================
def save_result_to_excel(name, book, correct, total, percent, grade, wrong):
    filename = "results.xlsx"

    row = {
        "Sana": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Ism-familiya": name,
        "Kitob": book,
        "To‘g‘ri": correct,
        "Jami": total,
        "Foiz": percent,
        "Baho": grade,
        "Xato savollar": ", ".join(wrong) if wrong else "-"
    }

    if os.path.exists(filename):
        df = pd.read_excel(filename)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_excel(filename, index=False)

# ======================================================
# 3. MATNLAR
# ======================================================
TEXT = {
    "uz": {
        "lang": "Tilni tanlang:\n1️⃣ O‘zbekcha\n2️⃣ Русский",
        "name": "Ism-familiyangizni kiriting:",
        "book": "7 xonali kitob raqamini kiriting:",
        "book_error": "❌ Bunday kitob raqami topilmadi.\nQayta kiriting:",
        "answers": "Test javoblarini yuboring:\n\n1a2b3c4d...",
        "result": "📊 NATIJA",
        "correct": "To‘g‘ri",
        "percent": "Foiz",
        "grade": "Baho",
        "wrong": "Xato savollar",
        "again": "Yangi test uchun /start ni bosing"
    },
    "ru": {
        "lang": "Выберите язык:\n1️⃣ O‘zbekcha\n2️⃣ Русский",
        "name": "Введите имя и фамилию:",
        "book": "Введите 7-значный номер книги:",
        "book_error": "❌ Такой номер книги не найден.\nВведите заново:",
        "answers": "Отправьте ответы:\n\n1a2b3c4d...",
        "result": "📊 РЕЗУЛЬТАТ",
        "correct": "Правильно",
        "percent": "Процент",
        "grade": "Оценка",
        "wrong": "Ошибочные вопросы",
        "again": "Для нового теста нажмите /start"
    }
}

# ======================================================
# 4. BUYRUQLAR
# ======================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = "lang"
    await update.message.reply_text(TEXT["uz"]["lang"])


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    global BOOK_ANSWERS
    BOOK_ANSWERS = load_answers()
    await update.message.reply_text("✅ Excel bazasi yangilandi.")

# ======================================================
# 5. JAVOBLARNI PARSE QILISH
# ======================================================
def parse_answers(text):
    text = text.replace(" ", "").lower()
    matches = re.findall(r"(\d+)([a-z])", text)
    return {int(q): ans for q, ans in matches}


# ======================================================
# 6. ASOSIY MULOQOT
# ======================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    msg = update.message.text.strip()

    # --- TIL ---
    if step == "lang":
        if msg == "1":
            context.user_data["lang"] = "uz"
        elif msg == "2":
            context.user_data["lang"] = "ru"
        else:
            return

        context.user_data["step"] = "name"
        await update.message.reply_text(TEXT[context.user_data["lang"]]["name"])
        return

    lang = context.user_data.get("lang")
    if not lang:
        await update.message.reply_text("Avval /start buyrug‘ini bosing.")
        return

    # --- ISM ---
    if step == "name":
        context.user_data["name"] = msg
        context.user_data["step"] = "book"
        await update.message.reply_text(TEXT[lang]["book"])
        return

    # --- KITOB ---
    if step == "book":
        if msg not in BOOK_ANSWERS:
            await update.message.reply_text(TEXT[lang]["book_error"])
            return

        context.user_data["book"] = msg
        context.user_data["key"] = BOOK_ANSWERS[msg]
        context.user_data["step"] = "answers"
        await update.message.reply_text(TEXT[lang]["answers"])
        return

    # --- TEKSHIRISH ---
    if step == "answers":
        key = context.user_data["key"]
        user = parse_answers(msg)

        total = len(key)
        correct = 0
        wrong = []

        for q, ans in key.items():
            if user.get(q) == ans:
                correct += 1
            else:
                wrong.append(str(q))

        percent = round(correct / total * 100, 1)
        grade = 5 if percent >= 86 else 4 if percent >= 71 else 3 if percent >= 56 else 2

        save_result_to_excel(
            context.user_data["name"],
            context.user_data["book"],
            correct,
            total,
            percent,
            grade,
            wrong
        )

        result = (
            f"👤 {context.user_data['name']}\n"
            f"📘 Kitob: {context.user_data['book']}\n\n"
            f"{TEXT[lang]['result']}:\n"
            f"{TEXT[lang]['correct']}: {correct}/{total}\n"
            f"{TEXT[lang]['percent']}: {percent}%\n"
            f"{TEXT[lang]['grade']}: {grade}\n"
        )

        if wrong:
            result += f"{TEXT[lang]['wrong']}: " + ", ".join(wrong)

        result += f"\n\n{TEXT[lang]['again']}"

        await update.message.reply_text(result)
        context.user_data.clear()

# ======================================================
# 7. BOTNI ISHGA TUSHIRISH
# ======================================================
app = ApplicationBuilder().token("8513329519:AAEXv1pcnFmvHJ8eRNaINkzDk-onpTtG8lI").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reload", reload_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling(drop_pending_updates=True)
