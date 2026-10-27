import { redirect } from "next/navigation";

/** Swagger UI lives on the API; the public API origin may differ from the internal one. */
export function GET() {
  redirect(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/docs`);
}
