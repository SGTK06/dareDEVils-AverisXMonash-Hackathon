const { spawn } = require("node:child_process");
const http = require("node:http");

const root = process.cwd();
const children = [];

function request(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (response) => {
      response.resume();
      resolve(response.statusCode >= 200 && response.statusCode < 500);
    });
    req.setTimeout(700, () => {
      req.destroy();
      resolve(false);
    });
    req.on("error", () => resolve(false));
  });
}

function run(name, command, args) {
  const child = spawn(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32"
  });
  children.push({ name, child });
  child.on("exit", (code) => {
    if (code && code !== 0) {
      console.error(`${name} exited with code ${code}`);
      stopAll(code);
    }
  });
}

function stopAll(code = 0) {
  for (const { child } of children) {
    if (!child.killed) child.kill();
  }
  process.exit(code);
}

async function main() {
  const apiReady = await request("http://127.0.0.1:8080/health");
  const webReady = await request("http://127.0.0.1:5173/");

  if (apiReady) {
    console.log("[API] Reusing healthy service at http://127.0.0.1:8080");
  } else {
    run("API", "npm", ["run", "dev:api"]);
  }

  if (webReady) {
    console.log("[WEB] Reusing frontend at http://127.0.0.1:5173");
  } else {
    run("WEB", "npm", ["run", "dev:web"]);
  }

  if (!children.length) {
    console.log("Both services are already running. Nothing to start.");
    return;
  }

  process.on("SIGINT", () => stopAll(0));
  process.on("SIGTERM", () => stopAll(0));
}

main().catch((error) => {
  console.error(error);
  stopAll(1);
});
