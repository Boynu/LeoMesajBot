import asyncio
import datetime
from bot import db
from config import BOT_USERNAME, WHISPER_ICON_URL, SUDO_USERS, CHAT_ID

from pyrogram import Client, filters, emoji, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.errors import FloodWait

LEARN_TEXT = f"""
    **Bu bot yalnız daxili rejimdə işləyir, istifadə nümunəsi
    Budur:
  
    - @username-ə gizli mesaj yazın
    `{BOT_USERNAME} @username gizli mesaj yazın.`
  
    - İstifadəçilərin dəfələrlə oxuya biləcəyi bir gizli mesaj yazın
    `{BOT_USERNAME} @username gizli mesaj yazın.`

    - İlk açana gizli mesaj göndərin.
    `{BOT_USERNAME} @username gizli mesaj yazın.`**"""

LEARN_REPLY_MARKUP = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Növbəti", callback_data="learn_next")]]
)

DEFAULT_TEXT = (
    "**Salam 👋 Mən Qruplar üçün yaradılmış**"
    "**bir gizli mesaj botuyam.**"
    "**Mənim sayəmdə qruplarda**"
    "**Dostlarınıza gizli mesaj**"
    "**göndərə bilərsiniz.\n\n**"
    "**Botun istifadəsi üçün**"
    "**/help kommandını istifadə edə bilərsiniz.**"
)
DEFAULT_REPLY_MARKUP = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Məni Qrupunuza Əlavə edin", url="https://t.me/LeoMesajBot?startgroup=true"),
            InlineKeyboardButton(
                "Məndən İstifadə edin", switch_inline_query_current_chat=""
            ),
        ],
        [InlineKeyboardButton("Mənim Mesajlarım", callback_data="list_whispers")],
    ]
)


def new_user(id):
    return dict(id=id, join_date=datetime.date.today().isoformat())


async def add_user(id):
    user = new_user(id)
    return db.users.insert_one(user)


async def is_user_exist(id):
    user = db.users.find_one({"id": id})
    return True if user else False


async def get_all_users():
    users = db.users.distinct("id")
    return users


@Client.on_message(
    filters.text
    & filters.private
    & filters.incoming
    & filters.command(["start", "help"])
)
async def command_start(client, m: Message):
    if len(m.command) == 2 and m.command[1] == "learn":
        text_start = LEARN_TEXT
        reply_markup = LEARN_REPLY_MARKUP
    elif m.text == "/help":
        text_start = LEARN_TEXT
        reply_markup = LEARN_REPLY_MARKUP
    else:
        text_start = DEFAULT_TEXT
        reply_markup = DEFAULT_REPLY_MARKUP
        if not await is_user_exist(m.from_user.id):
            await add_user(m.from_user.id)
            await client.send_message(
                chat_id=CHAT_ID,
                text=f"#YENİ_İSMARİC: \n\nİstifadəçi:- [{m.from_user.first_name}](tg://user?id={m.from_user.id})\nVaxtı:- `{datetime.date.today().isoformat()}`",
                parse_mode=enums.ParseMode.MARKDOWN,
            )
    await m.reply_photo(
        WHISPER_ICON_URL,
        caption=text_start,
        reply_markup=reply_markup,
    )


@Client.on_callback_query(filters.regex("^(learn_next|start)$"))
async def show_main_page(_, cq: CallbackQuery):
    await cq.edit_message_text(
        text=DEFAULT_TEXT,
        disable_web_page_preview=True,
        reply_markup=DEFAULT_REPLY_MARKUP,
    )
    await cq.answer(
        f"{emoji.ROBOT} İndi siz onu daxili rejimdə sınaya bilərsiniz"
        if cq.data == "learn_next"
        else None
    )


@Client.on_callback_query(filters.regex("^list_whispers$"))
async def list_whispers(_, cq: CallbackQuery):
    user_id = cq.from_user.id
    user_whispers_count = db.whispers.count_documents({"sender_uid": user_id})
    if user_whispers_count == 0:
        text = "Sənin heç bir gizli mesajın yoxdur"
    else:
        text = f"{user_whispers_count} gizli mesajlarınız var"

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{emoji.WASTEBASKET}  Gizli Mesajlarımı Sil",
                    callback_data="delete_my_whispers",
                )
            ],
            [
                InlineKeyboardButton(
                    f"{emoji.BACK_ARROW}  Geri", callback_data="start"
                )
            ],
        ]
    )

    await cq.edit_message_text(text=text, reply_markup=reply_markup)
    await cq.answer()


@Client.on_callback_query(filters.regex("^delete_my_whispers$"))
async def delete_my_whispers(_, cq: CallbackQuery):
    user_id = cq.from_user.id
    deleted_whispers = db.whispers.count_documents({"sender_uid": user_id})
    db.whispers.delete_many({"sender_uid": user_id})
    if not deleted_whispers:
        await cq.answer("You don't have any whispers")
    else:
        await cq.answer(f"{deleted_whispers} gizli mesaj silindi")
        utcnow = datetime.datetime.utcnow().strftime("%F %T")
        await cq.edit_message_text(
            f"f"Sizin Gizli Mesajlarınız silindi `{utcnow}`",
            reply_markup=cq.message.reply_markup,
        )


@Client.on_message(filters.command("broadcast") & filters.user(SUDO_USERS))
async def broadcast_message(client, message):
    chat = message.chat
    from_user = message.from_user
    reply_message = message.reply_to_message
    if not reply_message:
        return await message.reply_text(
            "**You need to reply to a text message to Broadcasted it.**"
        )
    sleep_time = 0.1

    if reply_message.text:
        text = reply_message.text.markdown
    else:
        return await message.reply_text("You can only Broadcast text messages.")

    reply_markup = None
    if reply_message.reply_markup:
        reply_markup = InlineKeyboardMarkup(reply_message.reply_markup.inline_keyboard)
    sent = 0
    chats = await get_all_users()
    m = await message.reply_text(
        f"Broadcast in progress, will take {len(chats) * sleep_time} seconds."
    )
    for i in chats:
        try:
            await client.send_message(
                i,
                text=text,
                reply_markup=reply_markup,
            )
            sent += 1
            await asyncio.sleep(sleep_time)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception as e:
            print(e)
            pass
    await m.edit(f"**Broadcasted Message In {sent} Chats.**")
    
