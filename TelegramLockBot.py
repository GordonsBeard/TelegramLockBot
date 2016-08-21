import logging
import configparser
from datetime import datetime, timedelta

from telegram.ext import (Updater, CommandHandler, ConversationHandler,
                          RegexHandler, MessageHandler, Filters)
from telegram import (ReplyKeyboardMarkup)

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


# Main functions
def start(bot, update):
    """
        Show a welcome message and information about available commands.
    """
    user = update.message.from_user

    # Welcome message / help screen
    msg = '*Welcome to KeyholderBot*\n'
    msg += '*>>* Before using, please read the /notice *<<*\n\n'
    msg += 'Please select from the following options:\n'
    msg += '\n*>> %s*\n' % user.first_name
    msg += '/lockme - Decide how long you will be locked\n'
    #msg += '/timeleft - How long until you can unlock?\n'
    #msg += '/unlock - End your current lockup, after confirmation\n'
    msg += '*\n>> Others*\n'
    #msg += '/vote @username - Display the voting options for a given user.\n'
    #msg += '/rtd - Alter the time left for a random user.\n'
    #msg += '/list - List currently locked users.\n\n'
    

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown')

def notice(bot, update):
    """
        Displays a disclosure notice to the user, so they understand
        what information about them might be revelaed to others.
    """

    # Build message
    msg = '*Please Read*\n\n'
    msg += 'This bot is provided for entertainment purposes only. '
    msg += 'Any foolish actions or harm that come from the use of this bot '
    msg += ' are purely the fault of the end user.\n'
    msg += '*Do not listen to the bot above what your own body tells you.*\n\n'
    msg += 'By allowing this bot to set a lock time you agree to have your '
    msg += 'username displayed for anyone who wishes to know.\n'
    msg += 'By allowing public voting on your time you understand what the '
    msg += 'ramifications might be. (More users = bigger numbers!)\n\n'
    msg += 'This bot has *no* enforcement capabilities, and so this is all '
    msg += 'under the honor system. Because of this, please use /unlock if '
    msg += 'you wish to end your current lock-up, and keep the list of users '
    msg += 'accurate.\n\n'
    msg += 'Return to /start'

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown')

DIFFICULTY, CONFIRM, VOTING = range(3)

def lockme(bot, update):
    reply_keyboard = [['Short', 'Medium', 'Long']]

    msg = '*How long do you wish to stay locked up?*\n'
    msg += '(Use the buttons below, /cancel at any time)'

    bot.sendMessage(update.message.chat_id, 
                    text=msg,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, 
                                                     one_time_keyboard=True))
    return DIFFICULTY

def difficulty(bot, update):
    reply_keyboard = [['Yes', 'No']]

    endtime = calculate_release_time(update.message.text)

    msg = 'You wish to be locked up for a %s while?\n\n' % update.message.text.lower()
    msg += 'You wont be let allowed to unlock until [%s].\n\n' % endtime
    msg += '*Is this OK?* (last chance to back out)'

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                     one_time_keyboard=True))
    return CONFIRM

def confirm_lock(bot, update):
    reply_keyboard = [['Yes', 'No']]
    user = update.message.from_user

    if update.message.text == 'No':
        bot.sendMessage(update.message.chat_id,
                        text='Process canceled. Enjoy your freedom for now!')
        return ConversationHandler.END

    elif update.message.text == 'Yes':
        msg = 'Locked and confirmed.\n'
        msg += 'Release time: [%s]\n\n' % ('END TIME')
        msg += '*Would you like to enable public voting on your lockup time?\n\n*'
        msg += 'Other users would be able to add or remove time, depending on '
        msg += 'the length of your initial lockup.\n\n'
        msg += 'Short: -30 minutes / +1 hour\n'
        msg += 'Medium: -5 hours / +10 hours\n'
        msg += 'Long: -6 hours / +20 hours\n'

        bot.sendMessage(update.message.chat_id,
                        text=msg,
                        parse_mode='Markdown',
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                           one_time_keyboard=True))
        logger.info('User %s locked up. Release time: %s' 
                    % (user.first_name, 'END TIME'))
        return VOTING
        
    

def confirm_voting(bot, update):
    user = update.message.from_user

    if update.message.text == 'No':
        msg = 'The public shall not alter your unlock time.'
    elif update.message.text == 'Yes':
        msg = 'Users will now be able to add or remove time from your lockup '
        msg += 'by using the command "/vote @%s"' % user.username

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown')

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
    updater = Updater(token=config['DEFAULT']['token'])
    
    dp = updater.dispatcher

    # Handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('lockme', lockme)],
        states={
            DIFFICULTY: [RegexHandler('^(Short|Medium|Long)$', difficulty)],
            CONFIRM: [RegexHandler('^(Yes|No)$', confirm_lock)],
            VOTING: [RegexHandler('^(Yes|No)$', confirm_voting)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    start_handler = CommandHandler('start', start)
    notice_handler = CommandHandler('notice', notice)
    unknown_handler = MessageHandler([Filters.command], unknown)

    # Dispatcher adds
    dp.add_handler(start_handler)
    dp.add_handler(notice_handler)
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