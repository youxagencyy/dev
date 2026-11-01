-- CreateEnum
CREATE TYPE "Theme" AS ENUM ('SYSTEM', 'LIGHT', 'DARK');

-- AlterTable
ALTER TABLE "User" ADD COLUMN     "feedCategories" "ArticleCategory"[] DEFAULT ARRAY['UKRAINA', 'VIINA', 'POLITYKA', 'SVIT']::"ArticleCategory"[],
ADD COLUMN     "passwordHash" TEXT,
ADD COLUMN     "theme" "Theme" NOT NULL DEFAULT 'SYSTEM';
