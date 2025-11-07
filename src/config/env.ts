import * as dotenv from 'dotenv';
import { logger } from '../services/logger';

// Load environment variables from .env file
dotenv.config();

interface EnvConfig {
  TELEGRAM_BOT_TOKEN: string;
  OPENAI_API_KEY: string;
  REDIS_URL: string;
  REDIS_PASSWORD: string;
  TRANSLATION_MODEL: string;
  DEFAULT_INTERFACE_LANG: string;
}

function validateEnv(): EnvConfig {
  const requiredVars = [
    'TELEGRAM_BOT_TOKEN',
    'OPENAI_API_KEY',
    'REDIS_URL',
  ];

  const missing: string[] = [];
  
  for (const varName of requiredVars) {
    if (!process.env[varName]) {
      missing.push(varName);
    }
  }

  if (missing.length > 0) {
    const errorMsg = `Missing required environment variables: ${missing.join(', ')}`;
    logger.error(errorMsg);
    throw new Error(errorMsg);
  }

  return {
    TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN as string,
    OPENAI_API_KEY: process.env.OPENAI_API_KEY as string,
    REDIS_URL: process.env.REDIS_URL as string,
    REDIS_PASSWORD: process.env.REDIS_PASSWORD || '',
    TRANSLATION_MODEL: process.env.TRANSLATION_MODEL || 'gpt-3.5-turbo',
    DEFAULT_INTERFACE_LANG: process.env.DEFAULT_INTERFACE_LANG || 'uk',
  };
}

export const config = validateEnv();
