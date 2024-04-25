from bot import db
from typing import Optional
from config import BOT_USERNAME
from pyrogram import Client, filters, emoji

from pyrogram.errors.exceptions.bad_request_400 import (
    MessageIdInvalid,
    MessageNotModified,
)
from pyrogram.types import (
    User,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ChosenInlineResult,
)

ANSWER_CALLBACK_QUERY_MAX_LENGTH = 200


@Client.on_inline_query()
async def answer_iq(_, iq: InlineQuery):
    query = iq.query
    split = query.split(" ", 1)
    if (
        query == ""
        or len(query) > ANSWER_CALLBACK_QUERY_MAX_LENGTH
        or (query.startswith("@") and len(split) == 1)
    ):
        title = f"{emoji.FIRE} Gizli mesajı yazın"
        content = (
            "**Daxili rejim vasitəsilə gizli mesajları göndərin**\n\n"
            f"İstifadəsi: `{BOT_USERNAME} [@username|@] mesaj`"
        )
        description = f"İstifadəsi: {BOT_USERNAME} [@username|@] mesaj"
        username = BOT_USERNAME.replace("@", "")
        button = InlineKeyboardButton(
            "Daha ətraflı", url=f"https://t.me/{username}?start=learn"
        )
    elif not query.startswith("@"):
        title = f"{emoji.EYE} Onu ilk açana bir dəfə gizli mesaj yazın."
        content = f"{emoji.EYE} Gizli Mesajı ilk açan oxuya bilər"
        description = f"{emoji.SHUSHING_FACE} {query}"
        button = InlineKeyboardButton(
            f"{emoji.EYE} Mesaja Bax", callback_data="show_whisper"
        )
    else:
        # Python 3.8+
        u_target = "anyone" if (x := split[0]) == "@" else x
        title = f"{emoji.LOCKED} Gizli Mesajı {u_target}"
        content = f"{emoji.LOCKED} Gizli Mesajı {u_target}"
        description = f"{emoji.SHUSHING_FACE} {split[1]}"
        button = InlineKeyboardButton(
            f"{emoji.LOCKED_WITH_KEY} Mesaja Bax", callback_data="show_whisper"
        )
    switch_pm_text = f"{emoji.INFORMATION} Gizli Mesajlarınızı necə göndərəcəyinizi öyrənin"
    switch_pm_parameter = "learn"
    await iq.answer(
        results=[
            InlineQueryResultArticle(
                title=title,
                input_message_content=InputTextMessageContent(content),
                description=description,
                thumb_url=WHISPER_ICON_URL,
                reply_markup=InlineKeyboardMarkup([[button]]),
            )
        ],
        switch_pm_text=switch_pm_text,
        switch_pm_parameter=switch_pm_parameter,
    )


@Client.on_chosen_inline_result()
async def chosen_inline_result(_, cir: ChosenInlineResult):
    query = cir.query
    if len(query) == 0:
        return
    split = query.split(" ", 1)
    len_split = len(split)
    if (
        len_split == 0
        or len(query) > ANSWER_CALLBACK_QUERY_MAX_LENGTH
        or (query.startswith("@") and len(split) < 1)
    ):
        return
    if len_split == 2 and query.startswith("@"):
        receiver_uname, text = split[0][1:] or "@", split[1]
    else:
        receiver_uname, text = None, query
    sender_uid = cir.from_user.id
    inline_message_id = cir.inline_message_id
    whisper_data = {
        "sender_uid": sender_uid,
        "receiver_uname": receiver_uname,
        "text": text,
    }
    return db.whispers.update_one(
        {"_id": inline_message_id}, {"$set": whisper_data}, upsert=True
    )


@Client.on_callback_query(filters.regex("^show_whisper$"))
async def answer_cq(_, cq: CallbackQuery):
    inline_message_id = cq.inline_message_id
    whisper = db.whispers.find_one({"_id": inline_message_id})
    if not whisper:
        try:
            await cq.answer("Can't find the whisper text", show_alert=True)
            await cq.edit_message_text(f"etibarsız gizli mesaj")
        except (MessageIdInvalid, MessageNotModified):
            pass
        return
    else:
        sender_uid = whisper["sender_uid"]
        receiver_uname: Optional[str] = whisper["receiver_uname"]
        whisper_text = whisper["text"]
        from_user: User = cq.from_user
        if (
            receiver_uname
            and from_user.username
            and from_user.username.lower() == receiver_uname.lower()
        ):
            await read_the_whisper(cq)
            return
        if from_user.id == sender_uid or receiver_uname == "@":
            await cq.answer(whisper_text, show_alert=True)
            return
        if not receiver_uname:
            await read_the_whisper(cq)
            return
        await cq.answer("Nə baxırsan? Bu mesaj sənin üçün deyil !", show_alert=True)


async def read_the_whisper(cq: CallbackQuery):
    inline_message_id = cq.inline_message_id
    whisper = db.whispers.find_one({"_id": inline_message_id})
    whisper_text = whisper["text"]
    await cq.answer(whisper_text, show_alert=True)
    receiver_uname: Optional[str] = whisper["receiver_uname"]
    from_user: User = cq.from_user
    user_mention = (
        f"{from_user.first_name} (@{from_user.username})"
        if from_user.username
        else from_user.mention
    )
    try:
        t_emoji = emoji.UNLOCKED if receiver_uname else emoji.EYES
        db.whispers.delete_one({"_id": inline_message_id})
        await cq.edit_message_text(f"{t_emoji} {user_mention} gizli mesajı oxuyun !")
    except (MessageIdInvalid, MessageNotModified):
        pass
