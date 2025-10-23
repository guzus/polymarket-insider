# 🤖 Polymarket Insider Telegram Bot Setup

## ✅ Status: BOT IS READY AND WORKING

### Bot Information
- **Bot Name**: polymarket_insider
- **Bot Username**: @polymarket_insiders_bot  
- **Bot ID**: 8427076253
- **Status**: ✅ Fully functional

### 🚀 Quick Start

#### Option 1: Test in Private Chat (Recommended)
1. **Message the bot directly**: Search for `@polymarket_insiders_bot` on Telegram
2. **Send `/start`** to see the welcome message
3. **Test commands**: `/help`, `/status`
4. The bot will respond immediately in your private chat

#### Option 2: Group Setup for "uncanny_guzus"
1. **Create a group** named "uncanny_guzus" (or your preferred name)
2. **Add the bot**: Search for `@polymarket_insiders_bot` and add it to the group
3. **Grant permissions**: Make sure the bot can send messages
4. **Update chat ID**: Run this script to get your group chat ID:
   ```bash
   python get_chat_id.py
   ```

### 🔧 Test Results
- ✅ Bot connection: Working
- ✅ Alert system: Working  
- ✅ Message formatting: Working
- ✅ Command handlers: Working
- ⚠️ Group messaging: Requires bot to be added to group

### 📱 Available Commands
- `/start` - Welcome message
- `/help` - Help information
- `/status` - Bot status and configuration

### 🚀 Run the Bot
```bash
# Activate virtual environment
source venv/bin/activate

# Start the bot
python run_bot.py
```

### 🔍 What the Bot Does
The bot monitors Polymarket for suspicious trading patterns and sends alerts for:
- Large trades from new wallets
- Wallets funded immediately before trading  
- Unusual trading patterns
- Manipulative activity detection

### 📞 Support
If you need any assistance, the bot is ready to respond to your messages!

---
**Setup completed successfully! 🎉**
