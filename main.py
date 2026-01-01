from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from config import BOT_TOKEN, ADMIN_ID, SUB_DAYS
import db

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    db.add_user(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username
    )
    await message.answer(
        "Assalomu alaykum! 🎬\n"
        "Bu bot oylik obuna asosida ishlaydi.\n\n"
        "📅 Obuna muddati: 30 kun\n\n"
        "❗ Hozircha sizda aktiv obuna yo‘q.\n\n"
        "To‘lov qilib, chekni shu yerga yuboring."
    )


@dp.message(F.photo)
async def check_handler(message: Message):
    user = db.get_user(message.from_user.id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Tasdiqlayman",
            callback_data=f"confirm_{message.from_user.id}"
        )]
    ])

    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=(
            "💳 TO‘LOV CHEK\n\n"
            f"👤 Ism: {message.from_user.full_name}\n"
            f"🔗 Username: @{message.from_user.username}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📅 Muddat: 30 kun"
        ),
        reply_markup=kb
    )

    await message.answer("⏳ Chek adminga yuborildi. Tasdiq kutilmoqda.")


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm(callback):
    user_id = int(callback.data.split("_")[1])
    db.activate_sub(user_id, SUB_DAYS)

    await bot.send_message(
        user_id,
        "✅ To‘lov tasdiqlandi.\n"
        "📅 Obunangiz 30 kunga aktiv."
    )

    await callback.message.answer("✅ Obuna faollashtirildi")
    await callback.answer()


@dp.message()
async def movie_request(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user[3] != "Active":
        await message.answer("❌ Sizda aktiv obuna yo‘q.")
        return

    await message.answer("🎬 Kino qidirish hali qo‘shilmagan (keyingi bosqich).")


if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
