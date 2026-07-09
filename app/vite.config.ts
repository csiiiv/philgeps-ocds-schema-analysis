import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
// Use demo data for webapp (fast, lightweight, exploratory use)
const browserCacheDir = path.join(repoRoot, "references", "transformed", "demo_by_year", "browser");
const yearDqCacheDir = path.join(repoRoot, "references", "transformed", "demo_by_year", "dq");
const byYearDir = path.join(repoRoot, "references", "transformed", "demo_by_year");
// Full dataset available on Google Drive for complete analysis
const MAX_ON_DEMAND_PACKAGE_MB = 250;

const ALLOWED_CORS_ORIGINS = new Set([
  "https://ocdsphilgeps.simple-systems.dev",
]);

function applyCors(
  req: import("http").IncomingMessage,
  res: import("http").ServerResponse,
): boolean {
  const origin = req.headers.origin;
  if (origin && ALLOWED_CORS_ORIGINS.has(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  }
  if (req.method === "OPTIONS") {
    res.statusCode = origin && ALLOWED_CORS_ORIGINS.has(origin) ? 204 : 403;
    res.end();
    return true;
  }
  return false;
}

function readJsonFile(filePath: string): unknown {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function findReleaseInYearPackage(year: string, ocid: string): Record<string, unknown> | null {
  const browserPath = path.join(browserCacheDir, `${year}.json`);
  if (fs.existsSync(browserPath)) {
    const cache = readJsonFile(browserPath) as {
      releases?: Record<string, Record<string, unknown>>;
    };
    const cached = cache.releases?.[ocid];
    if (cached) return cached;
  }

  const pkgPath = path.join(byYearDir, `${year}.json`);
  if (!fs.existsSync(pkgPath)) return null;

  const sizeMb = fs.statSync(pkgPath).size / 1e6;
  if (sizeMb > MAX_ON_DEMAND_PACKAGE_MB) {
    throw new Error(`Year package is ${sizeMb.toFixed(0)} MB; on-demand release fetch is capped at ${MAX_ON_DEMAND_PACKAGE_MB} MB`);
  }

  const pkg = readJsonFile(pkgPath) as { releases?: Record<string, unknown>[] };
  const releases = pkg.releases;
  if (!Array.isArray(releases)) return null;
  const match = releases.find((release) => release?.ocid === ocid);
  return (match as Record<string, unknown> | undefined) ?? null;
}

function serveReleaseBrowserCache(): Plugin {
  return {
    name: "serve-release-browser-cache",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith("/data")) {
          next();
          return;
        }
        if (applyCors(req, res)) return;
        next();
      });

      server.middlewares.use("/data/release", (req, res, next) => {
        const raw = req.url?.split("?")[0] ?? "";
        const match = raw.match(/^\/(\d{4})\/([^/]+)\.json$/);
        if (!match) {
          next();
          return;
        }
        const year = match[1];
        const ocid = decodeURIComponent(match[2]);
        if (!year || !ocid || ocid.includes("..")) {
          res.statusCode = 400;
          res.end(JSON.stringify({ error: "Invalid release path" }));
          return;
        }
        try {
          const release = findReleaseInYearPackage(year, ocid);
          if (!release) {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: "Release not found", year, ocid }));
            return;
          }
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify(release));
        } catch (err) {
          res.statusCode = 503;
          res.end(
            JSON.stringify({
              error: err instanceof Error ? err.message : "Failed to load release",
              year,
              ocid,
            }),
          );
        }
      });

      server.middlewares.use("/data/releases", (req, res, next) => {
        const raw = req.url?.split("?")[0] ?? "";
        const name = path.basename(decodeURIComponent(raw));
        if (!name.endsWith(".json") || name.includes("..")) {
          next();
          return;
        }
        const filePath = path.join(browserCacheDir, name);
        if (!filePath.startsWith(browserCacheDir) || !fs.existsSync(filePath)) {
          res.statusCode = 404;
          res.end(JSON.stringify({ error: "Year cache not found", year: name.replace(/\.json$/, "") }));
          return;
        }
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        fs.createReadStream(filePath).pipe(res);
      });

      server.middlewares.use("/data/dq", (req, res, next) => {
        const raw = req.url?.split("?")[0] ?? "";
        const name = path.basename(decodeURIComponent(raw));
        if (!name.endsWith(".json") || name.includes("..")) {
          next();
          return;
        }
        const filePath = path.join(yearDqCacheDir, name);
        if (!filePath.startsWith(yearDqCacheDir) || !fs.existsSync(filePath)) {
          res.statusCode = 404;
          res.end(JSON.stringify({ error: "Year DQ cache not found", year: name.replace(/\.json$/, "") }));
          return;
        }
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        fs.createReadStream(filePath).pipe(res);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveReleaseBrowserCache()],
  server: {
    port: 5173,
    open: true,
    allowedHosts: ["ocdsphilgeps.simple-systems.dev", "localhost"],
    cors: {
      origin: [...ALLOWED_CORS_ORIGINS],
    },
    fs: {
      allow: [repoRoot],
    },
  },
});
