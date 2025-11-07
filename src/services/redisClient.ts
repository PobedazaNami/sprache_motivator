import Redis, { RedisOptions } from 'ioredis';
import { config } from '../config/env';
import { logger } from './logger';

let redisClient: Redis | null = null;

export function createRedisClient(): Redis {
  if (redisClient) {
    return redisClient;
  }

  const options: RedisOptions = {
    lazyConnect: true,
    retryStrategy(times: number) {
      const delay = Math.min(times * 50, 2000);
      logger.warn(`Redis connection retry attempt ${times}, delay: ${delay}ms`);
      return delay;
    },
  };

  // Parse Redis URL and add password if provided
  if (config.REDIS_PASSWORD) {
    options.password = config.REDIS_PASSWORD;
  }

  redisClient = new Redis(config.REDIS_URL, options);

  redisClient.on('connect', () => {
    logger.info('Redis client connected');
  });

  redisClient.on('error', (err: Error) => {
    logger.error('Redis client error:', err);
  });

  redisClient.on('ready', () => {
    logger.info('Redis client ready');
  });

  return redisClient;
}

export async function connectRedis(): Promise<Redis> {
  const client = createRedisClient();
  
  try {
    await client.connect();
    logger.info('Successfully connected to Redis');
    return client;
  } catch (err) {
    logger.error('Failed to connect to Redis:', err);
    throw err;
  }
}

export function getRedisClient(): Redis {
  if (!redisClient) {
    throw new Error('Redis client not initialized. Call connectRedis() first.');
  }
  return redisClient;
}
