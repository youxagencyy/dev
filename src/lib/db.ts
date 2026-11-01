import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export function getPrisma(): PrismaClient | null {
  if (!process.env.DATABASE_URL) return null;
  if (!globalForPrisma.prisma) {
    globalForPrisma.prisma = new PrismaClient();
  }
  return globalForPrisma.prisma;
}

export function requirePrisma(): PrismaClient {
  const prisma = getPrisma();
  if (!prisma) throw new Error("DATABASE_URL is not set");
  return prisma;
}
