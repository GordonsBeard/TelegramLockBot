import logging
import configparser
from datetime import datetime, timedelta

from telegram.ext import (Updater, CommandHandler, ConversationHandler,
                          RegexHandler, MessageHandler, Filters)
from telegram import (ReplyKeyboardMarkup)

from secret import token

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Configuration
config = configparser.ConfigParser()
config.read_file(open('config.ini'))

# Helper functions
def calculate_release_time(difficulty):
    start_time = datetime.today()
    
    if difficulty == 'Short':
        start_time = start_time + timedelta(hours=3)
    elif difficulty == 'Medium':
        start_time = start_time + timedelta(days=2)
    elif difficulty == 'Long':
        start_time = start_time + timedelta(weeks=1)

    return datetime.strftime(start_time, '[%b %d] @ %I:%M%p')

# lockme variables
DIFFICULTY, CONFIRM = range(2)

# Main functions
def start(bot, update):
    '''
        Show a welcome message and information about available commands.
    '''
    user = update.message.from_user

    # Welcome message / Help screen
    msg = 'Welcome to KeyholderBot.\n'
    msg += 'Please select from the following options:\n'
    msg += '(options in italics are still being worked on)\n\n'
    msg += '*>> %s*\n' % user.first_name
    msg += '/lockme - Decide how long you will be locked\n'
    msg += '_/timeleft - How long until you can unlock?\n_'
    msg += '_/unlockme - End your current lockup, after confirmation\n\n_'
    msg += '*>> Others*\n'
    msg += '_/vote @username - Display the voting options for a given user.\n_'
    msg += '_/rtd - Alter the time left for a random user.\n_'
    msg += '/list - List currently locked users.\n'

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown')

def lockme(bot, update):
    reply_keyboard = [['Short', 'Medium', 'Long']]

    bot.sendMessage(update.message.chat_id, 
                    text='How long should you stay locked up? \n'
                         '(type /cancel to end this at any time)',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, 
                                                     one_time_keyboard=True,
                                                     resize_keyboard=True))

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
                                                     one_time_keyboard=True,
                                                     resize_keyboard=True))

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
                             'You are not allowed to unlock until: *%s.*'
                               % ('END TIME'),
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
                    text='Sorry, I did not understand that. '
                         'Try typing /start for a list of commands.')

def main():
    updater = Updater(token)
    
    dp = updater.dispatcher

    # Handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('lockme', lockme)],
        states={
            DIFFICULTY: [RegexHandler('^(Short|Medium|Long)$', difficulty)],
            CONFIRM: [RegexHandler('^(Yes|No)$', confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    start_handler = CommandHandler('start', start)
    unknown_handler = MessageHandler([Filters.command], unknown)

    # Dispatcher adds
    dp.add_handler(start_handler)
    dp.add_handler(conv_handler)
    dp.add_handler(unknown_handler)

    # Log all errors
    dp.add_error_handler(error)

    # Start the bot
    updater.start_polling()

    # Keep the bot idle
    updater.idle()

if __name__ == '__main__':
    main()