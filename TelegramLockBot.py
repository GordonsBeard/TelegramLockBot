import logging
import configparser
from datetime import datetime, timedelta

import redis
from telegram.ext import (Updater, CommandHandler, ConversationHandler,
                          RegexHandler, MessageHandler, Filters)
from telegram import (ReplyKeyboardMarkup)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Configuration
config = configparser.ConfigParser()
config.read_file(open('config.ini'))

# Database
db = redis.StrictRedis()


# Helper functions
def calculate_release_time(difficulty):
    """
        Turns "Easy", "Medium", "Hard" into actual times.
    """
    SHORT, MEDIUM, LONG = (3, 12, 24)
    start_time = datetime.today()

    if difficulty == 'Short':
        start_time = start_time + timedelta(hours=SHORT)
    elif difficulty == 'Medium':
        start_time = start_time + timedelta(hours=MEDIUM)
    elif difficulty == 'Long':
        start_time = start_time + timedelta(hours=LONG)

    return start_time

def remove_lockup(user):
    """
        Takes a given username and removes all lockup related DB entries.
    """
    user_key = 'user:{0}'.format(user.username)

    db.hdel(user_key, 'starttime')
    db.hdel(user_key, 'difficulty')
    db.hdel(user_key, 'endtime')
    db.hdel(user_key, 'voting')

# Main functions
def start(bot, update):
    """
        Show a welcome message and information about available commands.
    """
    # Get user information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)
    accepted_notice = db.hget(user_key, 'notice')
    is_locked = db.hexists(user_key, 'endtime')

    # Welcome message
    msg = '*Welcome to KeyholderBot*\n'

    # If user has not agreed to /notice, inform them.
    if not accepted_notice:
        msg += '*>>* Before using, please read the /notice *<<*\n\n'

    # Rest of main menu
    msg += 'Please select from the following options:\n'
    msg += '\n*>> %s*\n' % user.first_name

    # Display contents based on locked status
    if not is_locked:
        msg += '/lockme - Decide how long you will be locked\n'
    elif is_locked:
        msg += '/timeleft - How long until you can unlock?\n'
        msg += '/unlock - End your current lockup, after confirmation\n'
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
    msg += ' are purely the fault of the end user.\n\n'
    msg += '*Do not listen to the bot above what your own body tells you.*'
    msg += '\n\n'
    msg += 'This bot has *no* enforcement capabilities, and so this is all '
    msg += 'under the honor system. Because of this, please use /unlock if '
    msg += 'you wish to end your current lock-up, and keep the list of users '
    msg += 'accurate.'
    msg += '\n\n'
    msg += '_PRIVACY NOTE_\n'
    msg += '- By allowing this bot to set a lock time you agree to have your '
    msg += 'username displayed for anyone who wishes to know.\n\n'
    msg += '- By allowing public voting on your time you understand what the '
    msg += 'ramifications might be. (More users = bigger numbers!)\n\n'
    msg += 'If you agree to this please type /agree (required before locking)'
    msg += '\n\n'
    msg += 'Return to /start'

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown')

def agree(bot, update):
    """
        Confirms a user has agreed to the /notice.
    """
    user = update.message.from_user

    msg = 'Thank you for agreeing to these terms.\n'
    msg += 'You may now begin a lockup process with the /lockme command'

    # Set the notice flag on the user's account
    db.hset('user:{0}'.format(user.username), 'notice', 'True')

    bot.sendMessage(update.message.chat_id,
                    text=msg)
    

DIFFICULTY, CONFIRM, VOTING, UNLOCKED = range(4)

def lockme(bot, update):
    """
        Initial screen for the lockup conversation.
        Decide the length/difficulty.
    """
    # Get user information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)
    accepted_notice = db.hexists(user_key, 'notice')
    is_locked = db.hexists(user_key, 'endtime')

    # If user has not accepted notice, stop conversation
    if not accepted_notice:
        msg = 'You have not agreed to the /notice '
        msg += 'Lockup cannot proceed until you agree to the terms.'
        bot.sendMessage(update.message.chat_id,
                        text=msg)
        return

    # If user has a lockup time, stop the conversation
    if is_locked:
        msg = '*You are already locked up!*\n\n'
        msg += 'If you would like to end this, please use /unlock\n'
        msg += 'Otherwise, you can use /timeleft to see the amount of '
        msg += 'time left on your current session.'

        bot.sendMessage(update.message.chat_id,
                        text=msg,
                        parse_mode='Markdown')
        return

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
    """
        Confirm the difficulty selected, last chance to back out 
        of the lock confirmation.
    """
    reply_keyboard = [['Yes', 'No']]

    # Calculate endtime
    endtime = calculate_release_time(update.message.text)

    # User information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)

    # Store difficulty track
    db.hset(user_key, 'difficulty', update.message.text)

    # Store the start/endtime
    db.hset(user_key, 'endtime', endtime)
    db.hset(user_key, 'starttime', datetime.today())

    msg = 'You wish to be locked up for a %s while?\n\n' % update.message.text.lower()
    msg += 'You wont be let allowed to unlock until [%s].\n\n' % datetime.strftime(endtime, '[%b %d] @ %I:%M%p')
    msg += '*Is this OK?* (last chance to back out)'

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                     one_time_keyboard=True))
    return CONFIRM

def confirm_lock(bot, update):
    """
        Display the confirmation of time, ask user if they wish to 
        allow public voting on their time.
    """
    reply_keyboard = [['Yes', 'No']]

    # User information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)

    # User canceled process
    if update.message.text == 'No':
        db.hdel(user_key, 'starttime')
        db.hdel(user_key, 'difficulty')
        db.hdel(user_key, 'endtime')

        bot.sendMessage(update.message.chat_id,
                        text='Process canceled. Enjoy your freedom for now!')
        return ConversationHandler.END

    # User has agreed to the lockup
    elif update.message.text == 'Yes':
        starttime, endtime, difficulty = db.hmget(user_key,
                        'starttime', 'endtime', 'difficulty')

        # Build message and ask about public voting
        msg = 'Locked and confirmed.\n'
        msg += 'Release time: [%s]\n\n' % (endtime)
        msg += '*Would you like to enable public voting on your lockup time?*'
        msg += '\n\n'
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
        logger.info('User [%s] locked up for a [%s] Release time: [%s]' 
                    % (user.first_name, difficulty, endtime))
        return VOTING
        
def confirm_voting(bot, update):
    """
        Confirm the public vote option, display final information about
        time locked up. Also will include information on how to vote if
        applicable.
    """
    # User information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)

    if update.message.text == 'No':
        db.hset(user_key, 'voting', 'False')
        msg = 'The public shall not alter your unlock time.'
    elif update.message.text == 'Yes':
        db.hset(user_key, 'voting', 'True')
        msg = 'Users will now be able to add or remove time from your lockup '
        msg += 'by using the command "/vote @%s"' % user.username

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown')

    return ConversationHandler.END

def timeleft(bot, update):
    """
        Displays a user current time left/unlock date.
    """
    # User information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)
    is_locked = db.hexists(user_key, 'endtime')
    
    if not is_locked:
        msg = 'You are not locked up!\n'
        msg += 'Please use /lockme if you wish to start a timer.'
        bot.sendMessage(update.message.chat_id,
                        text=msg)
    else:
        endtime = db.hget(user_key, 'endtime')
        msg = 'Your current unlock date is *{0}*'.format(endtime)

        bot.sendMessage(update.message.chat_id,
                        text=msg,
                        parse_mode='Markdown')
    return

def unlock(bot, update):
    """
        Allows a user to unlock.
    """
    # TODO track early unlocks
    # TODO track successful lockups

    # User information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)
    is_locked = db.hexists(user_key, 'endtime')
    
    if not is_locked:
        msg = 'You are not currently locked.'
        bot.sendMessage(update.message.chat_id,
                        text=msg)
        return
    
    reply_keyboard = [['Yes', 'No']]

    msg = '*Would you like to unlock?*\n\n'
    msg += 'This will remove you from the list of locked users. You are free '
    msg += 'to use /lockme again once unlocking.'

    bot.sendMessage(update.message.chat_id,
                    text=msg,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                      one_time_keyboard=True))
    
    return UNLOCKED

def unlocked(bot, update):
    """
        Confirms users unlocking or aborting of unlocking.
    """
    # User information
    user = update.message.from_user
    user_key = 'user:{0}'.format(user.username)
    endtime = db.hget(user_key, 'endtime')

    if update.message.text == 'No':
        msg = 'Good. Your unlock date is still set for *%s*.' % endtime
        bot.sendMessage(update.message.chat_id,
                        text=msg,
                        parse_mode='Markdown')

    elif update.message.text == 'Yes':
        msg = 'Over so soon?\n'
        msg += 'You have been *unlocked* and removed from the list of '
        msg += 'currently locked users. Enjoy your freedom!'

        # Remove DB entries
        remove_lockup(user)
        logging.info('User %s unlocked.' % user.first_name)

        bot.sendMessage(update.message.chat_id,
                        text=msg,
                        parse_mode='Markdown')
        
    return ConversationHandler.END

def cancel(bot, update):
    """
        Cancels the lockme/unlock conversation, will remove any db entry.
    """
    # User information
    user = update.message.from_user

    # Remove ANY database entries that were created during lockme convo
    remove_lockup(user)

    bot.sendMessage(update.message.chat_id,
                    text='Process canceled.')

    return ConversationHandler.END

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def unknown(bot, update):
    """
        Fallback behavior if unknown command is issued.
    """
    bot.sendMessage(chat_id=update.message.chat_id,
                    text='Sorry, I did not understand that. '
                         'Try typing /start for a list of commands.')

def main():
    # Load up the bot
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
    unlock_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('unlock', unlock)],
        states={
            UNLOCKED: [RegexHandler('^(Yes|No)$', unlocked)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    start_handler = CommandHandler('start', start)
    notice_handler = CommandHandler('notice', notice)
    agree_handler = CommandHandler('agree', agree)
    timeleft_handler = CommandHandler('timeleft', timeleft)
    unknown_handler = MessageHandler([Filters.command], unknown)

    # Dispatcher
    dp.add_handler(start_handler)
    dp.add_handler(notice_handler)
    dp.add_handler(conv_handler)
    dp.add_handler(unlock_conv_handler)
    dp.add_handler(timeleft_handler)
    dp.add_handler(agree_handler)
    dp.add_handler(unknown_handler)
    dp.add_error_handler(error)

    # Start the bot, keep it idle until stopped
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()