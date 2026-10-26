import { readSession, writeSession } from "../store";

// Stores and refreshes the sync API session. The token comes from the sign-in flow and is
// kept only in the user's local session file, never in the repository.
export async function currentToken(refresh: (old: string) => Promise<string>): Promise<string> {
  const session = await readSession();
  if (session.expiresAt > Date.now()) {
    return session.token;
  }
  const token = await refresh(session.refreshToken);
  await writeSession({ ...session, token, expiresAt: Date.now() + 3600_000 });
  return token;
}
