import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { PrismaClient } = require("@prisma/client");
const { hash } = require("bcryptjs");

const email = String(process.env.ADMIN_EMAIL ?? "").trim().toLowerCase();
const password = String(process.env.ADMIN_PASSWORD ?? "");
const name = String(process.env.ADMIN_NAME ?? "Редактор").trim() || "Редактор";

if (!email.includes("@") || password.length < 8) {
  console.error("Set ADMIN_EMAIL and ADMIN_PASSWORD (8+ characters).");
  process.exit(1);
}

const prisma = new PrismaClient();
const passwordHash = await hash(password, 10);
await prisma.user.upsert({
  where: { email },
  update: { name, passwordHash, role: "ADMIN" },
  create: {
    email,
    name,
    passwordHash,
    role: "ADMIN",
    theme: "SYSTEM",
  },
});
console.log(`admin ready: ${email}`);
await prisma.$disconnect();
