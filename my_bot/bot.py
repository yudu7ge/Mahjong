import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import get_user_by_telegram_id, create_user, get_user_by_invite_code, update_user_balance, add_game_history
from dotenv import load_dotenv
import uuid

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("在 .env 文件中未找到 BOT_TOKEN")

def create_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 开始游戏", callback_data='start_game')],
        [InlineKeyboardButton("💰 余额查询", callback_data='balance')],
        [InlineKeyboardButton("🔗 邀请码", callback_data='invite_code')],
        [InlineKeyboardButton("❓ 帮助", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if args and len(args) == 1:
        # 处理游戏邀请
        await join_game(update, context)
        return

    telegram_id = str(update.message.from_user.id)
    user = get_user_by_telegram_id(telegram_id)
    
    if user:
        await update.message.reply_text(
            f"欢迎回来，{user['username']}！您可以开始游戏了。",
            reply_markup=create_main_menu()
        )
    else:
        await update.message.reply_text("请输入邀请码完成注册，注册后可获得1000空投游戏币：")
        context.user_data['awaiting_invite_code'] = True

async def handle_invite_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'awaiting_invite_code' not in context.user_data or not context.user_data['awaiting_invite_code']:
        return

    telegram_id = str(update.message.from_user.id)
    username = update.message.from_user.username
    invite_code = update.message.text.strip().upper()

    inviter = get_user_by_invite_code(invite_code)
    
    if not inviter:
        await update.message.reply_text("邀请码无效，请重新输入。")
        return

    new_user = create_user(telegram_id, username, inviter['id'])
    if new_user:
        await update.message.reply_text(
            f"注册成功！您已通过 @{inviter['username']} 的邀请获得了1000游戏币。",
            reply_markup=create_main_menu()
        )
        context.user_data['awaiting_invite_code'] = False
    else:
        await update.message.reply_text("注册失败，请稍后重试或联系客服。")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'start_game':
        await start_game(update, context)
    elif query.data == 'balance':
        await check_balance(update, context)
    elif query.data == 'invite_code':
        await show_invite_code(update, context)
    elif query.data == 'help':
        await show_help(update, context)
    elif query.data == 'cancel_game':
        await cancel_game(update, context)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(str(update.effective_user.id))
    if user:
        await update.callback_query.edit_message_text(f"您当前的余额是: {user['balance']} 游戏币")
    else:
        await update.callback_query.edit_message_text("未找到您的账户信息，请先注册。")

async def show_invite_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(str(update.effective_user.id))
    if user:
        await update.callback_query.edit_message_text(f"您的邀请码是: {user['invite_code']}\n分享给朋友以获得奖励！")
    else:
        await update.callback_query.edit_message_text("未找到您的账户信息，请先注册。")

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "游戏规则和帮助：\n"
        "1. 注册后获得1000游戏币空投\n"
        "2. 在1v1挖矿中下注，赢家获得奖励\n"
        "3. 邀请朋友使用您的邀请码注册，获得额外奖励\n"
        "如需更多帮助，请联系客服。"
    )
    await update.callback_query.edit_message_text(help_text)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = get_user_by_telegram_id(str(query.from_user.id))
    
    if not user:
        await query.edit_message_text("请先注册后再开始游戏。")
        return

    context.user_data['game_state'] = 'awaiting_bet'
    await query.edit_message_text(
        "请输入您要下注的金额（必须是100的倍数，最小100，最大1000）：",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("取消", callback_data='cancel_game')]])
    )

async def process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(str(update.message.from_user.id))
    bet_amount = int(update.message.text)

    if bet_amount % 100 != 0 or bet_amount < 100 or bet_amount > 1000:
        await update.message.reply_text("下注金额必须是100的倍数，最小100，最大1000。请重新输入：")
        return

    if user['balance'] < bet_amount:
        await update.message.reply_text("余额不足，请重新输入较小的金额：")
        return

    context.user_data['bet_amount'] = bet_amount
    context.user_data['dice_count'] = 0
    context.user_data['total_score'] = 0
    context.user_data['game_state'] = 'rolling_dice'
    
    await update.message.reply_text("请发送骰子表情来进行游戏。您需要发送3次骰子。")

async def handle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'game_state' not in context.user_data or context.user_data['game_state'] != 'rolling_dice':
        return

    if 'dice_count' not in context.user_data or context.user_data['dice_count'] >= 3:
        return

    dice_value = update.message.dice.value
    context.user_data['total_score'] = context.user_data.get('total_score', 0) + dice_value
    context.user_data['dice_count'] = context.user_data.get('dice_count', 0) + 1
async def handle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'game_state' not in context.user_data or context.user_data['game_state'] != 'rolling_dice':
        return

    if 'dice_count' not in context.user_data or context.user_data['dice_count'] >= 3:
        return

    dice_value = update.message.dice.value
    context.user_data['total_score'] = context.user_data.get('total_score', 0) + dice_value
    context.user_data['dice_count'] = context.user_data.get('dice_count', 0) + 1

    if context.user_data['dice_count'] < 3:
        await update.message.reply_text(f"您的第 {context.user_data['dice_count']} 次骰子点数为 {dice_value}。还需要再投 {3 - context.user_data['dice_count']} 次骰子。")
    else:
        total_score = context.user_data['total_score']
        bet_amount = context.user_data['bet_amount']
        user = get_user_by_telegram_id(str(update.message.from_user.id))

        game_id = str(uuid.uuid4())
        invite_link = f"https://t.me/{context.bot.username}?start={game_id}"

        # 发送第一条消息
        await update.message.reply_text(
            f"您已下注 {bet_amount} 游戏币，您的总得分是 {total_score}。\n\n"
            f"分享以下消息邀请对手："
        )

        # 发送第二条消息（可转发）
        invite_message = (
            f"@{user['username'] or 'Unknown'} 发起了一个{bet_amount}游戏币的挑战！\n"
            f"点击链接加入游戏：{invite_link}\n\n"
            f"快使用我的邀请码 {user['invite_code'] or 'Unknown'} 获取1000代币空投！！"
        )
        await update.message.reply_text(invite_message)

        context.bot_data.setdefault('pending_games', {})[game_id] = {
            'bet_amount': bet_amount,
            'creator_id': user['id'],
            'creator_score': total_score
        }

        del context.user_data['dice_count']
        del context.user_data['total_score']
        del context.user_data['bet_amount']
        context.user_data['game_state'] = 'waiting_for_opponent'

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    game_id = context.args[0]
    pending_game = context.bot_data.get('pending_games', {}).get(game_id)
    
    if not pending_game:
        await update.message.reply_text("这个游戏已经不存在或已经结束。")
        return

    joiner = get_user_by_telegram_id(str(update.message.from_user.id))
    if not joiner or joiner['balance'] < pending_game['bet_amount']:
        await update.message.reply_text("您的余额不足以加入这个游戏。")
        return

    context.user_data['joining_game'] = game_id
    context.user_data['dice_count'] = 0
    context.user_data['total_score'] = 0

    await update.message.reply_text(f"您正在加入一个 {pending_game['bet_amount']} 游戏币的游戏。请发送骰子表情来进行游戏。您需要发送3次骰子。")

async def handle_join_dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'joining_game' not in context.user_data:
        return

    dice_value = update.message.dice.value
    context.user_data['total_score'] = context.user_data.get('total_score', 0) + dice_value
    context.user_data['dice_count'] = context.user_data.get('dice_count', 0) + 1

    if context.user_data['dice_count'] < 3:
        await update.message.reply_text(f"您的第 {context.user_data['dice_count']} 次骰子点数为 {dice_value}。还需要再投 {3 - context.user_data['dice_count']} 次骰子。")
    else:
        game_id = context.user_data['joining_game']
        pending_game = context.bot_data['pending_games'][game_id]
        joiner_score = context.user_data['total_score']
        creator_score = pending_game['creator_score']
        bet_amount = pending_game['bet_amount']

        creator = get_user_by_telegram_id(str(pending_game['creator_id']))
        joiner = get_user_by_telegram_id(str(update.message.from_user.id))

        result_message = f"创建者 @{creator['username']} 得分：{creator_score}\n加入者 @{joiner['username']} 得分：{joiner_score}\n"

        if creator_score > joiner_score:
            winner = creator
            loser = joiner
        elif creator_score < joiner_score:
            winner = joiner
            loser = creator
        else:
            # 平局
            update_user_balance(str(creator['telegram_id']), 0)
            update_user_balance(str(joiner['telegram_id']), 0)
            result_message += "平局！双方收回下注金额。"
            await update.message.reply_text(result_message)
            await context.bot.send_message(chat_id=creator['telegram_id'], text=result_message)
            del context.bot_data['pending_games'][game_id]
            del context.user_data['joining_game']
            del context.user_data['dice_count']
            del context.user_data['total_score']
            return

        winnings = int(bet_amount * 1.9)  # 90% 的收益
        project_fee = int(bet_amount * 0.03)  # 3% 项目方收益
        inviter_fee = int(bet_amount * 0.07)  # 7% 邀请者收益

        update_user_balance(str(winner['telegram_id']), winnings - bet_amount)
        update_user_balance(str(loser['telegram_id']), -bet_amount)

        # 更新邀请者余额
        if winner['inviter_id']:
            update_user_balance(str(get_user_by_telegram_id(str(winner['inviter_id']))['telegram_id']), inviter_fee)

        result_message += f"赢家是：@{winner['username']}！\n"
        result_message += f"赢家获得：{winnings - bet_amount} 游戏币\n"
        result_message += f"输家失去：{bet_amount} 游戏币"

        await update.message.reply_text(result_message)
        await context.bot.send_message(chat_id=creator['telegram_id'], text=result_message)

        del context.bot_data['pending_games'][game_id]
        del context.user_data['joining_game']
        del context.user_data['dice_count']
        del context.user_data['total_score']

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    context.user_data['game_state'] = None
    await query.edit_message_text("游戏已取消。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'awaiting_invite_code' in context.user_data and context.user_data['awaiting_invite_code']:
        await handle_invite_code(update, context)
    elif 'game_state' in context.user_data and context.user_data['game_state'] == 'awaiting_bet':
        await process_bet(update, context)
    else:
        await update.message.reply_text("抱歉，我不理解这个命令。请使用菜单或 /start 命令来开始。")
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))
    application.add_handler(MessageHandler(filters.Dice.ALL & filters.ChatType.PRIVATE, handle_join_dice))

    application.run_polling()

if __name__ == '__main__':
    main()
