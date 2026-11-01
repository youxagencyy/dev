"use server";

import { Prisma } from "@prisma/client";
import { compare, hash } from "bcryptjs";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AuthError } from "next-auth";
import { auth, signIn, signOut } from "@/auth";
import { requirePrisma } from "@/lib/db";
import { safeNext } from "@/lib/paths";
import { THEME_COOKIE, parseTheme, themeCookie } from "@/lib/theme";

function field(formData: FormData, name: string): string {
  return String(formData.get(name) ?? "").trim();
}

export async function signupAction(formData: FormData) {
  const name = field(formData, "name").slice(0, 80);
  const email = field(formData, "email").toLowerCase();
  const password = String(formData.get("password") ?? "");
  const next = safeNext(field(formData, "next"));
  if (name.length < 2 || !email.includes("@") || password.length < 8) {
    redirect(`/reiestratsiia?error=fields&next=${encodeURIComponent(next)}`);
  }

  const prisma = requirePrisma();
  try {
    await prisma.user.create({
      data: {
        name,
        email,
        passwordHash: await hash(password, 10),
        role: "READER",
        theme: "SYSTEM",
        notificationPref: {
          create: {
            breaking: true,
            dailyBrief: true,
            emailEnabled: false,
            categories: ["UKRAINA", "VIINA", "POLITYKA", "SVIT"],
          },
        },
      },
    });
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      redirect(`/reiestratsiia?error=exists&next=${encodeURIComponent(next)}`);
    }
    throw error;
  }

  const jar = await cookies();
  jar.set(THEME_COOKIE, "SYSTEM", themeCookie);
  try {
    await signIn("credentials", { email, password, redirectTo: next });
  } catch (error) {
    if (error instanceof AuthError) {
      redirect(`/uviity?error=credentials&next=${encodeURIComponent(next)}`);
    }
    throw error;
  }
}

export async function loginAction(formData: FormData) {
  const email = field(formData, "email").toLowerCase();
  const password = String(formData.get("password") ?? "");
  const next = safeNext(field(formData, "next"));
  const prisma = requirePrisma();
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user?.passwordHash || !(await compare(password, user.passwordHash))) {
    redirect(`/uviity?error=credentials&next=${encodeURIComponent(next)}`);
  }

  const jar = await cookies();
  jar.set(THEME_COOKIE, parseTheme(user.theme), themeCookie);
  try {
    await signIn("credentials", { email, password, redirectTo: next });
  } catch (error) {
    if (error instanceof AuthError) {
      redirect(`/uviity?error=credentials&next=${encodeURIComponent(next)}`);
    }
    throw error;
  }
}

export async function logoutAction() {
  const session = await auth();
  if (!session?.user) redirect("/");
  const jar = await cookies();
  jar.delete(THEME_COOKIE);
  await signOut({ redirectTo: "/" });
}
