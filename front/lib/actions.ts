"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { COOKIE } from "./session.ts";

/** Sign out. A POST, not a link: a GET that changes state can be fired by any
 *  image tag on any page, which would let a stranger log you out for fun. */
export async function signOut() {
  (await cookies()).delete(COOKIE);
  redirect("/login");
}
