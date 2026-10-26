import { report, start, stop } from "./entries";
import { sync } from "./sync/client";

const [command, ...rest] = process.argv.slice(2);
const commands: Record<string, (args: string[]) => Promise<void>> = { start, stop, report, sync };

const run = commands[command];
if (!run) {
  console.error("usage: tally <start|stop|report|sync>");
  process.exit(2);
}
run(rest).catch((error) => {
  console.error(error.message);
  process.exit(1);
});
