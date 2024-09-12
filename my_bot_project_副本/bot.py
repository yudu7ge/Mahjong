import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_user_by_telegram_id, create_user, get_user_by_invite_code
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 从环境变量获取令牌
BOT_TOKEN = os.getenv('BOT_TOKEN')

def main():
    # 确保令牌不为空
    if not BOT_TOKEN:
        raise ValueError("在 .env 文件中未找到 BOT_TOKEN")
    
    application = Application.builder().token(BOT_TOKEN).build()

# 读取环境变量
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')

# 生成唯一邀请码
def generate_invite_code():
    import uuid
    return str(uuid.uuid4())[:8]

# 创建主菜单
def create_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 1v1挖矿", callback_data='mining')],
        [InlineKeyboardButton("💰 充值/提现", callback_data='recharge')],
        [InlineKeyboardButton("📊 代币数据", callback_data='token_data')],
        [InlineKeyboardButton("🔗 邀约收益", callback_data='referral')],
        [InlineKeyboardButton("❓ 如何赚钱", callback_data='how_to_earn')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 注册命令处理
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.message.from_user.id
    user = get_user_by_telegram_id(telegram_id)
    
    if user:
        await update.message.reply_text(
            "您已经注册过了，可以开始游戏了！",
            reply_markup=create_main_menu()
        )
    else:
        await update.message.reply_text("请输入邀请码完成注册，注册后可获得1000空投游戏币：")

# 处理注册命令
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.message.from_user.id
    username = update.message.from_user.username
    
    if not context.args:
        await update.message.reply_text("请输入邀请码。用法: /register <邀请码>")
        return

    invite_code = context.args[0]
    inviter = get_user_by_invite_code(invite_code)
    
    if not inviter:
        await update.message.reply_text("邀请码无效，请重新输入。")
        return

    new_invite_code = generate_invite_code()
    create_user(telegram_id, username, new_invite_code, inviter[0])
    await update.message.reply_text(f"注册成功！您已通过 @{inviter[1]} 的邀请获得了1000游戏币。", reply_markup=create_main_menu())

# 处理按钮点击的回调
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # 根据按钮的 callback_data 处理不同的功能
    if query.data == 'mining':
        await query.edit_message_text(text="1v1挖矿功能开发中...")
    elif query.data == 'recharge':
        await query.edit_message_text(text="充值/提现功能开发中...")
    elif query.data == 'token_data':
        await query.edit_message_text(text="代币数据展示功能开发中...")
    elif query.data == 'referral':
        await query.edit_message_text(text="邀约收益功能开发中...")
    elif query.data == 'how_to_earn':
        await query.edit_message_text(text="如何赚钱功能开发中...")

# 主函数，启动 Telegram 机器人
def main() -> None:
    # 确保令牌不为空
    if not BOT_TOKEN:
        raise ValueError("在 .env 文件中未找到 BOT_TOKEN")
    
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()

if __name__ == '__main__':
    main()