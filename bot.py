from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from dotenv import load_dotenv
import os
import sqlite3

# Load variables from .env file
load_dotenv()

# Retrieve variables
TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = os.getenv('CHANNEL_ID')

GENDER, LANGUAGE, INTEREST = range(3)

def create_connection():
    return sqlite3.connect("chatbot.db")

def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id == ADMIN_ID:
        update.message.reply_text("Welcome Admin!")
    else:
        reply_keyboard = [['Male', 'Female']]
        update.message.reply_text(
            'Hi! Please choose your gender:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
    return GENDER

def gender(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    gender = update.message.text

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute('REPLACE INTO users (user_id, gender) VALUES (?, ?)', (user.id, gender))
    connection.commit()
    connection.close()

    reply_keyboard = [['English', 'Indonesian']]
    update.message.reply_text(
        'Please choose your language:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return LANGUAGE

def language(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    language = update.message.text

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user.id))
    connection.commit()
    connection.close()

    update.message.reply_text(
        "Please tell us your interests (e.g., sports, music, reading):"
    )
    return INTEREST

def interest(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    interest = update.message.text

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute('UPDATE users SET interest = ? WHERE user_id = ?', (interest, user.id))
    connection.commit()
    connection.close()

    # Find partner automatically after registration
    match_user(user.id, interest, user.gender, update, context)

    return ConversationHandler.END

def find_partner(user_id, user_gender, user_interest):
    connection = create_connection()
    cursor = connection.cursor()

    opposite_gender = 'Female' if user_gender == 'Male' else 'Male'

    cursor.execute(
        'SELECT user_id FROM users WHERE gender = ? AND interest = ? AND user_id != ?',
        (opposite_gender, user_interest, user_id)
    )
    partner = cursor.fetchone()
    connection.close()

    return partner[0] if partner else None

def match_user(user_id, user_interest, user_gender, update: Update, context: CallbackContext):
    partner_id = find_partner(user_id, user_gender, user_interest)

    if partner_id:
        context.user_data[user_id] = {'partner': partner_id}
        context.user_data[partner_id] = {'partner': user_id}
        context.bot.send_message(chat_id=partner_id, text="You are now chatting with someone!")
        update.message.reply_text("You are now chatting with someone!")
    else:
        update.message.reply_text("Waiting for someone to chat with...")

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in context.user_data and 'partner' in context.user_data[user_id]:
        partner_id = context.user_data[user_id]['partner']
        context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        update.message.reply_text("Please register first by typing /start.")

def cancel(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Registration canceled.')
    return ConversationHandler.END

def broadcast(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id != ADMIN_ID:
        update.message.reply_text("You are not authorized to use this command.")
        return

    message = ' '.join(context.args)
    if not message:
        update.message.reply_text("Please provide a message to broadcast.")
        return

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    connection.close()

    for (user_id,) in users:
        context.bot.send_message(chat_id=user_id, text=message)

    update.message.reply_text("Message sent to all users.")

def channel_post(update: Update, context: CallbackContext) -> None:
    channel_message = update.channel_post.text
    if not channel_message:
        return

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    connection.close()

    for (user_id,) in users:
        context.bot.send_message(chat_id=user_id, text=channel_message)

def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(Filters.text & ~Filters.command, gender)],
            LANGUAGE: [MessageHandler(Filters.text & ~Filters.command, language)],
            INTEREST: [MessageHandler(Filters.text & ~Filters.command, interest)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("broadcast", broadcast, Filters.user(user_id=ADMIN_ID)))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.chat(CHANNEL_ID), channel_post))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()