"use client";

import { createContext, useContext } from "react";

import { Profile } from "@/lib/types";

export const AuthContext = createContext<Profile | null>(null);

export function useAuth(): Profile {
  const profile = useContext(AuthContext);
  if (!profile) {
    throw new Error("useAuth() called outside of an authenticated route");
  }
  return profile;
}
