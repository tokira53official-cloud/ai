# SiftNodes AI Discord Bot

Owner: NotRyxenYT (`1520903362667876523`)

This is a private Discord bot using a **local Ollama model**. It does not call a paid/external AI API, but it does need a model downloaded onto your machine. “Unlimited” panel allocations do not mean the physical node has infinite RAM/CPU/disk.

## 1. Install Python dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 2. Install and start Ollama (Ubuntu)

Install Ollama using its official installer instructions, then start the service. Once installed:

```bash
ollama pull qwen2.5:3b
ollama serve
```

If Ollama is already running as a system service, do not start a second `ollama serve` process. Test it in another terminal:

```bash
ollama run qwen2.5:3b
```

The default model is `qwen2.5:3b`. It is a modest local model; answer quality and speed depend on real server resources. You can change it with `OLLAMA_MODEL`.

## 3. Enable Discord settings

In the Discord Developer Portal for your bot:
- Enable **Message Content Intent**.
- Invite it with View Channels, Send Messages, Read Message History, and Use Application Commands (only if needed).

## 4. Set the token safely and run

Do not paste your bot token into public chats or commit it to GitHub.

```bash
export DISCORD_BOT_TOKEN='PASTE_YOUR_DISCORD_BOT_TOKEN_HERE'
python3 bot.py
```

Keep the process running using your hosting panel or a process manager. The bot is not configured to silently execute arbitrary shell commands.

## 5. Configure the AI channel

In your Discord server, run this command as the owner account:

```text
!ai setup 123456789012345678
```

Replace the example with the real text-channel ID. Enable Developer Mode in Discord and use Copy Channel ID.

After setup, messages in that channel are sent to the local model without a prefix. Other channels are ignored by the AI chat handler. Commands remain available with `!`.

Other commands:

```text
!ai status
!ai reset
!ai help
```

## Behavior and limitations

- The bot posts `🧠 SiftNodes AI is thinking...` while waiting, then edits that message into the answer.
- Conversation history is stored locally per user in `siftnodes_data/history/`.
- `!ai reset` clears history for the configured AI channel.
- The bot can generate code in replies. It does **not** yet create arbitrary downloadable HTML files, generate images, browse the web, or run generated code. Those need separate, sandboxed features and/or a local image model.
- It cannot display hidden chain-of-thought. The thinking message is a status indicator, not a transcript of private reasoning.
- Keep the bot token secret. If it is exposed, reset it in the Developer Portal.
