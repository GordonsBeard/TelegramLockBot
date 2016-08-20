#!/usr/bin/env python

import logging
from datetime import datetime, timedelta

from telegram.ext import (Updater, CommandHandler, ConversationHandler,
                          RegexHandler, MessageHandler, InlineQueryHandler,
                          Filters)
from telegram import (ReplyKeyboardMarkup, InlineQueryResultArticle,
                      InputTextMessageContent)

from secret import token

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

DIFFICULTY, CONFIRM = range(2)


# Helper functions
def calculate_release_time(difficulty):
    start_time = datetime.today()
    
    if difficulty == 'Short':
        start_time = start_time + timedelta(hours=3)
    elif difficulty == 'Medium':
        start_time = start_time + timedelta(days=2)
    elif difficulty == 'Long':
        start_time = start_time + timedelta(weeks=1)

    return datetime.strftime(start_time, "[%b %d] @ %I:%M%p")


# Main functions
def start(bot, update):
    reply_keyboard = [['Short', 'Medium', 'Long']]

    bot.sendMessage(update.message.chat_id, 
                    text='Welcome to LockBot. I do not seem to know you yet. '
                         'How long should you stay locked up? \n'
                         '(type /cancel to end this at any time)',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, 
                                                     one_time_keyboard=True))

    return DIFFICULTY

def difficulty(bot, update):
    reply_keyboard = [['Yes', 'No']]

    endtime = calculate_release_time(update.message.text)

    if endtime is None:
        logger.warn('Update "%s" caused None endtime.' & update.message.text)
        return ConversationHandler.END

    bot.sendMessage(update.message.chat_id,
                    text='You will be locked up for a %s while. '
                         'Your release will be *%s*, '
                         'is this alright with you? ' 
                            % (update.message.text.lower(), endtime),
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                     one_time_keyboard=True))

    return CONFIRM

def confirm(bot, update):
    user = update.message.from_user

    if update.message.text == 'No':
        bot.sendMessage(update.message.chat_id,
                        text='Process canceled. Enjoy your freedom for now!')
        return ConversationHandler.END

    elif update.message.text == 'Yes':
        bot.sendMessage(update.message.chat_id,
                        text='Locked and confirmed. '
                             'You are not allowed to uncage until: *%s.*'
                               % ("END TIME"),
                        parse_mode='Markdown')

        logger.info('User %s locked up. Release time: %s' % (user.first_name, 
                                                       'END TIME'))

    return ConversationHandler.END

def cancel(bot, update):
    user = update.message.from_user
    logger.info('User %s canceled the conversation.' % user.first_name)
    bot.sendMessage(update.message.chat_id,
                    text='Process canceled.')

    return ConversationHandler.END

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id,
                    text='Sorry, I did not understand that command. '
                         'Try typing /start to begin your chastity session.')

def list_locked_users(bot, update):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query,
            title='List Locked Users',
            input_message_content=InputTextMessageContent('1. lizard')
        )
    )
    bot.answerInlineQuery(update.inline_query.id, results=results)


def main():
    updater = Updater(token)
    
    dp = updater.dispatcher

    # Handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            DIFFICULTY: [RegexHandler('^(Short|Medium|Long)$', difficulty)],

            CONFIRM: [RegexHandler('^(Yes|No)$', confirm)],

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    unknown_handler = MessageHandler([Filters.command], unknown)
    inline_list_users_handler = InlineQueryHandler(list_locked_users)

    dp.add_handler(conv_handler)
    dp.add_handler(inline_list_users_handler)
    dp.add_handler(unknown_handler)

    # Log all errors
    dp.add_error_handler(error)

    # Start the bot
    updater.start_polling()

    # Keep the bot idle
    updater.idle()

if __name__ == '__main__':
    main()