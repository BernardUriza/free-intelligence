import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Container Apps runs the image, not the repo. `standalone` emits a self-contained
  // server carrying only the node_modules it actually reached, so the runtime layer
  // stays small and `npm install` never happens on the box.
  output: "standalone",
};

export default nextConfig;
