import { Telegraf } from 'telegraf';
import { config } from '../config/env';
import { logger } from '../services/logger';

let bot: Telegraf | null = null;

export function createBot(): Telegraf {
  if (bot) {
    return bot;
  }

  bot = new Telegraf(config.TELEGRAM_BOT_TOKEN);

  // Set up error handling
  bot.catch((err: unknown, ctx) => {
    logger.error('Bot error:', err);
    logger.error('Update:', ctx.update);
  });

  logger.info('Telegram bot initialized');
  
  return bot;
}

export function getBot(): Telegraf {
  if (!bot) {
    throw new Error('Bot not initialized. Call createBot() first.');
  }
  return bot;
}

export async function startBot(): Promise<void> {
  const botInstance = getBot();
  
  try {
    await botInstance.launch();
    logger.info('Bot launched successfully');
    
    // Enable graceful stop
    process.once('SIGINT', () => {
      logger.info('SIGINT received, stopping bot...');
      void botInstance.stop('SIGINT');
    });
    
    process.once('SIGTERM', () => {
      logger.info('SIGTERM received, stopping bot...');
      void botInstance.stop('SIGTERM');
    });
  } catch (err) {
    logger.error('Failed to launch bot:', err);
    throw err;
  }
}
