import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { compare } from "bcryptjs";
import type { ThemeChoice } from "@/lib/theme";
import { getPrisma } from "@/lib/db";

declare module "next-auth" {
  interface User {
    role: "READER" | "ADMIN";
    theme: ThemeChoice;
  }

  interface Session {
    user: {
      id: string;
      role: "READER" | "ADMIN";
      theme: ThemeChoice;
    } & DefaultSession["user"];
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    id: string;
    role: "READER" | "ADMIN";
    theme: ThemeChoice;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  session: { strategy: "jwt", maxAge: 60 * 60 * 24 * 30 },
  pages: { signIn: "/uviity" },
  providers: [
    Credentials({
      credentials: {
        email: { label: "Ел. пошта" },
        password: { label: "Пароль" },
      },
      authorize: async (credentials) => {
        const email = String(credentials?.email ?? "").trim().toLowerCase();
        const password = String(credentials?.password ?? "");
        if (!email || !password) return null;
        const prisma = getPrisma();
        if (!prisma) return null;
        const user = await prisma.user.findUnique({ where: { email } });
        if (!user?.passwordHash) return null;
        const matches = await compare(password, user.passwordHash);
        if (!matches) return null;
        return {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
          theme: user.theme,
        };
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.id = user.id ?? "";
        token.role = user.role;
        token.theme = user.theme;
      }
      return token;
    },
    session({ session, token }) {
      session.user.id = token.id;
      session.user.role = token.role;
      session.user.theme = token.theme;
      return session;
    },
  },
});
