import { createBot, startBot } from './bot/telegram';
import { connectRedis } from './services/redisClient';
import { logger } from './services/logger';
import { config } from './config/env';

async function main(): Promise<void> {
  try {
    logger.info('Starting Sprache Motivator Bot...');
    logger.info(`Translation model: ${config.TRANSLATION_MODEL}`);
    logger.info(`Default interface language: ${config.DEFAULT_INTERFACE_LANG}`);

    // Initialize Redis connection
    await connectRedis();

    // Initialize bot
    const bot = createBot();

    // Register /ping command
    bot.command('ping', (ctx) => {
      logger.debug(`Ping command received from user ${ctx.from?.id || 'unknown'}`);
      void ctx.reply('pong');
    });

    // Start the bot
    await startBot();

    logger.info('Sprache Motivator Bot is running!');
  } catch (err) {
    logger.error('Failed to start bot:', err);
    process.exit(1);
  }
}

// Start the application
void main();
