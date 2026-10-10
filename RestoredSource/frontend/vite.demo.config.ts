import { defineConfig, mergeConfig } from 'vite';
import path from 'path';
import base from './vite.config';

export default mergeConfig(base, defineConfig({
  build: {
    outDir: path.resolve(__dirname, '../../website/demo'),
    emptyOutDir: true,
    rollupOptions: { input: path.resolve(__dirname, 'demo.html') },
  },
}));
