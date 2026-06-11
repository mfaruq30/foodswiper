// Locks the response-envelope contract the iOS APIClient will decode against.

import { assertEquals } from "@std/assert";
import { fail, ok } from "./http.ts";

Deno.test("ok() wraps the payload in the envelope with status 200", async () => {
  const res = ok({ hello: "munch" });

  assertEquals(res.status, 200);
  assertEquals(res.headers.get("content-type"), "application/json; charset=utf-8");
  assertEquals(await res.json(), { ok: true, data: { hello: "munch" }, error: null });
});

Deno.test("fail() carries the error code and HTTP status", async () => {
  const res = fail("validation_failed", 400);

  assertEquals(res.status, 400);
  assertEquals(await res.json(), { ok: false, data: null, error: "validation_failed" });
});
