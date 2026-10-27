const assetHosts = new Set([
  "cdn.jsdelivr.net",
  "unpkg.com",
  "cdnjs.cloudflare.com",
  "fonts.googleapis.com",
  "fonts.gstatic.com",
  "images.unsplash.com",
  "esm.sh",
  "cdn.tailwindcss.com",
]);

export function allowsRequest(origin, path, target, method, resourceType) {
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) return false;
  let url;
  try {
    url = new URL(target);
  } catch {
    return false;
  }
  if (["data:", "blob:"].includes(url.protocol)) return true;
  if (url.protocol !== "https:" || url.username || url.password || url.port)
    return false;
  if (url.origin === origin && url.pathname.startsWith(path)) return true;
  return (
    assetHosts.has(url.hostname) &&
    ["script", "stylesheet", "image", "font"].includes(resourceType)
  );
}
