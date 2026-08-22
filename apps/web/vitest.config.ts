import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const root = fileURLToPath(new URL(".", import.meta.url));
const app = fileURLToPath(new URL("./app", import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@/components/ui/Card": `${app}/components/ui/Card.tsx`,
      "@/components/ui/Badge": `${app}/components/ui/Badge.tsx`,
      "@/components/ui/Button": `${app}/components/ui/Button.tsx`,
      "@/components/ui/Tabs": `${app}/components/ui/Tabs.tsx`,
      "@/components/ui/Drawer": `${app}/components/ui/Drawer.tsx`,
      "@/components/ui/Dropdown": `${app}/components/ui/Dropdown.tsx`,
      "@/components/ui/Input": `${app}/components/ui/Input.tsx`,
      "@/components/ui/Modal": `${app}/components/ui/Modal.tsx`,
      "@/components/ui/Progress": `${app}/components/ui/Progress.tsx`,
      "@/components/ui/Switch": `${app}/components/ui/Switch.tsx`,
      "@/components/ui/Tabs": `${app}/components/ui/Tabs.tsx`,
      "@/components/ui/Tooltip": `${app}/components/ui/Tooltip.tsx`,
      "@/components/ui/Tooltip.tsx": `${app}/components/ui/Tooltip.tsx`,
      "@/components/ui/Switch": `${app}/components/ui/Switch.tsx`,
      "@/components/ui/Progress": `${app}/components/ui/Progress.tsx`,
      "@/components/ui/Input": `${app}/components/ui/Input.tsx`,
      "@/components/ui/Modal": `${app}/components/ui/Modal.tsx`,
      "@/components/ui/Dropdown": `${app}/components/ui/Dropdown.tsx`,
      "@/components/ui/Drawer": `${app}/components/ui/Drawer.tsx`,
      "@/components/ui/Card": `${app}/components/ui/Card.tsx`,
      "@/components/ui/Badge": `${app}/components/ui/Badge.tsx`,
      "@/components/ui/Button": `${app}/components/ui/Button.tsx`,
      "@/components/ui/Tabs": `${app}/components/ui/Tabs.tsx`,
      "@/components/ui": `${app}/components/ui`,
      "@/components/ui/": `${app}/components/ui/`,
      "@/components": `${app}/components`,
      "@/components/": `${app}/components/`,
      "@/hooks": `${app}/hooks`,
      "@/hooks/": `${app}/hooks/`,
      "@/lib": `${root}/lib`,
      "@/lib/": `${root}/lib/`,
      "@": root,
      "@/*": `${app}/*`,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["lib/**/*.test.ts", "lib/**/*.test.tsx", "app/**/*.test.ts", "app/**/*.test.tsx"],
    setupFiles: ["vitest.setup.ts"],
    server: {
      deps: {
        inline: ["lucide-react"],
      },
    },
  },
});