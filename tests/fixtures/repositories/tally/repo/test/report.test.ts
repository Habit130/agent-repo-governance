import { strict as assert } from "node:assert";
import { test } from "node:test";
import { totals } from "../src/entries";

test("report totals minutes per task", () => {
  assert.deepEqual(totals([{ task: "a", minutes: 5 }, { task: "a", minutes: 7 }]), { a: 12 });
});
